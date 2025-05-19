# agent implementation
import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from retriever import *
from tools import *
from langchain_community.tools import DuckDuckGoSearchRun


load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



