"""
AI Real Estate Assistant - Main Application (V1)

This is the main application file for the AI Real Estate Assistant project (Version 1).
It creates a Streamlit web interface where users can load property data from CSV files,
interact with an AI assistant to find properties matching their criteria, and view
conversation history.

The application uses LangChain's pandas dataframe agent to process real estate data
and respond to user queries.
"""

import pandas as pd
import streamlit as st
import io
import requests
from yarl import URL

from ai.agent import RealEstateGPT  # Import the AI agent class
from common.cfg import *  # Import configuration variables
from data.csv_loader import DataLoaderCsv  # Import CSV loading utilities

# Configure the Streamlit page layout
st.set_page_config(
    page_title="🦾 AI Real Estate Assistant",
    page_icon='💬',
    layout='wide'  # Use the full width of the browser window
)

# Sample user messages for demonstration and testing purposes
_MSG1 = (
    'I am finding a cheap flat in Krakow.\n'
    'Better to have 1-3 rooms, not 1st floor, more than 20 square meters, with parking, '
    'also I would like to negotiate the final price.\n'
    'Please provide properties with important details in json format\n'
    'Do you have options for me?'
)
_MSG2 = (
    'Thanks. Good selection. But please find only one from those, use provided last time, which has middle price for rent, but cheapest price for media')
_MSG3 = 'Looks like you provided me property for Bialystok, but I need for Krakow and from the previous selection'

# Mapping of iteration number to sample messages
# Currently only using the first message, others are commented out
MSG_MAP = {
    0: _MSG1,
    # 1: _MSG2,
    # 2: _MSG3
}

def load_csv_data(url: str, format_data=False):
    """
    Load data from a single CSV URL and optionally format it.
    
    Parameters:
        url (str): URL to the CSV file
        format_data (bool): Whether to format the data after loading
        
    Returns:
        DataFrame: The loaded and optionally formatted dataframe
    """
    dataloader = DataLoaderCsv(URL(url))  # Create dataloader for this URL
    df = dataloader.load_df()  # Load the raw dataframe
    df_formatted = dataloader.load_format_df(df) if format_data else df  # Format if requested
    return df_formatted

def load_data(urls, format_data = None, expected_rows = None):
    """
    Load and combine data from multiple CSV URLs.
    
    This function loads data from each URL provided, combines them, and 
    optionally formats and trims the combined dataset to a specified size.
    
    Parameters:
        urls (list): List of URLs to CSV files
        format_data (bool): Whether to format the combined data
        expected_rows (int): Number of rows to aim for in the final dataset
        
    Returns:
        DataFrame: The combined and optionally formatted dataframe
    """
    all_data = []
    empty_df = pd.DataFrame()  # Fallback in case of errors
    
    # Load data from each URL
    for url in urls:
        try:
            df_formatted = load_csv_data(url)
            all_data.append(df_formatted)
        except Exception as e:
            st.error(f"Error loading data from {url}: {e}")
            return empty_df

    # Combine all loaded dataframes
    if all_data:
        data_final = pd.concat(all_data, ignore_index=True)
        print(f'Merged data rows: {len(data_final)}')
        
        # Format and trim the dataset if requested
        if format_data and expected_rows:
            data_final = DataLoaderCsv.format_df(data_final, rows_count=expected_rows)
            print(f'Concatenated data rows: {len(data_final)}')
        return data_final

    return empty_df

def fix_dataframe(df):
    """
    Convert all columns in a dataframe to string type.
    
    This ensures that all data can be displayed properly in Streamlit tables.
    
    Parameters:
        df (DataFrame): The pandas dataframe to convert
        
    Returns:
        DataFrame: The dataframe with all columns converted to strings
    """
    for column in df.columns:
        df[column] = df[column].astype(str)
    return df

