import avwx

def fetch_airport_data(airport_codes):
    for airport_code in airport_codes:
        # Fetch METAR data
        metar = avwx.Metar(airport_code)
        if metar.update():
            print(f"METAR for {airport_code} ({metar.station.name}):")
            print(f"Raw METAR: {metar.raw}")
            print(f"Flight Rules: {metar.data.flight_rules}")
            print(f"Summary: {metar.summary}\n")
        else:
            print(f"Failed to fetch METAR data for {airport_code}\n")

        # Fetch TAF data
        taf = avwx.Taf(airport_code)
        if taf.update():
            print(f"TAF for {airport_code}:")
            print(f"Raw TAF: {taf.raw}")
            for line in taf.data.forecast:
                print(f"{line.flight_rules} from {line.start_time.dt.strftime('%d-%H:%M')} to {line.end_time.dt.strftime('%d-%H:%M')}")
            print("\n")
        else:
            print(f"Failed to fetch TAF data for {airport_code}\n")

# Example usage:
fetch_airport_data(['KHHR', 'KSBA', 'KSQL', 'KTRK'])