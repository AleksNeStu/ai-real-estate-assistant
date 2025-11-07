"""
AI Real Estate Assistant - Modern Version (V3) - Phases 1-5

A modernized real estate assistant with:
- Multiple model providers (OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama)
- 25+ AI models across 6 providers
- Persistent vector storage with ChromaDB
- Intelligent hybrid agent (RAG + Tools)
- Query analysis and routing
- Result reranking
- Personalized recommendations
- Modern UI with enhanced features (multi-language, dark/light themes)
- Type-safe data models with Pydantic
- Market insights and analytics (Phase 3)
- Export functionality (Phase 3)
- Saved searches and comparisons (Phase 3)
- Advanced visualizations (Phase 4)
- Notification system with email alerts (Phase 5)

Copyright (c) 2025 Alex Nesterovich
GitHub: https://github.com/AleksNeStu/ai-real-estate-assistant
"""

import streamlit as st
import pandas as pd
from typing import Optional, List
from pathlib import Path
import uuid
from datetime import datetime

# Import our custom modules
from config import settings, update_api_key
from models.provider_factory import ModelProviderFactory, get_model_display_info
from vector_store.chroma_store import ChromaPropertyStore, get_vector_store
from vector_store.hybrid_retriever import create_retriever
from vector_store.reranker import create_reranker
from data.csv_loader import DataLoaderCsv
from data.schemas import PropertyCollection, Property, UserPreferences
from streaming import StreamHandler

# Phase 2 imports
from agents.hybrid_agent import create_hybrid_agent, HybridPropertyAgent
from agents.query_analyzer import analyze_query
from agents.recommendation_engine import create_recommendation_engine

# Phase 3 imports
from analytics import MarketInsights, SessionTracker, EventType
from utils import PropertyExporter, ExportFormat, SavedSearchManager
from ui.comparison_viz import PropertyComparison, display_comparison_ui, display_market_insights_ui

# Phase 5 imports
from notifications import (
    EmailService,
    EmailConfig,
    EmailProvider,
    EmailServiceFactory,
    NotificationPreferencesManager,
    NotificationPreferences,
    AlertFrequency,
    DigestDay,
    NotificationHistory,
    PriceDropTemplate,
    TestEmailTemplate
)

# Internationalization
from i18n import get_text, get_available_languages

# LangChain imports
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage


# Page configuration
st.set_page_config(
    page_title=settings.app_title,
    page_icon=settings.app_icon,
    layout=settings.page_layout,
    initial_sidebar_state=settings.initial_sidebar_state,
)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None

    if "property_collection" not in st.session_state:
        st.session_state.property_collection = None

    if "selected_provider" not in st.session_state:
        st.session_state.selected_provider = "openai"

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "gpt-4o-mini"

    if "conversation_chain" not in st.session_state:
        st.session_state.conversation_chain = None

    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False

    # Phase 2 state variables
    if "use_hybrid_agent" not in st.session_state:
        st.session_state.use_hybrid_agent = True

    if "show_query_analysis" not in st.session_state:
        st.session_state.show_query_analysis = False

    if "use_reranking" not in st.session_state:
        st.session_state.use_reranking = True

    if "hybrid_agent" not in st.session_state:
        st.session_state.hybrid_agent = None

    if "recommendation_engine" not in st.session_state:
        st.session_state.recommendation_engine = create_recommendation_engine()

    # Phase 3 state variables
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "session_tracker" not in st.session_state:
        st.session_state.session_tracker = SessionTracker(st.session_state.session_id)

    if "search_manager" not in st.session_state:
        st.session_state.search_manager = SavedSearchManager()

    if "market_insights" not in st.session_state:
        st.session_state.market_insights = None

    if "selected_properties_for_comparison" not in st.session_state:
        st.session_state.selected_properties_for_comparison = []

    # Phase 5 state variables
    if "notification_prefs_manager" not in st.session_state:
        st.session_state.notification_prefs_manager = NotificationPreferencesManager()

    if "notification_history" not in st.session_state:
        st.session_state.notification_history = NotificationHistory()

    if "email_service" not in st.session_state:
        st.session_state.email_service = None

    if "user_email" not in st.session_state:
        st.session_state.user_email = ""

    # Language support
    if "language" not in st.session_state:
        st.session_state.language = "en"

    # Theme support
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"


