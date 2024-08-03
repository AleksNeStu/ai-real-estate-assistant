import pandas as pd
import streamlit as st
import io
import requests
from yarl import URL

from ai.agent import RealEstateGPT
from common.cfg import *
from data.csv_loader import DataLoaderCsv

st.set_page_config(
    page_title="🦾 AI Real Estate Assistant Poland",
    page_icon='💬',
    layout='wide'
)

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

MSG_MAP = {
    0: _MSG1,
    1: _MSG2,
    2: _MSG3
}

# @st.cache_data
def load_data(_url: URL):
    try:
        dataloader = DataLoaderCsv(_url)
        df = dataloader.load_df()
        df_formatted = dataloader.load_format_df(df)
        return df_formatted
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error

def fix_dataframe(df):
    for column in df.columns:
        df[column] = df[column].astype(str)
    return df

@st.cache_data
def display_filters(df_data):
    if df_data.empty:
        st.warning("Data is empty. No filters to display.")
        return

    rows = []
    max_sample_size = 3

    for col in df_data.columns:
        unique_values = df_data[col].unique()
        sample_values = unique_values[:max_sample_size]
        sample_values = list(sample_values) + [''] * (max_sample_size - len(sample_values))
        rows.append([col] + sample_values)

    columns = ["Header"] + [f"Value {i+1}" for i in range(max_sample_size)]
    df_summary = pd.DataFrame(rows, columns=columns)

    st.write("Here are the column headers and sample values:")
    df_summary_fixed = fix_dataframe(df_summary)
    st.table(df_summary_fixed)

def display_api_key():
    st.markdown(
        'Setup [\"OPENAI\\_API\\_KEY\"]('
        'https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)',
        unsafe_allow_html=True
    )
    st.write('___')
    st.markdown(
        'Enter [OpenAI API Key](https://platform.openai.com/account/api-keys) * optional',
        unsafe_allow_html=True
    )

    openai_api_key = st.text_input(
        'OpenAI API Key [Optional]', type='password', key='api_key_input', label_visibility='collapsed'
    )
    return openai_api_key

def process_query(query, use_test_data):
    if query:
        if use_test_data:
            response = 'FAKE: '
            response += fake_en.text(max_nb_chars=100)
        else:
            response = st.session_state['ai_agent'].ask_qn(query)

        if response.startswith('GPT Error:'):
            st.warning(response, icon='⚠')
            st.session_state['conversation_history'].insert(0, {'Client': query, 'AI': ''})
        else:
            st.session_state['conversation_history'].insert(0, {'Client': query, 'AI': response})

def display_conversation():
    if 'conversation_history' not in st.session_state:
        st.session_state['conversation_history'] = []

    if st.session_state['conversation_history']:
        for idx, exchange in enumerate(st.session_state['conversation_history'], start=1):
            st.text_area(f"Client 🧑:", value=exchange['Client'], height=100, disabled=True, key=f"client_{idx}")
            st.text_area(f"AI 🤖:", value=exchange['AI'], height=100, disabled=True, key=f"ai_{idx}")

# Initialize session state variables if not already present
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = []

if 'iteration' not in st.session_state:
    st.session_state['iteration'] = 0

st.title('🦾 AI Real Estate Assistant Poland 🇵🇱')

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

col1, col2 = st.columns([2, 2])  # Adjust column widths as needed

with col1:
    st.write("### Input and Settings")

    url_input = st.text_input('Enter CSV URL (Optional)', GIT_FS_DATA_SET_PL, key='csv_url')

    # Use a unique cache key for each URL to force cache invalidation
    load_data_key = f"load_data_{url_input}"

    load_data_button = st.button("Load Data")

    if load_data_button and url_input:
        st.session_state['df_data'] = load_data(_url=URL(url_input))
        st.session_state['df_url'] = url_input
        if not st.session_state['df_data'].empty:
            st.write("Data loaded successfully.")
            # display_filters(st.session_state['df_data'])
        else:
            st.error("Failed to load data or the data is empty.")

    # OpenAI API Key section
    if st.button("OpenAI API Key", key="api_key"):
        st.session_state.show_api_key = not st.session_state.get('show_api_key', False)

    if st.session_state.get('show_api_key', False):
        openai_api_key = display_api_key()
    else:
        openai_api_key = None

    use_test_data = st.checkbox('Use Test Responses', value=True, key='use_test_data')

    with st.form(key='full-width-form'):
        label = 'Talk to me about your dream property 😎:\n'

        iteration = st.session_state.get('iteration', 0)
        msg_example = MSG_MAP.get(iteration, '')

        text = st.text_area(label=label, value=msg_example, height=200)

        submitted = st.form_submit_button('Submit')

        if submitted:
            if openai_api_key:
                if not openai_api_key.startswith('sk-'):
                    st.warning('Please enter a valid OpenAI API key starting with "sk-".', icon='⚠')
                key = openai_api_key
            else:
                key = OPENAI_API_KEY

            if not key.startswith('sk-'):
                st.warning('Please enter a valid OpenAI API key starting with "sk-".', icon='⚠')
            else:
                df_data_act = st.session_state.get('df_data')
                if df_data_act is None or df_data_act.empty:
                    st.error('Please load data first.')
                else:
                    if 'ai_agent' not in st.session_state:
                        st.session_state['ai_agent'] = RealEstateGPT(df_data_act, key)
                    process_query(text, use_test_data)

                st.session_state['iteration'] = (iteration + 1) % len(MSG_MAP)

with col2:
    st.write("### Conversation History")
    with st.container():
        st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
        display_conversation()
        st.markdown('</div>', unsafe_allow_html=True)
