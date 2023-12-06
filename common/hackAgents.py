import re
import os
import json
import requests
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
from langchain.output_parsers import PydanticOutputParser

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

    def _run(self, query: str) -> str:
        try:
            # # reponse represents the action to be taken
            # # we will now execute the action
            # # we will use the simulator to execute the action
            # # reponse format JSON
            chat_chain = LLMChain(
                llm=self.llm,
                prompt=HOUSECONTROL_PROMPT_PREFIX,
                callback_manager=self.callbacks,
                verbose=self.verbose,
            )

            response_action = chat_chain.run(query)

            # executer action
            parser = PydanticOutputParser(pydantic_object=Action)
            action = parser.parse(response_action)

            if response_action == None:
                return "No Results Found"

            house_action = {
                "target_temp_command": response_action["target_temp_command"],
                "EV_action": {
                    "plug_action": None,
                    "endtrip_autonomy": None,
                    "autonomy_objective": response_action["target_autonomy_command"],
                },
            }
            
            # call function app to execute action
            return
        except Exception as e:
            print(e)

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("HouseControl Tool does not support async")


class HouseControlAction(BaseTool):
    name = "@housecontrol"
    description = "useful when the questions includes the term: @housecontrol.\n"

    def _run(self, query: str) -> str:
        try:
            return ""
        except:
            return "No Results Found"

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("HouseControl Tool does not support async")


class HouseControlStatus(BaseTool):
    """Tool for a House Control Wrapper"""

    name = "@housecontrol"
    description = "useful when the questions includes the term: @housecontrol.\n"

    def _run(self, query: str) -> str:
        try:
            return """The current state of the house is:"""
        except:
            return "No Results Found"

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("HouseControl Tool does not support async")


class Action(BaseModel):
    target_temp_command: str
    target_autonomy_command: str
