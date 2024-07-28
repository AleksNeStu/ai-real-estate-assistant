from pathlib import Path

import streamlit as st
from langchain_community.llms import OpenAI
from common.cfg import *
from data.csv_loader import DataLoaderLocalCsv


# New
dataloader = DataLoaderLocalCsv()
df_data = dataloader.df_formatted

# Legacy
def get_openai_api_key():
    openai_api_key = st.sidebar.text_input(
        'OpenAI API Key [Optional]', type='password')
    if openai_api_key:
        if not openai_api_key.startswith('sk-'):
            st.warning('Please enter your OpenAI API key!', icon='⚠')
        else:
            return openai_api_key


st.title('GPT with langchain and streamlit')

def generate_response(input_text, api_key):
    llm = OpenAI(temperature=0.7, openai_api_key=api_key)
    res = llm(input_text)
    st.info(res)
    return res

def execute():
    openai_api_key = get_openai_api_key()
    with st.form('my_form'):
        text = st.text_area('Enter text:', 'What is GenAI? 3 steps to learn.')
        submitted = st.form_submit_button('Submit')
        if submitted:
            key = openai_api_key or OPENAI_API_KEY
            generate_response(text, key)

execute()
# if __name__ == "__main__":
#     # Check if the script is being run directly or via subprocess
#     if len(sys.argv) > 1 and sys.argv[1] == "run":
#         execute()
#     else:
#         # Re-run the script with Streamlit
#         filename = Path(__file__).resolve()
#         subprocess.run([sys.executable, "-m", "streamlit", "run", str(filename), "run"])