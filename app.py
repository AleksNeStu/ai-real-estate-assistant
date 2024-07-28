import pandas as pd
import streamlit as st
from langchain_openai import OpenAI
from data.csv_loader import DataLoaderLocalCsv
from common.cfg import *

@st.cache_data
def load_data():
    dataloader = DataLoaderLocalCsv()
    df_data = dataloader.df_formatted
    return df_data

# Load data using the cached function
df_data = load_data()
df_header = df_data.columns.tolist()

def generate_response(input_text, api_key):
    llm = OpenAI(temperature=0, openai_api_key=api_key)
    res = llm.invoke(input_text)
    st.info(res)
    return res

def fix_dataframe(df):
    # Iterate over each column in the DataFrame
    for column in df.columns:
        # Convert each column to string type
        df[column] = df[column].astype(str)
    return df

@st.cache_data
def display_filters():
    # Prepare data for horizontal display
    rows = []
    max_sample_size = 3  # Number of sample values to show

    for col in df_data.columns:
        unique_values = df_data[col].unique()
        # Limit the number of values to display
        sample_values = unique_values[:max_sample_size]
        # Fill up with empty strings if fewer values than max_sample_size
        sample_values = list(sample_values) + [''] * (max_sample_size - len(sample_values))
        rows.append([col] + sample_values)

    # Define columns based on the number of sample values
    columns = ["Header"] + [f"Value {i+1}" for i in range(max_sample_size)]

    # Convert to DataFrame for display
    df_summary = pd.DataFrame(rows, columns=columns)

    st.write("Here are the column headers and sample values:")
    df_summary_fixed = fix_dataframe(df_summary)
    st.table(df_summary_fixed)  # Display as a table

def display_api_key():
    st.markdown(
        'Setup [\"OPENAI\\_API\\_KEY\"]('
        'https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)',
        unsafe_allow_html=True
    )
    st.write('___')
    st.markdown(
        'Enter ['
        'OpenAI API Key](https://platform.openai.com/account/api-keys) * optional',
        unsafe_allow_html=True
    )

    openai_api_key = st.text_input(
        'OpenAI API Key [Optional]', type='password', key='api_key_input', label_visibility='collapsed'
    )
    return openai_api_key

def execute():
    st.title('🦾 AI real estate assistant Poland 🇵🇱')

    # Custom CSS to style the layout
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
            align-items: center; /* Align items vertically center */
            gap: 10px; /* Adjust space between elements */
            margin-bottom: 20px;
        }
        .form-container {
            flex: 1;
        }
        .api-key-container {
            flex: 1;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create a container for buttons and form
    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("Filters", key="filters"):
            st.session_state.show_filters = not st.session_state.get('show_filters', False)

    with col2:
        if st.button("OpenAI API Key", key="api_key"):
            st.session_state.show_api_key = not st.session_state.get('show_api_key', False)

    # Display the sections based on button clicks
    if st.session_state.get('show_filters', False):
        display_filters()

    if st.session_state.get('show_api_key', False):
        openai_api_key = display_api_key()
    else:
        openai_api_key = None

    # Create a form with a unique key
    st.markdown('<div class="form-container">', unsafe_allow_html=True)

    with st.form(key='full-width-form'):
        # Input for user message
        label = 'Talk to me about your dream house 😎:\n'
        msg_example = (
            'I am finding a cheap flat in Krakow.\n'
            'Better to have 2 rooms, not 1st floor, more than 30 square meters, with garage and storage room, '
            'also I would like to negotiate the final price.\n'
            'Do you have options for me?'
        )
        text = st.text_area(label, msg_example, height=300)  # Adjust height as needed

        # Submit button
        submitted = st.form_submit_button('Submit')
        key = OPENAI_API_KEY
        if submitted:
            # Ensure key starts with 'sk-' before proceeding
            if openai_api_key:
                if not openai_api_key.startswith('sk-'):
                    st.warning('Please enter a valid OpenAI API key starting with "sk-".', icon='⚠')
                else:
                    key = openai_api_key

            generate_response(text, key)

    st.markdown('</div>', unsafe_allow_html=True)

execute()
