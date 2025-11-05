"use client";

import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

interface StreamingMessageProps {
  content: string;
}

export default function StreamingMessage({ content }: StreamingMessageProps) {
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex w-full mb-4 justify-start animate-in fade-in-0 slide-in-from-bottom-2">
      <div className="max-w-[80%] rounded-2xl px-4 py-3 shadow-sm bg-muted text-foreground">
        <div className="text-sm whitespace-pre-wrap break-words">
          {content}
          <span
            className={cn(
              "inline-block w-2 h-4 ml-1 bg-foreground",
              showCursor ? "opacity-100" : "opacity-0"
            )}
          />
        </div>
        <div className="text-xs mt-1 opacity-70 text-left">Typing...</div>
      </div>
    </div>
  );
}
