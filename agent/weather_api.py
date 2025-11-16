"""
Weather.gov API Client

Provides weather data integration using the National Weather Service API.
"""
import httpx
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Simple in-memory cache
_weather_cache: Dict[str, Tuple['WeatherData', datetime]] = {}
CACHE_DURATION = timedelta(minutes=30)


class WeatherAPIError(Exception):
    """Base exception for weather API errors"""
    pass


class LocationNotFoundError(WeatherAPIError):
    """Location not found or outside US"""
    pass


class WeatherServiceError(WeatherAPIError):
    """Weather.gov API service error"""
    pass


@dataclass
class WeatherPeriod:
    """Single forecast period (e.g., 'This Afternoon', 'Tonight')"""
    name: str
    temperature: int
    temperature_unit: str  # 'F' or 'C'
    short_forecast: str  # 'Partly Cloudy'
    detailed_forecast: str  # Full description


@dataclass
class WeatherData:
    """Complete weather response"""
    location: str  # "Carmel, IN"
    current_temp: int  # 45
    current_conditions: str  # "Cloudy"
    forecast_short: str  # "Rain expected around 3pm"
    periods: List[WeatherPeriod]  # Next 12-24 hours (2-4 periods)
    timestamp: datetime  # When data was fetched


async def get_forecast_url(lat: float, lon: float) -> str:
    """
    Step 1: Convert lat/lon to forecast URL

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Forecast URL string

    Raises:
        LocationNotFoundError: If location is invalid or outside US
        WeatherServiceError: If API fails
    """
    url = f"https://api.weather.gov/points/{lat},{lon}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                url,
                headers={"User-Agent": "PydanticAI-WeatherBot/1.0"},
                timeout=10.0
            )

            if response.status_code == 404:
                raise LocationNotFoundError(
                    f"Location ({lat}, {lon}) not found or outside US. "
                    "Weather.gov only supports US locations."
                )

            if response.status_code != 200:
                raise WeatherServiceError(
                    f"Weather.gov API returned status {response.status_code}"
                )

            data = response.json()

            # Extract forecast URL from response
            forecast_url = data.get("properties", {}).get("forecast")

            if not forecast_url:
                raise WeatherServiceError(
                    "Weather.gov API response missing forecast URL"
                )

            logger.info(f"Got forecast URL for ({lat}, {lon}): {forecast_url}")
            return forecast_url

        except httpx.RequestError as e:
            raise WeatherServiceError(f"Failed to connect to Weather.gov API: {e}")


async def get_weather_forecast(forecast_url: str) -> WeatherData:
    """
    Step 2: Fetch forecast from URL

    Args:
        forecast_url: URL from get_forecast_url()

    Returns:
        Structured weather data

    Raises:
        WeatherServiceError: If forecast fetch fails
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                forecast_url,
                headers={"User-Agent": "PydanticAI-WeatherBot/1.0"},
                timeout=10.0
            )

            if response.status_code != 200:
                raise WeatherServiceError(
                    f"Weather.gov forecast API returned status {response.status_code}"
                )

            data = response.json()

            # Extract forecast periods
            periods_data = data.get("properties", {}).get("periods", [])

            if not periods_data:
                raise WeatherServiceError(
                    "Weather.gov API response missing forecast periods"
                )

            # Take first 4 periods (next 12-24 hours typically)
            periods = []
            for period_data in periods_data[:4]:
                periods.append(WeatherPeriod(
                    name=period_data.get("name", "Unknown"),
                    temperature=period_data.get("temperature", 0),
                    temperature_unit=period_data.get("temperatureUnit", "F"),
                    short_forecast=period_data.get("shortForecast", ""),
                    detailed_forecast=period_data.get("detailedForecast", "")
                ))

            # Extract current/first period info
            first_period = periods[0] if periods else None

            if not first_period:
                raise WeatherServiceError("No forecast periods available")

            # Build weather data
            weather_data = WeatherData(
                location="",  # Will be set by caller
                current_temp=first_period.temperature,
                current_conditions=first_period.short_forecast,
                forecast_short=_build_short_forecast(periods),
                periods=periods,
                timestamp=datetime.now()
            )

            logger.info(f"Fetched weather forecast: {first_period.temperature}°{first_period.temperature_unit}, {first_period.short_forecast}")
            return weather_data

        except httpx.RequestError as e:
            raise WeatherServiceError(f"Failed to fetch forecast: {e}")


def _build_short_forecast(periods: List[WeatherPeriod]) -> str:
    """
    Build a concise forecast summary from periods

    Args:
        periods: List of forecast periods

    Returns:
        Short forecast string like "Rain expected this afternoon, clearing tonight"
    """
    if not periods:
        return "No forecast available"

    # Use first 2-3 periods for short summary
    forecast_parts = []
    for period in periods[:3]:
        forecast_parts.append(f"{period.name}: {period.short_forecast}")

    return ". ".join(forecast_parts)


async def get_weather_by_location(lat: float, lon: float, location_name: str = "") -> WeatherData:
    """
    Convenience wrapper - combines both steps with caching

    Args:
        lat: Latitude
        lon: Longitude
        location_name: Optional location name for display (e.g., "Carmel, IN")

    Returns:
        Cached or fresh weather data

    Raises:
        LocationNotFoundError: If location is invalid or outside US
        WeatherServiceError: If API fails
    """
    cache_key = f"{lat:.4f},{lon:.4f}"  # Round to ~10m precision

    # Check cache
    if cache_key in _weather_cache:
        data, timestamp = _weather_cache[cache_key]
        age = datetime.now() - timestamp

        if age < CACHE_DURATION:
            logger.info(f"Using cached weather data (age: {age.seconds}s)")
            # Update location name if provided
            if location_name:
                data.location = location_name
            return data

    # Fetch fresh data
    logger.info(f"Fetching fresh weather data for {cache_key}")

    # Step 1: Get forecast URL
    forecast_url = await get_forecast_url(lat, lon)

    # Step 2: Get forecast
    weather_data = await get_weather_forecast(forecast_url)

    # Set location name
    weather_data.location = location_name if location_name else f"{lat}, {lon}"
    weather_data.timestamp = datetime.now()

    # Cache it
    _weather_cache[cache_key] = (weather_data, datetime.now())

    return weather_data
