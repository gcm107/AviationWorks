# AviationWorks
An advanced software solution designed for real-time flight tracking and weather forecasting. It presents data in an intuitive and comprehensive manner suitable for industry stakeholders. Currently under development at AviationWork.

### Flask web-app (app.py)
![Screenshot 2023-10-05 at 4 36 39 PM](https://github.com/gcm107/AviationWorks/assets/60047556/64c37c04-086b-4666-90df-cb74a75dcbee)

#### Map of flight paths. (track.ipynb)
![flightpath](https://github.com/gcm107/AviationWorks/assets/60047556/98bae37b-c89e-4274-9c1d-2422024892fd)



## Installs
Required to run the code:
- Flight Tracking:
opensky
- Weather (you can use your own basemap, of course):
AVWX-Engine
- Basemap:
folium


```
pip install flask opensky-api pandas folium sqlite3 python-dotenv

```
If you get errors innstalling opensky-api, try it this way:
```
pip install https://github.com/openskynetwork/opensky-api/archive/master.zip#subdirectory=python
```

## Usage
1. First clone the repo. (AviationWorks/tracking)
2. In your terminal cd to the tracking folder (AviationWorks/tracking).
3. If you know the airline or flights you want to track, you can replace the filter in the get_fdy() to suit your needs.\
   Note: if there is no filter, all flights currently flying will be shown. (Not recommended)
4. Run the following in your terminal. If you 
   ```
   python3 app.py
   ```
5. Open your browser and navigate to your local host. (The server it is running on can be found in the .log file)


