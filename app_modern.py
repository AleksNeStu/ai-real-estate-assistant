"""
AI Real Estate Assistant - Modern Version (V3)

A modernized real estate assistant with:
- Multiple model providers (OpenAI, Anthropic, Google, Ollama)
- Persistent vector storage with ChromaDB
- Hybrid semantic search
- Modern UI with enhanced features
- Type-safe data models with Pydantic
"""

import streamlit as st
import pandas as pd
from typing import Optional, List
from pathlib import Path

# Import our custom modules
from config import settings, update_api_key
from models.provider_factory import ModelProviderFactory, get_model_display_info
from vector_store.chroma_store import ChromaPropertyStore, get_vector_store
from vector_store.hybrid_retriever import create_retriever
from data.csv_loader import DataLoaderCsv
from data.schemas import PropertyCollection, Property
from streaming import StreamHandler

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
    """Create conversational retrieval chain."""
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


def render_main_content():
    """Render main chat interface."""
    st.title(f"{settings.app_icon} AI Real Estate Assistant")
    st.caption("Find your perfect property with AI-powered search")

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
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                # Create or get conversation chain
                if st.session_state.conversation_chain is None:
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

                # Display answer
                response_placeholder.markdown(answer)

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
