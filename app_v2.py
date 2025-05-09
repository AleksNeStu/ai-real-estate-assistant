"""
AI Real Estate Assistant - RAG Implementation (V2)

This file implements the Version 2 of the AI Real Estate Assistant, which uses 
a Retrieval-Augmented Generation (RAG) approach with vector databases and 
ConversationalRetrievalChain from LangChain.

Unlike V1 which uses a pandas dataframe agent, this version:
1. Uses vector databases for efficient information retrieval
2. Supports multiple LLM models (OpenAI GPT, Llama)
3. Implements streaming responses for better user experience
4. Provides source references for transparency
"""

import os  # For path operations and environment variables
import utils  # Custom utilities for the application
import requests  # For HTTP requests to load external data
import traceback  # For detailed error tracking
import validators  # For validating URLs
import streamlit as st  # Web UI framework
from streaming import StreamHandler  # Custom handler for streaming responses
from common.cfg import *  # Import configuration variables
from langchain.memory import ConversationBufferMemory  # For storing conversation context
from langchain.chains import ConversationalRetrievalChain  # Main RAG chain
import pandas as pd  # For data manipulation
from langchain_core.documents.base import Document  # LangChain document structure
from langchain_community.document_loaders.csv_loader import CSVLoader  # For loading local CSV files
from langchain_community.document_loaders.dataframe import DataFrameLoader  # For loading pandas DataFrames
from langchain.text_splitter import RecursiveCharacterTextSplitter  # For chunking documents
from langchain_community.vectorstores import DocArrayInMemorySearch  # In-memory vector store

# Configure the Streamlit page
st.set_page_config(page_title="🦾 AI Real Estate Assistant", page_icon='💬', layout='wide')
st.header('Chat with Real Estate AI Assistant')  # Main heading
st.write('[![view source code ](https://img.shields.io/badge/view_source_code-gray?logo=github)](https://github.com/AleksNeStu/ai-real-estate-assistant)')  # GitHub link

