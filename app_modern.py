"""
AI Real Estate Assistant - Modern Version (V3) - Phase 3

A modernized real estate assistant with:
- Multiple model providers (OpenAI, Anthropic, Google, Ollama)
- Persistent vector storage with ChromaDB
- Intelligent hybrid agent (RAG + Tools)
- Query analysis and routing
- Result reranking
- Personalized recommendations
- Modern UI with enhanced features
- Type-safe data models with Pydantic
- Market insights and analytics (Phase 3)
- Export functionality (Phase 3)
- Saved searches and comparisons (Phase 3)
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


def render_sidebar():
    """Render sidebar with model selection and configuration."""
    with st.sidebar:
        st.title(f"{settings.app_icon} {settings.app_title}")
        st.caption(f"Version {settings.version}")

        st.divider()

        # Model Provider Selection
        st.subheader("🤖 Model Configuration")

        # Get available providers
        providers = ModelProviderFactory.list_providers()
        provider_display = {
            "openai": "OpenAI",
            "anthropic": "Anthropic (Claude)",
            "google": "Google (Gemini)",
            "ollama": "Ollama (Local)",
        }

        selected_provider = st.selectbox(
            "Provider",
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
                }.get(selected_provider)

                if not api_key_env:
                    api_key = st.text_input(
                        f"{provider.display_name} API Key",
                        type="password",
                        help=f"Enter your {provider.display_name} API key"
                    )
                    if api_key:
                        update_api_key(selected_provider, api_key)
                        st.success("API key updated!")
                else:
                    st.success(f"✓ {provider.display_name} API key configured")

            # Model selection
            models = provider.list_models()
            model_options = {m.id: m for m in models}

            selected_model_id = st.selectbox(
                "Model",
                options=list(model_options.keys()),
                format_func=lambda x: model_options[x].display_name,
                key="model_select"
            )

            st.session_state.selected_model = selected_model_id

            # Display model info
            model_info = model_options[selected_model_id]
            with st.expander("ℹ️ Model Details"):
                info = get_model_display_info(model_info)
                st.write(f"**Context:** {info['context']}")
                st.write(f"**Cost:** {info['cost']}")
                if 'description' in info:
                    st.write(f"**Description:** {info['description']}")
                if 'recommended_for' in info:
                    st.write("**Best for:**", ", ".join(info['recommended_for']))

            # Advanced settings
            with st.expander("⚙️ Advanced Settings"):
                temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=settings.default_temperature,
                    step=0.1,
                    help="Controls randomness in responses"
                )
                st.session_state.temperature = temperature

                max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=256,
                    max_value=32000,
                    value=settings.default_max_tokens,
                    step=256,
                    help="Maximum length of response"
                )
                st.session_state.max_tokens = max_tokens

                k_results = st.slider(
                    "Results to retrieve",
                    min_value=1,
                    max_value=20,
                    value=settings.default_k_results,
                    help="Number of properties to search"
                )
                st.session_state.k_results = k_results

            # Phase 2 settings
            with st.expander("🧠 Intelligence Features (Phase 2)"):
                use_hybrid_agent = st.checkbox(
                    "Use Hybrid Agent",
                    value=st.session_state.use_hybrid_agent,
                    help="Enable intelligent routing between RAG and tools"
                )
                st.session_state.use_hybrid_agent = use_hybrid_agent

                show_query_analysis = st.checkbox(
                    "Show Query Analysis",
                    value=st.session_state.show_query_analysis,
                    help="Display query intent and routing decisions"
                )
                st.session_state.show_query_analysis = show_query_analysis

                use_reranking = st.checkbox(
                    "Use Result Reranking",
                    value=st.session_state.use_reranking,
                    help="Rerank results for better relevance"
                )
                st.session_state.use_reranking = use_reranking

                if use_hybrid_agent:
                    st.caption("✨ Agent tools: Mortgage calc, Comparator, Price analyzer")

        except Exception as e:
            st.error(f"Error configuring provider: {e}")

        st.divider()

        # Data Source Management
        st.subheader("📊 Data Sources")

        data_source_tab = st.radio(
            "Data Source",
            options=["URL", "Sample Datasets"],
            horizontal=True
        )

        if data_source_tab == "URL":
            csv_url = st.text_input(
                "CSV URL",
                placeholder="https://example.com/data.csv",
                help="Enter URL to CSV file with property data"
            )

            if st.button("Load Data", type="primary"):
                if csv_url:
                    load_data_from_url(csv_url)
                else:
                    st.warning("Please enter a CSV URL")

        else:
            st.write("Quick start with sample datasets:")
            if st.button("Load Sample Data", type="primary"):
                load_sample_data()

        # Data status
        if st.session_state.data_loaded:
            st.success(f"✓ Data loaded: {len(st.session_state.property_collection.properties)} properties")

            # Vector store stats
            if st.session_state.vector_store:
                stats = st.session_state.vector_store.get_stats()
                st.info(f"📦 Vector store: {stats.get('total_documents', 0)} documents")

        st.divider()

        # Session Management
        st.subheader("🔄 Session")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.conversation_chain = None
                st.rerun()

        with col2:
            if st.button("Reset All", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


def load_data_from_url(url: str):
    """Load property data from URL."""
    try:
        with st.spinner("Loading data from URL..."):
            # Load CSV
            loader = DataLoaderCsv(url)
            df = loader.load_df()
            df_formatted = loader.load_format_df(df)

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

            st.success(f"✓ Loaded {len(collection.properties)} properties!")
            st.session_state.data_loaded = True

    except Exception as e:
        st.error(f"Error loading data: {e}")


def load_sample_data():
    """Load sample datasets."""
    try:
        with st.spinner("Loading sample data..."):
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

    # Check if data is loaded
    if not st.session_state.data_loaded:
        st.info("👈 Please load property data from the sidebar to get started")

        # Show feature highlights
        st.subheader("✨ Features")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **🤖 Multiple AI Models**
            - OpenAI (GPT-4o, GPT-3.5)
            - Anthropic (Claude 3.5)
            - Google (Gemini 1.5)
            - Ollama (Local models)
            """)

        with col2:
            st.markdown("""
            **🔍 Smart Search**
            - Semantic search
            - Metadata filtering
            - Hybrid retrieval
            - MMR diversity
            """)

        with col3:
            st.markdown("""
            **💾 Persistent Storage**
            - ChromaDB vector store
            - Fast embeddings
            - Incremental updates
            - Source attribution
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
                        st.error("Failed to create hybrid agent")
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
                        st.error("Failed to create conversation chain")
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
    if not st.session_state.data_loaded or st.session_state.market_insights is None:
        st.info("👈 Please load property data from the sidebar to view market insights")
        return

    st.header("📈 Market Insights & Analytics")

    insights = st.session_state.market_insights

    # Overall statistics
    stats = insights.get_overall_statistics()

    st.subheader("Market Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Properties", stats.total_properties)
    with col2:
        st.metric("Average Price", f"${stats.average_price:.2f}")
    with col3:
        st.metric("Median Price", f"${stats.median_price:.2f}")
    with col4:
        st.metric("Avg Rooms", f"{stats.avg_rooms:.1f}")

    st.divider()

    # Price trends
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Price Trend")
        trend = insights.get_price_trend()
        trend_emoji = {
            "increasing": "📈",
            "decreasing": "📉",
            "stable": "➡️",
            "insufficient_data": "❓"
        }.get(trend.direction.value, "")

        st.metric(
            "Market Direction",
            f"{trend_emoji} {trend.direction.value.title()}",
            f"{trend.change_percent:+.1f}%"
        )
        st.caption(f"Confidence: {trend.confidence.title()}")
        st.caption(f"Sample size: {trend.sample_size} properties")

    with col2:
        st.subheader("Price Distribution")
        price_dist = insights.get_price_distribution(bins=8)
        dist_df = pd.DataFrame({
            'Price Range': price_dist['bins'],
            'Count': price_dist['counts']
        })
        st.bar_chart(dist_df.set_index('Price Range'))

    st.divider()

    # Location insights
    st.subheader("Location Analysis")

    cities = list(stats.cities.keys())
    if len(cities) >= 2:
        col1, col2 = st.columns(2)

        with col1:
            selected_city = st.selectbox("Select City", cities)
            if selected_city:
                city_insights = insights.get_location_insights(selected_city)
                if city_insights:
                    st.write(f"**{city_insights.city}**")
                    st.write(f"Properties: {city_insights.property_count}")
                    st.write(f"Avg Price: ${city_insights.avg_price:.2f}")
                    st.write(f"Median Price: ${city_insights.median_price:.2f}")
                    if city_insights.avg_price_per_sqm:
                        st.write(f"Price/sqm: ${city_insights.avg_price_per_sqm:.2f}")
                    st.write(f"Market Position: {city_insights.price_comparison.replace('_', ' ').title()}")

        with col2:
            if len(cities) >= 2:
                st.write("**City Comparison**")
                compare_city1 = st.selectbox("Compare City 1", cities, key="compare1")
                compare_city2 = st.selectbox("Compare City 2", [c for c in cities if c != compare_city1], key="compare2")

                if compare_city1 and compare_city2:
                    comparison = insights.compare_locations(compare_city1, compare_city2)
                    if 'error' not in comparison:
                        cheaper = comparison['cheaper_city']
                        diff = abs(comparison['price_difference'])
                        diff_pct = abs(comparison['price_difference_percent'])

                        st.success(f"💰 **{cheaper}** is cheaper by ${diff:.2f} ({diff_pct:.1f}%)")
    else:
        st.info("Load data with multiple cities for location comparison")

    st.divider()

    # Best value properties
    st.subheader("🏆 Best Value Properties")

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
    st.subheader("Amenity Impact on Price")

    amenity_impact = insights.get_amenity_impact_on_price()
    if amenity_impact:
        impact_df = pd.DataFrame([
            {'Amenity': amenity.replace('_', ' ').title(), 'Price Increase %': impact}
            for amenity, impact in amenity_impact.items()
        ]).sort_values('Price Increase %', ascending=False)

        st.bar_chart(impact_df.set_index('Amenity'))
        st.caption("Shows average % price increase for properties with each amenity")


def render_export_tab():
    """Render export functionality tab."""
    if not st.session_state.data_loaded or st.session_state.property_collection is None:
        st.info("👈 Please load property data from the sidebar to export")
        return

    st.header("💾 Export Properties")

    st.write("Export your property data in multiple formats for further analysis or sharing.")

    # Export options
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Export Settings")

        format_choice = st.selectbox(
            "Select Format",
            options=[fmt.value for fmt in ExportFormat],
            format_func=lambda x: {
                'csv': '📄 CSV (Spreadsheet)',
                'xlsx': '📊 Excel (Multi-sheet)',
                'json': '🔧 JSON (Structured)',
                'md': '📝 Markdown (Report)'
            }.get(x, x)
        )

        include_summary = st.checkbox("Include summary statistics", value=True)

        if format_choice == 'md':
            max_props = st.number_input(
                "Max properties in report",
                min_value=5,
                max_value=len(st.session_state.property_collection.properties),
                value=min(20, len(st.session_state.property_collection.properties))
            )

    with col2:
        st.subheader("Preview")

        properties = st.session_state.property_collection
        st.write(f"**Total Properties:** {len(properties.properties)}")

        if properties.properties:
            sample = properties.properties[0]
            st.write(f"**Sample:** {sample.city} - ${sample.price}/mo - {int(sample.rooms)} rooms")

        st.divider()

        # Export button
        if st.button("🚀 Generate Export", type="primary", use_container_width=True):
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
    with st.expander("ℹ️ Format Information"):
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
    if not st.session_state.data_loaded or st.session_state.property_collection is None:
        st.info("👈 Please load property data from the sidebar to compare properties")
        return

    st.header("🔄 Property Comparison")

    properties = st.session_state.property_collection.properties

    st.write("Select 2-4 properties to compare side-by-side")

    # Property selection
    st.subheader("Select Properties")

    # Create property display names
    property_options = {
        f"{i+1}. {prop.city} - ${prop.price} - {int(prop.rooms)}BR ({prop.id})": prop
        for i, prop in enumerate(properties)
    }

    selected_names = st.multiselect(
        "Choose properties (2-4)",
        options=list(property_options.keys()),
        max_selections=4
    )

    selected_properties = [property_options[name] for name in selected_names]

    if len(selected_properties) < 2:
        st.info("Please select at least 2 properties to compare")
        return

    if len(selected_properties) > 4:
        st.warning("Maximum 4 properties can be compared at once")
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
    st.header("📊 Session Analytics")

    tracker = st.session_state.session_tracker

    # Session statistics
    stats = tracker.get_session_stats()

    st.subheader("Current Session")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Queries", stats.total_queries)
    with col2:
        st.metric("Property Views", stats.total_property_views)
    with col3:
        st.metric("Exports", stats.total_exports)
    with col4:
        st.metric("Duration", f"{stats.total_duration_minutes:.1f} min")

    st.divider()

    # Popular queries
    if stats.total_queries > 0:
        st.subheader("Query Activity")

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
        st.subheader("Models Used")
        for model in stats.unique_models_used:
            st.write(f"- {model}")

    # Tools used
    if stats.tools_used:
        st.subheader("Tools Used")
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
            st.subheader("All-Time Statistics")

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


def render_main_content():
    """Render main content area with tabs."""
    st.title(f"{settings.app_icon} AI Real Estate Assistant")
    st.caption("Find your perfect property with AI-powered search")

    # Create tabs
    tabs = st.tabs(["💬 Chat", "📈 Market Insights", "🔄 Compare", "💾 Export", "📊 Analytics"])

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


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Render UI
    render_sidebar()
    render_main_content()

    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col2:
        st.caption(f"Powered by {st.session_state.get('selected_provider', 'AI').title()} | Version {settings.version}")


if __name__ == "__main__":
    main()
