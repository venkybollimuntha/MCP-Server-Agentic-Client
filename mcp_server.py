from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("SharedToolsMCP")


def health_check() -> dict:
    """A simple health check tool."""
    print("[SERVER] health_check() called")
    return {"status": "ok", "message": "MCP server is healthy!"}

@mcp.tool()
def calculate(expression: str) -> dict:
    """
    Evaluate a safe mathematical expression.
    Supports +, -, *, /, **, parentheses, and basic math.
    Example: '(24 * 3) + 5', '2 ** 10', '100 / 4'
    """
    print(f"[SERVER] calculate() called with expression={expression!r}")
    allowed = set("0123456789+-*/().**% ")
    if any(ch not in allowed for ch in expression):
        return {"error": "Invalid characters in expression. Only numbers and +-*/().**% are allowed."}
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return {"expression": expression, "result": result}
    except ZeroDivisionError:
        return {"error": "Division by zero."}
    except Exception as e:
        return {"error": f"Could not evaluate expression: {e}"}

@mcp.tool()
def normalize_name(name: str) -> str:
    """Normalize a name by stripping whitespace and capitalizing."""
    print(f"[SERVER] normalize_name() called with name={name!r}")
    return name.strip().title()


@mcp.tool()
def get_weather(city: str) -> dict:
    """
    Get real-time current weather for a city using Open-Meteo (no API key required).
    Returns temperature, wind speed, weather condition, and local time.
    """
    print(f"[SERVER] get_weather() called with city={city!r}")

    # Step 1: Geocode city name → lat/lon
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_resp = requests.get(geo_url, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()

    if not geo_data.get("results"):
        return {"error": f"City '{city}' not found."}

    result = geo_data["results"][0]
    lat = result["latitude"]
    lon = result["longitude"]
    display_name = f"{result['name']}, {result.get('country', '')}"
    timezone = result.get("timezone", "UTC")

    # Step 2: Fetch current weather
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_resp = requests.get(weather_url, params={
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "timezone": timezone,
        "forecast_days": 1
    }, timeout=10)
    weather_resp.raise_for_status()
    weather_data = weather_resp.json()

    current = weather_data.get("current", {})
    units = weather_data.get("current_units", {})

    # WMO weather code → human-readable description
    WMO_CODES = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Icy fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
    }
    code = current.get("weather_code", -1)
    condition = WMO_CODES.get(code, f"Weather code {code}")

    return {
        "city": display_name,
        "time": current.get("time"),
        "temperature": f"{current.get('temperature_2m')} {units.get('temperature_2m', '°C')}",
        "feels_like": f"{current.get('apparent_temperature')} {units.get('apparent_temperature', '°C')}",
        "humidity": f"{current.get('relative_humidity_2m')} {units.get('relative_humidity_2m', '%')}",
        "wind_speed": f"{current.get('wind_speed_10m')} {units.get('wind_speed_10m', 'km/h')}",
        "condition": condition
    }


if __name__ == "__main__":
    print("[SERVER] MCP server started, waiting for requests...")
    mcp.run(transport="stdio")  # Use stdio for communication with the agent