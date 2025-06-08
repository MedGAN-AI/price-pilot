'''
this code to test our agents and graphs in a single script.

import os
import sys

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# === Uncomment the desired graph import and builder ===

# --- Shopping Assistant ---
from src.graphs.chat_graph import build_chat_graph as build_graph
GRAPH_NAME = "Shopping Assistant Chat"

# --- Inventory Agent ---
# from src.graphs.inventory_graph import build_inventory_graph as build_graph
# GRAPH_NAME = "Inventory Agent Chat"

# --- Forecast Agent ---
# from src.graphs.forecast_graph import build_forecast_graph as build_graph
# GRAPH_NAME = "Forecast Agent Chat"

# --- Order Agent ---
# from src.graphs.order_graph import build_order_graph as build_graph
# GRAPH_NAME = "Order Agent Chat"

# --- Logistics Agent ---
# from src.graphs.logistics_graph import build_logistics_graph as build_graph
# GRAPH_NAME = "Logistics Agent Chat"

def main():
    # 1) Load environment variables from .env
    load_dotenv()

    # 2) Build the appropriate StateGraph
    graph = build_graph()

    # 3) Initialize graph state
    state = {
        "messages": [],           # list of AnyMessage (HumanMessage/AIMessage)
        "intermediate_steps": []  # used by LangGraph to decide if a tool node should run
    }

    print(f"=== {GRAPH_NAME} ===")
    print("(Type 'exit' or 'quit' to end.)")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # 4a) Wrap user input as HumanMessage and append
        state["messages"].append(HumanMessage(content=user_input))

        # 4b) Invoke the graph
        result = graph.invoke(state)

        # 4c) Extract and print last AIMessage
        ai_msg = result["messages"][-1]
        if isinstance(ai_msg, AIMessage):
            print("Bot:", ai_msg.content)
        else:
            print("Bot (unexpected msg type):", ai_msg)

        # 4d) Update state
        state = result

if __name__ == "__main__":
    main()'''


import os
import sys

# Ensure 'src' is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from src.graphs.orchestrator import orchestrator, initialize_state

def main():
    load_dotenv()
    state = initialize_state()

    print("=== Multi-Agent Orchestrator ===")
    print("(Type 'exit' or 'quit' to end.)")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # Add user message
        state["messages"].append(HumanMessage(content=user_input))

        # Run orchestrator
        result = orchestrator.invoke(state)

        # Print the bot’s reply
        ai_msg = result["messages"][-1]
        if isinstance(ai_msg, AIMessage):
            print("Bot:", ai_msg.content)
        else:
            print("Bot (unexpected):", ai_msg)

        # Prepare next state
        state = {
            "messages": result["messages"],
            "intermediate_steps": [],
            "intent": ""
        }

if __name__ == "__main__":
    main()


