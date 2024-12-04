import os
import utils
import requests
import traceback
import validators
import streamlit as st
from streaming import StreamHandler
from common.cfg import *
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
import pandas as pd
from langchain_core.documents.base import Document
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders.dataframe import DataFrameLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch

st.set_page_config(page_title="🦾 AI Real Estate Assistant", page_icon='💬', layout='wide')
st.header('Chat with Real Estate AI Assistant')
st.write('[![view source code ](https://img.shields.io/badge/view_source_code-gray?logo=github)](https://github.com/AleksNeStu/ai-real-estate-assistant)')

class ChatbotWeb:

    def __init__(self):
        utils.sync_st_session()
        self.llm = utils.configure_llm()
        self.embedding_model = utils.configure_embedding_model()

    def scrape_website(self, url):
        content = ""
        try:
            base_url = "https://r.jina.ai/"
            final_url = base_url + url
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'
            }
            response = requests.get(final_url, headers=headers)
            content = response.text
            return content
        except Exception as e:
            traceback.print_exc()

    def load_docs_from_csv_local(self, path):
        content = ""
        try:
            loader = CSVLoader(path)
            docs = loader.load()
            return docs
        except Exception as e:
            traceback.print_exc()

    def load_docs_from_csv_web(self, url):
        try:
            df = pd.read_csv(url)
            loader = DataFrameLoader(data_frame=df)
            docs = loader.load()
            return docs
        except Exception as e:
            traceback.print_exc()

    def load_data_from_csv_web(self, url):
        try:
            df = pd.read_csv(url)
            # content = df.to_string(index=False)
            # content = '\n'.join(df['content'].tolist())
            content = str(df.to_dict(orient='records'))
            return content
        except Exception as e:
            traceback.print_exc()

    @st.cache_resource(show_spinner='Analyzing csv data set', ttl=3600)
    def setup_vectordb(_self, websites):
        # Scrape and load documents
        docs = []
        for url in websites:
            # loader = CSVLoader('./ai-real-estate-assistant/dataset/pl/apartments_rent_pl_2024_01.csv')
            # docs.extend(loader.load())
            docs.append(Document(
                page_content=_self.load_data_from_csv_web(url),
                metadata={"source":url}
                )
            )

        # Split documents and store in vector db
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)

        vectordb = DocArrayInMemorySearch.from_documents(splits, _self.embedding_model)

        # from langchain_community.vectorstores import Chroma
        # from langchain_openai import OpenAIEmbeddings
        # vectordb = Chroma.from_documents(splits, OpenAIEmbeddings())

        return vectordb

    def setup_qa_chain(self, vectordb):

        # Define retriever
        retriever = vectordb.as_retriever(
            search_type='mmr',
            search_kwargs={'k':2, 'fetch_k':4}
        )

        # Setup memory for contextual conversation
        memory = ConversationBufferMemory(
            memory_key='chat_history',
            output_key='answer',
            return_messages=True
        )

        # Setup QA chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=memory,
            return_source_documents=True,
            verbose=False
        )
        return qa_chain

    @utils.enable_chat_history
    def main(self):
        csv_url = 'CSV Data Set URL'
        # User Inputs
        if "websites" not in st.session_state:
            st.session_state["websites"] = []
            st.session_state["value_urls"] = GIT_DATA_SET_URLS_STR.split('\n')

        # Def value for url
        url_val = ''
        value_urls = st.session_state.get("value_urls", [])
        if len(value_urls) >= 1:
            url_val = value_urls[0]
        web_url = st.sidebar.text_area(
            label=f'Enter {csv_url}s',
            placeholder="https://",
            # help="To add another website, modify this field after adding the website.",
            value=url_val
        )
        # st.sidebar.text(GIT_DATA_SET_URLS_STR)

        if st.sidebar.button(":heavy_plus_sign: Add Website"):
            valid_url = web_url.startswith('http') and validators.url(web_url)
            if not valid_url :
                st.sidebar.error(f"Invalid URL! Please check {csv_url} that you have entered.", icon="⚠️")
            else:
                st.session_state["websites"].append(web_url)

        if st.sidebar.button("Clear", type="primary"):
            st.session_state["websites"] = []

        websites = list(set(st.session_state["websites"]))

        if not websites:
            st.error(f"Please enter {csv_url} to continue!")
            st.stop()
        else:
            st.sidebar.info("CSV Data Sets - \n - {}".format('\n - '.join(websites)))

            vectordb = self.setup_vectordb(websites)
            qa_chain = self.setup_qa_chain(vectordb)

            user_query = st.chat_input(placeholder="Ask me question about real estate properties!")
            if websites and user_query:

                utils.display_msg(user_query, 'user')

                with st.chat_message("assistant"):
                    st_cb = StreamHandler(st.empty())
                    result = qa_chain.invoke(
                        {"question":user_query},
                        {"callbacks": [st_cb]}
                    )
                    response = result["answer"]
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    utils.print_qa(ChatbotWeb, user_query, response)

                    # to show references
                    for idx, doc in enumerate(result['source_documents'],1):
                        url = os.path.basename(doc.metadata['source'])
                        ref_title = f":blue[Reference {idx}: *{url}*]"
                        with st.popover(ref_title):
                            st.caption(doc.page_content)


if __name__ == "__main__":
    obj = ChatbotWeb()
    obj.main()
