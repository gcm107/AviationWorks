from flask import Flask, render_template, jsonify, request
import requests
import time
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import folium
from folium.plugins import HeatMap
from typing import Dict, List, Optional, Tuple
import threading

# load environment variables
load_dotenv()

# initialize flask app
app = Flask(__name__)

# configure logging
logging.basicConfig(
    filename='flight_tracker.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# opensky oauth2 endpoints and base url (per docs)
# see: https://openskynetwork.github.io/opensky-api/rest.html#all-state-vectors
OPENSKY_AUTH_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
OPENSKY_API_BASE = "https://opensky-network.org/api"

# token state (thread-safe)
access_token: Optional[str] = None
token_expires_at: float = 0
token_lock = threading.Lock()

# read creds from env
CLIENT_ID = os.getenv('OPENSKY_CLIENT_ID')
CLIENT_SECRET = os.getenv('OPENSKY_CLIENT_SECRET')

if not CLIENT_ID or not CLIENT_SECRET:
    logger.warning("missing OPENSKY_CLIENT_ID / OPENSKY_CLIENT_SECRET in .env; api calls will fail until configured")


def get_access_token() -> Optional[str]:
    """get a fresh access token using oauth2 client credentials; refresh slightly early."""
    global access_token, token_expires_at
    with token_lock:
        if access_token and time.time() < token_expires_at - 60:
            return access_token
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
            }
            resp = requests.post(OPENSKY_AUTH_URL, data=data, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            access_token = payload['access_token']
            token_expires_at = time.time() + payload.get('expires_in', 1800)
            logger.info("obtained opensky access token")
            return access_token
        except Exception as exc:
            logger.error(f"failed to obtain token: {exc}")
            return None


def make_opensky_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """make an authenticated request to the opensky api with one retry on 401."""
    token = get_access_token()
    if not token:
        return None
    headers = {'Authorization': f'Bearer {token}'}
    url = f"{OPENSKY_API_BASE}/{endpoint}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 401:
            # token likely expired; try once
            token = get_access_token()
            if not token:
                return None
            headers['Authorization'] = f'Bearer {token}'
            r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.error(f"api request failed: {exc}")
        return None


def fetch_live_track(icao24: str) -> List[Tuple[float, float]]:
    """fetch the live track for an aircraft (waypoints lat/lon) using time=0.
    note: opensky tracks are experimental and may be unavailable or rate-limited.
    """
    if not icao24:
        return []
    data = make_opensky_request('tracks/all', {'icao24': icao24, 'time': 0})
    if not data or 'path' not in data:
        return []
    coords: List[Tuple[float, float]] = []
    for wp in data.get('path', []):
        # wp: [time, lat, lon, baro_altitude, true_track, on_ground]
        lat, lon = wp[1], wp[2]
        if lat is not None and lon is not None:
            coords.append((lat, lon))
    return coords

def fetch_all_aircraft_states(bbox: Optional[Tuple[float, float, float, float]] = None) -> List[Dict]:
    """fetch live aircraft state vectors; optionally bound to a bbox."""
    params: Dict = {}
    if bbox:
        params = {'lamin': bbox[0], 'lomin': bbox[1], 'lamax': bbox[2], 'lomax': bbox[3]}
    resp = make_opensky_request('states/all', params)
    if not resp or 'states' not in resp:
        return []
    result: List[Dict] = []
    for s in resp['states']:
        if len(s) >= 17:
            result.append({
                'icao24': s[0],
                'callsign': (s[1] or '').strip() or 'N/A',
                'origin_country': s[2] or 'Unknown',
                'time_position': s[3],
                'last_contact': s[4],
                'longitude': s[5],
                'latitude': s[6],
                'baro_altitude': s[7],
                'on_ground': s[8],
                'velocity': s[9],
                'true_track': s[10],
                'vertical_rate': s[11],
                'sensors': s[12],
                'geo_altitude': s[13],
                'squawk': s[14],
                'spi': s[15],
                'position_source': s[16],
                'category': s[17] if len(s) > 17 else None,
            })
    logger.info(f"fetched {len(result)} aircraft")
    return result


def get_aircraft_category_name(category: Optional[int]) -> str:
    categories = {
        0: "No information", 1: "No ADS-B info", 2: "Light (< 15,500 lbs)", 3: "Small (15,500-75,000 lbs)",
        4: "Large (75,000-300,000 lbs)", 5: "High Vortex Large", 6: "Heavy (> 300,000 lbs)", 7: "High Performance",
        8: "Rotorcraft", 9: "Glider/Sailplane", 10: "Lighter-than-air", 11: "Parachutist/Skydiver", 12: "Ultralight",
        13: "Reserved", 14: "UAV/Drone", 15: "Space Vehicle", 16: "Emergency Vehicle", 17: "Service Vehicle",
        18: "Point Obstacle", 19: "Cluster Obstacle", 20: "Line Obstacle"
    }
    return categories.get(category, "Unknown")


def create_flight_map(
    aircraft: List[Dict],
    show_tracks: bool = False,
    track_limit: int = 20,
    track_icao24_whitelist: Optional[set] = None,
) -> str:
    """create folium map with individual markers, density heatmap, and optional tracks.
    - if track_icao24_whitelist is provided, draw tracks only for those icao24 values.
    - if show_tracks is true and whitelist is None, draw for up to track_limit flights.
    """
    center_lat, center_lon = 39.5, -98.35  # rough us centroid
    valid = [(a['latitude'], a['longitude']) for a in aircraft if a['latitude'] and a['longitude']]
    if valid:
        center_lat = sum(x for x, _ in valid) / len(valid)
        center_lon = sum(y for _, y in valid) / len(valid)

    # pick a darker map as default to fit the ui
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles='CartoDB Dark_Matter')
    folium.TileLayer('OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB Positron').add_to(m)

    flights_group = folium.FeatureGroup(name='Flights', show=True)
    heat_group = folium.FeatureGroup(name='Density Heatmap', show=True)
    tracks_group = folium.FeatureGroup(name='Tracks', show=False)

    for a in aircraft:
        if not a['latitude'] or not a['longitude']:
            continue
        status = "In Air" if not a['on_ground'] else "On Ground"
        icon_color = 'blue' if (not a['on_ground'] and (a['velocity'] or 0) > 100) else ('green' if not a['on_ground'] else 'gray')

        popup = f"""
        <div style="width: 250px;">
            <h4>{a['callsign']}</h4>
            <p><strong>ICAO24:</strong> {a['icao24']}</p>
            <p><strong>Country:</strong> {a['origin_country']}</p>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Category:</strong> {get_aircraft_category_name(a['category'])}</p>
            <p><strong>Altitude:</strong> {f"{a['baro_altitude']:.0f}m" if a['baro_altitude'] is not None else "N/A"}</p>
            <p><strong>Speed:</strong> {f"{a['velocity']:.0f} m/s" if a['velocity'] is not None else "N/A"}</p>
            <p><strong>Heading:</strong> {f"{a['true_track']:.0f}°" if a['true_track'] is not None else "N/A"}</p>
        </div>
        """

        # tiny plane-only marker using a divicon (no pin background)
        plane_char = '✈︎'
        color_map = {
            'blue': '#60a5fa',   # fast & in air
            'green': '#86efac',  # slow & in air
            'gray': '#9ca3af',   # on ground
        }
        plane_color = color_map.get(icon_color, '#60a5fa')
        # inject a click handler that calls a global function defined in the page js
        icon_html = (
            f"<div class=\"plane-marker\" data-icao=\"{a['icao24']}\" data-callsign=\"{a['callsign']}\" "
            f"onclick=\"if(window.__drawTrack) window.__drawTrack('{a['icao24']}')\" "
            f"style=\"font-size:11px;line-height:11px;color:{plane_color}; text-shadow:0 0 2px rgba(0,0,0,.8); cursor:pointer;\">"
            + plane_char + "</div>"
        )
        folium.Marker(
            [a['latitude'], a['longitude']],
            popup=folium.Popup(popup, max_width=300),
            icon=folium.DivIcon(html=icon_html, icon_size=(11,11), icon_anchor=(5,5), class_name=''),
            tooltip=f"{a['callsign']} - {status}"
        ).add_to(flights_group)

    # optionally draw live tracks (limit for responsiveness)
    if show_tracks:
        count = 0
        for a in aircraft:
            if track_icao24_whitelist is None and count >= max(0, track_limit):
                break
            if track_icao24_whitelist is not None and a['icao24'] not in track_icao24_whitelist:
                continue
            coords = fetch_live_track(a['icao24'])
            if len(coords) >= 2:
                folium.PolyLine(coords, color='#60a5fa', weight=2, opacity=0.6).add_to(tracks_group)
                count += 1

    # build heatmap data
    heat_points = [[a['latitude'], a['longitude'], 1] for a in aircraft if a['latitude'] and a['longitude']]
    if heat_points:
        HeatMap(heat_points, radius=18, blur=22, min_opacity=0.2, max_zoom=7).add_to(heat_group)

    flights_group.add_to(m)
    heat_group.add_to(m)
    if show_tracks:
        tracks_group.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m._repr_html_()


