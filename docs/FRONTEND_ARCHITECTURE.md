# Frontend Architecture Documentation

**Project:** Pydantic AI Agent - Streaming Chat Interface
**Stack:** Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui
**Architecture:** Monorepo with Backend (Python/FastAPI) + Frontend (Next.js)

---

## Table of Contents

1. [Overview](#overview)
2. [Monorepo Structure](#monorepo-structure)
3. [Technology Stack](#technology-stack)
4. [Architecture Diagram](#architecture-diagram)
5. [Component Hierarchy](#component-hierarchy)
6. [Data Flow](#data-flow)
7. [File Organization](#file-organization)
8. [Key Design Decisions](#key-design-decisions)

---

## Overview

The Pydantic AI Agent frontend is a modern web application built with Next.js 15 that provides a streaming chat interface for interacting with the AI agent. The application features:

- **Real-time Streaming**: Token-by-token response streaming using Server-Sent Events (SSE)
- **Beautiful UI**: Built with shadcn/ui components on top of Radix UI and Tailwind CSS
- **Type Safety**: Full TypeScript implementation with strict typing
- **Responsive Design**: Mobile-first approach that works on all screen sizes
- **Dark Mode**: Built-in theme switching with system preference detection
- **Accessibility**: WAI-ARIA compliant components from Radix UI

---

## Monorepo Structure

The project uses a monorepo structure where both backend and frontend live in the same repository:

```
D:\agent\
├── agent/                  # Backend (Python/FastAPI)
│   ├── main.py            # Pydantic AI agent
│   ├── api.py             # FastAPI streaming API (NEW)
│   ├── config.py
│   ├── prompts.py
│   ├── utils.py
│   ├── Dockerfile
│   ├── Dockerfile.api     # NEW
│   └── requirements.txt
│
├── frontend/              # Frontend (Next.js) - NEW
│   ├── app/              # Next.js App Router
│   ├── components/       # React components
│   ├── lib/             # Utilities
│   ├── types/           # TypeScript types
│   └── package.json
│
├── docs/                # Documentation - NEW
├── docker-compose.yml   # Full stack orchestration
├── .env                # Environment variables
└── README.md           # Project README
```

### Benefits of Monorepo

1. **Simplified Development**: Run both frontend and backend from single repo
2. **Shared Configuration**: Environment variables, Docker setup
3. **Easier Deployment**: Single repository to clone and deploy
4. **Version Synchronization**: Backend and frontend versions stay in sync
5. **Atomic Changes**: Changes that touch both backend and frontend are in one commit

---

## Technology Stack

### Frontend Core

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 15.x | React framework with App Router |
| **React** | 19.x | UI library |
| **TypeScript** | 5.x | Type safety and better DX |
| **Tailwind CSS** | 3.x | Utility-first CSS framework |
| **shadcn/ui** | Latest | Pre-built accessible components |

### UI Components

| Library | Purpose |
|---------|---------|
| **Radix UI** | Headless UI components (via shadcn) |
| **Lucide React** | Icon library |
| **class-variance-authority** | Component variants (via shadcn) |
| **clsx** | Conditional className utility |
| **tailwind-merge** | Merge Tailwind classes intelligently |

### State & Data Management

- **React Hooks**: Built-in state management (useState, useEffect)
- **Server-Sent Events (SSE)**: Real-time streaming from backend
- **Fetch API**: HTTP requests to backend API

---

## Architecture Diagram

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                        │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Next.js Frontend (Port 3000)           │    │
│  │                                                 │    │
│  │  ┌──────────────┐  ┌──────────────────────┐   │    │
│  │  │  Chat UI     │  │  Streaming Client    │   │    │
│  │  │  (shadcn/ui) │  │  (SSE EventSource)   │   │    │
│  │  └──────────────┘  └──────────────────────┘   │    │
│  └────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP POST + SSE
                       ▼
┌─────────────────────────────────────────────────────────┐
│        FastAPI Backend (Port 8000)                      │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  POST /api/chat/stream                         │    │
│  │  - Receives user message                       │    │
│  │  - Streams response via SSE                    │    │
│  │  - Returns tokens as they're generated         │    │
│  └──────────────────────┬─────────────────────────┘    │
└─────────────────────────┼──────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│             Pydantic AI Agent                           │
│                                                          │
│  ┌──────────────────────────────────────────────┐      │
│  │  agent.run_stream()                          │      │
│  │  - Streams tokens from Ollama LLM            │      │
│  │  - Manages memory (Mem0/Qdrant)              │      │
│  │  - Applies guardrails validation             │      │
│  │  - Logs to Langfuse                          │      │
│  └──────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## Component Hierarchy

### Page Structure

```
app/page.tsx
  └── ChatInterface
        ├── Card (shadcn)
        │     ├── Header
        │     │     ├── Title
        │     │     └── Subtitle
        │     │
        │     ├── ScrollArea (shadcn)
        │     │     └── MessageList
        │     │           ├── MessageBubble (user)
        │     │           │     ├── Avatar (shadcn)
        │     │           │     ├── Card (shadcn)
        │     │           │     └── Timestamp
        │     │           │
        │     │           ├── MessageBubble (assistant)
        │     │           │     ├── Avatar (shadcn)
        │     │           │     ├── Card (shadcn)
        │     │           │     └── Timestamp
        │     │           │
        │     │           └── StreamingMessage
        │     │                 ├── Avatar (shadcn)
        │     │                 ├── Card (shadcn)
        │     │                 └── Cursor animation
        │     │
        │     └── InputBar
        │           ├── Input (shadcn)
        │           └── Button (shadcn)
        │
        └── Toast (shadcn) - for errors
```

---

## Data Flow

### Message Sending Flow

1. **User Input** → User types in InputBar
2. **State Update** → Add message to history
3. **API Call** → POST to `/api/chat/stream`
4. **SSE Stream** → Receive tokens one by one
5. **Update UI** → Display in StreamingMessage
6. **Complete** → Move to message history

### State Management

```typescript
// Message History
const [messages, setMessages] = useState<Message[]>([]);

// Current Streaming Content
const [streaming, setStreaming] = useState('');

// Loading State
const [isLoading, setIsLoading] = useState(false);
```

---

## File Organization

### Frontend Directory Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Chat page
│   └── globals.css             # Global styles
│
├── components/
│   ├── ui/                     # shadcn components
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── button.tsx
│   │   ├── scroll-area.tsx
│   │   ├── avatar.tsx
│   │   └── toast.tsx
│   │
│   └── chat/                   # Custom components
│       ├── ChatInterface.tsx
│       ├── MessageBubble.tsx
│       ├── StreamingMessage.tsx
│       └── InputBar.tsx
│
├── lib/
│   ├── utils.ts               # cn() helper
│   ├── streaming.ts           # SSE client
│   └── api.ts                 # API utilities
│
└── types/
    └── chat.ts                # TypeScript types
```

---

## Key Design Decisions

### 1. Next.js App Router
**Why**: Latest architecture, better TypeScript support, future-proof

### 2. shadcn/ui
**Why**: Full control, accessible, beautiful defaults, no bundle overhead

### 3. Server-Sent Events (SSE)
**Why**: Perfect for unidirectional streaming, simpler than WebSockets

### 4. Client-Side Rendering
**Why**: Chat requires real-time interactivity, better UX

### 5. React Hooks for State
**Why**: Simple requirements, no global state needed

---

## Development Workflow

### Backend
```bash
docker-compose up -d
docker-compose logs -f api
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

**Last Updated**: 2025-11-04
**Version**: 1.0.0