@st.cache_data  # Cache the result to avoid recomputing when the page is refreshed
def display_filters(df_data):
    """
    Display a summary of the dataframe columns and sample values.
    
    Creates a table showing each column and up to 3 sample values
    from each column to give the user an idea of the data structure.
    
    Parameters:
        df_data (DataFrame): The dataframe to display filters for
    """
    if df_data.empty:
        st.warning("Data is empty. No filters to display.")
        return

    rows = []
    max_sample_size = 3  # Show up to 3 sample values per column

    # Create a summary with column names and sample values
    for col in df_data.columns:
        unique_values = df_data[col].unique()
        sample_values = unique_values[:max_sample_size]
        # Pad with empty strings if fewer than max_sample_size unique values
        sample_values = list(sample_values) + [''] * (max_sample_size - len(sample_values))
        rows.append([col] + sample_values)

    # Create a summary dataframe
    columns = ["Header"] + [f"Value {i+1}" for i in range(max_sample_size)]
    df_summary = pd.DataFrame(rows, columns=columns)

    st.write("Here are the column headers and sample values:")
    df_summary_fixed = fix_dataframe(df_summary)  # Convert to string for display
    st.table(df_summary_fixed)  # Show as a fixed-width table

def display_api_key():
    """
    Display the UI components for entering an OpenAI API key.
    
    This function shows instructional text with links to Streamlit secrets
    management and OpenAI API key page, followed by a password input field.
    
    Returns:
        str: The API key entered by the user
    """
    # Display link to Streamlit secrets management documentation
    st.markdown(
        'Setup [\"OPENAI\\_API\\_KEY\"]('
        'https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)',
        unsafe_allow_html=True
    )
    st.write('___')
    
    # Display link to OpenAI API key page
    st.markdown(
        'Enter [OpenAI API Key](https://platform.openai.com/account/api-keys) * optional',
        unsafe_allow_html=True
    )

    # Create a password input field for the API key
    openai_api_key = st.text_input(
        'OpenAI API Key [Optional]', type='password', key='api_key_input', label_visibility='collapsed'
    )
    return openai_api_key

def process_query(query, use_test_data):
    """
    Process a user query and generate a response.
    
    This function either generates a fake response using Faker (if use_test_data is True)
    or passes the query to the AI agent to get a real response.
    The query and response are then stored in the conversation history.
    
    Parameters:
        query (str): The user's input query
        use_test_data (bool): Whether to use fake test data instead of actual AI responses
    """
    if query:
        if use_test_data:
            # Generate a fake response for testing
            response = 'FAKE: '
            response += fake_en.text(max_nb_chars=100)  # Generate random English text
        else:
            # Get a real response from the AI agent
            response = st.session_state['ai_agent'].ask_qn(query)

        # Handle errors and add to conversation history
        if response.startswith('GPT Error:'):
            st.warning(response, icon='⚠')  # Display warning for errors
            st.session_state['conversation_history'].insert(0, {'Client': query, 'AI': ''})
        else:
            # Add the successful exchange to conversation history (newest first)
            st.session_state['conversation_history'].insert(0, {'Client': query, 'AI': response})

def display_conversation():
    """
    Display the conversation history between the user and the AI.
    
    This function renders the conversation history as a series of text areas,
    with the most recent exchanges displayed first.
    """
    # Initialize conversation history if it doesn't exist
    if 'conversation_history' not in st.session_state:
        st.session_state['conversation_history'] = []

    # Display each exchange in the conversation history
    if st.session_state['conversation_history']:
        for idx, exchange in enumerate(st.session_state['conversation_history'], start=1):
            # Display user messages with client icon
            st.text_area(f"Client 🧑:", value=exchange['Client'], height=100, disabled=True, key=f"client_{idx}")
            # Display AI responses with robot icon
            st.text_area(f"AI 🤖:", value=exchange['AI'], height=100, disabled=True, key=f"ai_{idx}")

# Initialize session state variables
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = []  # To store the conversation exchanges

if 'iteration' not in st.session_state:
    st.session_state['iteration'] = 0  # Track the conversation turns

if 'test_msg' not in st.session_state:
    st.session_state['test_msg'] = _MSG1  # Set default test message

# Set the application title
st.title('🦾 AI Real Estate Assistant')

