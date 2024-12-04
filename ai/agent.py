import os
from typing import Sequence

import pandas as pd
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

class RealEstateGPT:

    def __init__(self, df: pd.DataFrame | Sequence[pd.DataFrame], key: str):
        # Define system and user prompts for context
        self.system_msg = (
            "System: You are a specialized real estate assistant. Your role is to help users find the perfect home, "
            "provide real estate advice, and offer insights into property market trends. You should focus on the "
            "following aspects: assisting users in understanding property details, highlighting key features, and "
            "advising on price negotiations based on the 'Possibly to negotiate' column. Ensure all responses are "
            "relevant to real estate and property management. Do not respond to questions outside the real estate domain."
        )
        self.user_msg = "User: {query}"  # Format for user queries
        self.assistant_msg = "Assistant: Please keep responses relevant to real estate only."

        os.environ["OPENAI_API_KEY"] = key

        # Initialize the agent
        self.agent = create_pandas_dataframe_agent(
            ChatOpenAI(temperature=0, model="gpt-3.5-turbo"),
            df,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True,
            prefix=self.system_msg
        )
        self.conversation_history = []

    def ask_qn(self, query):
        formatted_history = self._format_history()
        # Use the system message as a prefix and add suffix to reinforce the domain
        dynamic_prompt = f'{self.system_msg}\n\n{formatted_history}\n\n{self.user_msg.format(query=query)}\n\n{self.assistant_msg}'

        try:
            answer = self.agent.run(dynamic_prompt)
            history_item = {'User': query, 'Assistant': answer}
            self.conversation_history.append(history_item)
            return answer

        except Exception as ex:
            err_msg = f"GPT Error: {ex} for question: {query}"
            return err_msg

    def _format_history(self):
        formatted_history = ""
        for history_item in self.conversation_history:
            formatted_history += f"User: {history_item['User']}\nAssistant: {history_item['Assistant']}\n"
        return formatted_history