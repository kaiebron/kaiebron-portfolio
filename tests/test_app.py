import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import app  # noqa: E402

RAW = {
    "current": {"temperature_2m": 82.4, "apparent_temperature": 89.1,
                "relative_humidity_2m": 71, "weather_code": 2, "wind_speed_10m": 9.3},
    "daily": {
        "time": ["2026-10-31", "2026-11-01"],
        "weather_code": [2, 95],
        "temperature_2m_max": [86.0, 84.5],
        "temperature_2m_min": [74.0, 73.2],
        "precipitation_probability_max": [20, None],
    },
}


def test_normalize_shape_and_values():
    now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    out = app.normalize(RAW, "Miami, FL", now=now)
    assert out["location"] == "Miami, FL"
    assert out["updated_at"].startswith("2026-10-31T12:00:00")
    assert out["current"]["summary"] == "Partly cloudy"
    assert out["daily"][1]["summary"] == "Thunderstorm"
    assert out["daily"][1]["rain_chance"] == 0  # None -> 0


def test_unknown_weather_code():
    assert app.describe(1234) == "Unknown"


def test_build_url_contains_coordinates_and_units():
    url = app.build_url("25.7617", "-80.1918")
    assert "latitude=25.7617" in url and "longitude=-80.1918" in url
    assert "temperature_unit=fahrenheit" in url


def test_publish_writes_expected_object():
    calls = []

    class FakeS3:
        def put_object(self, **kw):
            calls.append(kw)

    app.publish({"a": 1}, "my-bucket", s3=FakeS3())
    kw = calls[0]
    assert kw["Bucket"] == "my-bucket" and kw["Key"] == "data/weather.json"
    assert kw["ContentType"] == "application/json"
    assert "max-age=300" in kw["CacheControl"]
    assert json.loads(kw["Body"]) == {"a": 1}


def test_handler_end_to_end(monkeypatch):
    monkeypatch.setenv("SITE_BUCKET", "b")
    monkeypatch.setattr(app, "fetch_forecast", lambda lat, lon: RAW)
    published = {}
    monkeypatch.setattr(app, "publish", lambda payload, bucket, s3=None: published.update(p=payload, b=bucket))
    result = app.handler({}, None)
    assert result["ok"] is True
    assert published["b"] == "b" and published["p"]["current"]["temp_f"] == 82.4
