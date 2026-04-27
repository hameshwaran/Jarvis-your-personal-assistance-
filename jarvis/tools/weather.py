"""
===========================================================
J.A.R.V.I.S. — Weather Tool
===========================================================
Open-Meteo API (free, no key needed).
Auto-detect location via ip-api.com.
===========================================================
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("jarvis.tools.weather")


class WeatherTool:
    """Get weather information using Open-Meteo (free, no API key)."""

    def __init__(self, memory=None):
        self.memory = memory
        self._default_lat = None
        self._default_lon = None
        self._default_city = None

    def execute(self, params: dict) -> str:
        """
        Get weather for a location.
        
        Params:
            location (str): City name (optional — auto-detect if empty)
        """
        location = params.get("location", "")

        try:
            # Geocode the location
            lat, lon, city = self._get_coordinates(location)
            if lat is None:
                return "I couldn't determine the location, Sir."

            # Fetch weather
            weather = self._fetch_weather(lat, lon)
            if not weather:
                return "Weather data is temporarily unavailable, Sir."

            return self._format_weather(weather, city)

        except Exception as e:
            logger.error(f"Weather tool failed: {e}")
            return f"Weather service error, Sir: {str(e)}"

    def _get_coordinates(self, location: str) -> tuple:
        """Get latitude, longitude, and city name for a location."""
        if location:
            return self._geocode(location)
        
        # Auto-detect from IP
        if self._default_lat is not None:
            return self._default_lat, self._default_lon, self._default_city

        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5)
            data = resp.json()
            self._default_lat = data.get("lat")
            self._default_lon = data.get("lon")
            self._default_city = data.get("city", "your location")
            return self._default_lat, self._default_lon, self._default_city
        except Exception as e:
            logger.error(f"IP geolocation failed: {e}")
            # Fallback to config default
            from jarvis.config import DEFAULT_LOCATION
            if DEFAULT_LOCATION:
                return self._geocode(DEFAULT_LOCATION)
            return None, None, None

    def _geocode(self, location: str) -> tuple:
        """Geocode a location name using Nominatim (OpenStreetMap)."""
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": location, "format": "json", "limit": 1},
                headers={"User-Agent": "JARVIS-AI/1.0"},
                timeout=5
            )
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", location).split(",")[0]
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
        return None, None, None

    def _fetch_weather(self, lat: float, lon: float) -> Optional[dict]:
        """Fetch weather data from Open-Meteo API."""
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True,
                    "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,uv_index",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,sunrise,sunset",
                    "timezone": "auto",
                    "forecast_days": 2,
                },
                timeout=10
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Open-Meteo API failed: {e}")
            return None

    def _format_weather(self, data: dict, city: str) -> str:
        """Format weather data into a readable report."""
        current = data.get("current_weather", {})
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        temp = current.get("temperature", "N/A")
        wind = current.get("windspeed", "N/A")
        wmo = current.get("weathercode", 0)
        condition = self._wmo_to_text(wmo)

        lines = [f"Weather in {city}:"]
        lines.append(f"  Current: {temp}°C, {condition}")
        lines.append(f"  Wind: {wind} km/h")

        # Today's highs/lows
        if daily.get("temperature_2m_max"):
            high = daily["temperature_2m_max"][0]
            low = daily["temperature_2m_min"][0]
            lines.append(f"  Today: High {high}°C / Low {low}°C")

        # Rain probability
        if hourly.get("precipitation_probability"):
            max_rain = max(hourly["precipitation_probability"][:24])
            lines.append(f"  Rain probability: {max_rain}%")

        # UV index
        if hourly.get("uv_index"):
            max_uv = max(hourly["uv_index"][:24])
            lines.append(f"  UV Index: {max_uv}")

        # Humidity
        if hourly.get("relative_humidity_2m"):
            humidity = hourly["relative_humidity_2m"][0]
            lines.append(f"  Humidity: {humidity}%")

        # Tomorrow forecast
        if daily.get("temperature_2m_max") and len(daily["temperature_2m_max"]) > 1:
            tmrw_high = daily["temperature_2m_max"][1]
            tmrw_low = daily["temperature_2m_min"][1]
            tmrw_rain = daily.get("precipitation_sum", [0, 0])[1]
            lines.append(f"  Tomorrow: {tmrw_high}°C / {tmrw_low}°C, Rain: {tmrw_rain}mm")

        return "\n".join(lines)

    @staticmethod
    def _wmo_to_text(code: int) -> str:
        """Convert WMO weather code to human-readable text."""
        wmo_map = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
            3: "Overcast", 45: "Foggy", 48: "Rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains", 80: "Slight showers", 81: "Moderate showers",
            82: "Violent showers", 85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
        }
        return wmo_map.get(code, "Unknown")