def filter_aircraft(aircraft: List[Dict], filters: Dict) -> List[Dict]:
    """filter aircraft on callsign/country/category/altitude/ground flags."""
    data = aircraft
    if filters.get('callsign_pattern'):
        pat = filters['callsign_pattern'].upper()
        data = [x for x in data if pat in (x['callsign'] or '').upper()]
    if filters.get('country'):
        data = [x for x in data if x['origin_country'] == filters['country']]
    if filters.get('category') is not None:
        data = [x for x in data if x['category'] == filters['category']]
    if filters.get('min_altitude') is not None:
        data = [x for x in data if x['baro_altitude'] is not None and x['baro_altitude'] >= filters['min_altitude']]
    if filters.get('max_altitude') is not None:
        data = [x for x in data if x['baro_altitude'] is not None and x['baro_altitude'] <= filters['max_altitude']]
    if filters.get('on_ground') is not None:
        data = [x for x in data if x['on_ground'] == filters['on_ground']]
    return data


@app.route('/')
def index():
    # serve the main ui
    return render_template('index.html')


@app.route('/api/aircraft')
def api_aircraft():
    # provide aircraft json (default to southwest flights for a friendly first view)
    filters = {
        'callsign_pattern': request.args.get('callsign') or 'EJA',
        'country': request.args.get('country'),
        'category': request.args.get('category', type=int),
        'min_altitude': request.args.get('min_alt', type=float),
        'max_altitude': request.args.get('max_alt', type=float),
        'on_ground': request.args.get('ground', type=lambda x: x.lower() == 'true' if x else None),
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    data = fetch_all_aircraft_states()
    if not data:
        return jsonify({'in_air': [], 'on_ground': [], 'total': 0, 'timestamp': datetime.now().isoformat()}), 200
    data = filter_aircraft(data, filters)
    return jsonify({
        'in_air': [x for x in data if not x['on_ground']],
        'on_ground': [x for x in data if x['on_ground']],
        'total': len(data),
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/map')
def api_map():
    # return folium map html matching same filters as /api/aircraft
    filters = {
        'callsign_pattern': request.args.get('callsign') or 'EJA',
        'country': request.args.get('country'),
        'category': request.args.get('category', type=int),
        'min_altitude': request.args.get('min_alt', type=float),
        'max_altitude': request.args.get('max_alt', type=float),
        'on_ground': request.args.get('ground', type=lambda x: x.lower() == 'true' if x else None),
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    data = fetch_all_aircraft_states()
    data = filter_aircraft(data, filters)
    if not data:
        return jsonify({'map_html': '<div style="padding:1rem;color:#666;">no aircraft match the current filters</div>'})
    # optional single or all tracks
    track_one = request.args.get('track_icao24')
    tracks_all = (request.args.get('tracks') == 'all')
    if track_one:
        return jsonify({'map_html': create_flight_map(data, show_tracks=True, track_icao24_whitelist={track_one})})
    if tracks_all:
        return jsonify({'map_html': create_flight_map(data, show_tracks=True)})
    return jsonify({'map_html': create_flight_map(data, show_tracks=False)})


@app.route('/api/track/<icao24>')
def api_track_single(icao24: str):
    # return a single aircraft polyline path for lightweight updates
    coords = fetch_live_track(icao24)
    return jsonify({'coords': coords})


@app.route('/api/tracks')
def api_tracks_bulk():
    # optional: draw tracks for all filtered flights (checkbox by map)
    filters = {
        'callsign_pattern': request.args.get('callsign') or 'EJA',
        'country': request.args.get('country'),
        'category': request.args.get('category', type=int),
        'min_altitude': request.args.get('min_alt', type=float),
        'max_altitude': request.args.get('max_alt', type=float),
        'on_ground': request.args.get('ground', type=lambda x: x.lower() == 'true' if x else None),
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    data = fetch_all_aircraft_states()
    data = filter_aircraft(data, filters)
    limit = request.args.get('track_limit', default=30, type=int)
    out = {}
    count = 0
    for a in data:
        if count >= max(0, limit):
            break
        coords = fetch_live_track(a['icao24'])
        if len(coords) >= 2:
            out[a['icao24']] = coords
            count += 1
    return jsonify(out)


if __name__ == '__main__':
    # local-only defaults: bind to localhost; honor PORT when set
    logger.info('starting flight tracker (local only)')
    _ = get_access_token()  # warm up once; failures will retry on request
    port = int(os.getenv('PORT', '5050'))
    host = os.getenv('HOST', '127.0.0.1')  # keep it local by default
    debug = (os.getenv('FLASK_DEBUG', '1') == '1')
    app.run(debug=debug, host=host, port=port)


