# Streaming Implementation Guide

**Topic**: Server-Sent Events (SSE) for Real-Time AI Responses
**Stack**: FastAPI (Backend) + Next.js (Frontend)
**Last Updated**: 2025-11-04

---

## Table of Contents

1. [Overview](#overview)
2. [How SSE Works](#how-sse-works)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Debugging](#debugging)
6. [Performance Optimization](#performance-optimization)
7. [Common Issues](#common-issues)

---

## Overview

### What is Streaming?

Streaming allows the AI agent to send its response token-by-token as it's being generated, rather than waiting for the complete response. This provides:

- **Better UX**: Users see progress immediately
- **Perceived Performance**: Feels faster even if total time is the same
- **Real-time Feel**: Like chatting with a human
- **Error Recovery**: Can show partial results if connection drops

### Why Server-Sent Events (SSE)?

We chose SSE over WebSockets because:

| Feature | SSE | WebSockets |
|---------|-----|------------|
| Direction | Server → Client | Bidirectional |
| Protocol | HTTP | Custom |
| Reconnection | Automatic | Manual |
| Complexity | Simple | Complex |
| Browser Support | All modern | All modern |
| Use Case | One-way streaming | Two-way communication |

For our chat interface, communication is primarily one-way (server streaming response to client), making SSE the perfect choice.

---

## How SSE Works

### SSE Protocol

SSE uses a simple text-based format over HTTP:

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"token": "Hello"}\n\n
data: {"token": " "}\n\n
data: {"token": "there"}\n\n
data: {"done": true}\n\n
```

**Key Points**:
- Each event starts with `data: `
- Event ends with double newline (`\n\n`)
- Payload is typically JSON
- Connection stays open

### Flow Diagram

```
┌─────────┐                                  ┌─────────┐
│ Browser │                                  │  FastAPI │
└────┬────┘                                  └────┬────┘
     │                                            │
     │  POST /api/chat/stream                    │
     │  {"message": "Hello"}                     │
     │───────────────────────────────────────────>│
     │                                            │
     │                                            │  Call agent.run_stream()
     │                                            │──┐
     │                                            │  │
     │  data: {"token": "Hello"}\n\n             │<─┘
     │<───────────────────────────────────────────│
     │                                            │
     │  (Display "Hello")                         │
     │                                            │
     │  data: {"token": " world"}\n\n            │
     │<───────────────────────────────────────────│
     │                                            │
     │  (Display "Hello world")                   │
     │                                            │
     │  data: {"done": true}\n\n                 │
     │<───────────────────────────────────────────│
     │                                            │
     │  (Close stream, finalize)                  │
     │                                            │
```

---

## Backend Implementation

### FastAPI Streaming Response

**`agent/api.py`**:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import asyncio

app = FastAPI()

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_stream():
        """Generator function that yields SSE events"""
        try:
            # Get streaming response from agent
            async for token in agent.process_message_stream(request.message):
                # Format as SSE event
                event_data = json.dumps({'token': token})
                yield f"data: {event_data}\n\n"

                # Allow other tasks to run
                await asyncio.sleep(0)

            # Send completion event
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### Agent Streaming Method

**`agent/main.py`**:

```python
async def process_message_stream(self, user_input: str):
    """Stream agent response token by token"""
    try:
        # Sanitize input
        user_input = sanitize_input(user_input)

        # Validate with guardrails
        if self.guard and not self._validate_with_guardrails(user_input):
            yield "I'm sorry, but I cannot process that message."
            return

        # Get memory context
        memory_context = await self._get_memory_context_async(user_input)
        full_message = f"{memory_context}\n\n{user_input}" if memory_context else user_input

        # Stream response from Pydantic AI
        full_response = ""
        async with self.agent.run_stream(full_message) as result:
            # Stream text deltas
            async for text in result.stream_text(delta=True):
                full_response += text
                yield text  # Yield each token

        # Save complete response to memory
        if self.memory:
            await self._save_to_memory_async(user_input, full_response)

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"Error: {str(e)}"
```

### Pydantic AI Stream Methods

Pydantic AI provides several streaming methods:

```python
# Option 1: Stream text deltas (incremental tokens)
async with agent.run_stream(message) as result:
    async for text in result.stream_text(delta=True):
        yield text  # "Hello", " ", "world", "!"

# Option 2: Stream cumulative text
async with agent.run_stream(message) as result:
    async for text in result.stream_text(delta=False):
        yield text  # "Hello", "Hello world", "Hello world!"

# Option 3: Stream with debouncing (performance)
async with agent.run_stream(message) as result:
    async for text in result.stream_output(debounce_by=0.01):
        yield text  # Batches tokens every 10ms
```

**We use delta=True** for character-by-character streaming effect.

### Important Headers

```python
headers = {
    # Prevent caching
    "Cache-Control": "no-cache",

    # Keep connection alive
    "Connection": "keep-alive",

    # Disable nginx buffering (important!)
    "X-Accel-Buffering": "no",

    # CORS for frontend
    "Access-Control-Allow-Origin": "http://localhost:3000",
}
```

---

## Frontend Implementation

### SSE Client (TypeScript)

**`frontend/lib/streaming.ts`**:

```typescript
export async function streamChat(
  message: string,
  onToken: (token: string) => void,
  onComplete: () => void,
  onError: (error: string) => void
) {
  try {
    // Make POST request
    const response = await fetch('http://localhost:8000/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    // Check response status
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Get reader from response body
    const reader = response.body!
      .pipeThrough(new TextDecoderStream())
      .getReader();

    // Read stream
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      // Parse SSE format
      const lines = value.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          // Extract JSON from "data: {...}"
          const jsonStr = line.slice(6);  // Remove "data: " prefix
          const data = JSON.parse(jsonStr);

          // Handle different event types
          if (data.token) {
            onToken(data.token);
          } else if (data.done) {
            onComplete();
            return;  // Exit function
          } else if (data.error) {
            onError(data.error);
            return;
          }
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error.message : 'Unknown error');
  }
}
```

### React Component Usage

**`components/chat/ChatInterface.tsx`**:

```typescript
import { useState } from 'react';
import { streamChat } from '@/lib/streaming';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (userMessage: string) => {
    // Add user message to history
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    setIsLoading(true);
    let fullResponse = '';

    await streamChat(
      userMessage,

      // onToken: Called for each token
      (token) => {
        fullResponse += token;
        setStreaming(fullResponse);  // Update streaming display
      },

      // onComplete: Called when stream ends
      () => {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: fullResponse,
          timestamp: new Date()
        }]);
        setStreaming('');  // Clear streaming display
        setIsLoading(false);
      },

      // onError: Called on error
      (error) => {
        console.error('Streaming error:', error);
        toast({
          variant: 'destructive',
          title: 'Error',
          description: error,
        });
        setIsLoading(false);
      }
    );
  };

  return (
    <div>
      {/* Message history */}
      {messages.map((msg, i) => (
        <MessageBubble key={i} {...msg} />
      ))}

      {/* Streaming message */}
      {streaming && <StreamingMessage content={streaming} />}

      {/* Input */}
      <InputBar onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
```

### Streaming Display Component

**`components/chat/StreamingMessage.tsx`**:

```typescript
export function StreamingMessage({ content }: { content: string }) {
  return (
    <div className="flex gap-3">
      <Avatar>
        <AvatarFallback>AI</AvatarFallback>
      </Avatar>

      <Card className="max-w-[70%] bg-muted">
        <CardContent className="p-3">
          <p className="text-sm whitespace-pre-wrap">
            {content}
            {/* Animated cursor */}
            <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Debugging

### Backend Debugging

**1. Log SSE Events**:

```python
async def event_stream():
    async for token in agent.process_message_stream(request.message):
        event_data = json.dumps({'token': token})
        event_str = f"data: {event_data}\n\n"

        # Log what we're sending
        logger.debug(f"SSE event: {event_str!r}")

        yield event_str
```

**2. Test with curl**:

```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Count to 5"}' \
  --no-buffer
```

Expected output:
```
data: {"token":"1"}\n\n
data: {"token":", "}\n\n
data: {"token":"2"}\n\n
data: {"token":", "}\n\n
data: {"token":"3"}\n\n
data: {"token":", "}\n\n
data: {"token":"4"}\n\n
data: {"token":", "}\n\n
data: {"token":"5"}\n\n
data: {"done":true}\n\n
```

**3. Check Headers**:

```bash
curl -I -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Test"}'
```

Should see:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### Frontend Debugging

**1. Log Raw Stream Data**:

```typescript
const { value, done } = await reader.read();
console.log('Raw stream value:', value);  // Debug

const lines = value.split('\n');
console.log('Split lines:', lines);  // Debug
```

**2. Browser DevTools**:

- Open Network tab
- Find request to `/api/chat/stream`
- Click on it
- Check "Response" tab
- Should see events arriving in real-time

**3. Log Parsed Events**:

```typescript
for (const line of lines) {
  if (line.startsWith('data: ')) {
    const jsonStr = line.slice(6);
    console.log('JSON string:', jsonStr);  // Debug

    const data = JSON.parse(jsonStr);
    console.log('Parsed data:', data);  // Debug
  }
}
```

---

## Performance Optimization

### Backend Optimizations

**1. Token Batching**:

Instead of yielding every single character, batch tokens:

```python
async def event_stream():
    buffer = []
    buffer_size = 5  # Batch 5 tokens

    async for token in agent.process_message_stream(request.message):
        buffer.append(token)

        if len(buffer) >= buffer_size:
            # Send batch
            batch = ''.join(buffer)
            yield f"data: {json.dumps({'token': batch})}\n\n"
            buffer = []

    # Send remaining
    if buffer:
        batch = ''.join(buffer)
        yield f"data: {json.dumps({'token': batch})}\n\n"
```

**2. Async Sleep**:

Allow other tasks to run:

```python
yield event
await asyncio.sleep(0)  # Yield control
```

**3. Compression**:

Enable gzip for SSE (if supported):

```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Frontend Optimizations

**1. Debounce Updates**:

```typescript
const [streaming, setStreaming] = useState('');
const [debouncedStreaming, setDebouncedStreaming] = useState('');

useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedStreaming(streaming);
  }, 50);  // Update UI every 50ms max

  return () => clearTimeout(timer);
}, [streaming]);
```

**2. Virtual Scrolling**:

For long conversations:

```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={messages.length}
  itemSize={100}
