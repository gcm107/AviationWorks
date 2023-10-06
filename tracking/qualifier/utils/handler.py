from opensky_api import OpenSkyApi
import pandas as pd
import logging
import os

# Load environment variables (assuming dotenv is used across the application)
from dotenv import load_dotenv
load_dotenv()

# Retrieve OpenSky credentials from environment variables
opensky_user = os.getenv('OPENSKY_USER')
opensky_api_key = os.getenv('OPENSKY_API_KEY')
api = OpenSkyApi(opensky_user, opensky_api_key)

# Set up logging (can be centralized or set up in the main app)
logging.basicConfig(filename='flight_tracker.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# CSV path (can be passed as an argument or centralized)
CSV_PATH = 'data/fdy_aircraft.csv'

def fetch_flight_data():
    """
    Fetch current states of all aircraft and filter for FDY callsigns.
    """
    states = api.get_states()
    if not states or not states.states:
        logging.error("Failed to retrieve states from OpenSky API.")
        return []

    # #xtract relevent aelements
    data = [{
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
    } for s in states.states if s.callsign and s.callsign.startswith('FDY')]

    return data


def update_icao_csv(data):
    """
    Update the CSV with any new ICAO24 codes.
    """
    if os.path.exists(CSV_PATH):
        existing_df = pd.read_csv(CSV_PATH)
    else:
        existing_df = pd.DataFrame(columns=['ICAO24', 'Tail Number', 'Mode S Code'])

    new_icao24 = set([entry['ICAO24'] for entry in data]) - set(existing_df['ICAO24'].tolist())
    new_icao24_df = pd.DataFrame({
        'ICAO24': list(new_icao24),
        'Tail Number': [''] * len(new_icao24),
        'Mode S Code': [''] * len(new_icao24)
    })
    
    updated_df = pd.concat([existing_df, new_icao24_df])
    updated_df.to_csv(CSV_PATH, index=False)

