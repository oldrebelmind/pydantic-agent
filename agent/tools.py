"""
Pydantic AI Tools

Tool functions that the AI agent can call.
"""
import logging
from typing import Optional
from weather_api import (
    get_weather_by_location,
    WeatherAPIError,
    LocationNotFoundError,
    WeatherServiceError,
    WeatherData
)

logger = logging.getLogger(__name__)


def format_weather_for_ai(weather: WeatherData) -> str:
    """
    Format weather data as natural text for AI to use in responses

    Args:
        weather: Structured weather data

    Returns:
        Natural language summary like:
        "Current weather in Carmel, IN: 45°F and cloudy. Next 12 hours:
         Rain expected around 3pm, temperature dropping to 38°F by evening."
    """
    # Build current conditions
    current = f"Current weather in {weather.location}: {weather.current_temp}°F and {weather.current_conditions.lower()}."

    # Build forecast summary from periods
    if weather.periods:
        forecast_parts = []
        for period in weather.periods[:3]:  # Use first 3 periods
            forecast_parts.append(
                f"{period.name}: {period.short_forecast}, {period.temperature}°{period.temperature_unit}"
            )
        forecast = " ".join(forecast_parts)
        return f"{current} {forecast}"

    return current


async def get_current_weather_tool(location: Optional[dict] = None) -> str:
    """
    Get current weather and short-term forecast for a location.

    This tool fetches weather data from Weather.gov API for US locations.

    Use this when the user asks about:
    - Current weather conditions
    - Temperature
    - What to wear
    - Upcoming weather in next 12-24 hours
    - Should I bring an umbrella/jacket?

    Args:
        location: Location dict with latitude, longitude, city, state

    Returns:
        Formatted weather string for AI to use in response
    """
    if not location:
        return "I don't have your location. Could you share your city or enable location access?"

    # Extract location data
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    city = location.get("city", "")
    state = location.get("state", "")

    if not latitude or not longitude:
        return "I don't have your location coordinates. Please enable location access."

    # Build location name for display
    location_name = f"{city}, {state}" if city and state else f"{city}" if city else f"{latitude}, {longitude}"

    try:
        logger.info(f"Fetching weather for {location_name} ({latitude}, {longitude})")

        # Fetch weather with caching
        weather = await get_weather_by_location(
            lat=latitude,
            lon=longitude,
            location_name=location_name
        )

        # Format for AI consumption
        result = format_weather_for_ai(weather)
        logger.info(f"Weather data retrieved successfully: {result[:100]}...")
        return result

    except LocationNotFoundError as e:
        logger.warning(f"Location not found: {e}")
        return "Weather.gov only supports US locations. I can't get weather data for your location."

    except WeatherServiceError as e:
        logger.error(f"Weather service error: {e}")
        return "I'm having trouble fetching weather data right now. Please try again in a moment."

    except WeatherAPIError as e:
        logger.error(f"Weather API error: {e}")
        return "I couldn't get weather for that location. Please check your location settings."

    except Exception as e:
        logger.error(f"Unexpected error fetching weather: {e}")
        return "I encountered an error fetching weather data. Please try again."
