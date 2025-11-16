# Weather Tool Design

**Date:** 2025-01-16
**Status:** Approved
**Author:** Claude Code (with Brian McCleskey)

## Overview

A weather tool for the Pydantic AI agent that answers weather questions conversationally using the Weather.gov API and user geolocation data.

## Goals

- Enable AI agent to answer weather questions naturally
- Use Weather.gov API (free, no API key required)
- Leverage existing geolocation functionality
- Provide current conditions + 12-24 hour forecast
- Keep implementation simple and maintainable

## Architecture

### Single Backend Tool Approach

**No frontend widget** - All weather interaction happens through conversation with the AI agent.

**Data Flow:**
1. User asks weather question in chat
2. AI agent detects weather intent, calls weather tool
3. Tool receives user location from request context
4. Tool calls Weather.gov API (2-step process)
5. Returns structured weather data to AI
6. AI responds naturally with weather information

### Weather.gov API Integration

Weather.gov requires a 2-step process:

1. **Points Endpoint:** Convert lat/lon to grid coordinates
   ```
   GET https://api.weather.gov/points/{latitude},{longitude}
   ```
   Returns: Grid office, coordinates, and forecast URL

2. **Forecast Endpoint:** Fetch forecast from URL
   ```
   GET https://api.weather.gov/gridpoints/{office}/{gridX},{gridY}/forecast
   ```
   Returns: Forecast periods with temperature, conditions, detailed forecast

## Components

### 1. Weather API Client

**File:** `agent/weather_api.py`

**Purpose:** Encapsulate all Weather.gov API interactions

**Key Functions:**

```python
async def get_forecast_url(lat: float, lon: float) -> str:
    """
    Step 1: Convert lat/lon to forecast URL

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Forecast URL string

    Raises:
        WeatherAPIError: If location is invalid or API fails
    """

async def get_weather_forecast(forecast_url: str) -> WeatherData:
    """
    Step 2: Fetch forecast from URL

    Args:
        forecast_url: URL from get_forecast_url()

    Returns:
        Structured weather data

    Raises:
        WeatherAPIError: If forecast fetch fails
    """

async def get_weather_by_location(lat: float, lon: float) -> WeatherData:
    """
    Convenience wrapper - combines both steps with caching

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Cached or fresh weather data
    """
```

**Data Structures:**

```python
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
```

### 2. Pydantic AI Weather Tool

**File:** `agent/tools.py` or `agent/main.py`

**Purpose:** Make weather data available to AI agent

**Implementation:**

```python
@agent.tool
async def get_current_weather(ctx: RunContext[AgentDeps]) -> str:
    """
    Get current weather and short-term forecast for the user's location.

    Use this when the user asks about:
    - Current weather conditions
    - Temperature
    - What to wear
    - Upcoming weather in next 12-24 hours

    Returns:
        Formatted weather string for AI to use in response
    """
    # Get user's location from context
    user_location = ctx.deps.user_location

    if not user_location:
        return "I don't have your location. Could you share your city or enable location access?"

    try:
        # Fetch weather with caching
        weather = await get_weather_by_location(
            lat=user_location.latitude,
            lon=user_location.longitude
        )

        # Format for AI consumption
        return format_weather_for_ai(weather)

    except WeatherAPIError as e:
        if "404" in str(e):
            return "Weather.gov only supports US locations. I can't get weather data for your location."
        return "I'm having trouble fetching weather data right now. Please try again in a moment."

def format_weather_for_ai(weather: WeatherData) -> str:
    """
    Format weather data as natural text for AI to use

    Returns:
        String like: "Current weather in Carmel, IN: 45°F and cloudy.
                     Next 12 hours: Rain expected around 3pm, temperature
                     dropping to 38°F by evening."
    """
    # Build natural language summary
```

### 3. Frontend Updates

**File:** `frontend/src/lib/streaming.ts` (or chat API module)

**Changes Required:**

Update chat API requests to include geolocation data:

```typescript
// Current request
POST /api/chat/stream
{
  "message": "What's the weather like?",
  "user_id": "Brian McCleskey"
}

// Updated request
POST /api/chat/stream
{
  "message": "What's the weather like?",
  "user_id": "Brian McCleskey",
  "location": {
    "latitude": 39.9784,
    "longitude": -86.1180,
    "city": "Carmel",
    "state": "Indiana"
  }
}
```

**Implementation:**

