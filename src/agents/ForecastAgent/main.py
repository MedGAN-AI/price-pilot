from agent import forecast_agent

def main():
    user_input = "Forecast demand for SKU123 for 7 days"

    # When invoking LangChain agents, pass all needed variables
    inputs = {
        "input": user_input,
        "tools": forecast_agent.tools,      # list of tools
        "tool_names": [tool.name for tool in forecast_agent.tools],  # list of tool names
        "chat_history": [],                  # empty chat history for first run
    }

    response = forecast_agent.invoke(inputs)
    print("Agent response:\n", response)

if __name__ == "__main__":
    main()
