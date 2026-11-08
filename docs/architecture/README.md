# Architecture Documentation

This directory contains comprehensive documentation for the AI Real Estate Assistant system architecture.

## Overview

The AI Real Estate Assistant is a **conversational AI platform** for property search using:

- **Frontend**: Next.js (React 19) with App Router
- **Backend**: FastAPI (Python 3.12+)
- **AI Engine**: Hybrid Agent (RAG + LangChain Tools)
- **Vector Store**: ChromaDB with FastEmbed embeddings
- **Authentication**: Dual-mode (API Key + JWT)

## Documentation Files

| File | Description |
|------|-------------|
| `request-flow.md` | Complete request flow with Mermaid diagrams |
| `agent-system.md` | QueryAnalyzer and HybridAgent architecture |
| `llm-integration.md` | Multi-provider LLM factory system |
| `vector-store.md` | ChromaDB integration and hybrid retrieval |
| `authentication.md` | API Key and JWT authentication flows |
| `dependency-injection.md` | FastAPI dependency injection patterns |

## System Architecture Diagram

```mermaid
graph TB
    subgraph Frontend
        A[Next.js :3000]
        B[API Proxy Route]
    end

    subgraph Backend
        C[FastAPI :8000]
        D[QueryAnalyzer]
        E[HybridAgent]
        F[RAG Chain]
        G[Tool Agent]
        H[ChromaDB]
        I[LLM Provider Factory]
    end

    subgraph Auth
        J[API Key Auth]
        K[JWT Auth]
    end

    A -->|SSE| B
    B -->|X-API-Key injected| C
    C --> J
    C --> K
    C --> D
    D --> E
    E --> F
    E --> G
    F --> H
    G --> H
    F --> I
    G --> I
```

## Key Architectural Patterns

### 1. Hybrid Query Routing

The system uses a **smart query analyzer** to route requests:

| Query Type | Route | Example |
|------------|-------|---------|
| Simple | RAG-only | "What properties in Berlin?" |
| Medium | Hybrid (RAG + enhancement) | "2-bedroom apartments under 500k" |
| Complex | Agent + Tools | "Compare mortgage options for 3 properties" |

### 2. Dependency Injection

All major components are injected via FastAPI's `Depends()`:

- `get_llm()` - Cached LLM with user preference support
- `get_vector_store()` - Cached ChromaPropertyStore
- `get_agent()` - HybridAgent with all dependencies

### 3. Multi-Provider LLM System

Supports 16 LLM providers with automatic fallback:

1. OpenAI
2. Anthropic
3. Google (Gemini)
4. Grok
5. DeepSeek
6. OpenRouter
7. Groq
8. Mistral
9. Qwen
10. Z.ai (Zhipu)
11. Moonshot
12. OpenCode
13. Together
14. Fireworks
15. Hugging Face
16. Ollama (local models)

The registry lives in `apps/api/models/provider_factory.py` (`_PROVIDER_MODULES`);
providers are imported lazily, so a deployment only loads what it uses.

### 4. Dual-Mode Authentication

| Auth Type | Use Case | Header |
|-----------|----------|--------|
| API Key | Backend access, all basic endpoints | `X-API-Key` |
| JWT | User-specific features (favorites, saved searches) | `Authorization: Bearer <token>` |

## Technology Stack

- **Frontend**: Next.js, React 19, TypeScript, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, SQLAlchemy
- **AI/ML**: LangChain, LangChain Community, ChromaDB, FastEmbed
- **Testing**: Pytest (backend), Jest (frontend)
- **DevOps**: Docker, Docker Compose, GitHub Actions

## Quick Links

- [Developer Setup Guide](../development/README.md)
- [API Documentation](../api/README.md)
- [Testing Guide](../testing/README.md)
- [Deployment Guide](../deployment/README.md)
