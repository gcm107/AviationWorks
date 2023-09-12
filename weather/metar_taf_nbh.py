# Correcting the indentation and finalizing the file creation process
import pandas as pd
import avwx 
from datetime import datetime

def fetch_and_save_airport_data_final(airport_codes):
    metar_taf_data = []
    nbh_data_list = []

    for airport_code in airport_codes:
        airport_data_metar_taf = {"Airport Code": airport_code}
        airport_data_nbh = {"Airport Code": airport_code}

        # Fetch METAR data
        metar = avwx.Metar(airport_code)
        if metar.update():
            airport_data_metar_taf.update({
                "Station Name": metar.station.name,
                "METAR": metar.raw,
                "Summary": metar.summary,
                "Flight Rules": metar.data.flight_rules
            })

            # Decide weather condition
            if metar.data.flight_rules == "VFR":
                condition = "Good"
            else:
                condition = "Bad"
            airport_data_metar_taf["Condition"] = condition
        else:
            airport_data_metar_taf["Summary"] = "Failed to fetch METAR data"

        # Fetch TAF data
        taf = avwx.Taf(airport_code)
        if taf.update():
            airport_data_metar_taf["TAF"] = taf.raw
        else:
            airport_data_metar_taf["TAF"] = "Failed to fetch TAF data"

        # Fetch NBH data
        nbh = avwx.Nbh(airport_code)
        if nbh.update():
            # Extracting all the specified fields for NBH
            nbh_data_values = {
                "Temperature (°C)": [period.temperature.value if period.temperature else None for period in nbh.data.forecast],
                "Wind Speed (knots)": [period.wind_speed.value if period.wind_speed else None for period in nbh.data.forecast],
                "Visibility (miles)": [period.visibility.value if period.visibility else None for period in nbh.data.forecast],
                "Ceiling": [period.ceiling.value if period.ceiling else None for period in nbh.data.forecast],
                "Cloud Base": [period.cloud_base.value if period.cloud_base else None for period in nbh.data.forecast],
                "Dewpoint": [period.dewpoint.value if period.dewpoint else None for period in nbh.data.forecast],
                "Freezing Precip": [period.freezing_precip.value if period.freezing_precip else None for period in nbh.data.forecast],
                "Haines": [period.haines.value if period.haines else None for period in nbh.data.forecast],
                "Icing Amount 1": [period.icing_amount_1.value if period.icing_amount_1 else None for period in nbh.data.forecast],
                "Mixing Height": [period.mixing_height.value if period.mixing_height else None for period in nbh.data.forecast],
                "Precip Amount 1": [period.precip_amount_1.value if period.precip_amount_1 else None for period in nbh.data.forecast],
                "Precip Chance 1": [period.precip_chance_1.value if period.precip_chance_1 else None for period in nbh.data.forecast],
                "Precip Chance 6": [period.precip_chance_6.value if period.precip_chance_6 else None for period in nbh.data.forecast],
                "Precip Duration": [period.precip_duration.value if period.precip_duration else None for period in nbh.data.forecast],
                "Rain": [period.rain.value if period.rain else None for period in nbh.data.forecast],
                "Sky Cover": [period.sky_cover.value if period.sky_cover else None for period in nbh.data.forecast],
                "Sleet": [period.sleet.value if period.sleet else None for period in nbh.data.forecast],
                "Snow Amount 1": [period.snow_amount_1.value if period.snow_amount_1 else None for period in nbh.data.forecast],
                "Snow Level": [period.snow_level.value if period.snow_level else None for period in nbh.data.forecast],
                "Snow": [period.snow.value if period.snow else None for period in nbh.data.forecast],
                "Solar Radiation": [period.solar_radiation.value if period.solar_radiation else None for period in nbh.data.forecast],
                "Thunderstorm 1": [period.thunderstorm_1.value if period.thunderstorm_1 else None for period in nbh.data.forecast],
                "Transport Wind Direction": [period.transport_wind_direction.value if period.transport_wind_direction else None for period in nbh.data.forecast],
                "Transport Wind Speed": [period.transport_wind_speed.value if period.transport_wind_speed else None for period in nbh.data.forecast],
                "Wave Height": [period.wave_height.value if period.wave_height else None for period in nbh.data.forecast],
                "Wind Direction": [period.wind_direction.value if period.wind_direction else None for period in nbh.data.forecast],
                "Wind Gust": [period.wind_gust.value if period.wind_gust else None for period in nbh.data.forecast]
            }
            airport_data_nbh.update(nbh_data_values)
        
        else:
            airport_data_nbh["Error"] = "Failed to fetch NBH data"

        metar_taf_data.append(airport_data_metar_taf)
        nbh_data_list.append(airport_data_nbh)

    # Convert to DataFrames for easy saving
    df_metar_taf = pd.DataFrame(metar_taf_data)
    df_nbh = pd.DataFrame(nbh_data_list)

    # Current date and time for filenames
    current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save to HTML with current date and time in the filename
    html_filename = f'airport_data_{current_datetime}.html'
    with open(html_filename, 'w') as f:
        f.write(df_metar_taf.to_html(index=False))
        f.write("<br><br>")  # Separate the tables
        f.write(df_nbh.to_html(index=False))

    # Save to Excel with current date and time in the filename
    excel_filename = f'airport_data_{current_datetime}.xlsx'
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df_metar_taf.to_excel(writer, sheet_name='METAR_TAF', index=False)
        df_nbh.to_excel(writer, sheet_name='NBH', index=False)

    print(f"Data saved to '{html_filename}' and '{excel_filename}'")

if __name__ == "__main__":
    fetch_and_save_airport_data_final(['KHHR', 'KSBA', 'KSQL', 'KTRK'])