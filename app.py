import pandas as pd
import streamlit as st

from ai.agent import RealEstateGPT
from common.cfg import *
from data.csv_loader import DataLoaderLocalCsv


@st.cache_data
def load_data():
    dataloader = DataLoaderLocalCsv()
    df_data = dataloader.df_formatted
    return df_data

df_data = load_data()

if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = []

def generate_response(input_text, use_test_data):
    process_query(input_text, use_test_data)
    st.rerun()

def fix_dataframe(df):
    for column in df.columns:
        df[column] = df[column].astype(str)
    return df

@st.cache_data
def display_filters():
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
        response = 'FAKE: '
        if use_test_data:
            response += fake_en.text(max_nb_chars=100)
        else:
            response = st.session_state['ai_agent'].ask_qn(query)
        st.session_state['conversation_history'].insert(0, {'Client': query, 'AI': response})

def display_conversation():
    if st.session_state['conversation_history']:
        for idx, exchange in enumerate(st.session_state['conversation_history'], start=1):
            st.text_area(f"Client ({idx})", value=exchange['Client'], height=100, disabled=True, key=f"client_{idx}")
            st.text_area(f"AI ({idx})", value=exchange['AI'], height=100, disabled=True, key=f"ai_{idx}")

def execute():
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
            # width: 100%;
            # overflow-y: auto;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 2])  # Adjust column widths as needed
    # col1, col2 = st.columns([3, 1])  # Adjust column widths as needed

    with col1:
        st.write("### Input and Settings")

        if st.button("Filters", key="filters"):
            st.session_state.show_filters = not st.session_state.get('show_filters', False)

        if st.button("OpenAI API Key", key="api_key"):
            st.session_state.show_api_key = not st.session_state.get('show_api_key', False)

        if st.session_state.get('show_filters', False):
            display_filters()

        if st.session_state.get('show_api_key', False):
            openai_api_key = display_api_key()
        else:
            openai_api_key = None

        use_test_data = st.checkbox('Use Test Responses', value=True, key='use_test_data')

        with st.form(key='full-width-form'):
            label = 'Talk to me about your dream property 😎:\n'

            conversation_history = st.session_state.get('conversation_history', [])
            msg_example = '' if conversation_history else (
                'I am finding a cheap flat in Krakow.\n'
                'Better to have 2 rooms, not 1st floor, more than 30 square meters, with garage and storage room, '
                'also I would like to negotiate the final price.\n'
                'Do you have options for me?'
            )
            text = st.text_area(label=label, value=msg_example, height=200)

            submitted = st.form_submit_button('Submit')
            key = OPENAI_API_KEY
            if submitted:
                if openai_api_key:
                    if not openai_api_key.startswith('sk-'):
                        st.warning('Please enter a valid OpenAI API key starting with "sk-".', icon='⚠')
                    else:
                        key = openai_api_key

                if 'ai_agent' not in st.session_state:
                    st.session_state['ai_agent'] = RealEstateGPT(df_data, key)
                generate_response(text, use_test_data)

    with col2:
        st.write("### Conversation History")
        with st.container():
            st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
            display_conversation()
            st.markdown('</div>', unsafe_allow_html=True)

execute()
