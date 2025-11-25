# AI Real Estate Assistant — Test Run Checklist

## Instructions
- Check items as you validate functionality. Add notes inline if needed.
- If you encounter issues, log them in the Bug Log section at the end.
- This checklist focuses on sidebar, data loading, chat/agent, insights, comparison, export, analytics, notifications, i18n, and resilience.

## 0) Preconditions
- [ ] App opens (local: `streamlit run app_modern.py`, Cloud: app URL)
- [ ] Sidebar shows these top-level sections: ⚙️ Preferences, 🧩 Model Configuration, ⚙️ Advanced Settings, 🧠 Intelligence Features, 📊 Data Sources, 🔄 Session
- [ ] No nested expanders (each section expands/collapses independently)
- [ ] On Cloud, use remote providers (OpenAI/Anthropic/Google); avoid Ollama/local models

## 1) Sidebar: Preferences
- [ ] Changing language in `⚙️ Preferences` re-renders UI texts
- [ ] Theme/styles applied without visual artifacts
- [ ] Section is expanded by default; expand/collapse works

## 2) Sidebar: Model Configuration
- [ ] Provider selection (OpenAI/Anthropic/Google/Grok/DeepSeek/Ollama)
- [ ] API key input/validation: Validate/Save/Change buttons work; key status visible
- [ ] Model list populates; selected model persists in state
- [ ] ℹ️ Model Details shows context, pricing, description, “Best for”

## 3) Sidebar: Advanced Settings
- [ ] `Temperature` slider affects response variability
- [ ] `Max tokens` input affects response length
- [ ] `Results to retrieve (k)` affects number of RAG documents

## 4) Sidebar: Intelligence Features
- [ ] `Smart AI Assistant` toggles hybrid agent
- [ ] `Show Query Analysis` adds “🔍 Query Analysis” with Intent/Complexity/Tools
- [ ] `Better Search Results (Reranking)` toggles and shows “✨ Results reranked for relevance”
- [ ] Header shows a single brain emoji (no duplicates)

## 5) Sidebar: Data Sources
- [ ] URL loading (single/multiple): success count visible; failures listed in “Failed URLs” expander
- [ ] GitHub URL auto-converts to raw format (info message visible)
- [ ] Metrics show: “✓ Data loaded success” and Vector Store stats (if embeddings available)
- [ ] Local CSV upload (multiple) works; errors visible in “Error Details” expander

## 6) Chat (Tab: 💬 Chat)
- [ ] Chat history renders; user and assistant messages display correctly
- [ ] With Hybrid Agent ON: shows badge “🛠️ Agent + Tools” or “🔀 Hybrid”
- [ ] With Hybrid Agent OFF: uses Conversational Retrieval Chain (RAG), no agent badge
- [ ] “📚 Sources” expander shows source documents and metadata
- [ ] “🔍 Query Analysis” expander visible when enabled
- [ ] Streaming response works (at least for OpenAI)

## 7) Reranking
- [ ] With reranking ON: source documents are reordered; “✨ Results reranked…” caption appears
- [ ] With reranking OFF: source order reflects base retriever

## 8) Recommendations (Hybrid Agent)
- [ ] Queries like “recommend X” return relevant properties with filters/preferences considered
- [ ] Response shows processing method (Agent/Hybrid/RAG)

## 9) Compare (Tab: 🔄 Compare)
- [ ] If no data: shows “Please load data…” info
- [ ] Select 2–4 properties via Multiselect; <2 or >4 shows appropriate messages
- [ ] Comparison UI renders tables/visualizations; differences in price/rooms/amenities visible

## 10) Insights (Tab: 📈 Insights)
- [ ] If no data: shows “Please load data…” info
- [ ] Metrics and charts display: price distribution, trend direction, location stats
- [ ] City selection updates charts and stats

## 11) Export (Tab: 💾 Export)
- [ ] Choosing CSV/JSON/Markdown/Excel generates a downloadable file
- [ ] “📥 Download” button downloads with correct structure
- [ ] “ℹ️ Format Information” expander explains formats

## 12) Analytics (Tab: 📊 Analytics)
- [ ] Current session metrics: Queries, Property Views, Exports, Duration
- [ ] Popular queries, Avg processing time (if events accumulated)
- [ ] “All-Time Statistics” displayed when aggregate data exists

## 13) Notifications (Tab: 🔔 Notifications)
- [ ] Email input; SMTP config (Gmail/Outlook/Custom) saves/validates
- [ ] Test email sends (success/error feedback shown)
- [ ] Preferences: frequency, thresholds, quiet hours, alert types — saved successfully
- [ ] Notification history lists recent items + delivery stats

## 14) Session (Sidebar: 🔄 Session)
- [ ] “Clear Chat” wipes chat and chain; app reruns
- [ ] “Reset All” clears `st.session_state`; app restarts cleanly

## 15) Internationalization & UI
- [ ] Language switching updates all labels (RU/EN/PL/ES/DE/FR/IT/中文)
- [ ] Light/Dark styles apply without rendering defects

## 16) Resilience & Errors
- [ ] If embeddings unavailable: clear warning shown; app remains functional
- [ ] CSV/URL errors shown in “Error Details” expander
- [ ] No secrets/API keys exposed in logs/UI

## 17) Performance (Quick Checks)
- [ ] Minimal lag on small dataset (≤ 2k properties)
- [ ] Switching model/k/temperature doesn’t freeze UI

---

## Notes (Cloud vs Local)
- Cloud: use remote providers (OpenAI/Anthropic/Google); Ollama/local models are not available.
- If ONNX/FastEmbed fail to install: rely on OpenAI embeddings (`OPENAI_API_KEY` required).
- Vector store may rebuild between runs in ephemeral environments.

## Bug Log
- Date/Time:
- Section:
- Repro Steps:
- Expected:
- Actual:
- Screenshots:
- Logs (no secrets):
