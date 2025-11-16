"""
FastAPI Application - Streaming Chat API

This module provides the REST API for the Pydantic AI Agent with Server-Sent Events (SSE)
streaming support for real-time chat responses.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import asyncio
import logging

from main import PydanticAIAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Pydantic AI Chat API",
    description="Streaming chat API with Server-Sent Events for real-time AI responses",
    version="1.0.0",
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development server
        "http://localhost:3001",  # Alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: PydanticAIAgent | None = None


# Request/Response Models
class LocationContext(BaseModel):
    """User's location context from IP geolocation"""
    city: str | None = Field(None, description="City name")
    state: str | None = Field(None, description="State/Province")
    country: str | None = Field(None, description="Country name")
    timezone: str | None = Field(None, description="IANA timezone (e.g., 'America/New_York')")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")

    class Config:
        json_schema_extra = {
            "example": {
                "city": "Indianapolis",
                "state": "Indiana",
                "country": "United States",
                "timezone": "America/Indiana/Indianapolis",
                "latitude": 39.7684,
                "longitude": -86.1581
            }
        }


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message to the AI agent"
    )
    location: LocationContext | None = Field(
        None,
        description="Optional location context from IP geolocation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is the capital of France?",
                "location": {
                    "city": "Indianapolis",
                    "state": "Indiana",
                    "country": "United States",
                    "timezone": "America/Indiana/Indianapolis",
                    "latitude": 39.7684,
                    "longitude": -86.1581
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    agent: str = Field(..., description="Agent status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "agent": "ready"
            }
        }


# Startup/Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize the agent on application startup"""
    global agent
    try:
        logger.info("Initializing Pydantic AI Agent...")
        agent = PydanticAIAgent()
        logger.info("Agent created successfully!")

        # Initialize hybrid memory (async)
        if agent and agent.memory:
            logger.info("Initializing hybrid memory system...")
            await agent.initialize_memory_async()
            logger.info("Hybrid memory initialized!")

        logger.info("Agent fully initialized!")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        # Continue startup but agent will be unavailable
        agent = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    global agent
    logger.info("Shutting down API...")

    # Close hybrid memory connections
    if agent and agent.memory:
        try:
            await agent.memory.close()
            logger.info("Hybrid memory connections closed")
        except Exception as e:
            logger.error(f"Error closing hybrid memory: {e}")

    agent = None


# API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Pydantic AI Chat API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns the status of the API and the AI agent.
    """
    if agent is None:
        return HealthResponse(
            status="unhealthy",
            agent="not_initialized"
        )

    return HealthResponse(
        status="healthy",
        agent="ready"
    )


@app.post("/api/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """
    Stream a chat response using Server-Sent Events (SSE)

    This endpoint accepts a user message and streams the AI's response
    token-by-token in real-time using the SSE protocol.

    Args:
        request: ChatRequest containing the user's message

    Returns:
        StreamingResponse with text/event-stream content type

    SSE Event Format:
        data: {"token": "text"}\\n\\n     - Token event
        data: {"done": true}\\n\\n         - Completion event
        data: {"error": "message"}\\n\\n   - Error event
    """
    # Check if agent is available
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="AI agent is not initialized. Please try again later."
        )

    async def event_stream():
        """
        Generator function that yields Server-Sent Events

        Yields SSE-formatted events containing tokens, completion signal, or errors.
        """
        try:
            # Log message with location context if available
            if request.location:
                logger.info(
                    f"Processing message: {request.message[:50]}... "
                    f"[Location: {request.location.city}, {request.location.state} - {request.location.timezone}]"
                )
            else:
                logger.info(f"Processing message: {request.message[:50]}...")

            # Convert Pydantic LocationContext to dict for agent
            location_dict = None
            if request.location:
                location_dict = request.location.model_dump()

            # Stream response from agent with location context
            async for token in agent.process_message_stream(
                user_input=request.message,
                location_context=location_dict
            ):
                # Format as SSE event
                event_data = json.dumps({'token': token})
                yield f"data: {event_data}\n\n"

            # Send completion event
            logger.info("Stream completed successfully")
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            # Log error
            logger.error(f"Error during streaming: {str(e)}", exc_info=True)

            # Send error event to client
            error_data = json.dumps({'error': str(e)})
            yield f"data: {error_data}\n\n"

    # Return streaming response
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # Prevent caching
            "Cache-Control": "no-cache",

            # Keep connection alive
            "Connection": "keep-alive",

            # Disable nginx buffering (important for streaming)
            "X-Accel-Buffering": "no",

            # Content encoding
            "Content-Encoding": "none",
        }
    )


# Error Handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return {
        "detail": "Endpoint not found",
        "available_endpoints": {
            "root": "/",
            "docs": "/docs",
            "health": "/api/health",
            "chat": "/api/chat/stream"
        }
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return {
        "detail": "Internal server error. Please check logs."
    }


# Development helper
if __name__ == "__main__":
    import uvicorn

    print("Starting Pydantic AI Chat API...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs at: http://localhost:8000/docs")

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