class ChatbotWeb:
    """
    Main class that implements the RAG-based chatbot for real estate data.
    
    This class handles:
    1. Loading and processing CSV data from URLs
    2. Setting up vector stores for efficient retrieval
    3. Configuring the LLM and embedding models
    4. Managing the conversational interface
    5. Displaying source references for transparency
    """

    def __init__(self):
        """
        Initialize the ChatbotWeb instance.
        
        This method:
        1. Synchronizes Streamlit session state variables
        2. Configures the Language Model (LLM) based on user selection
        3. Sets up the embedding model for vector searches
        """
        utils.sync_st_session()  # Ensure session state consistency
        self.llm = utils.configure_llm()  # Set up the language model (OpenAI or Llama)
        self.embedding_model = utils.configure_embedding_model()  # Set up embeddings for vector search

    def scrape_website(self, url):
        """
        Scrape content from a website using a proxy service.
        
        This method uses r.jina.ai as a proxy to fetch web content,
        which helps avoid CORS issues and standardizes web scraping.
        
        Parameters:
            url (str): URL to scrape content from
            
        Returns:
            str: The scraped content or None if an error occurs
        """
        content = ""
        try:
            base_url = "https://r.jina.ai/"  # Proxy service to avoid CORS issues
            final_url = base_url + url
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'
            }
            response = requests.get(final_url, headers=headers)
            content = response.text
            return content
        except Exception as e:
            traceback.print_exc()  # Print detailed error information

    def load_docs_from_csv_local(self, path):
        """
        Load documents from a local CSV file.
        
        Uses LangChain's CSVLoader to convert each row in the CSV file
        to a Document object that can be processed by the RAG pipeline.
        
        Parameters:
            path (str): Path to the local CSV file
            
        Returns:
            list: List of Document objects or None if an error occurs
        """
        content = ""
        try:
            loader = CSVLoader(path)  # Initialize loader for CSV
            docs = loader.load()  # Load CSV into Document objects
            return docs
        except Exception as e:
            traceback.print_exc()  # Print detailed error information

    def load_docs_from_csv_web(self, url):
        """
        Load documents from a CSV file hosted on the web.
        
        First downloads the CSV file as a pandas DataFrame, then converts
        each row to a Document object using DataFrameLoader.
        
        Parameters:
            url (str): URL to the CSV file
            
        Returns:
            list: List of Document objects or None if an error occurs
        """
        try:
            df = pd.read_csv(url)  # Download and parse CSV
            loader = DataFrameLoader(data_frame=df)  # Convert DataFrame to Documents
            docs = loader.load()
            return docs
        except Exception as e:
            traceback.print_exc()

    def load_data_from_csv_web(self, url):
        """
        Load data from a web-hosted CSV and convert it to a string representation.
        
        This method is optimized for RAG processing by converting the CSV data
        to a dictionary string representation that can be easily chunked and embedded.
        
        Parameters:
            url (str): URL to the CSV file
            
        Returns:
            str: String representation of the CSV data or None if an error occurs
        """
        try:
            df = pd.read_csv(url)  # Download and parse CSV
            # Convert to dictionary format for better structure in embeddings
            # Alternative formats are commented out:
            # content = df.to_string(index=False)
            # content = '\n'.join(df['content'].tolist())
            content = str(df.to_dict(orient='records'))  # List of row dictionaries
            return content
        except Exception as e:
            traceback.print_exc()

    @st.cache_resource(show_spinner='Analyzing csv data set', ttl=3600)
    def setup_vectordb(_self, websites):
        """
        Set up a vector database from the provided website URLs.
        
        This method:
        1. Loads CSV data from each URL
        2. Creates Document objects with metadata
        3. Splits documents into chunks for better retrieval
        4. Creates and returns a vector database for semantic search
        
        The function is cached using Streamlit's cache_resource for performance,
        with a time-to-live (TTL) of 1 hour before it needs to be refreshed.
        
        Parameters:
            _self: The ChatbotWeb instance
            websites (list): List of URLs to CSV files
            
        Returns:
            DocArrayInMemorySearch: A vector database for document retrieval
        """
        # Scrape and load documents
        docs = []
        for url in websites:
            # Alternative approach using local files (commented out):
            # loader = CSVLoader('./ai-real-estate-assistant/dataset/pl/apartments_rent_pl_2024_01.csv')
            # docs.extend(loader.load())
            
            # Create a Document object for each website with source metadata
            docs.append(Document(
                page_content=_self.load_data_from_csv_web(url),  # Content from CSV
                metadata={"source": url}  # Track source URL for citations
                )
            )

        # Split documents into smaller chunks for better retrieval
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Split into chunks of 1000 characters
            chunk_overlap=200  # With 200 character overlap between chunks
        )
        splits = text_splitter.split_documents(docs)

        # Create in-memory vector database using DocArrayInMemorySearch
        # Uses the embedding model configured in __init__
        vectordb = DocArrayInMemorySearch.from_documents(splits, _self.embedding_model)

        # Alternative vector store implementation (commented out):
        # from langchain_community.vectorstores import Chroma
        # from langchain_openai import OpenAIEmbeddings
        # vectordb = Chroma.from_documents(splits, OpenAIEmbeddings())

        return vectordb

    def setup_qa_chain(self, vectordb):
        """
        Set up a Conversational Retrieval Chain for question answering.
        
        This method configures:
        1. A retriever from the vector database with Maximum Marginal Relevance (MMR)
        2. Conversation memory to maintain context across interactions
        3. A QA chain that combines the retriever, memory, and LLM
        
        Parameters:
            vectordb: The vector database to use for retrieval
            
        Returns:
            ConversationalRetrievalChain: The configured QA chain
        """
        # Define retriever using Maximum Marginal Relevance (MMR) for diverse results
        retriever = vectordb.as_retriever(
            search_type='mmr',  # MMR helps ensure diversity in retrieved documents
            search_kwargs={
                'k': 2,  # Return 2 most relevant documents
                'fetch_k': 4  # Fetch 4 candidates before selecting the 2 most diverse
            }
        )

        # Setup memory for contextual conversation
        memory = ConversationBufferMemory(
            memory_key='chat_history',  # Key used to access chat history in the chain
            output_key='answer',  # Key used to store the final answer
            return_messages=True  # Return chat history as message objects
        )

        # Setup QA chain that combines the LLM, retriever, and memory
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,  # Language model configured in __init__
            retriever=retriever,  # Document retriever
            memory=memory,  # Conversation memory
            return_source_documents=True,  # Include source documents in the output
            verbose=False  # Don't print debug info
        )
        return qa_chain

    @utils.enable_chat_history  # Decorator to enable persistent chat history
    def main(self):
        """
        Main method to run the Streamlit application.
        
        This method:
        1. Sets up the UI for URL input
        2. Handles adding and clearing data sources
        3. Creates the vector database and QA chain
        4. Manages the chat interface
        5. Processes user queries and displays responses with citations
        """
        csv_url = 'CSV Data Set URL'  # Label for the URL input
        
        # Initialize session state for websites if not already set
        if "websites" not in st.session_state:
            st.session_state["websites"] = []  # List to store added URLs
            # Load default URLs from config
            st.session_state["value_urls"] = GIT_DATA_SET_URLS_STR.split('\n')

        # Set default URL for the input field
        url_val = ''
        value_urls = st.session_state.get("value_urls", [])
        if len(value_urls) >= 1:
            url_val = value_urls[0]  # Use first URL as default
            
        # Create text area for URL input in the sidebar
        web_url = st.sidebar.text_area(
            label=f'Enter {csv_url}s',
            placeholder="https://",
            # help="To add another website, modify this field after adding the website.",
            value=url_val
        )
        # Alternative way to display URLs (commented out)
        # st.sidebar.text(GIT_DATA_SET_URLS_STR)

        # Button to add new URL to the list
        if st.sidebar.button(":heavy_plus_sign: Add Website"):
            # Validate URL format before adding
            valid_url = web_url.startswith('http') and validators.url(web_url)
            if not valid_url:
                # Show error for invalid URL
                st.sidebar.error(f"Invalid URL! Please check {csv_url} that you have entered.", icon="⚠️")
            else:
                # Add valid URL to the session state
                st.session_state["websites"].append(web_url)

        # Button to clear all URLs
        if st.sidebar.button("Clear", type="primary"):
            st.session_state["websites"] = []

        # Remove duplicates by converting to set and back to list
        websites = list(set(st.session_state["websites"]))

        # Stop execution if no websites are provided
        if not websites:
            st.error(f"Please enter {csv_url} to continue!")
            st.stop()
        else:
            # Show list of loaded data sources in sidebar
            st.sidebar.info("CSV Data Sets - \n - {}".format('\n - '.join(websites)))

            # Set up vector database and QA chain
            vectordb = self.setup_vectordb(websites)  # Create vector database from URLs
            qa_chain = self.setup_qa_chain(vectordb)  # Configure the QA chain

            # Create chat input field
            user_query = st.chat_input(placeholder="Ask me question about real estate properties!")
            
            # Process query when user inputs a message
            if websites and user_query:
                # Display the user message
                utils.display_msg(user_query, 'user')

                # Display assistant response with streaming
                with st.chat_message("assistant"):
                    # Set up streaming handler to show response as it's generated
                    st_cb = StreamHandler(st.empty())
                    
                    # Process the query through the QA chain
                    result = qa_chain.invoke(
                        {"question": user_query},
                        {"callbacks": [st_cb]}  # Use streaming callback
                    )
                    
                    # Extract and store the response
                    response = result["answer"]
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    utils.print_qa(ChatbotWeb, user_query, response)  # Log the Q&A

                    # Display source references for transparency
                    for idx, doc in enumerate(result['source_documents'], 1):
                        # Extract filename from the source URL
                        url = os.path.basename(doc.metadata['source'])
                        # Create a reference title with clickable popup
                        ref_title = f":blue[Reference {idx}: *{url}*]"
                        # Show document content in a popup when clicked
                        with st.popover(ref_title):
                            st.caption(doc.page_content)


# Application entry point
if __name__ == "__main__":
    obj = ChatbotWeb()  # Create an instance of the chatbot
    obj.main()  # Run the main application loop
