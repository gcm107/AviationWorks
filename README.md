# AviationWorks (Local Flight Tracker)

local-only setup for a modern styled flight tracker

## prerequisites
- python 3.11 
- `.env` at project root with:
```
OPENSKY_CLIENT_ID=your_client_id_here
OPENSKY_CLIENT_SECRET=your_client_secret_here
```

## install
```
pip install -r requirements.txt
```

## run (local only)
```
export FLASK_DEBUG=1
export HOST=127.0.0.1
export PORT=5050
python app.py
```

open http://127.0.0.1:5050 and use the callsign box (defaults to `SWA`).

## notes
- Change the callsign filter as needed.

## data attribution
- live flight data is provided by the [OpenSky Network](https://opensky-network.org/).
- api docs referenced: [`states/all`](https://openskynetwork.github.io/opensky-api/rest.html#all-state-vectors) and related endpoints.
Designed for real-time flight tracking and weather forecasting. It presents data in an intuitive and comprehensive manner. Currently under development.

