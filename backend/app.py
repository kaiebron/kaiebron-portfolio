"""Scheduled Lambda: fetch a forecast from Open-Meteo and publish it as JSON to S3.

Triggered by EventBridge. The static site reads the file at /data/weather.json
through CloudFront, so the browser never calls the weather API directly and no
API key is exposed. Open-Meteo needs no key; to swap in a keyed API later, put
the key in SSM Parameter Store or Secrets Manager and read it here.
"""
import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API = "https://api.open-meteo.com/v1/forecast"
OBJECT_KEY = "data/weather.json"

# WMO weather interpretation codes -> short description
WMO = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail",
}


def describe(code):
    return WMO.get(int(code), "Unknown")


def build_url(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": 5,
    }
    return API + "?" + urllib.parse.urlencode(params)


def fetch_forecast(lat, lon, timeout=8):
    req = urllib.request.Request(build_url(lat, lon), headers={"User-Agent": "kaiebron-portfolio/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - fixed https URL
        return json.loads(resp.read().decode("utf-8"))


def normalize(raw, label, now=None):
    """Turn the API response into the small, stable shape the frontend renders."""
    cur = raw["current"]
    daily = raw["daily"]
    days = []
    for i, date in enumerate(daily["time"]):
        days.append({
            "date": date,
            "summary": describe(daily["weather_code"][i]),
            "high_f": daily["temperature_2m_max"][i],
            "low_f": daily["temperature_2m_min"][i],
            "rain_chance": daily["precipitation_probability_max"][i] or 0,
        })
    return {
        "location": label,
        "updated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "source": "Open-Meteo",
        "current": {
            "temp_f": cur["temperature_2m"],
            "feels_like_f": cur["apparent_temperature"],
            "humidity": cur["relative_humidity_2m"],
            "wind_mph": cur["wind_speed_10m"],
            "summary": describe(cur["weather_code"]),
        },
        "daily": days,
    }


def publish(payload, bucket, s3=None):
    if s3 is None:
        import boto3  # imported lazily so unit tests don't need AWS
        s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=OBJECT_KEY,
        Body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        ContentType="application/json",
        CacheControl="public, max-age=300",
    )


def handler(event, context):
    bucket = os.environ["SITE_BUCKET"]
    lat = os.environ.get("LATITUDE", "25.7617")
    lon = os.environ.get("LONGITUDE", "-80.1918")
    label = os.environ.get("LOCATION_LABEL", "Miami, FL")

    raw = fetch_forecast(lat, lon)
    payload = normalize(raw, label)
    publish(payload, bucket)
    logger.info("Published %s for %s", OBJECT_KEY, label)
    return {"ok": True, "location": label, "updated_at": payload["updated_at"]}