```typescript
// In ChatInterface.tsx or wherever messages are sent
const sendMessage = async (message: string) => {
  // Get geolocation (already implemented)
  const geoData = await fetchGeolocation();

  // Include location in request
  await streamChatMessage({
    message,
    user_id: userName,
    location: geoData ? {
      latitude: geoData.latitude,
      longitude: geoData.longitude,
      city: geoData.city,
      state: geoData.state_prov
    } : null
  });
};
```

### 4. Backend API Updates

**File:** `agent/main.py`

**Changes Required:**

1. Accept location in request body
2. Pass location to agent context/deps
3. Make available to weather tool

```python
class ChatRequest(BaseModel):
    message: str
    user_id: str
    location: Optional[LocationData] = None

class LocationData(BaseModel):
    latitude: float
    longitude: float
    city: str
    state: str

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # Pass location to agent context
    deps = AgentDeps(
        user_location=request.location,
        # ... other deps
    )

    # Run agent with location context
    result = await agent.run(
        request.message,
        deps=deps
    )
```

## Error Handling

### Scenarios and Responses

| Scenario | Detection | Response |
|----------|-----------|----------|
| No location provided | `user_location is None` | "I don't have your location. Please enable location access or tell me your city." |
| Non-US location | API returns 404 | "Weather.gov only supports US locations. I can't get weather data for your location." |
| API rate limit | API returns 429 | "I'm making too many weather requests. Please try again in a minute." |
| API service down | Network error, 500 error | "I'm having trouble fetching weather data right now. Please try again in a moment." |
| Invalid coordinates | API returns 400 | "I couldn't get weather for that location. Please check your location settings." |

### Exception Handling

```python
class WeatherAPIError(Exception):
    """Base exception for weather API errors"""
    pass

class LocationNotFoundError(WeatherAPIError):
    """Location not found or outside US"""
    pass

class WeatherServiceError(WeatherAPIError):
    """Weather.gov API service error"""
    pass
```

## Caching Strategy

**Why Cache:**
- Weather data doesn't change every second
- Avoid hitting Weather.gov API rate limits
- Faster responses for repeated questions
- Reduced network latency

**Implementation:**

```python
# Simple in-memory cache
_weather_cache: Dict[str, Tuple[WeatherData, datetime]] = {}
CACHE_DURATION = timedelta(minutes=30)

async def get_weather_by_location(lat: float, lon: float) -> WeatherData:
    cache_key = f"{lat:.4f},{lon:.4f}"  # Round to ~10m precision

    # Check cache
    if cache_key in _weather_cache:
        data, timestamp = _weather_cache[cache_key]
        age = datetime.now() - timestamp

        if age < CACHE_DURATION:
            logger.info(f"Using cached weather data (age: {age.seconds}s)")
            return data

    # Fetch fresh data
    logger.info(f"Fetching fresh weather data for {cache_key}")

    # Step 1: Get forecast URL
    forecast_url = await get_forecast_url(lat, lon)

    # Step 2: Get forecast
    weather_data = await get_weather_forecast(forecast_url)
    weather_data.timestamp = datetime.now()

    # Cache it
    _weather_cache[cache_key] = (weather_data, datetime.now())

    return weather_data
```

**Cache Invalidation:**
- Time-based: 30 minutes
- No manual invalidation needed
- Cache is in-memory (cleared on restart)
- Could upgrade to Redis for multi-instance deployments

## Testing Strategy

### Unit Tests

**File:** `agent/tests/test_weather_api.py`

```python
@pytest.mark.asyncio
async def test_get_forecast_url_valid_location():
    """Test forecast URL retrieval for valid US location"""
    url = await get_forecast_url(39.9784, -86.1180)
    assert "api.weather.gov/gridpoints" in url

@pytest.mark.asyncio
async def test_get_forecast_url_invalid_location():
    """Test error handling for non-US location"""
    with pytest.raises(LocationNotFoundError):
        await get_forecast_url(51.5074, -0.1278)  # London, UK

@pytest.mark.asyncio
async def test_weather_caching():
    """Test that repeated calls use cache"""
    # First call - should fetch
    weather1 = await get_weather_by_location(39.9784, -86.1180)

    # Second call - should use cache
    weather2 = await get_weather_by_location(39.9784, -86.1180)

    assert weather1.timestamp == weather2.timestamp
```

### Integration Tests

**File:** `agent/tests/test_weather_tool.py`