def render_sidebar():
    """Render sidebar with model selection and configuration."""
    with st.sidebar:
        lang = st.session_state.language
        st.title(f"{settings.app_icon} {get_text('app_title', lang)}")
        st.caption(f"{get_text('version', lang)} {settings.version}")

        st.divider()

        # Language Selection
        st.subheader(f"🌍 {get_text('language', lang)}")
        languages = get_available_languages()
        selected_lang = st.selectbox(
            get_text('language', lang),
            options=list(languages.keys()),
            format_func=lambda x: languages[x],
            index=list(languages.keys()).index(st.session_state.language),
            key="language_selector",
            label_visibility="collapsed"
        )
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()

        st.divider()

        # Theme Selection
        st.subheader(f"🎨 {get_text('theme', lang)}")
        theme_options = {
            "light": get_text('light_theme', lang),
            "dark": get_text('dark_theme', lang)
        }
        selected_theme = st.selectbox(
            get_text('theme', lang),
            options=list(theme_options.keys()),
            format_func=lambda x: theme_options[x],
            index=list(theme_options.keys()).index(st.session_state.theme),
            key="theme_selector",
            label_visibility="collapsed"
        )
        if selected_theme != st.session_state.theme:
            st.session_state.theme = selected_theme
            st.rerun()

        st.divider()

        # Model Provider Selection
        st.subheader(f"🤖 {get_text('model_config', lang)}")

        # Get available providers
        providers = ModelProviderFactory.list_providers()
        provider_display = {
            "openai": "OpenAI",
            "anthropic": "Anthropic (Claude)",
            "google": "Google (Gemini)",
            "grok": "Grok (xAI)",
            "deepseek": "DeepSeek",
            "ollama": "Ollama (Local)",
        }

        selected_provider = st.selectbox(
            get_text("provider", lang),
            options=providers,
            format_func=lambda x: provider_display.get(x, x),
            key="provider_select"
        )

        st.session_state.selected_provider = selected_provider

        # Get provider instance
        try:
            provider = ModelProviderFactory.get_provider(selected_provider)

            # API Key input for remote providers
            if provider.requires_api_key:
                api_key_env = {
                    "openai": settings.openai_api_key,
                    "anthropic": settings.anthropic_api_key,
                    "google": settings.google_api_key,
                    "grok": None,  # Will use XAI_API_KEY or GROK_API_KEY from env
                    "deepseek": None,  # Will use DEEPSEEK_API_KEY from env
                }.get(selected_provider)

                if not api_key_env:
                    api_key = st.text_input(
                        f"{provider.display_name} API Key",
                        type="password",
                        help=f"Enter your {provider.display_name} API key"
                    )
                    if api_key:
                        update_api_key(selected_provider, api_key)
                        st.success(get_text('api_key_updated_success', lang))
                else:
                    st.success(f"✓ {provider.display_name} API key configured")

            # Model selection
            models = provider.list_models()
            model_options = {m.id: m for m in models}

            selected_model_id = st.selectbox(
                get_text('model', lang),
                options=list(model_options.keys()),
                format_func=lambda x: model_options[x].display_name,
                key="model_select"
            )

            st.session_state.selected_model = selected_model_id

            # Display model info
            model_info = model_options[selected_model_id]
            with st.expander(f"ℹ️ {get_text('model_details', lang)}"):
                info = get_model_display_info(model_info)
                st.write(f"**{get_text('context', lang)}:** {info['context']}")
                st.write(f"**{get_text('cost', lang)}:** {info['cost']}")
                if 'description' in info:
                    st.write(f"**{get_text('description', lang)}:** {info['description']}")
                if 'recommended_for' in info:
                    st.write(f"**{get_text('best_for', lang)}:**", ", ".join(info['recommended_for']))

            # Advanced settings
            with st.expander(f"⚙️ {get_text('advanced_settings', lang)}"):
                temperature = st.slider(
                    get_text('temperature', lang),
                    min_value=0.0,
                    max_value=2.0,
                    value=settings.default_temperature,
                    step=0.1,
                    help=get_text('controls_randomness', lang)
                )
                st.session_state.temperature = temperature

                max_tokens = st.number_input(
                    get_text('max_tokens', lang),
                    min_value=256,
                    max_value=32000,
                    value=settings.default_max_tokens,
                    step=256,
                    help=get_text('maximum_response_length', lang)
                )
                st.session_state.max_tokens = max_tokens

                k_results = st.slider(
                    get_text('results_to_retrieve', lang),
                    min_value=1,
                    max_value=20,
                    value=settings.default_k_results,
                    help=get_text('num_properties_search', lang)
                )
                st.session_state.k_results = k_results

            # Phase 2 settings
            with st.expander(f"🧠 {get_text('intelligence_features', lang)}"):
                use_hybrid_agent = st.checkbox(
                    get_text('use_hybrid_agent', lang),
                    value=st.session_state.use_hybrid_agent,
                    help=get_text('enable_intelligent_routing', lang)
                )
                st.session_state.use_hybrid_agent = use_hybrid_agent

                show_query_analysis = st.checkbox(
                    get_text('show_query_analysis', lang),
                    value=st.session_state.show_query_analysis,
                    help=get_text('display_query_intent', lang)
                )
                st.session_state.show_query_analysis = show_query_analysis

                use_reranking = st.checkbox(
                    get_text('use_reranking', lang),
                    value=st.session_state.use_reranking,
                    help=get_text('rerank_better_relevance', lang)
                )
                st.session_state.use_reranking = use_reranking

                if use_hybrid_agent:
                    st.caption(f"✨ {get_text('agent_tools', lang)}")

        except Exception as e:
            st.error(f"Error configuring provider: {e}")

        st.divider()

        # Data Source Management
        st.subheader(f"📊 {get_text('data_sources', lang)}")

        data_source_tab = st.radio(
            get_text('data_source', lang),
            options=["URL", get_text('sample_datasets', lang)],
            horizontal=True
        )

        if data_source_tab == "URL":
            csv_url = st.text_input(
                get_text('csv_url', lang),
                placeholder=get_text('csv_url_placeholder', lang),
                help=get_text('csv_url_help', lang)
            )

            if st.button(get_text('load_data', lang), type="primary"):
                if csv_url:
                    load_data_from_url(csv_url)
                else:
                    st.warning(get_text('please_enter_csv_url', lang))

        else:
            st.write(get_text('quick_start_datasets', lang))
            if st.button(get_text('load_sample_data', lang), type="primary"):
                load_sample_data()

        # Data status
        if st.session_state.data_loaded:
            st.success(f"✓ {get_text('data_loaded_success', lang)}: {len(st.session_state.property_collection.properties)} {get_text('properties', lang)}")

            # Vector store stats
            if st.session_state.vector_store:
                stats = st.session_state.vector_store.get_stats()
                st.info(f"📦 {get_text('vector_store', lang)}: {stats.get('total_documents', 0)} {get_text('documents', lang)}")

        st.divider()

        # Session Management
        st.subheader(f"🔄 {get_text('session', lang)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(get_text('clear_chat', lang), use_container_width=True):
                st.session_state.messages = []
                st.session_state.conversation_chain = None
                st.rerun()

        with col2:
            if st.button(get_text('reset_all', lang), use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


def load_data_from_url(url: str):
    """Load property data from URL."""
    lang = st.session_state.language

    try:
        with st.spinner(get_text('loading_data_url', lang)):
            # Load CSV
            loader = DataLoaderCsv(url)

            # Show converted URL if it's a GitHub URL
            raw_url = DataLoaderCsv.convert_github_url_to_raw(url)
            if raw_url != url:
                st.info(f"🔗 Converting GitHub URL to raw format: {raw_url}")

            df = loader.load_df()
            st.info(f"📊 Loaded {len(df)} rows from CSV")

            df_formatted = loader.load_format_df(df)
            st.info(f"✨ Formatted {len(df_formatted)} properties")

            # Convert to PropertyCollection
            collection = PropertyCollection.from_dataframe(
                df_formatted,
                source=url
            )

            st.session_state.property_collection = collection

            # Load into vector store
            load_into_vector_store(collection)

            # Create market insights (Phase 3)
            st.session_state.market_insights = MarketInsights(collection)

            st.success(f"✓ {get_text('data_loaded_success', lang)}: {len(collection.properties)} {get_text('properties', lang)}!")
            st.session_state.data_loaded = True

    except Exception as e:
        st.error(f"❌ {get_text('error_occurred', lang)}: {str(e)}")
        # Show more details in an expander
        with st.expander("🔍 Error Details"):
            st.code(str(e))
            st.write("**Tip:** Make sure the URL points to a valid CSV file. For GitHub, use the 'Raw' URL.")


def load_sample_data():
    """Load sample datasets."""
    lang = st.session_state.language

    try:
        with st.spinner(get_text('loading_sample_data', lang)):
            all_properties = []

            # Load first sample dataset
            url = settings.default_datasets[0]
            loader = DataLoaderCsv(url)
            df = loader.load_df()
            df_formatted = loader.load_format_df(df)

            collection = PropertyCollection.from_dataframe(
                df_formatted,
                source="sample_data"
            )

            st.session_state.property_collection = collection

            # Load into vector store
            load_into_vector_store(collection)

            # Create market insights (Phase 3)
            st.session_state.market_insights = MarketInsights(collection)

            st.success(f"✓ Loaded {len(collection.properties)} sample properties!")
            st.session_state.data_loaded = True

    except Exception as e:
        st.error(f"Error loading sample data: {e}")


def load_into_vector_store(collection: PropertyCollection):
    """Load property collection into vector store."""
    try:
        # Get or create vector store
        if st.session_state.vector_store is None:
            st.session_state.vector_store = get_vector_store()

        # Add properties
        vector_store = st.session_state.vector_store
        added = vector_store.add_property_collection(
            collection,
            replace_existing=True
        )

        print(f"Added {added} properties to vector store")

    except Exception as e:
        st.error(f"Error loading into vector store: {e}")
        raise


def create_conversation_chain():
    """Create conversational retrieval chain (simple RAG mode)."""
    try:
        # Get model configuration
        provider_name = st.session_state.selected_provider
        model_id = st.session_state.selected_model
        temperature = st.session_state.get("temperature", settings.default_temperature)
        max_tokens = st.session_state.get("max_tokens", settings.default_max_tokens)
        k_results = st.session_state.get("k_results", settings.default_k_results)

        # Create model
        stream_handler = StreamHandler(st.empty())
        llm = ModelProviderFactory.create_model(
            model_id=model_id,
            provider_name=provider_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
            callbacks=[stream_handler]
        )

        # Create retriever
        retriever = create_retriever(
            vector_store=st.session_state.vector_store,
            k=k_results,
            search_type="mmr"
        )

        # Create memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

        # Create chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            return_source_documents=True,
            verbose=True
        )

        return chain

    except Exception as e:
        st.error(f"Error creating conversation chain: {e}")
        return None


def create_hybrid_agent_instance():
    """Create hybrid agent instance (Phase 2)."""
    try:
        # Get model configuration
        provider_name = st.session_state.selected_provider
        model_id = st.session_state.selected_model
        temperature = st.session_state.get("temperature", settings.default_temperature)
        max_tokens = st.session_state.get("max_tokens", settings.default_max_tokens)
        k_results = st.session_state.get("k_results", settings.default_k_results)

        # Create model
        llm = ModelProviderFactory.create_model(
            model_id=model_id,
            provider_name=provider_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=False,  # Agent doesn't support streaming in same way
        )

        # Create retriever
        retriever = create_retriever(
            vector_store=st.session_state.vector_store,
            k=k_results,
            search_type="mmr"
        )

        # Create hybrid agent
        agent = create_hybrid_agent(
            llm=llm,
            retriever=retriever,
            use_tools=True,
            verbose=True
        )

        return agent

    except Exception as e:
        st.error(f"Error creating hybrid agent: {e}")
        return None


def render_chat_tab():
    """Render chat interface tab."""
    lang = st.session_state.language

    # Check if data is loaded
    if not st.session_state.data_loaded:
        st.info(get_text('please_load_data', lang))

        # Show feature highlights
        st.subheader(get_text('features_title', lang))
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            **{get_text('chat_tab_features', lang)}**
            - {get_text('chat_feature_1', lang)}
            - {get_text('chat_feature_2', lang)}
            - {get_text('chat_feature_3', lang)}
            - {get_text('chat_feature_4', lang)}
            """)

        with col2:
            st.markdown(f"""
            **{get_text('compare_tab_features', lang)}**
            - {get_text('compare_feature_1', lang)}
            - {get_text('compare_feature_2', lang)}
            - {get_text('compare_feature_3', lang)}
            - {get_text('compare_feature_4', lang)}
            """)

        with col3:
            st.markdown(f"""
            **{get_text('export_tab_features', lang)}**
            - {get_text('export_feature_1', lang)}
            - {get_text('export_feature_2', lang)}
            - {get_text('export_feature_3', lang)}
            - {get_text('export_feature_4', lang)}
            """)

        return

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Display source documents if available
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 Sources"):
                    for i, doc in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {i}:**")
                        st.markdown(doc.page_content[:300] + "...")
                        st.json(doc.metadata)

    # Chat input
    if prompt := st.chat_input("Ask about properties..."):
        # Track query start time (Phase 3)
        import time
        query_start = time.time()

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Show query analysis if enabled
        if st.session_state.show_query_analysis:
            analysis = analyze_query(prompt)
            with st.expander("🔍 Query Analysis", expanded=False):
                st.write(f"**Intent:** {analysis.intent.value}")
                st.write(f"**Complexity:** {analysis.complexity.value}")
                st.write(f"**Tools needed:** {[t.value for t in analysis.tools_needed]}")
                if analysis.extracted_filters:
                    st.write(f"**Extracted filters:** {analysis.extracted_filters}")
                st.write(f"**Should use agent:** {analysis.should_use_agent()}")

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                # Use hybrid agent or regular chain based on settings
                use_hybrid = st.session_state.use_hybrid_agent

                if use_hybrid:
                    # Create or get hybrid agent
                    if st.session_state.hybrid_agent is None:
                        with st.spinner("Initializing AI agent..."):
                            st.session_state.hybrid_agent = create_hybrid_agent_instance()

                    if st.session_state.hybrid_agent is None:
                        st.error(get_text('failed_create_agent', lang))
                        return

                    # Get response from hybrid agent
                    with st.spinner("🧠 Analyzing query and processing..."):
                        response = st.session_state.hybrid_agent.process_query(
                            query=prompt,
                            return_analysis=True
                        )

                    answer = response["answer"]
                    source_docs = response.get("source_documents", [])
                    method = response.get("method", "unknown")
                    intent = response.get("intent", "unknown")

                    # Display method badge
                    if method == "agent":
                        st.caption("🛠️ Processed with AI Agent + Tools")
                    elif method == "hybrid":
                        st.caption("🔀 Processed with Hybrid (RAG + Agent)")
                    else:
                        st.caption("📚 Processed with RAG")

                else:
                    # Use regular RAG chain
                    if st.session_state.conversation_chain is None:
                        with st.spinner("Initializing conversation..."):
                            st.session_state.conversation_chain = create_conversation_chain()

                    if st.session_state.conversation_chain is None:
                        st.error(get_text('failed_create_chain', lang))
                        return

                    # Get response
                    with st.spinner("Thinking..."):
                        response = st.session_state.conversation_chain({
                            "question": prompt
                        })

                    answer = response["answer"]
                    source_docs = response.get("source_documents", [])

                # Apply reranking if enabled
                if st.session_state.use_reranking and source_docs:
                    reranker = create_reranker(advanced=True)
                    reranked = reranker.rerank(
                        query=prompt,
                        documents=source_docs,
                        k=min(5, len(source_docs))
                    )
                    source_docs = [doc for doc, score in reranked]
                    st.caption("✨ Results reranked for relevance")

                # Display answer
                response_placeholder.markdown(answer)

                # Track query completion (Phase 3)
                processing_time_ms = int((time.time() - query_start) * 1000)
                intent_val = intent if use_hybrid else "unknown"
                st.session_state.session_tracker.track_query(
                    query=prompt,
                    intent=intent_val,
                    complexity="medium",
                    processing_time_ms=processing_time_ms
                )

                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": source_docs
                })

                # Display sources
                if source_docs:
                    with st.expander(f"📚 Sources ({len(source_docs)})"):
                        for i, doc in enumerate(source_docs, 1):
                            st.markdown(f"**Source {i}:**")
                            st.markdown(doc.page_content[:300] + "...")
                            with st.container():
                                st.json(doc.metadata, expanded=False)

            except Exception as e:
                st.error(f"Error generating response: {e}")
                st.exception(e)

                # Track error (Phase 3)
                st.session_state.session_tracker.track_error(
                    error_type=type(e).__name__,
                    error_message=str(e)
                )


def render_market_insights_tab():
    """Render market insights and analytics tab."""
    lang = st.session_state.language

    if not st.session_state.data_loaded or st.session_state.market_insights is None:
        st.info(get_text('please_load_data_insights', lang))
        return

    st.header(f"📈 {get_text('market_insights_analytics', lang)}")

    insights = st.session_state.market_insights

    # Overall statistics
    stats = insights.get_overall_statistics()

    st.subheader(get_text('market_overview', lang))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(get_text('total_properties', lang), stats.total_properties)
    with col2:
        st.metric(get_text('average_price', lang), f"${stats.average_price:.2f}")
    with col3:
        st.metric(get_text('median_price', lang), f"${stats.median_price:.2f}")
    with col4:
        st.metric(get_text('avg_rooms', lang), f"{stats.avg_rooms:.1f}")

    st.divider()

    # Price trends
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(get_text('price_trend', lang))
        trend = insights.get_price_trend()
        trend_emoji = {
            "increasing": "📈",
            "decreasing": "📉",
            "stable": "➡️",
            "insufficient_data": "❓"
        }.get(trend.direction.value, "")

        st.metric(
            get_text('market_direction', lang),
            f"{trend_emoji} {trend.direction.value.title()}",
            f"{trend.change_percent:+.1f}%"
        )
        st.caption(f"{get_text('confidence_high', lang).split(':')[0]}: {trend.confidence.title()}")
        st.caption(f"{get_text('sample_size', lang)}: {trend.sample_size} {get_text('properties', lang).lower()}")

    with col2:
        st.subheader(get_text('price_distribution', lang))
        price_dist = insights.get_price_distribution(bins=8)
        dist_df = pd.DataFrame({
            'Price Range': price_dist['bins'],
            'Count': price_dist['counts']
        })
        st.bar_chart(dist_df.set_index('Price Range'))

    st.divider()

    # Location insights
    st.subheader(get_text('location_analysis', lang))

    cities = list(stats.cities.keys())
    if len(cities) >= 2:
        col1, col2 = st.columns(2)

        with col1:
            selected_city = st.selectbox(get_text('select_city', lang), cities)
            if selected_city:
                city_insights = insights.get_location_insights(selected_city)
                if city_insights:
                    st.write(f"**{city_insights.city}**")
                    st.write(f"{get_text('properties', lang)}: {city_insights.property_count}")
                    st.write(f"{get_text('average_price', lang).split()[0]}: ${city_insights.avg_price:.2f}")
                    st.write(f"{get_text('median_price', lang)}: ${city_insights.median_price:.2f}")
                    if city_insights.avg_price_per_sqm:
                        st.write(f"Price/sqm: ${city_insights.avg_price_per_sqm:.2f}")
                    st.write(f"{get_text('market_position', lang)} {city_insights.price_comparison.replace('_', ' ').title()}")

        with col2:
            if len(cities) >= 2:
                st.write(f"**{get_text('city_comparison', lang)}**")
                compare_city1 = st.selectbox(get_text('compare_city_1', lang), cities, key="compare1")
                compare_city2 = st.selectbox(get_text('compare_city_2', lang), [c for c in cities if c != compare_city1], key="compare2")

                if compare_city1 and compare_city2:
                    comparison = insights.compare_locations(compare_city1, compare_city2)
                    if 'error' not in comparison:
                        cheaper = comparison['cheaper_city']
                        diff = abs(comparison['price_difference'])
                        diff_pct = abs(comparison['price_difference_percent'])

                        st.success(f"💰 **{cheaper}** {get_text('is_cheaper_by', lang)} ${diff:.2f} ({diff_pct:.1f}%)")
    else:
        st.info(get_text('load_multiple_cities', lang))

    st.divider()

    # Best value properties
    st.subheader(f"🏆 {get_text('best_value_properties', lang)}")

    best_values = insights.get_best_value_properties(top_n=5)
    if best_values:
        for i, prop in enumerate(best_values, 1):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{i}. {prop['city']}**")
            with col2:
                st.write(f"${prop['price']:.0f}/mo")
            with col3:
                st.write(f"{int(prop['rooms'])} rooms")
            with col4:
                st.write(f"⭐ {prop['value_score']:.2f}")

    st.divider()

    # Amenity impact
    st.subheader(get_text('amenity_impact_title', lang))

    amenity_impact = insights.get_amenity_impact_on_price()
    if amenity_impact:
        impact_df = pd.DataFrame([
            {'Amenity': amenity.replace('_', ' ').title(), 'Price Increase %': impact}
            for amenity, impact in amenity_impact.items()
        ]).sort_values('Price Increase %', ascending=False)

        st.bar_chart(impact_df.set_index('Amenity'))
        st.caption(get_text('amenity_impact_caption', lang))


def render_export_tab():
    """Render export functionality tab."""
    lang = st.session_state.language

    if not st.session_state.data_loaded or st.session_state.property_collection is None:
        st.info(get_text('please_load_data_export', lang))
        return

    st.header(f"💾 {get_text('export_properties', lang)}")

    st.write(get_text('export_subtitle', lang))

    # Export options
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader(get_text('export_settings', lang))

        format_choice = st.selectbox(
            get_text('select_format', lang),
            options=[fmt.value for fmt in ExportFormat],
            format_func=lambda x: {
                'csv': '📄 CSV (Spreadsheet)',
                'xlsx': '📊 Excel (Multi-sheet)',
                'json': '🔧 JSON (Structured)',
                'md': '📝 Markdown (Report)'
            }.get(x, x)
        )

        include_summary = st.checkbox(get_text('include_summary_stats', lang), value=True)

        if format_choice == 'md':
            max_props = st.number_input(
                get_text('max_properties_report', lang),
                min_value=5,
                max_value=len(st.session_state.property_collection.properties),
                value=min(20, len(st.session_state.property_collection.properties))
            )

    with col2:
        st.subheader(get_text('preview', lang))

        properties = st.session_state.property_collection
        st.write(f"**{get_text('total_properties', lang)}:** {len(properties.properties)}")

        if properties.properties:
            sample = properties.properties[0]
            st.write(f"**{get_text('sample', lang)}** {sample.city} - ${sample.price}/mo - {int(sample.rooms)} {get_text('rooms', lang).lower()}")

        st.divider()

        # Export button
        if st.button(get_text('generate_export_button', lang), type="primary", use_container_width=True):
            try:
                with st.spinner(f"Generating {format_choice.upper()} export..."):
                    exporter = PropertyExporter(properties)

                    if format_choice == 'csv':
                        data = exporter.export_to_csv()
                        filename = exporter.get_filename(ExportFormat.CSV)
                        mime = "text/csv"

                    elif format_choice == 'xlsx':
                        data = exporter.export_to_excel(
                            include_summary=include_summary,
                            include_statistics=True
                        )
                        filename = exporter.get_filename(ExportFormat.EXCEL)
                        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        data = data.getvalue()

                    elif format_choice == 'json':
                        data = exporter.export_to_json(
                            pretty=True,
                            include_metadata=include_summary
                        )
                        filename = exporter.get_filename(ExportFormat.JSON)
                        mime = "application/json"

                    else:  # markdown
                        data = exporter.export_to_markdown(
                            include_summary=include_summary,
                            max_properties=max_props if format_choice == 'md' else None
                        )
                        filename = exporter.get_filename(ExportFormat.MARKDOWN)
                        mime = "text/markdown"

                    # Track export (Phase 3)
                    st.session_state.session_tracker.track_export(
                        format=format_choice,
                        property_count=len(properties.properties)
                    )

                    st.success("✅ Export generated successfully!")

                    st.download_button(
                        label=f"📥 Download {format_choice.upper()}",
                        data=data,
                        file_name=filename,
                        mime=mime,
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"Error generating export: {e}")
                st.exception(e)

    st.divider()

    # Export format descriptions
    with st.expander(f"ℹ️ {get_text('format_information', lang)}"):
        st.markdown("""
        **CSV (Comma-Separated Values)**
        - Simple spreadsheet format
        - Compatible with Excel, Google Sheets
        - Best for data import/export

        **Excel (XLSX)**
        - Multi-sheet workbook
        - Includes summary and statistics sheets
        - Best for comprehensive reports

        **JSON (JavaScript Object Notation)**
        - Structured data format
        - Best for API integration
        - Machine-readable

        **Markdown (MD)**
        - Human-readable report format
        - Best for documentation
        - Includes summaries and descriptions
        """)


def render_comparisons_tab():
    """Render property comparison tab."""
    lang = st.session_state.language

    if not st.session_state.data_loaded or st.session_state.property_collection is None:
        st.info(get_text('please_load_data_compare', lang))
        return

    st.header(f"🔄 {get_text('property_comparison', lang)}")

    properties = st.session_state.property_collection.properties

    st.write(get_text('select_2_4_properties', lang))

    # Property selection
    st.subheader(get_text('select_properties', lang))

    # Create property display names
    property_options = {
        f"{i+1}. {prop.city} - ${prop.price} - {int(prop.rooms)}BR ({prop.id})": prop
        for i, prop in enumerate(properties)
    }

    selected_names = st.multiselect(
        get_text('choose_properties_2_4', lang),
        options=list(property_options.keys()),
        max_selections=4
    )

    selected_properties = [property_options[name] for name in selected_names]

    if len(selected_properties) < 2:
        st.info(get_text('select_at_least_2', lang))
        return

    if len(selected_properties) > 4:
        st.warning(get_text('maximum_4_properties', lang))
        return

    st.divider()

    # Display comparison
    try:
        display_comparison_ui(selected_properties)

    except Exception as e:
        st.error(f"Error creating comparison: {e}")
        st.exception(e)


def render_analytics_tab():
    """Render session analytics tab."""
    lang = st.session_state.language

    st.header(f"📊 {get_text('session_analytics', lang)}")

    tracker = st.session_state.session_tracker

    # Session statistics
    stats = tracker.get_session_stats()

    st.subheader(get_text('current_session', lang))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(get_text('queries', lang), stats.total_queries)
    with col2:
        st.metric(get_text('property_views', lang), stats.total_property_views)
    with col3:
        st.metric(get_text('exports', lang), stats.total_exports)
    with col4:
        st.metric(get_text('duration', lang), f"{stats.total_duration_minutes:.1f} min")

    st.divider()

    # Popular queries
    if stats.total_queries > 0:
        st.subheader(get_text('query_activity', lang))

        popular = tracker.get_popular_queries(top_n=5)
        if popular:
            st.write("**Most Common Intents:**")
            for item in popular:
                st.write(f"- {item['intent']}: {item['count']} queries")

        # Average processing time
        avg_time = tracker.get_avg_processing_time(EventType.QUERY)
        if avg_time:
            st.metric("Avg Query Processing Time", f"{avg_time:.0f}ms")

    st.divider()

    # Models used
    if stats.unique_models_used:
        st.subheader(get_text('models_used', lang))
        for model in stats.unique_models_used:
            st.write(f"- {model}")

    # Tools used
    if stats.tools_used:
        st.subheader(get_text('tools_used', lang))
        tool_counts = {}
        for tool in stats.tools_used:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {tool}: {count} times")

    st.divider()

    # Aggregate statistics
    try:
        aggregate = SessionTracker.get_aggregate_stats()
        if aggregate.get('total_sessions', 0) > 0:
            st.subheader(get_text('all_time_stats', lang))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Sessions", aggregate.get('total_sessions', 0))
            with col2:
                st.metric("Total Queries", aggregate.get('total_queries', 0))
            with col3:
                st.metric("Total Exports", aggregate.get('total_exports', 0))

    except Exception:
        pass  # Aggregate stats not available

    st.divider()

    st.caption(f"Session ID: {st.session_state.session_id}")


def render_notifications_tab():
    """Render notifications configuration and management tab."""
    lang = st.session_state.language

    st.header(f"🔔 {get_text('notification_settings', lang)}")

    # User email input
    st.subheader(f"📧 {get_text('user_information', lang)}")
    user_email = st.text_input(
        get_text('your_email', lang),
        value=st.session_state.user_email,
        placeholder=get_text('email_placeholder', lang),
        help=get_text('email_help', lang)
    )

    if user_email != st.session_state.user_email:
        st.session_state.user_email = user_email

    st.divider()

    # Email Service Configuration
    st.subheader(f"⚙️ {get_text('email_service_config', lang)}")

    with st.expander(get_text('configure_email', lang), expanded=st.session_state.email_service is None):
        provider_options = {
            "Gmail": EmailProvider.GMAIL,
            "Outlook": EmailProvider.OUTLOOK,
            "Custom SMTP": EmailProvider.CUSTOM
        }

        selected_provider = st.selectbox(
            "Email Provider",
            options=list(provider_options.keys()),
            help="Select your email service provider"
        )

        provider = provider_options[selected_provider]

        col1, col2 = st.columns(2)
        with col1:
            smtp_username = st.text_input(
                "Email Username",
                help="Your email address for SMTP authentication"
            )
        with col2:
            smtp_password = st.text_input(
                "Email Password/App Password",
                type="password",
                help="Use app-specific password for Gmail/Outlook"
            )

        if provider == EmailProvider.CUSTOM:
            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input("SMTP Server", value="smtp.example.com")
            with col2:
                smtp_port = st.number_input("SMTP Port", value=587, min_value=1, max_value=65535)

            use_tls = st.checkbox("Use TLS", value=True)

        if st.button("💾 Save Email Configuration", type="primary"):
            if not smtp_username or not smtp_password:
                st.error(get_text('provide_credentials', lang))
            else:
                try:
                    if provider == EmailProvider.GMAIL:
                        email_service = EmailServiceFactory.create_gmail_service(
                            username=smtp_username,
                            password=smtp_password
                        )
                    elif provider == EmailProvider.OUTLOOK:
                        email_service = EmailServiceFactory.create_outlook_service(
                            username=smtp_username,
                            password=smtp_password
                        )
                    else:  # Custom
                        config = EmailConfig(
                            provider=provider,
                            smtp_server=smtp_server,
                            smtp_port=smtp_port,
                            username=smtp_username,
                            password=smtp_password,
                            from_email=smtp_username,
                            use_tls=use_tls
                        )
                        email_service = EmailService(config)

                    st.session_state.email_service = email_service
                    st.success("✅ Email service configured successfully!")
                except Exception as e:
                    st.error(f"❌ Error configuring email service: {str(e)}")

    # Test email configuration
    if st.session_state.email_service and user_email:
        if st.button("📧 Send Test Email"):
            try:
                subject, html = TestEmailTemplate.render(user_name=user_email.split('@')[0])
                success = st.session_state.email_service.send_email(
                    to_email=user_email,
                    subject=subject,
                    body=html,
                    html=True
                )
                if success:
                    st.success("✅ Test email sent successfully! Check your inbox.")
                else:
                    st.error("❌ Failed to send test email. Check your configuration.")
            except Exception as e:
                st.error(f"❌ Error sending test email: {str(e)}")

    st.divider()

    # Notification Preferences
    if user_email:
        st.subheader("🔔 Notification Preferences")

        prefs_manager = st.session_state.notification_prefs_manager
        prefs = prefs_manager.get_preferences(user_email)

        # Enable/Disable notifications
        enabled = st.checkbox(
            "Enable Notifications",
            value=prefs.enabled,
            help="Turn notifications on or off"
        )

        col1, col2 = st.columns(2)

        with col1:
            # Alert frequency
            frequency_options = {
                "Instant": AlertFrequency.INSTANT,
                "Hourly": AlertFrequency.HOURLY,
                "Daily Digest": AlertFrequency.DAILY,
                "Weekly Digest": AlertFrequency.WEEKLY
            }

            current_freq = next(k for k, v in frequency_options.items() if v == prefs.alert_frequency)

            selected_frequency = st.selectbox(
                "Alert Frequency",
                options=list(frequency_options.keys()),
                index=list(frequency_options.keys()).index(current_freq),
                help="How often to receive notifications"
            )

            # Price drop threshold
            price_threshold = st.slider(
                "Price Drop Threshold (%)",
                min_value=1.0,
                max_value=20.0,
                value=prefs.price_drop_threshold,
                step=0.5,
                help="Minimum price drop percentage to trigger alert"
            )

            # Max alerts per day
            max_alerts = st.number_input(
                "Max Alerts Per Day",
                min_value=1,
                max_value=100,
                value=prefs.max_alerts_per_day,
                help="Maximum number of alerts to receive per day"
            )

        with col2:
            # Quiet hours
            st.write("**Quiet Hours** (No alerts during these times)")
            quiet_start = st.time_input(
                "Quiet Hours Start",
                value=datetime.strptime(prefs.quiet_hours_start or "22:00", "%H:%M").time()
            )
            quiet_end = st.time_input(
                "Quiet Hours End",
                value=datetime.strptime(prefs.quiet_hours_end or "08:00", "%H:%M").time()
            )

            # Digest time (if daily/weekly)
            if frequency_options[selected_frequency] in [AlertFrequency.DAILY, AlertFrequency.WEEKLY]:
                digest_time = st.time_input(
                    "Digest Send Time",
                    value=datetime.strptime(prefs.daily_digest_time, "%H:%M").time()
                )

                if frequency_options[selected_frequency] == AlertFrequency.WEEKLY:
                    digest_day = st.selectbox(
                        "Weekly Digest Day",
                        options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                        index=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(prefs.weekly_digest_day.value)
                    )

        # Alert type toggles
        st.write("**Alert Types**")
        alert_col1, alert_col2 = st.columns(2)

        with alert_col1:
            enable_price_drops = st.checkbox(
                "💰 Price Drop Alerts",
                value="price_drop" in [a.value for a in prefs.enabled_alerts],
                help="Get notified when property prices drop"
            )
            enable_new_properties = st.checkbox(
                "🏠 New Property Alerts",
                value="new_property" in [a.value for a in prefs.enabled_alerts],
                help="Get notified about new properties"
            )

        with alert_col2:
            enable_saved_searches = st.checkbox(
                "🔍 Saved Search Matches",
                value="saved_search_match" in [a.value for a in prefs.enabled_alerts],
                help="Get notified when properties match your saved searches"
            )
            enable_market_updates = st.checkbox(
                "📈 Market Updates",
                value="market_update" in [a.value for a in prefs.enabled_alerts],
                help="Get market insights and trends"
            )

        # Save preferences button
        if st.button("💾 Save Notification Preferences", type="primary"):
            try:
                # Build enabled alerts set
                enabled_alerts = set()
                if enable_price_drops:
                    from notifications.alert_manager import AlertType as AMAlertType
                    enabled_alerts.add(AMAlertType.PRICE_DROP)
                if enable_new_properties:
                    from notifications.alert_manager import AlertType as AMAlertType
                    enabled_alerts.add(AMAlertType.NEW_PROPERTY)
                if enable_saved_searches:
                    from notifications.alert_manager import AlertType as AMAlertType
                    enabled_alerts.add(AMAlertType.SAVED_SEARCH_MATCH)
                if enable_market_updates:
                    from notifications.alert_manager import AlertType as AMAlertType
                    enabled_alerts.add(AMAlertType.MARKET_UPDATE)

                # Update preferences
                prefs_manager.update_preferences(
                    user_email,
                    enabled=enabled,
                    alert_frequency=frequency_options[selected_frequency],
                    price_drop_threshold=price_threshold,
                    max_alerts_per_day=max_alerts,
                    quiet_hours_start=quiet_start.strftime("%H:%M"),
                    quiet_hours_end=quiet_end.strftime("%H:%M"),
                    enabled_alerts=enabled_alerts
                )

                if frequency_options[selected_frequency] in [AlertFrequency.DAILY, AlertFrequency.WEEKLY]:
                    prefs_manager.update_preferences(
                        user_email,
                        daily_digest_time=digest_time.strftime("%H:%M")
                    )

                    if frequency_options[selected_frequency] == AlertFrequency.WEEKLY:
                        day_map = {
                            "Monday": DigestDay.MONDAY,
                            "Tuesday": DigestDay.TUESDAY,
                            "Wednesday": DigestDay.WEDNESDAY,
                            "Thursday": DigestDay.THURSDAY,
                            "Friday": DigestDay.FRIDAY,
                            "Saturday": DigestDay.SATURDAY,
                            "Sunday": DigestDay.SUNDAY
                        }
                        prefs_manager.update_preferences(
                            user_email,
                            weekly_digest_day=day_map[digest_day]
                        )

                st.success("✅ Notification preferences saved successfully!")
            except Exception as e:
                st.error(f"❌ Error saving preferences: {str(e)}")

    st.divider()

    # Notification History
    if user_email:
        st.subheader("📊 Notification History")

        history = st.session_state.notification_history
        user_notifications = history.get_user_notifications(user_email, limit=20)

        if user_notifications:
            st.write(f"**Recent Notifications** (Last 20)")

            for notification in user_notifications:
                with st.expander(
                    f"{notification.subject} - {notification.status.value.title()} ({notification.created_at.strftime('%Y-%m-%d %H:%M')})"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {notification.notification_type.value}")
                        st.write(f"**Status:** {notification.status.value}")
                    with col2:
                        if notification.sent_at:
                            st.write(f"**Sent:** {notification.sent_at.strftime('%Y-%m-%d %H:%M')}")
                        if notification.delivered_at:
                            st.write(f"**Delivered:** {notification.delivered_at.strftime('%Y-%m-%d %H:%M')}")

                    if notification.error_message:
                        st.error(f"Error: {notification.error_message}")

            # Statistics
            stats = history.get_user_statistics(user_email)

            st.divider()
            st.write("**Your Notification Statistics**")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Sent", stats['total_sent'])
            with col2:
                st.metric("Delivered", stats['total_delivered'])
            with col3:
                st.metric("Delivery Rate", f"{stats['delivery_rate']:.1f}%")
            with col4:
                st.metric("Failed", stats['total_failed'])
        else:
            st.info(get_text('no_notifications_yet', lang))


def render_main_content():
    """Render main content area with tabs."""
    lang = st.session_state.language
    st.title(f"{settings.app_icon} {get_text('app_title', lang)}")
    st.caption(get_text('app_subtitle', lang))

    # Create tabs
    tabs = st.tabs([
        get_text('tab_chat', lang),
        get_text('tab_insights', lang),
        get_text('tab_compare', lang),
        get_text('tab_export', lang),
        get_text('tab_analytics', lang),
        get_text('tab_notifications', lang)
    ])

    with tabs[0]:
        render_chat_tab()

    with tabs[1]:
        render_market_insights_tab()

    with tabs[2]:
        render_comparisons_tab()

    with tabs[3]:
        render_export_tab()

    with tabs[4]:
        render_analytics_tab()

    with tabs[5]:
        render_notifications_tab()


def apply_theme():
    """Apply custom CSS based on selected theme."""
    theme = st.session_state.get('theme', 'dark')

    if theme == 'dark':
        st.markdown("""
        <style>
            /* Dark theme colors - Comprehensive */
            .stApp {
                background-color: #0e1117 !important;
                color: #fafafa !important;
            }
            .stSidebar {
                background-color: #1a1d24 !important;
            }
            /* Sidebar text elements */
            .stSidebar .stMarkdown, .stSidebar h1, .stSidebar h2, .stSidebar h3,
            .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar .stCaption {
                color: #fafafa !important;
            }
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #1a1d24 !important;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: #262730 !important;
                color: #fafafa !important;
                border-radius: 4px 4px 0px 0px;
            }
            .stTabs [aria-selected="true"] {
                background-color: #3a3f4b !important;
                color: #fafafa !important;
            }
            /* Form inputs */
            .stTextInput>div>div>input, .stSelectbox>div>div>div,
            .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
                background-color: #262730 !important;
                color: #fafafa !important;
                border-color: #3a3f4b !important;
            }
            /* Buttons */
            .stButton>button {
                background-color: #262730 !important;
                color: #fafafa !important;
                border: 1px solid #3a3f4b !important;
            }
            .stButton>button:hover {
                background-color: #3a3f4b !important;
                border: 1px solid #4a4f5b !important;
            }
            /* All text elements */
            .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li {
                color: #fafafa !important;
            }
            /* Chat messages */
            .stChatMessage {
                background-color: #1a1d24 !important;
                color: #fafafa !important;
            }
            /* Metrics */
            div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
                color: #fafafa !important;
            }
            /* Expanders */
            .stExpander {
                background-color: #262730 !important;
                border-color: #3a3f4b !important;
            }
            .stExpander p, .stExpander span, .stExpander label {
                color: #fafafa !important;
            }
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: #fafafa !important;
            }
            /* Form controls */
            .stRadio label, .stCheckbox label {
                color: #fafafa !important;
            }
            .stSlider label, .stSlider p {
                color: #fafafa !important;
            }
            /* Header bar */
            [data-testid="stHeader"] {
                background-color: #0e1117 !important;
            }
            /* Captions */
            .stCaption {
                color: #b0b0b0 !important;
            }
            /* Alerts */
            .stAlert {
                background-color: #262730 !important;
                color: #fafafa !important;
            }
            /* Dataframes */
            .stDataFrame {
                color: #fafafa !important;
            }
            /* Multiselect */
            .stMultiSelect label {
                color: #fafafa !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light theme (default Streamlit theme)
        st.markdown("""
        <style>
            /* Light theme colors (enhanced) */
            .stApp {
                background-color: #ffffff;
                color: #31333F;
            }
            .stSidebar {
                background-color: #f0f2f6;
            }
        </style>
        """, unsafe_allow_html=True)


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Apply theme
    apply_theme()

    # Render UI
    render_sidebar()
    render_main_content()

    # Footer
    lang = st.session_state.language
    st.divider()
    st.caption(f"© 2025 [Alex Nesterovich](https://github.com/AleksNeStu) | {get_text('version', lang)} {settings.version}")


if __name__ == "__main__":
    main()