>
  {({ index, style }) => (
    <div style={style}>
      <MessageBubble message={messages[index]} />
    </div>
  )}
</FixedSizeList>
```

**3. Memoization**:

```typescript
const StreamingMessage = React.memo(({ content }) => {
  return <div>{content}<Cursor /></div>;
});
```

---

## Common Issues

### 1. Events Not Arriving

**Symptoms**: Frontend receives no events, or events arrive all at once at the end

**Causes**:
- Server buffering (nginx, reverse proxy)
- Missing headers
- Python buffering

**Solutions**:

```python
# Add header to disable nginx buffering
headers = {"X-Accel-Buffering": "no"}

# Use sys.stdout.flush() if printing
import sys
sys.stdout.flush()

# Use asyncio.sleep(0) to yield
await asyncio.sleep(0)
```

### 2. JSON Parse Errors

**Symptoms**: `JSON.parse()` fails in frontend

**Causes**:
- Malformed JSON
- Event split across multiple reads
- Extra characters

**Solutions**:

```typescript
// Handle incomplete events
let buffer = '';

const { value, done } = await reader.read();
buffer += value;

// Split only on complete events (ending with \n\n)
const events = buffer.split('\n\n');
buffer = events.pop() || '';  // Keep incomplete event

for (const event of events) {
  if (event.startsWith('data: ')) {
    try {
      const data = JSON.parse(event.slice(6));
      // Process data
    } catch (e) {
      console.error('JSON parse error:', e, event);
    }
  }
}
```

### 3. Connection Drops

**Symptoms**: Stream stops mid-response

**Causes**:
- Network timeout
- Server error
- Client navigation

**Solutions**:

```typescript
// Implement retry logic
async function streamWithRetry(message, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await streamChat(message, ...);
      return;  // Success
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * i));
    }
  }
}
```

### 4. CORS Errors

**Symptoms**: `Access-Control-Allow-Origin` errors in browser console

**Solutions**:

```python
# Backend: Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Memory Leaks

