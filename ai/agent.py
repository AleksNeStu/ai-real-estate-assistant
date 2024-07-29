import os

import pandas as pd
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI


class RealEstateGPT:

    def __init__(self, df: pd.DataFrame, key: str):
        self.conversational_prompt = (
            "As a seasoned real estate agent, your role involves assisting the user in locating their ideal home, "
            "offering real estate advice, negotiating deals, and supplying expert knowledge on the property market. "
            "The 'Possibly to negotiate' column indicates the extent to which you can negotiate with the client. "
            "Utilize the Price Cut to highlight properties with significant reductions in price. Engage in "
            "negotiations with the client. Here's how your conversation has unfolded so far:"
        )
        os.environ["OPENAI_API_KEY"] = key
        # Initialize the agent
        self.agent = create_pandas_dataframe_agent(
            ChatOpenAI(temperature=0, model="gpt-3.5-turbo"),
            df,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True
        )
        self.conversation_history = []

    def ask_qn(self, query):
        formated_history = self._format_history()
        dynamic_prompt = f'{self.conversational_prompt}\n\n{formated_history}\n\nClient: {query}'

        try:
            answer = self.agent.run(dynamic_prompt)
            history_item = {'Client': query, 'AI': answer}
            self.conversation_history.append(history_item)
            return answer

        except Exception as ex:
            print(f"Error: {ex} for question: {query}")
            return ''

    def _format_history(self):
        formatted_history = ""
        for history_item in self.conversation_history:
            formatted_history += f"Client: {history_item['Client']}\nAI: {history_item['AI']}\n"
        return formatted_history
