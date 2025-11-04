# Deployment Guide

**Project:** Pydantic AI Agent with Next.js Frontend
**Environment**: Development & Production
**Last Updated**: 2025-11-04

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Environment Variables](#environment-variables)
5. [Port Configuration](#port-configuration)
6. [Troubleshooting](#troubleshooting)
7. [Production Deployment](#production-deployment)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| **Docker** | 24.0+ | Container runtime |
| **Docker Compose** | 2.0+ | Multi-container orchestration |
| **Node.js** | 18.0+ | Frontend development |
| **npm** | 9.0+ | Package management |
| **Python** | 3.11+ | Backend development (optional) |
| **Git** | 2.30+ | Version control |

### System Requirements

**Minimum**:
- CPU: 4 cores
- RAM: 8GB
- Disk: 20GB free space
- OS: Windows 10/11, macOS 12+, or Linux

**Recommended**:
- CPU: 8+ cores
- RAM: 16GB
- Disk: 50GB SSD
- GPU: NVIDIA (for faster Ollama inference)

### External Services

- **Ollama**: Running at `ollama.brainiacs.technology:11434`
  - Or install locally: https://ollama.ai
  - Ensure model is pulled: `ollama pull llama3.2`

- **Neo4j**: Running at `192.168.1.97:7474`
  - For GraphRAG functionality

---

## Local Development Setup

### Step 1: Clone Repository

```bash
# If not already cloned
git clone <repository-url>
cd agent
```

Or if using the existing project at `D:\agent`:
```bash
cd D:\agent
```

### Step 2: Environment Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# Windows
notepad .env

# Linux/Mac
nano .env
```

3. Required variables (minimum):
```bash
OLLAMA_HOST=http://ollama.brainiacs.technology:11434
OLLAMA_MODEL=llama3.2
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

### Step 3: Start Backend Services

```bash
# Start all backend services
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
```

Expected output:
```
NAME                IMAGE                  STATUS
pydantic-api       agent-agent-api        Up
qdrant            qdrant/qdrant:latest   Up
langfuse-server   langfuse/langfuse:2    Up
langfuse-db       postgres:15-alpine     Up
```

### Step 4: Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Expected output:
```
✓ Ready in 2.3s
○ Local:   http://localhost:3000
○ Network: http://192.168.1.x:3000
```

### Step 5: Verify Installation

1. **Backend API**:
   ```bash
   curl http://localhost:8000/api/health
   # Expected: {"status":"healthy","agent":"ready"}
   ```

2. **Qdrant**:
   ```bash
   curl http://localhost:6333/health
   # Expected: {"status":"ok"}
   ```

3. **Langfuse**:
   - Open http://localhost:3000
   - Should see Langfuse dashboard

4. **Frontend**:
   - Open http://localhost:3000
   - Should see chat interface

---

## Docker Deployment

### Full Stack (Backend + Frontend in Docker)

**Option 1**: Add frontend to docker-compose.yml

```yaml
# Add to docker-compose.yml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: pydantic-frontend
  environment:
    - NEXT_PUBLIC_API_URL=http://api:8000
  networks:
    - agent-network
  ports:
    - "3001:3000"
  depends_on:
    - api
```

Then:
```bash
docker-compose up -d --build
```

**Option 2**: Keep frontend running via npm (easier for development)

```bash
# Terminal 1: Backend
docker-compose up

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Container Management

**Start services**:
```bash
docker-compose up -d
```

**Stop services**:
```bash
docker-compose down
```

**Restart a service**:
```bash
docker-compose restart api
```

**Rebuild a service**:
```bash
docker-compose up -d --build api
```

**View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

**Execute command in container**:
```bash
docker-compose exec api bash
```

---

## Environment Variables

### Backend (.env)

```bash
# Ollama Configuration
OLLAMA_HOST=http://ollama.brainiacs.technology:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=120

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=agent_memory

# Mem0 Configuration
MEM0_USER_ID=default_user
MEM0_AGENT_ID=pydantic_agent

# Langfuse Configuration
LANGFUSE_HOST=http://langfuse-server:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_ENABLED=true

# Guardrails AI
GUARDRAILS_ENABLED=true

# Agent Configuration
AGENT_PROMPT_TEMPLATE=GENERAL_ASSISTANT
AGENT_NAME=Pydantic AI Agent
AGENT_MAX_TOKENS=2048
AGENT_TEMPERATURE=0.7

# Langfuse Server
NEXTAUTH_SECRET=your-secret-here
SALT=your-salt-here

# Logging
LOG_LEVEL=INFO
```

### Frontend (.env.local)

Create `frontend/.env.local`:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Analytics
# NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
```

---

## Port Configuration

### Default Ports

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Frontend** | 3000 | http://localhost:3000 | Next.js app |
| **Langfuse** | 3000 | http://localhost:3000 | (conflicts with frontend) |
| **API** | 8000 | http://localhost:8000 | FastAPI backend |
| **Qdrant HTTP** | 6333 | http://localhost:6333 | Vector database |
| **Qdrant gRPC** | 6334 | - | Internal communication |
| **PostgreSQL** | 5432 | - | Langfuse database |
| **Neo4j HTTP** | 7474 | http://192.168.1.97:7474 | GraphRAG browser |
| **Neo4j Bolt** | 7687 | bolt://192.168.1.97:7687 | GraphRAG protocol |

### Port Conflicts

**Issue**: Langfuse and Frontend both use port 3000

**Solutions**:

1. **Use Langfuse on different port**:
   ```yaml
   # docker-compose.yml
   langfuse-server:
     ports:
       - "3001:3000"  # Access at http://localhost:3001
   ```

2. **Access Langfuse via container**:
   ```bash
   # No external port needed if accessed only by API
   # Remove ports section from langfuse-server service
   ```

3. **Run frontend on different port**:
   ```bash
   # package.json
   "dev": "next dev -p 3001"
   ```

---

## Troubleshooting

### Common Issues

#### 1. API Not Starting

**Symptoms**:
```
ERROR: Container pydantic-api exited with code 1
```

**Diagnosis**:
```bash
docker-compose logs api
```

**Solutions**:
- Check Python dependencies: `docker-compose up --build api`
- Verify environment variables in `.env`
- Check Ollama connectivity: `curl http://ollama.brainiacs.technology:11434/api/tags`

#### 2. Frontend Can't Connect to API

**Symptoms**:
- Network errors in browser console
- CORS errors

**Solutions**:

1. Check API is running:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. Verify CORS configuration in `agent/api.py`:
   ```python
   allow_origins=["http://localhost:3000"]
   ```

3. Check frontend API URL in `frontend/.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

#### 3. Qdrant Connection Errors

**Symptoms**:
```
Failed to connect to Qdrant at qdrant:6333
```

**Solutions**:

1. Check Qdrant is running:
   ```bash
   docker-compose ps qdrant
   curl http://localhost:6333/health
   ```

2. Verify network connectivity:
   ```bash
   docker-compose exec api ping qdrant
   ```

3. Check Docker network:
   ```bash
   docker network ls
   docker network inspect agent-network
   ```

#### 4. Langfuse Keys Not Working

**Symptoms**:
- 401 Unauthorized errors in logs
- Langfuse traces not appearing

**Solutions**:

1. Access Langfuse dashboard: http://localhost:3001
2. Create new API keys: Settings → API Keys
3. Update `.env`:
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-new-key
   LANGFUSE_SECRET_KEY=sk-lf-new-key
   ```
4. Restart API:
   ```bash
   docker-compose restart api
   ```

#### 5. Streaming Not Working

**Symptoms**:
- No tokens appearing in frontend
- Connection times out

**Solutions**:

1. Test streaming directly:
   ```bash
   curl -X POST http://localhost:8000/api/chat/stream \
     -H "Content-Type: application/json" \
     -d '{"message":"Hello"}' \
     --no-buffer
   ```

2. Check browser Network tab:
   - Look for `/api/chat/stream` request
   - Should show "text/event-stream" content type
   - Check for CORS errors

3. Verify SSE support in browser (should work in all modern browsers)

#### 6. Docker Build Failures

**Symptoms**:
```
ERROR: failed to solve: process "/bin/sh -c pip install ..." did not complete
```

**Solutions**:

1. Clear Docker cache:
   ```bash
   docker system prune -a
   ```

2. Rebuild without cache:
   ```bash
   docker-compose build --no-cache api
   ```

3. Check disk space:
   ```bash
   docker system df
   ```

---

## Production Deployment

### Preparation

1. **Environment Configuration**:
   ```bash
   # Create production .env
   cp .env.example .env.production

   # Update with production values
   OLLAMA_HOST=https://ollama.production.com
   LANGFUSE_HOST=https://langfuse.production.com
   ```

2. **Security**:
   ```bash
   # Generate secure secrets
   NEXTAUTH_SECRET=$(openssl rand -base64 32)
   SALT=$(openssl rand -base64 32)

   # Add to .env.production
   ```

3. **Database Backups**:
   ```bash
   # Backup Qdrant
   docker run --rm -v pydantic-ai-agent_qdrant_storage:/data \
     -v $(pwd)/backups:/backup \
     ubuntu tar czf /backup/qdrant-$(date +%Y%m%d).tar.gz /data

   # Backup PostgreSQL
   docker-compose exec langfuse-db pg_dump -U langfuse > backup.sql
   ```

### Deployment Options

#### Option 1: Docker Compose (Simple)

```bash
# On production server
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

#### Option 2: Kubernetes (Scalable)

See production Kubernetes manifests in `/k8s` directory (to be created).

#### Option 3: Cloud Platforms

- **AWS**: ECS or EKS
- **Google Cloud**: Cloud Run or GKE
- **Azure**: Container Apps or AKS

### Health Checks

Set up monitoring:
```bash
# API health
curl https://api.production.com/api/health

# Automated monitoring with cron
*/5 * * * * curl -f https://api.production.com/api/health || alert
```

---

## Development Workflow

### Typical Development Session

```bash
# 1. Start backend
docker-compose up -d

# 2. Start frontend (separate terminal)
cd frontend && npm run dev

# 3. Make changes to code
# - Backend: Auto-reloads via volume mount
# - Frontend: Auto-reloads via Next.js

# 4. View logs
docker-compose logs -f api

# 5. Test changes
# - Frontend: http://localhost:3000
# - API: curl http://localhost:8000/api/health

# 6. Stop when done
docker-compose down
```

### Adding New Dependencies

**Backend**:
```bash
# Add to agent/requirements.txt
echo "new-package==1.0.0" >> agent/requirements.txt

# Rebuild container
docker-compose up -d --build api
```

**Frontend**:
```bash
cd frontend
npm install new-package
# Automatically updates package.json
```

---

## Backup and Restore

### Backup

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup Qdrant
docker run --rm \
  -v pydantic-ai-agent_qdrant_storage:/data \
  -v $(pwd)/backups/$(date +%Y%m%d):/backup \
  ubuntu tar czf /backup/qdrant.tar.gz /data

# Backup Langfuse DB
docker-compose exec -T langfuse-db pg_dump -U langfuse \
  > backups/$(date +%Y%m%d)/langfuse.sql

# Backup environment
cp .env backups/$(date +%Y%m%d)/
```

### Restore

```bash
# Restore Qdrant
docker run --rm \
  -v pydantic-ai-agent_qdrant_storage:/data \
  -v $(pwd)/backups/20251104:/backup \
  ubuntu tar xzf /backup/qdrant.tar.gz -C /

# Restore Langfuse DB
cat backups/20251104/langfuse.sql | \
  docker-compose exec -T langfuse-db psql -U langfuse
```

---

**Last Updated**: 2025-11-04
**Maintained By**: Pydantic AI Agent Team
