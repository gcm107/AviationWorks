from flask import Flask, render_template
from opensky_api import OpenSkyApi, FlightTrack
import os.path
import pandas as pd
import folium
import sqlite3
import logging
from dotenv import load_dotenv
from folium.plugins import MarkerCluster

# Load environment variables
load_dotenv()

# Retrieve OpenSky credentials from environment variables
opensky_user = os.getenv('OPENSKY_USER')
opensky_api_key = os.getenv('OPENSKY_API_KEY')
api = OpenSkyApi(opensky_user, opensky_api_key)

app = Flask(__name__)

# Set up logging
logging.basicConfig(filename='flight_tracker.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_fdy():
    """Fetch current states of all aircraft and filter for FDY callsigns."""
    try:
        states = api.get_states()
        # Ensure that the 'states' object is not None
        if states is None or states.states is None:
            logging.error("Failed to retrieve states from OpenSky API.")
            return pd.DataFrame(), pd.DataFrame(), []

        data = []
        for s in states.states:
            data.append({
                "ICAO24": s.icao24,
                "Callsign": s.callsign,
                "Origin Country": s.origin_country,
                "Latitude": s.latitude,
                "Longitude": s.longitude,
                "Baro Altitude": s.baro_altitude,
                "Geo Altitude": s.geo_altitude,
                "Velocity": s.velocity,
                "True Track": s.true_track,
                "Vertical Rate": s.vertical_rate,
                "On Ground": s.on_ground,
                "Category": s.category,
                "Last Contact": s.last_contact,
                "Position Source": s.position_source,
                "Sensors": s.sensors,
                "SPI": s.spi,
                "Squawk": s.squawk,
                "Time Position": s.time_position
            })

        df = pd.DataFrame(data)
        df = df[df['Callsign'].str.startswith('FDY')]

        if os.path.isfile('icao24_codes.csv'):
            icao24_codes = pd.read_csv('icao24_codes.csv')
            new_data = df[['ICAO24', 'Callsign']].drop_duplicates()
            new_data = new_data[~new_data['ICAO24'].isin(icao24_codes['ICAO24'])]
            icao24_codes = pd.concat([icao24_codes, new_data]).reset_index(drop=True)
            icao24_codes_list = icao24_codes['ICAO24'].tolist()
        else:
            icao24_codes = df[['ICAO24', 'Callsign']].drop_duplicates().reset_index(drop=True)
            
        icao24_codes.to_csv('icao24_codes.csv', index=False)
        return df, icao24_codes, icao24_codes_list

    except Exception as e:
        logging.error(f"Error in get_fdy: {e}")
        # Return empty DataFrames and list in case of an error
        return pd.DataFrame(), pd.DataFrame(), []



def log_flights_to_db(df):
    """Log flights to an SQLite database."""
    try:
        conn = sqlite3.connect('flight_tracker.db')
        cursor = conn.cursor()

        # Prepare the insert statement
        insert_stmt = """
        INSERT INTO flights (
            ICAO24, Callsign, "Origin Country", Latitude, Longitude, 
            "Baro Altitude", "Geo Altitude", Velocity, "True Track", "Vertical Rate",
            "On Ground", Category, "Last Contact", "Position Source", Sensors,
            SPI, Squawk, "Time Position"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Insert each flight into the database
        for _, row in df.iterrows():
            cursor.execute(insert_stmt, tuple(row))

        conn.commit()  # Ensure changes are committed
        conn.close()
    except Exception as e:
        logging.error(f"Database error encountered: {e}")

def add_track_to_map(m, track):
    """Add flight track to the map."""
    if not hasattr(track, 'path') or track.path is None:
        return

    coords = [(point[1], point[2]) for point in track.path]
    folium.PolyLine(coords, color='blue').add_to(m)
    folium.Marker([coords[-1][0], coords[-1][1]], popup=track.callsign).add_to(m)

@app.route('/')
def index():
    """Main route for the Flask app."""
    m = folium.Map(location=[40, -100], zoom_start=4)
    try:
        df, icao24_codes, icao24_codes_list = get_fdy()
        log_flights_to_db(df)
        
        for icao24 in icao24_codes_list:
            track = api.get_track_by_aircraft(icao24)
            if track is not None:
                add_track_to_map(m, track)

        map_html = m._repr_html_()

        return render_template('index.html', map_html=map_html)

    except Exception as e:
        logging.error(f"Error encountered: {e}")
        print(f"Error encountered: {e}")
        return f"An error occurred: {e}"

if __name__ == '__main__':
    app.run(debug=True)
