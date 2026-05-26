"""Simple tools for the DeepAgent example."""

import urllib.parse
import urllib.request

from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """Return the current weather for a city.

    Input: city name. Output: weather condition and temperature.
    """
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=1"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            weather = response.read().decode().strip()
        return f"Current weather at {city}: {weather}"
    except Exception as exc:
        return f"Error: {exc}"


TOOLS = [get_weather]
