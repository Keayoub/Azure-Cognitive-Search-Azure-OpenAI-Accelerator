import re
import os
import json
from typing import Any, Dict, List, Optional, Awaitable, Callable, Tuple, Type, Union

from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.chat_models import AzureChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import BaseOutputParser, OutputParserException
from langchain.vectorstores import VectorStore
from langchain.vectorstores.faiss import FAISS
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from openai.error import AuthenticationError
from langchain.docstore.document import Document
from pypdf import PdfReader
from sqlalchemy.engine.url import URL
from langchain.sql_database import SQLDatabase
from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.tools import BaseTool
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.callbacks.base import BaseCallbackManager
from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.llms.openai import OpenAI
from langchain_experimental.agents.agent_toolkits import create_python_agent
from langchain_experimental.tools import PythonREPLTool
from utils import run_agent
from env import Simulator

try:
    from .prompts import (
        HOUSECONTROL_PROMPT_PREFIX,
    )
except Exception as e:
    print(e)
    from prompts import HOUSECONTROL_PROMPT_PREFIX


######## TOOL CLASSES #####################################
###########################################################
class HouseControlTool(BaseTool):
    """Tool for a House Control Wrapper"""

    name = "@housecontrol"
    description = "useful when the questions includes the term: @housecontrol.\n"

    llm: AzureChatOpenAI
    k: int = 5
    house_simulator:Simulator

    def _run(
        self,
        tool_input: Union[str, Dict],
    ) -> str:
        try:
            tools = [HouseControlAction(house_simulator=self.house_simulator)]
            parsed_input = self._parse_input(tool_input)

            agent_executor = initialize_agent(
                tools=tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                agent_kwargs={"prefix": HOUSECONTROL_PROMPT_PREFIX},
                callback_manager=self.callbacks,
                verbose=self.verbose,
                handle_parsing_errors=True,
            )

            for i in range(2):
                try:
                    response = run_agent(parsed_input, agent_executor)
                    break
                except Exception as e:
                    response = str(e)
                    continue


            # reponse represents the action to be taken
            # we will now execute the action
            # we will use the simulator to execute the action            
            # reponse format JSON      

            return response

        except Exception as e:
            print(e)

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("HouseControl Tool does not support async")


class HouseControlStatus(BaseTool):
   """Tool for a House Control Wrapper"""

    name = "@housecontrol"
    description = "useful when the questions includes the term: @housecontrol.\n"

    house_simulator:Simulator

    def _run(self, query: str) -> str:        
        try:
            return  house_simulator.get_env_state_in_natural_language()
        except:
            return "No Results Found"

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("HouseControl Tool does not support async")


class HouseControlAction(BaseTool):
   """Tool for a House Control Wrapper"""

    name = "@housecontrol"
    description = "useful when the questions includes the term: @housecontrol.\n"
    action:str
    house_simulator:Simulator

    def _run(self, query: str) -> str:       
        try:
            return house_simulator.describe_action_in_natural_language(action)
        except:
            return "No Results Found"

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("HouseControl Tool does not support async")
