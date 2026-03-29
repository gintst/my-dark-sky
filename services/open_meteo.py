from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlencode

import requests

from services.cache import JsonCache


class WeatherServiceError(Exception):
    pass


class OpenMeteoClient:
    GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, cache: JsonCache) -> None:
        self.cache = cache

    def search_locations(self, query: str) -> list[dict[str, Any]]:
        payload = self._request_json(
            self.GEO_URL,
            {"name": query, "count": 6, "language": "en", "format": "json"},
        )
        results = payload.get("results") or []
        formatted = []
        for item in results:
            parts = [item.get("name"), item.get("admin1"), item.get("country")]
            display_name = ", ".join(part for part in parts if part)
            formatted.append(
                {
                    "display_name": display_name,
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "timezone": item.get("timezone", "auto"),
                }
            )
        return formatted

    def fetch_weather(self, latitude: float, longitude: float, target_date: date) -> dict[str, Any]:
        if target_date > date.today():
            day_delta = (target_date - date.today()).days
            if day_delta > 15:
                raise WeatherServiceError(
                    "Open-Meteo forecast data is limited to 16 days ahead. Choose a nearer future date."
                )
            return self._fetch_forecast_day(latitude, longitude, target_date, day_delta + 1)
        return self._fetch_archive_day(latitude, longitude, target_date)

    def _fetch_forecast_day(self, latitude: float, longitude: float, target_date: date, forecast_days: int) -> dict[str, Any]:
        payload = self._request_json(
            self.FORECAST_URL,
            self._forecast_params(latitude, longitude)
            | {
                "forecast_days": forecast_days,
                "current": ",".join(
                    [
                        "temperature_2m",
                        "apparent_temperature",
                        "relative_humidity_2m",
                        "precipitation",
                        "weather_code",
                        "wind_speed_10m",
                        "is_day",
                    ]
                ),
            },
        )
        return self._shape_weather_payload(payload, target_date, include_current=True)

    def _fetch_archive_day(self, latitude: float, longitude: float, target_date: date) -> dict[str, Any]:
        payload = self._request_json(
            self.ARCHIVE_URL,
            self._archive_params(latitude, longitude)
            | {
                "start_date": target_date.isoformat(),
                "end_date": target_date.isoformat(),
            },
        )
        return self._shape_weather_payload(payload, target_date, include_current=False)

    def _forecast_params(self, latitude: float, longitude: float) -> dict[str, Any]:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "auto",
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "apparent_temperature_max",
                    "apparent_temperature_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                    "sunrise",
                    "sunset",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                    "precipitation_probability",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
        }

    def _archive_params(self, latitude: float, longitude: float) -> dict[str, Any]:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "auto",
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "apparent_temperature_max",
                    "apparent_temperature_min",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                    "sunrise",
                    "sunset",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
        }

    def _shape_weather_payload(self, payload: dict[str, Any], target_date: date, include_current: bool) -> dict[str, Any]:
        daily = payload.get("daily") or {}
        daily_index = self._find_index(daily.get("time", []), target_date.isoformat())
        hourly = payload.get("hourly") or {}
        day_hours = []
        for index, hour in enumerate(hourly.get("time", [])):
            if not hour.startswith(target_date.isoformat()):
                continue
            day_hours.append(
                {
                    "time": hour[-5:],
                    "temperature": self._value(hourly, "temperature_2m", index),
                    "apparent_temperature": self._value(hourly, "apparent_temperature", index),
                    "humidity": self._value(hourly, "relative_humidity_2m", index),
                    "precipitation_probability": self._value(hourly, "precipitation_probability", index),
                    "precipitation": self._value(hourly, "precipitation", index),
                    "weather_code": self._value(hourly, "weather_code", index),
                    "wind_speed": self._value(hourly, "wind_speed_10m", index),
                }
            )

        midday_snapshot = day_hours[min(len(day_hours) // 2, len(day_hours) - 1)] if day_hours else None
        current = payload.get("current") if include_current else None
        hero_snapshot = current or midday_snapshot or {}

        return {
            "target_date": target_date.isoformat(),
            "timezone": payload.get("timezone", "auto"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "summary": {
                "weather_code": self._value(daily, "weather_code", daily_index),
                "temperature_max": self._value(daily, "temperature_2m_max", daily_index),
                "temperature_min": self._value(daily, "temperature_2m_min", daily_index),
                "apparent_temperature_max": self._value(daily, "apparent_temperature_max", daily_index),
                "apparent_temperature_min": self._value(daily, "apparent_temperature_min", daily_index),
                "precipitation_sum": self._value(daily, "precipitation_sum", daily_index),
                "precipitation_probability_max": self._value(daily, "precipitation_probability_max", daily_index),
                "wind_speed_max": self._value(daily, "wind_speed_10m_max", daily_index),
                "sunrise": self._trim_time(self._value(daily, "sunrise", daily_index)),
                "sunset": self._trim_time(self._value(daily, "sunset", daily_index)),
            },
            "current": {
                "temperature": hero_snapshot.get("temperature_2m") if current else hero_snapshot.get("temperature"),
                "apparent_temperature": hero_snapshot.get("apparent_temperature"),
                "humidity": hero_snapshot.get("relative_humidity_2m") if current else hero_snapshot.get("humidity"),
                "precipitation": hero_snapshot.get("precipitation"),
                "weather_code": hero_snapshot.get("weather_code"),
                "wind_speed": hero_snapshot.get("wind_speed_10m") if current else hero_snapshot.get("wind_speed"),
                "is_day": hero_snapshot.get("is_day"),
            },
            "hourly": day_hours,
        }

    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        cache_key = f"{url}?{urlencode(sorted(params.items()), doseq=True)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WeatherServiceError(
                "Weather data could not be retrieved right now. Check your connection and try again."
            ) from exc

        payload = response.json()
        self.cache.set(cache_key, payload)
        return payload

    @staticmethod
    def _find_index(values: list[str], target: str) -> int:
        try:
            return values.index(target)
        except ValueError:
            return 0

    @staticmethod
    def _value(bucket: dict[str, list[Any]], key: str, index: int) -> Any:
        values = bucket.get(key) or []
        if not values or index >= len(values):
            return None
        return values[index]

    @staticmethod
    def _trim_time(value: str | None) -> str | None:
        if not value:
            return None
        return value[-5:]
