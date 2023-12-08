from utils import *
from langchain.callbacks.manager import CallbackManager
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
from "../apps/backend/bot" import BotServiceCallbackHandler

def debug():
    print("This is a debug message")
    cb_handler = BotServiceCallbackHandler(turn_context)
    cb_manager = CallbackManager(handlers=[cb_handler])
    llm = AzureChatOpenAI(
            deployment_name="Gpt4-32k"
            temperature=0.5,
            max_tokens=1000,
            callback_manager=cb_manager,
        )
    house = HouseControlTool()