**Symptoms**: Browser memory grows over time

**Solutions**:

```typescript
// Close reader when done
const reader = response.body.getReader();
try {
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    // Process value
  }
} finally {
  reader.releaseLock();  // Important!
}

// Clean up on unmount
useEffect(() => {
  return () => {
    // Cancel ongoing stream
    reader.cancel();
  };
}, []);
```

---

## Testing

### Unit Test (Backend)

```python
import pytest

async def test_chat_stream():
    async def mock_stream():
        yield "Hello"
        yield " "
        yield "world"

    # Test SSE formatting
    events = []
    async for token in mock_stream():
        event = f"data: {json.dumps({'token': token})}\n\n"
        events.append(event)

    assert len(events) == 3
    assert 'Hello' in events[0]
```

### Integration Test (Frontend)

```typescript
test('streaming chat works', async () => {
  const tokens: string[] = [];

  await streamChat(
    'Test message',
    (token) => tokens.push(token),
    () => console.log('Done'),
    (error) => console.error(error)
  );

  expect(tokens.length).toBeGreaterThan(0);
  expect(tokens.join('')).toBeTruthy();
});
```

---

## Resources

- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Pydantic AI Streaming](https://ai.pydantic.dev/api/agent/#pydantic_ai.Agent.run_stream)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

---

**Last Updated**: 2025-11-04
**Author**: Pydantic AI Agent Team
