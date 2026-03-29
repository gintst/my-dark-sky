# Welcome to My Dark Sky
***

## Task
Build a modern weather application in Python with Flask that recreates the spirit of Dark Sky. The app must support:

- current weather for a location
- weather by search
- weather from the browser's current location
- forecast on a selected date
- moving forward into forecast data
- moving backward into historical weather
- a cache layer that stores weather lookups for 5 minutes

The core challenge is to create a polished user-facing product, not just an API wrapper. The app has to combine geolocation, location search, time-based weather lookup, cache management, and a beautiful interface in one cohesive Flask application.

## Description
This project is implemented as a Flask application backed by the Open-Meteo APIs.

Main technical choices:

- `Flask` for routing and server rendering
- `Bootstrap 5` plus custom CSS for a polished UI
- `requests` for server-side API calls
- a local JSON cache file stored under `instance/weather_cache.json`
- Open-Meteo geocoding, forecast, and archive APIs for search, future forecast, and historical weather

Application behavior:

- the user can search for a city or place name
- the browser can provide the user's current coordinates through geolocation
- the user can choose a date and move backward or forward day by day
- future dates are served from the forecast API
- past dates are served from the archive API
- repeated identical requests are served from cache for 5 minutes

## Installation
Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
Run the Flask application locally:

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The project URL file required by the assignment is:

- `my_dark_sky_url.txt`

Current project structure:

- `app.py`
- `services/cache.py`
- `services/open_meteo.py`
- `templates/`
- `static/`
- `my_dark_sky_url.txt`

## API Notes
The implementation uses Open-Meteo because it supports both forecast and historical weather without requiring an API key.

Relevant official documentation used:

- Forecast API: https://open-meteo.com/en/docs
- Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Geocoding API: https://open-meteo.com/en/docs/geocoding-api

## Cache
Weather responses are cached locally for 5 minutes. The cache key is based on the full request URL and parameters, so identical requests within the TTL reuse stored JSON instead of making another upstream call.

## Deployment
Replace the placeholder in `my_dark_sky_url.txt` with the deployed public application URL after hosting the app on a cloud platform.

### The Core Team

The core team consists of Gints Turlajs and Gints Turlajs aka The Dream Team.

<span><i>Made at <a href='https://qwasar.io'>Qwasar SV -- Software Engineering School</a></i></span>
<span><img alt='Qwasar SV -- Software Engineering School's Logo' src='https://storage.googleapis.com/qwasar-public/qwasar-logo_50x50.png' width='20px' /></span>
