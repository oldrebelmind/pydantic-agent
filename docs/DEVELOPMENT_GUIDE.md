# Development Guide

**Project:** Pydantic AI Agent Monorepo
**For Developers**: Contributing to backend or frontend
**Last Updated**: 2025-11-04

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Code Organization](#code-organization)
3. [Backend Development](#backend-development)
4. [Frontend Development](#frontend-development)
5. [Adding Features](#adding-features)
6. [Testing](#testing)
7. [Best Practices](#best-practices)

---

## Getting Started

### Development Environment

**Required Tools**:
- **IDE**: VS Code (recommended) or PyCharm
- **VS Code Extensions**:
  - Python
  - Pylance
  - ES Lint
  - Tailwind CSS IntelliSense
  - Prettier
  - Docker

### Initial Setup

```bash
# 1. Clone and navigate
cd D:\agent

# 2. Backend setup
docker-compose up -d

# 3. Frontend setup
cd frontend
npm install

# 4. Start development
npm run dev
```

---

## Code Organization

### Monorepo Structure

```
D:\agent\
├── agent/              # Python backend
├── frontend/           # Next.js frontend
├── docs/              # Documentation
└── docker-compose.yml  # Orchestration
```

### Backend Structure

```
agent/
├── main.py            # Core agent logic
├── api.py             # FastAPI endpoints
├── config.py          # Configuration loading
├── prompts.py         # System prompts
├── utils.py           # Utilities
├── requirements.txt    # Dependencies
├── Dockerfile         # CLI agent
└── Dockerfile.api     # API service
```

### Frontend Structure

```
frontend/
├── app/
│   ├── layout.tsx     # Root layout
│   ├── page.tsx       # Chat page
│   └── globals.css    # Global styles
├── components/
│   ├── ui/            # shadcn components
│   └── chat/          # Custom components
├── lib/
│   ├── utils.ts       # Utilities
│   ├── streaming.ts   # SSE client
│   └── api.ts         # API client
└── types/
    └── chat.ts        # TypeScript types
```

---

## Backend Development

### Setting Up Python Environment (Optional)

For local development without Docker:

```bash
cd agent

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

### Adding New Dependencies

1. Add to `requirements.txt`:
   ```
   new-package==1.0.0
   ```

2. Rebuild container:
   ```bash
   docker-compose up -d --build api
   ```

### Modifying the Agent

**`agent/main.py`**:

```python
class PydanticAIAgent:
    def __init__(self):
        # Initialization logic

    async def process_message(self, user_input: str) -> str:
        # Standard (non-streaming) message processing

    async def process_message_stream(self, user_input: str):
        # Streaming message processing
        async with self.agent.run_stream(message) as result:
            async for token in result.stream_text(delta=True):
                yield token
```

**Key Methods**:
- `_initialize_memory()`: Mem0 setup
- `_initialize_langfuse()`: Observability setup
- `_initialize_guardrails()`: Safety setup
- `_get_memory_context()`: Retrieve relevant memories
- `_save_to_memory()`: Store conversation

### Adding API Endpoints

**`agent/api.py`**:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class NewRequest(BaseModel):
    param: str

@app.post("/api/new-endpoint")
async def new_endpoint(request: NewRequest):
    # Implementation
    return {"result": "success"}
```

### Adding System Prompts

**`agent/prompts.py`**:

```python
NEW_PROMPT = """
You are a specialized assistant for...
Your capabilities include...
"""

PROMPT_TEMPLATES = {
    "GENERAL_ASSISTANT": GENERAL_ASSISTANT_PROMPT,
    "NEW_TEMPLATE": NEW_PROMPT,  # Add here
}
```

Update `.env`:
```bash
AGENT_PROMPT_TEMPLATE=NEW_TEMPLATE
```

### Adding Guardrails Validators

```python
from guardrails.hub import ToxicLanguage, PIIDetector

def _initialize_guardrails(self):
    guard = Guard().use_many(
        ToxicLanguage(threshold=0.5),
        PIIDetector(),  # Add new validator
    )
    return guard
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log levels
logger.debug("Debug info")
logger.info("Info message")
logger.warning("Warning")
logger.error("Error occurred")
```

View logs:
```bash
docker-compose logs -f api
```

---

## Frontend Development

### Running Frontend

```bash
cd frontend

# Development mode (hot reload)
npm run dev

# Build for production
npm run build

# Run production build
npm start

# Lint code
npm run lint
```

### Project Structure Deep Dive

#### app/ Directory (Next.js 15 App Router)

**`app/layout.tsx`**: Root layout

```typescript
import { ThemeProvider } from 'next-themes';
import { Toaster } from '@/components/ui/toaster';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <ThemeProvider attribute="class">
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**`app/page.tsx`**: Main page

```typescript
import ChatInterface from '@/components/chat/ChatInterface';

export default function Home() {
  return <ChatInterface />;
}
```

#### components/ Directory

**shadcn/ui components**: Auto-generated, don't modify directly

**Custom components**:

```typescript
// components/chat/ChatInterface.tsx
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);

  return (
    <Card>
      <MessageList messages={messages} />
      <InputBar onSend={handleSend} />
    </Card>
  );
}
```

### Using shadcn/ui Components

**Installing new components**:
```bash
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
```

**Using components**:
```typescript
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';

export function MyComponent() {
  return (
    <Dialog>
      <Button>Click me</Button>
    </Dialog>
  );
}
```

### Styling with Tailwind

```typescript
// Use Tailwind classes
<div className="flex items-center gap-4 p-4 bg-background">
  <Button className="bg-primary hover:bg-primary/90">
    Send
  </Button>
</div>

// Use cn() utility for conditional classes
import { cn } from '@/lib/utils';

<div className={cn(
  "base-classes",
  isActive && "active-classes",
  error && "error-classes"
)}>
```

### TypeScript Best Practices

**Define types**:
```typescript
// types/chat.ts
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
}
```

**Use types in components**:
```typescript
interface MyComponentProps {
  messages: Message[];
  onSend: (message: string) => void;
}

export function MyComponent({ messages, onSend }: MyComponentProps) {
  // TypeScript knows the types
}
```

---

## Adding Features

### Adding a New Chat Component

1. **Create component file**:
```typescript
// components/chat/MessageActions.tsx
import { Button } from '@/components/ui/button';

interface MessageActionsProps {
  messageId: string;
  onCopy: () => void;
  onDelete: () => void;
}

export function MessageActions({ messageId, onCopy, onDelete }: MessageActionsProps) {
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="ghost" onClick={onCopy}>
        Copy
      </Button>
      <Button size="sm" variant="ghost" onClick={onDelete}>
        Delete
      </Button>
    </div>
  );
}
```

2. **Use in parent component**:
```typescript
import { MessageActions } from './MessageActions';

<MessageBubble>
  {content}
  <MessageActions messageId={msg.id} onCopy={...} onDelete={...} />
</MessageBubble>
```

### Adding a New API Endpoint

#### Backend (`agent/api.py`):

```python
from pydantic import BaseModel

class ConversationHistoryRequest(BaseModel):
    user_id: str
    limit: int = 10

@app.get("/api/conversations")
async def get_conversations(request: ConversationHistoryRequest):
    # Implementation
    conversations = load_conversations(request.user_id, request.limit)
    return {"conversations": conversations}
```

#### Frontend (`lib/api.ts`):

```typescript
export async function getConversations(
  userId: string,
  limit: number = 10
): Promise<Conversation[]> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/conversations?` +
    `user_id=${userId}&limit=${limit}`
  );

  if (!response.ok) {
    throw new Error('Failed to fetch conversations');
  }

  const data = await response.json();
  return data.conversations;
}
```

#### Component:

```typescript
import { getConversations } from '@/lib/api';
import { useEffect, useState } from 'react';

export function ConversationList() {
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    getConversations('user123').then(setConversations);
  }, []);

  return (
    <div>
      {conversations.map(conv => (
        <div key={conv.id}>{conv.title}</div>
      ))}
    </div>
  );
}
```

### Adding a New Page

1. **Create page file**:
```typescript
// app/settings/page.tsx
export default function SettingsPage() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold">Settings</h1>
      {/* Settings content */}
    </div>
  );
}
```

2. **Add navigation**:
```typescript
// components/Navigation.tsx
import Link from 'next/link';

<nav>
  <Link href="/">Chat</Link>
  <Link href="/settings">Settings</Link>
</nav>
```

---

## Testing

### Backend Testing

**Manual testing with curl**:
```bash
# Health check
curl http://localhost:8000/api/health

# Stream test
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Test"}' \
  --no-buffer
```

**Python unit tests** (future):
```python
# tests/test_agent.py
import pytest

def test_process_message():
    agent = PydanticAIAgent()
    response = await agent.process_message("Hello")
    assert len(response) > 0
```

### Frontend Testing

**Component testing** (future):
```typescript
// __tests__/ChatInterface.test.tsx
import { render, screen } from '@testing-library/react';
import ChatInterface from '@/components/chat/ChatInterface';

test('renders chat interface', () => {
  render(<ChatInterface />);
  expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument();
});
```

**Manual testing**:
1. Open http://localhost:3000
2. Type a message
3. Verify streaming works
4. Check browser console for errors
5. Test responsive design (mobile view)

---

## Best Practices

### Backend

1. **Type Hints**: Always use type hints
   ```python
   async def process_message(self, user_input: str) -> str:
   ```

2. **Error Handling**: Try/except blocks
   ```python
   try:
       result = await agent.run(message)
   except Exception as e:
       logger.error(f"Error: {e}")
       return "Sorry, an error occurred"
   ```

3. **Async/Await**: Use async for I/O operations
   ```python
   async def fetch_data():
       async with httpx.AsyncClient() as client:
           return await client.get(url)
   ```

4. **Configuration**: Use environment variables
   ```python
   from config import config
   model = config.OLLAMA_MODEL
   ```

### Frontend

1. **Component Size**: Keep components small and focused
   ```typescript
   // Good: Single responsibility
   function MessageBubble() { }
   function InputBar() { }

   // Bad: Too many responsibilities
   function ChatEverything() { }
   ```

2. **State Management**: Keep state close to where it's used
   ```typescript
   // Good: Local state
   function MessageBubble() {
     const [isExpanded, setIsExpanded] = useState(false);
   }
   ```

3. **Props Drilling**: Use context for deep props
   ```typescript
   // For widely-used values
   const ThemeContext = createContext();
   ```

4. **Memoization**: Use for expensive computations
   ```typescript
   const sortedMessages = useMemo(
     () => messages.sort(...),
     [messages]
   );
   ```

5. **Error Boundaries**: Catch component errors
   ```typescript
   <ErrorBoundary fallback={<ErrorMessage />}>
     <ChatInterface />
   </ErrorBoundary>
   ```

### Code Style

**Python (PEP 8)**:
```python
# Good
def process_message(user_input: str) -> str:
    """Process a user message."""
    result = transform(user_input)
    return result

# Bad
def processMessage(UserInput):
    Result=Transform(UserInput)
    return Result
```

**TypeScript**:
```typescript
// Good
interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
}

// Bad
interface messageBubbleProps {
  Role: string;
  Content: any;
}
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-chat-feature

# Make changes
git add .
git commit -m "Add: New chat feature"

# Push to remote
git push origin feature/new-chat-feature

# Create pull request
```

**Commit Messages**:
- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Modify existing
- `Remove:` Delete code
- `Docs:` Documentation only

---

## Debugging

### Backend Debugging

**View logs**:
```bash
docker-compose logs -f api
```

**Attach to container**:
```bash
docker-compose exec api bash
python
>>> from main import PydanticAIAgent
>>> agent = PydanticAIAgent()
```

**Python debugger**:
```python
import pdb; pdb.set_trace()
```

### Frontend Debugging

**Browser DevTools**:
- Console: `console.log()` statements
- Network: Check API calls
- React DevTools: Inspect component state

**Debug streaming**:
```typescript
async for (const line of lines) {
  console.log('SSE line:', line);  // Debug
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));
    console.log('Parsed data:', data);  // Debug
  }
}
```

---

## Common Tasks

### Update Ollama Model

```bash
# In .env
OLLAMA_MODEL=llama3.1

# Restart API
docker-compose restart api
```

### Change Theme Colors

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#3b82f6',  // Change this
          foreground: '#ffffff',
        },
      },
    },
  },
};
```

### Add Loading Skeleton

```typescript
import { Skeleton } from '@/components/ui/skeleton';

{isLoading ? (
  <Skeleton className="h-20 w-full" />
) : (
  <MessageList />
)}
```

---

**Happy Coding!**

For questions, check:
- `docs/FRONTEND_ARCHITECTURE.md`
- `docs/API_SPECIFICATION.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/STREAMING_IMPLEMENTATION.md`
