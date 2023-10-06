from flask import Flask, render_template
from opensky_api import OpenSkyApi, FlightTrack
import os.path
import pandas as pd
import folium
import sqlite3
import logging
from dotenv import load_dotenv
from folium.plugins import MarkerCluster
from flask import Flask, render_template
from qualifier.utils.handler import fetch_flight_data, update_icao_csv
# Load environment variables
load_dotenv()

opensky_user = os.getenv('OPENSKY_USER')
opensky_api_key = os.getenv('OPENSKY_API_KEY')
api = OpenSkyApi(opensky_user, opensky_api_key)

app = Flask(__name__)

logging.basicConfig(filename='flight_tracker.log', level=logging.INFO)

def log_flights_to_db(df):
    conn = sqlite3.connect('flight_tracker.db')
    cursor = conn.cursor()
    insert_stmt = """
    INSERT INTO flights (
        ICAO24, Callsign, "Origin Country", Latitude, Longitude, 
        "Baro Altitude", "Geo Altitude", Velocity, "True Track", "Vertical Rate",
        "On Ground", Category, "Last Contact", "Position Source", Sensors,
        SPI, Squawk, "Time Position"
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for _, row in df.iterrows():
        cursor.execute(insert_stmt, tuple(row))
    conn.commit()
    conn.close()

def add_track_to_map(m, track):
    coords = [(point[1], point[2]) for point in track.path]
    folium.PolyLine(coords, color='blue').add_to(m)
    folium.Marker([coords[-1][0], coords[-1][1]], popup=track.callsign).add_to(m)

@app.route('/')
def index():
    m = folium.Map(location=[40, -100], zoom_start=4)
    flight_data = fetch_flight_data()
    update_icao_csv(flight_data)
    df = pd.DataFrame(flight_data)
    print(df.columns)
    # Segment the flights based on the 'On Ground' status
    flights_in_air = df[df['On Ground'] == False].to_dict(orient='records')
    flights_on_ground = df[df['On Ground'] == True].to_dict(orient='records')

    log_flights_to_db(df)
    for icao24 in df['ICAO24']:
        track = api.get_track_by_aircraft(icao24)
        if track:
            add_track_to_map(m, track)
    
    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html, flights_in_air=flights_in_air, flights_on_ground=flights_on_ground)

if __name__ == '__main__':
    app.run(debug=True)