st.markdown("""
    <style>
    .full-width-form {
        width: 100%;
    }
    .full-width-form .stTextArea {
        width: 100%;
    }
    .full-width-form .stButton {
        width: 100%;
    }
    .form-container {
        margin: 20px;
    }
    .api-key-container {
        margin-top: 20px;
    }
    .button-container {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
    }
    .form-container {
        flex: 1;
    }
    .api-key-container {
        flex: 1;
    }
    .conversation-container {
        max-height: 90vh; /* Adjust to fill more of the screen */
        overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# Create a two-column layout
col1, col2 = st.columns([2, 2])  # Equal width for input and conversation columns

# Left column: Input and Settings
with ((col1)):
    st.write("### Input and Settings")

    # Input area for multiple CSV URLs
    urls_input = st.text_area('Enter CSV URLs (one per line)', 
                             GIT_DATA_SET_URLS_STR,  # Default URLs from config
                             key='csv_urls', 
                             height=200)

    # Process the input text into a list of URLs
    urls = [url.strip() for url in urls_input.split('\n') if url.strip()]

    # Button to trigger data loading
    load_data_button = st.button("Load Data")

    # Data processing options
    format_data = st.checkbox('Concatenate & And format data', 
                             value=True,  # Enabled by default
                             key='format_data')
    
    expected_rows = st.number_input('Expected Rows Count', 
                                   min_value=1, 
                                   value=2000,  # Default row count
                                   step=500, 
                                   key='expected_rows')

    # Handle data loading when the button is clicked
    if load_data_button and urls:
        # Load data from the URLs and store in session state
        st.session_state['df_data'] = load_data(urls, format_data, expected_rows)
        st.session_state['df_urls'] = urls  # Save URLs for reference
        
        # Display confirmation or error message
        if not st.session_state['df_data'].empty:
            st.write(f"Data loaded successfully.")
            st.write(f"Rows count: {len(st.session_state['df_data'])}")
        else:
            st.error("Failed to load data or the data is empty.")

    # Toggle button for API key input visibility
    if st.button("OpenAI API Key", key="api_key"):
        # Toggle the visibility state
        st.session_state.show_api_key = not st.session_state.get('show_api_key', False)

    # Display API key input field if toggled on
    if st.session_state.get('show_api_key', False):
        openai_api_key = display_api_key()
    else:
        openai_api_key = None

    # Option to use fake test responses instead of real AI
    use_test_data = st.checkbox('Use Test Responses', value=True, key='use_test_data')

    # Create a form for user input and submission
    with st.form(key='full-width-form'):
        # Input prompt for the user
        label = 'Talk to me about your dream property 😎:\n'
        
        # Track conversation iterations
        iteration = st.session_state.get('iteration', 0)
        
        # Get test message from session state
        test_msg = st.session_state['test_msg']
        
        # Text area for user input
        text = st.text_area(label=label, height=200)
        
        # Submit button to process the query
        submitted = st.form_submit_button('Submit')
        
        # Handle form submission
        if submitted:
            # Determine which API key to use (user-provided or from config)
            if openai_api_key:
                if not openai_api_key.startswith('sk-'):
                    st.warning('Please enter a valid OpenAI API key starting with "sk-".', icon='⚠')
                key = openai_api_key
            else:
                key = OPENAI_API_KEY

            # Validate the API key format
            if not key.startswith('sk-'):
                st.warning('Please enter a valid OpenAI API key starting with "sk-".', icon='⚠')
            else:
                # Get the loaded data from session state
                df_data_act = st.session_state.get('df_data')
                if df_data_act is None or df_data_act.empty:
                    st.error('Please load data first.')
                else:
                    # Initialize the AI agent if not already done
                    if 'ai_agent' not in st.session_state:
                        st.session_state['ai_agent'] = RealEstateGPT(df_data_act, key)
                    
                    # Process the user's query and get a response
                    process_query(text, use_test_data)
                    
                    # Clear test message after first iteration and increment counter
                    if st.session_state['iteration'] == 0:
                        st.session_state['test_msg'] = ''
                    st.session_state['iteration'] += 1

# Right column: Conversation History
with col2:
    st.write("### Conversation History")
    
    # Create a scrollable container for the conversation history
    with st.container():
        # Add custom CSS class for styling the container
        st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
        
        # Display all conversation exchanges
        display_conversation()
        
        # Close the custom CSS container
        st.markdown('</div>', unsafe_allow_html=True)