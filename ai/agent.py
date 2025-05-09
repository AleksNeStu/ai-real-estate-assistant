import os
from typing import Sequence

import pandas as pd
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

class RealEstateGPT:
    """
    A specialized AI agent for real estate assistance that uses LangChain's
    pandas dataframe agent to process and respond to real estate queries.
    
    This class encapsulates the functionality for creating a conversational
    AI assistant that can analyze real estate data and provide relevant
    property recommendations and insights.
    """

    def __init__(self, df: pd.DataFrame | Sequence[pd.DataFrame], key: str):
        """
        Initialize the RealEstateGPT agent.
        
        This method sets up the LangChain agent with the provided dataframe(s) and
        configures the conversational context with system and user message templates.
        It creates a pandas dataframe agent that can execute Python code to answer
        questions about the real estate data.
        
        Parameters:
            df (pd.DataFrame | Sequence[pd.DataFrame]): The property dataset(s) to analyze.
                Can be a single DataFrame or a sequence of DataFrames.
            key (str): OpenAI API key for authentication.
        """
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
        """
        Process a user query and generate a response using the LangChain agent.
        
        This method constructs a dynamic prompt with conversation history,
        passes it to the LangChain agent, and handles the response. The agent
        uses its understanding of real estate concepts combined with data analysis
        capabilities to generate relevant answers.
        
        The method:
        1. Formats the conversation history
        2. Constructs a dynamic prompt with system message, history, and current query
        3. Runs the LangChain agent to get an answer
        4. Updates the conversation history with the new Q&A pair
        5. Handles any exceptions that may occur during processing
        
        Parameters:
            query (str): The user's question or request about real estate
            
        Returns:
            str: The agent's response to the user query, or an error message
                if processing fails
        """
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
        """
        Format the conversation history into a string for context in the prompt.
        
        This private helper method converts the stored conversation history
        (a list of dictionaries with 'User' and 'Assistant' keys) into a
        formatted string that can be included in the prompt to the LLM.
        
        The conversation history provides context for the current query,
        allowing the agent to maintain continuity and coherence across
        multiple interactions. This enables multi-turn conversations where
        the agent can refer to previously discussed properties or preferences.
        
        Returns:
            str: A formatted string containing the conversation history with
                alternating user and assistant messages
        """
        formatted_history = ""
        for history_item in self.conversation_history:
            formatted_history += f"User: {history_item['User']}\nAssistant: {history_item['Assistant']}\n"
        return formatted_history