from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, redirect, render_template, request, url_for

from services.cache import JsonCache
from services.open_meteo import OpenMeteoClient, WeatherServiceError


BASE_DIR = Path(__file__).resolve().parent
CACHE_PATH = BASE_DIR / "instance" / "weather_cache.json"

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

cache = JsonCache(CACHE_PATH, ttl_seconds=300)
weather_client = OpenMeteoClient(cache=cache)


WMO_LABELS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}

WMO_ICONS = {
    0: "☀",
    1: "🌤",
    2: "⛅",
    3: "☁",
    45: "🌫",
    48: "🌫",
    51: "🌦",
    53: "🌦",
    55: "🌧",
    56: "🌨",
    57: "🌨",
    61: "🌧",
    63: "🌧",
    65: "⛈",
    66: "🌨",
    67: "🌨",
    71: "🌨",
    73: "❄",
    75: "❄",
    77: "❄",
    80: "🌦",
    81: "🌧",
    82: "⛈",
    85: "🌨",
    86: "❄",
    95: "⛈",
    96: "⛈",
    99: "⛈",
}


def parse_target_date(raw_value: str | None) -> date:
    if not raw_value:
        return date.today()
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def describe_weather_code(code: int | None) -> str:
    if code is None:
        return "Unknown conditions"
    return WMO_LABELS.get(code, "Unknown conditions")


def weather_icon(code: int | None) -> str:
    if code is None:
        return "•"
    return WMO_ICONS.get(code, "•")


def format_location_label(name: str | None, latitude: float, longitude: float) -> str:
    if name:
        return name
    return f"My location ({latitude:.2f}, {longitude:.2f})"


@app.template_filter("weather_label")
def weather_label_filter(code: int | None) -> str:
    return describe_weather_code(code)


@app.template_filter("weather_icon")
def weather_icon_filter(code: int | None) -> str:
    return weather_icon(code)


@app.route("/")
def index() -> str:
    raw_query = request.args.get("q", "").strip()
    raw_lat = request.args.get("lat")
    raw_lon = request.args.get("lon")
    location_name = request.args.get("name", "").strip()
    error_message = None
    search_results: list[dict[str, Any]] = []
    weather = None
    selected_date = parse_target_date(request.args.get("date"))
    selected_date_str = selected_date.isoformat()
    previous_date = (selected_date - timedelta(days=1)).isoformat()
    next_date = (selected_date + timedelta(days=1)).isoformat()
    can_view_future = selected_date < (date.today() + timedelta(days=15))

    latitude = None
    longitude = None

    if raw_query and not (raw_lat and raw_lon):
        try:
            search_results = weather_client.search_locations(raw_query)
            if len(search_results) == 1:
                result = search_results[0]
                return redirect(
                    url_for(
                        "index",
                        lat=result["latitude"],
                        lon=result["longitude"],
                        name=result["display_name"],
                        date=selected_date_str,
                    )
                )
        except WeatherServiceError as exc:
            error_message = str(exc)

    if raw_lat and raw_lon:
        try:
            latitude = float(raw_lat)
            longitude = float(raw_lon)
            weather = weather_client.fetch_weather(latitude, longitude, selected_date)
            if not location_name:
                location_name = format_location_label(None, latitude, longitude)
        except ValueError:
            error_message = "Coordinates must be valid numbers."
        except WeatherServiceError as exc:
            error_message = str(exc)

    return render_template(
        "index.html",
        today=date.today().isoformat(),
        selected_date=selected_date_str,
        previous_date=previous_date,
        next_date=next_date,
        can_view_future=can_view_future,
        query=raw_query,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        search_results=search_results,
        weather=weather,
        error_message=error_message,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
