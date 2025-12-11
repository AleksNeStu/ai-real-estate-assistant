# Architecture (V3)

## System Overview
- Streamlit UI (model selection, settings, chat, Expert Panel)
- Query Analyzer (intent, filters)
- Hybrid processing: simple → RAG, complex → Agent + Tools
- Tools: mortgage, comparison, analysis
- Retriever: ChromaDB (semantic + keyword, MMR), AdvancedPropertyRetriever (geo radius, price filters)
- Reranker (multi-signal)
- Response formatter

## Technology Stack
- UI: Streamlit 1.37+
- AI Orchestration: LangChain 0.2+
- Providers: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama
- Vector store: ChromaDB 0.5+
- Embeddings: FastEmbed (BGE)
- Data: Pandas 2.2+, Pydantic 2.5+
- Python 3.11+

## Key Data Flows
- Data load → embeddings → ChromaDB persist → hybrid retrieval → rerank → response
- Expert Panel → geo radius/indices/time‑series → export digest

