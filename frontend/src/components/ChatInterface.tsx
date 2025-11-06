"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2 } from "lucide-react";
import { ChatMessage, streamChatMessage, LocationContext } from "@/lib/streaming";
import { fetchGeolocation, GeolocationData } from "@/lib/geolocation";
import MessageBubble from "./MessageBubble";
import StreamingMessage from "./StreamingMessage";

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [locationContext, setLocationContext] = useState<LocationContext | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const streamingContentRef = useRef("");

  // Fetch user's location on component mount
  useEffect(() => {
    const loadLocation = async () => {
      const geoData: GeolocationData | null = await fetchGeolocation();

      if (geoData) {
        // Convert GeolocationData to LocationContext
        const context: LocationContext = {
          city: geoData.city,
          state: geoData.state_prov,
          country: geoData.country_name,
          timezone: geoData.timezone?.name,
          latitude: geoData.latitude,
          longitude: geoData.longitude,
        };

        setLocationContext(context);
        console.log('[CHAT] Location context loaded:', context);
      }
    };

    loadLocation();
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!input.trim() || isStreaming) {
      return;
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError(null);
    setIsStreaming(true);
    setStreamingContent("");
    streamingContentRef.current = "";

    await streamChatMessage(
      userMessage.content,
      // onToken
      (token: string) => {
        streamingContentRef.current += token;
        setStreamingContent(streamingContentRef.current);
      },
      // onComplete
      () => {
        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: streamingContentRef.current,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setStreamingContent("");
        streamingContentRef.current = "";
        setIsStreaming(false);
        inputRef.current?.focus();
      },
      // onError
      (errorMsg: string) => {
        setError(errorMsg);
        setIsStreaming(false);
        setStreamingContent("");
        streamingContentRef.current = "";
        inputRef.current?.focus();
      },
      // locationContext
      locationContext
    );
  };

  return (
    <Card className="w-full h-[700px] flex flex-col shadow-2xl border-2">
      <CardHeader className="border-b bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-900">
        <CardTitle className="text-2xl font-bold">Chat with AI Agent</CardTitle>
      </CardHeader>

      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div ref={scrollRef} className="p-6 space-y-4">
            {messages.length === 0 && !isStreaming && (
              <div className="text-center text-muted-foreground py-12">
                <p className="text-lg mb-2">Start a conversation!</p>
                <p className="text-sm">
                  Ask me anything. I have memory powered by Mem0 GraphRAG.
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}

            {isStreaming && streamingContent && (
              <StreamingMessage content={streamingContent} />
            )}

            {error && (
              <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-lg text-sm">
                <strong>Error:</strong> {error}
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>

      <CardFooter className="border-t p-4">
        <form onSubmit={handleSubmit} className="flex w-full gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isStreaming}
            className="flex-1"
            autoFocus
          />
          <Button
            type="submit"
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="shrink-0"
            aria-label={isStreaming ? "Sending message" : "Send message"}
            data-testid="send-button"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}
