/**
 * Types for streaming chat messages
 */
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface StreamEvent {
  token?: string;
  done?: boolean;
  error?: string;
}

export interface LocationContext {
  city?: string;
  state?: string;
  country?: string;
  timezone?: string;
  latitude?: number;
  longitude?: number;
}

/**
 * Stream chat messages from the backend API using Server-Sent Events (SSE)
 *
 * @param message - The user's message to send
 * @param onToken - Callback function called for each token received
 * @param onComplete - Callback function called when streaming completes
 * @param onError - Callback function called on error
 * @param locationContext - Optional location context from IP geolocation
 * @returns Promise that resolves when streaming is complete
 */
export async function streamChatMessage(
  message: string,
  onToken: (token: string) => void,
  onComplete: () => void,
  onError: (error: string) => void,
  locationContext?: LocationContext | null
): Promise<void> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  try {
    // Build request body with optional location context
    const requestBody: any = { message };

    if (locationContext) {
      requestBody.location = locationContext;
    }

    const response = await fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages in buffer
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data: StreamEvent = JSON.parse(line.slice(6));

            if (data.error) {
              reader.cancel();
              onError(data.error);
              return;
            }

            if (data.done) {
              reader.cancel();
              onComplete();
              return;
            }

            if (data.token) {
              onToken(data.token);
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }

      // OPTIMIZATION: Check buffer immediately for complete done message without newline
      if (buffer.trim().startsWith('data: ')) {
        try {
          const data: StreamEvent = JSON.parse(buffer.trim().slice(6));
          if (data.done) {
            reader.cancel();
            onComplete();
            return;
          }
        } catch (e) {
          // Not a complete JSON yet, continue reading
        }
      }
    }

    // Process any remaining data in buffer (e.g., final message without trailing newline)
    if (buffer.trim() && buffer.startsWith('data: ')) {
      try {
        const data: StreamEvent = JSON.parse(buffer.slice(6));
        if (data.done) {
          reader.cancel();
          onComplete();
          return;
        }
        if (data.token) {
          onToken(data.token);
        }
      } catch (e) {
        console.error('Error parsing final SSE data:', e);
      }
    }

    reader.cancel();
    onComplete();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    onError(errorMessage);
  }
}

/**
 * Format a timestamp for display
 */
export function formatTimestamp(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: 'numeric',
    hour12: true,
  }).format(date);
}