```python
@pytest.mark.asyncio
async def test_weather_tool_with_location():
    """Test weather tool returns formatted response"""
    # Mock location context
    deps = AgentDeps(
        user_location=LocationData(
            latitude=39.9784,
            longitude=-86.1180,
            city="Carmel",
            state="Indiana"
        )
    )

    ctx = RunContext(deps=deps)
    result = await get_current_weather(ctx)

    assert "Carmel" in result
    assert "°F" in result

@pytest.mark.asyncio
async def test_weather_tool_no_location():
    """Test graceful handling when location not provided"""
    deps = AgentDeps(user_location=None)
    ctx = RunContext(deps=deps)

    result = await get_current_weather(ctx)
    assert "don't have your location" in result
```

### Manual Testing

1. **Happy Path:**
   - Ask: "What's the weather like?"
   - Expected: Natural response with current temp and forecast

2. **No Location:**
   - Disable geolocation
   - Ask about weather
   - Expected: Friendly message asking for location

3. **Repeated Questions:**
   - Ask about weather twice within 30 minutes
   - Expected: Second response should be faster (cached)

4. **Non-US Location:**
   - Mock location to London, UK
   - Ask about weather
   - Expected: "Weather.gov only supports US locations"

## Implementation Checklist

### Backend Tasks

- [ ] Create `agent/weather_api.py`
  - [ ] Implement `get_forecast_url()`
  - [ ] Implement `get_weather_forecast()`
  - [ ] Implement `get_weather_by_location()` with caching
  - [ ] Define `WeatherData` and `WeatherPeriod` dataclasses
  - [ ] Add error handling and custom exceptions

- [ ] Add weather tool to `agent/tools.py` or `agent/main.py`
  - [ ] Implement `@agent.tool get_current_weather()`
  - [ ] Implement `format_weather_for_ai()`
  - [ ] Add location context handling

- [ ] Update `agent/main.py` API endpoint
  - [ ] Add `LocationData` to request model
  - [ ] Pass location to agent deps/context
  - [ ] Update `ChatRequest` schema

- [ ] Add tests
  - [ ] Unit tests for weather API functions
  - [ ] Integration tests for weather tool
  - [ ] Test error scenarios

### Frontend Tasks

- [ ] Update `frontend/src/lib/streaming.ts`
  - [ ] Modify chat request to include location
  - [ ] Get location from `fetchGeolocation()`
  - [ ] Handle cases where location is unavailable

- [ ] Update chat component
  - [ ] Ensure geolocation is fetched on page load
  - [ ] Include location in message sending logic

### Testing & Deployment

- [ ] Test with real Weather.gov API
- [ ] Test caching behavior
- [ ] Test error scenarios (no location, non-US, API failures)
- [ ] Load test cache performance
- [ ] Document API usage in README

## Future Enhancements

### Phase 2 (Optional)

- **Weather Alerts:** Include severe weather warnings
- **Extended Forecast:** 7-day forecast option
- **Hourly Details:** Breakdown by hour instead of periods
- **Weather History:** "What was the weather like yesterday?"
- **Location Override:** "What's the weather in Chicago?"
- **Multiple Units:** Celsius option for international users
- **Weather Icons:** Visual representation in chat
- **Precipitation Probability:** Rain/snow chances

### Technical Improvements

- **Redis Caching:** Replace in-memory cache for multi-instance deployments
- **Rate Limiting:** Implement per-user rate limits
- **Metrics:** Track API usage, cache hit rate, error rates
- **Alternative APIs:** Fallback to OpenWeather if Weather.gov is down

## Constraints & Limitations

1. **US Only:** Weather.gov API only covers United States territories
2. **30-Minute Cache:** Weather updates every 30 minutes, not real-time
3. **No Historical Data:** Only current and forecast data available
4. **Geolocation Required:** Tool needs lat/lon from frontend
5. **No Severe Weather Details:** Basic alerts only, not detailed warnings

## Success Criteria

- ✅ AI agent can answer "What's the weather?" questions
- ✅ Responses include current conditions and short forecast
- ✅ Error messages are friendly and actionable
- ✅ Response time < 2 seconds (including cached data)
- ✅ Cache reduces API calls by 80%+ for repeated queries
- ✅ Works seamlessly with existing geolocation system

## References

- [Weather.gov API Documentation](https://www.weather.gov/documentation/services-web-api)
- [Pydantic AI Tools Documentation](https://ai.pydantic.dev/tools/)
- Existing geolocation implementation: `frontend/src/lib/geolocation.ts`
