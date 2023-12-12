
import avwx
from avwx.forecast import *
import asyncio

# Function to Fetch Data
async def fetch_airport_data_async(airport_codes):
    airport_data = {}
    for airport_code in airport_codes:
        data = {}
        # Fetch METAR data
        metar = avwx.Metar(airport_code)
        if await metar.async_update():
            data["metar"] = {
                "raw": metar.raw,
                "flight_rules": metar.data.flight_rules,
                "summary": metar.summary, 
            }
        else:
            data["metar"] = None

        # Fetch TAF data
        taf = avwx.Taf(airport_code)
        if await taf.async_update():
            data["taf"] = {
                "raw": taf.raw,
                "forecast": [
                    {
                        "flight_rules": line.flight_rules,
                        "start_time": line.start_time.dt.strftime('%d-%H:%M'),
                        "end_time": line.end_time.dt.strftime('%d-%H:%M'),
                    }
                    for line in taf.data.forecast
                ],
            }
        else:
            data["taf"] = None
        
        airport_data[airport_code] = data
    return airport_data

# Function to Generate HTML
def generate_summary_html_safe(airports_data):
    # Styles
    styles = """
    <style>
        table {
            border-collapse: collapse;
            width: 80%;
            margin: 20px auto;
        }
        th, td {
            text-align: left;
            padding: 8px 12px;
            border: 1px solid #ddd;
        }
        tr:nth-child(even) {
            background-color: #f4f4f4;
        }
        th {
            background-color: #f2f2f2;
        }
        .airport-name {
            font-weight: bold;
            font-size: 1.5em;
            text-align: center;
            margin-top: 20px;
        }
        .section-header {
            font-weight: bold;
            margin-top: 40px;
            font-size: 1.3em;
            text-align: center;
        }
    </style>
    """
    
    # Rows
    metar_rows_html = ""
    taf_rows_html = ""
    for airport, data in airports_data.items():
        # METAR
        if data["metar"]:
            metar = data["metar"]["summary"].split(", ")
            metar_rows_html += f"<tr>"
            metar_rows_html += f"<td>{airport}</td>"
            metar_rows_html += f"<td>{data['metar']['flight_rules']}</td>"
            for item in metar:
                metar_rows_html += f"<td>{item}</td>"
            metar_rows_html += "</tr>"
        
        # TAF
        if data["taf"]:
            taf_rows_html += f"<tr>"
            taf_rows_html += f"<td>{airport}</td>"
            taf_forecast = ', '.join([f"{forecast['flight_rules']} from {forecast['start_time']} to {forecast['end_time']}" for forecast in data['taf']['forecast']])
            taf_rows_html += f"<td>{taf_forecast}</td>"
            taf_rows_html += "</tr>"

    # Complete HTML Structure
    html = f"""
    <html>
        <head>
            <title>Weather Summary</title>
            {styles}
        </head>
        <body>
            <div class='airport-name'>Weather Summary for {', '.join(airports_data.keys())}</div>
            <div class='section-header'>METAR</div>
            <table>
                <tr><th>Airport</th><th>Flight Rules</th><th>Wind</th><th>Visibility</th><th>Temperature</th><th>Dew Point</th><th>Pressure</th><th>Clouds</th><th>Conditions</th></tr>
                {metar_rows_html}
            </table>
            <div class='section-header'>TAF</div>
            <table>
                <tr><th>Airport</th><th>Forecast</th></tr>
                {taf_rows_html}
            </table>
        </body>
    </html>
    """
    return html

# Async Main Function to Drive the Process
async def main():
    airports = ['KHHR', 'KSBA', 'KSJC', 'KTRK']
    data = await fetch_airport_data_async(airports)
    html_output = generate_summary_html_safe(data)
    with open("weather_summary.html", "w") as file:
        file.write(html_output)

# Run the Main Function
if __name__ == "__main__":
    asyncio.run(main())
