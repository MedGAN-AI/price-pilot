import os
import sys

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from src.graphs.chat_graph import build_chat_graph

def main():
    # 1) Load environment variables from .env (must contain GOOGLE_API_KEY=...)
    load_dotenv()

    # 2) Build the ChatAgent StateGraph
    chat_graph = build_chat_graph()

    # 3) Initialize graph state
    state = {
        "messages": [],           # list of AnyMessage (HumanMessage/AIMessage)
        "intermediate_steps": []  # used internally to decide if a tool node should run
    }

    print("=== Shopping Assistant Chat ===")
    print("(Type 'exit' or 'quit' to end.)")

    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # 4a) Wrap the user input as a HumanMessage and append
        state["messages"].append(HumanMessage(content=user_input))

        # 4b) Invoke the graph once (runs: assistant → maybe tools → assistant …)
        result = chat_graph.invoke(state)

        # 4c) Extract the last message (should be an AIMessage)
        ai_msg = result["messages"][-1]
        if isinstance(ai_msg, AIMessage):
            print("Bot:", ai_msg.content)
        else:
            # Fallback if something unexpected was returned
            print("Bot (unexpected msg type):", ai_msg)

        # 4d) Update state for next iteration (carries forward chat history & any intermediate steps)
        state = result

if __name__ == "__main__":
    main()
