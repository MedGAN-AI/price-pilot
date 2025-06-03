import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
from typing import Dict, Any, List, Optional
import json
import os

# LangChain imports - Fixed imports
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.manager import CallbackManagerForToolRun

# LangGraph imports - Fixed imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from typing_extensions import TypedDict

warnings.filterwarnings('ignore')

# State definition for LangGraph
class AgentState(TypedDict):
    messages: list
    forecast_data: dict
    analysis: dict  # Added missing field
    user_query: str
    steps: int
    analysis_complete: bool

class ForecastTool(BaseTool):
    """Custom tool for ARIMA forecasting"""
    
    name = "forecast_generator"
    description = "Generate time series forecasts using ARIMA model. Input should be number of steps to forecast."
    
    def __init__(self, model_path: str = "models/arima_model.pkl"):
        super().__init__()
        self.model_path = model_path
        self.model = None
        self.load_model()
    
    def load_model(self):
        """Load the ARIMA model from pickle file"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                print(f"✅ ARIMA model loaded from {self.model_path}")
            else:
                print(f"⚠️ Model file not found: {self.model_path}")
                print("Creating mock model for demonstration...")
                self.model = self._create_mock_model()
        except Exception as e:
            print(f"❌ Error loading model: {str(e)}")
            print("Creating mock model for demonstration...")
            self.model = self._create_mock_model()
    
    def _create_mock_model(self):
        """Create a mock model for demonstration purposes"""
        class MockARIMAModel:
            def __init__(self):
                self.resid = np.random.normal(0, 1, 100)
            
            def forecast(self, steps, return_conf_int=False):
                # Generate mock forecast data
                base_values = np.random.normal(100, 10, steps)
                trend = np.linspace(0, 5, steps)
                forecast = base_values + trend
                
                if return_conf_int:
                    std_error = np.std(self.resid)
                    margin = 1.96 * std_error
                    lower = forecast - margin
                    upper = forecast + margin
                    conf_int = np.column_stack([lower, upper])
                    return forecast, conf_int
                return forecast
        
        return MockARIMAModel()
    
    def _run(
        self, 
        steps: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the forecasting tool"""
        try:
            steps_int = int(steps)
            if steps_int <= 0 or steps_int > 365:
                return json.dumps({"error": "Steps must be between 1 and 365"})
            
            if self.model is None:
                return json.dumps({"error": "ARIMA model not loaded properly"})
            
            # Generate forecast
            try:
                forecast_result, conf_int = self.model.forecast(steps=steps_int, return_conf_int=True)
                lower_bound = conf_int[:, 0].tolist()
                upper_bound = conf_int[:, 1].tolist()
            except Exception as e:
                # Fallback if confidence intervals fail
                forecast_result = self.model.forecast(steps=steps_int)
                if hasattr(forecast_result, '__iter__'):
                    forecast_values = list(forecast_result)
                else:
                    forecast_values = [float(forecast_result)]
                    
                forecast_std = np.std(self.model.resid) if hasattr(self.model, 'resid') else np.std(forecast_values) * 0.1
                margin = 1.96 * forecast_std
                lower_bound = [v - margin for v in forecast_values]
                upper_bound = [v + margin for v in forecast_values]
                forecast_result = forecast_values
            
            # Ensure forecast_result is a list
            if not hasattr(forecast_result, '__iter__'):
                forecast_result = [float(forecast_result)]
            else:
                forecast_result = [float(x) for x in forecast_result]
            
            # Create date range
            forecast_dates = pd.date_range(
                start=datetime.now() + timedelta(days=1),
                periods=steps_int,
                freq='D'
            ).strftime('%Y-%m-%d').tolist()
            
            results = {
                "forecast_values": forecast_result,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "forecast_dates": forecast_dates,
                "steps": steps_int,
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "mean": float(np.mean(forecast_result)),
                    "min": float(np.min(forecast_result)),
                    "max": float(np.max(forecast_result)),
                    "trend": "increasing" if forecast_result[-1] > forecast_result[0] else "decreasing"
                }
            }
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Error generating forecast: {str(e)}"})
    
    async def _arun(self, steps: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version - not implemented for this tool"""
        return self._run(steps, run_manager)

class DataAnalysisTool(BaseTool):
    """Tool for analyzing forecast data"""
    
    name = "data_analyzer"
    description = "Analyze forecast data and provide insights. Input should be forecast data in JSON format."
    
    def _run(
        self, 
        forecast_data: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Analyze the forecast data"""
        try:
            if isinstance(forecast_data, str):
                data = json.loads(forecast_data)
            else:
                data = forecast_data
            
            if "error" in data:
                return json.dumps({"error": "Cannot analyze data due to forecast generation error."})
            
            forecast_values = data.get("forecast_values", [])
            summary = data.get("summary", {})
            
            if not forecast_values:
                return json.dumps({"error": "No forecast values to analyze"})
            
            # Perform analysis
            analysis = {
                "total_periods": len(forecast_values),
                "average_value": summary.get("mean", np.mean(forecast_values)),
                "volatility": float(np.std(forecast_values)),
                "trend_direction": summary.get("trend", "stable"),
                "confidence_range": {
                    "lower_avg": float(np.mean(data.get("lower_bound", []))),
                    "upper_avg": float(np.mean(data.get("upper_bound", [])))
                },
                "key_insights": []
            }
            
            # Generate insights
            avg_val = analysis["average_value"]
            volatility = analysis["volatility"]
            
            if volatility > avg_val * 0.2:
                analysis["key_insights"].append("High volatility detected in forecast")
            
            if summary.get("trend") == "increasing":
                analysis["key_insights"].append("Positive growth trend identified")
            elif summary.get("trend") == "decreasing":
                analysis["key_insights"].append("Declining trend observed")
            else:
                analysis["key_insights"].append("Stable trend with minimal change")
            
            # Additional insights
            if len(forecast_values) > 1:
                change_pct = ((forecast_values[-1] - forecast_values[0]) / forecast_values[0]) * 100
                analysis["change_percentage"] = float(change_pct)
                
                if abs(change_pct) > 10:
                    analysis["key_insights"].append(f"Significant change of {change_pct:.1f}% over forecast period")
            
            return json.dumps(analysis, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Error analyzing data: {str(e)}"})
    
    async def _arun(self, forecast_data: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Async version - not implemented for this tool"""
        return self._run(forecast_data, run_manager)

class ForecastOutputParser(BaseOutputParser):
    """Custom output parser for forecast responses"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        try:
            # Try to parse as JSON first
            return json.loads(text)
        except:
            # If not JSON, return as text
            return {"response": text}

class ForecastAgent:
    """Main Forecast Agent using LangChain and LangGraph"""
    
    def __init__(
        self, 
        model_path: str = "models/arima_model.pkl",
        prompt_path: str = "prompts/forecast_prompt.txt",
        llm_model: str = "gpt-3.5-turbo"
    ):
        self.model_path = model_path
        self.prompt_path = prompt_path
        self.llm_model = llm_model
        
        # Initialize LLM with error handling
        try:
            self.llm = ChatOpenAI(model=llm_model, temperature=0.1)
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize ChatOpenAI: {e}")
            print("LLM features will be limited")
            self.llm = None
        
        # Load prompt template
        self.prompt_template = self.load_prompt_template()
        
        # Initialize tools
        self.forecast_tool = ForecastTool(model_path)
        self.analysis_tool = DataAnalysisTool()
        self.tools = [self.forecast_tool, self.analysis_tool]
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize LangGraph
        self.graph = self.create_graph()
    
    def load_prompt_template(self) -> PromptTemplate:
        """Load the prompt template"""
        try:
            if os.path.exists(self.prompt_path):
                with open(self.prompt_path, 'r', encoding='utf-8') as f:
                    template = f.read()
                return PromptTemplate.from_template(template)
        except Exception as e:
            print(f"Warning: Could not load prompt template: {e}")
        
        # Default template
        default_template = """
You are an expert forecasting analyst. Based on the user's question: {user_query}

Forecast Data: {forecast_data}
Analysis: {analysis}

Provide a comprehensive forecast analysis including:
1. Key findings from the forecast
2. Trend analysis
3. Risk factors and confidence levels
4. Actionable recommendations

Make your response clear, professional, and actionable.
"""
        return PromptTemplate.from_template(default_template)
    
    def create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        
        def forecast_node(state: AgentState) -> AgentState:
            """Node to generate forecast"""
            steps = state.get("steps", 30)
            forecast_result = self.forecast_tool._run(str(steps))
            
            try:
                forecast_data = json.loads(forecast_result)
            except:
                forecast_data = {"error": forecast_result}
            
            state["forecast_data"] = forecast_data
            return state
        
        def analysis_node(state: AgentState) -> AgentState:
            """Node to analyze forecast data"""
            forecast_data = state.get("forecast_data", {})
            analysis_result = self.analysis_tool._run(json.dumps(forecast_data))
            
            try:
                analysis_data = json.loads(analysis_result)
            except:
                analysis_data = {"error": analysis_result}
            
            state["analysis"] = analysis_data
            return state
        
        def response_node(state: AgentState) -> AgentState:
            """Node to generate final response"""
            user_query = state.get("user_query", "")
            forecast_data = state.get("forecast_data", {})
            analysis = state.get("analysis", {})
            
            if self.llm:
                # Use LLM to generate response
                try:
                    prompt = self.prompt_template.format(
                        user_query=user_query,
                        forecast_data=json.dumps(forecast_data, indent=2),
                        analysis=json.dumps(analysis, indent=2)
                    )
                    
                    response = self.llm.invoke(prompt)
                    content = response.content
                except Exception as e:
                    content = f"Error generating LLM response: {str(e)}"
            else:
                # Fallback response without LLM
                content = self._generate_fallback_response(forecast_data, analysis, user_query)
            
            state["messages"].append({"role": "assistant", "content": content})
            state["analysis_complete"] = True
            
            return state
        
        # Build the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("forecast", forecast_node)
        workflow.add_node("analysis", analysis_node)
        workflow.add_node("response", response_node)
        
        # Add edges
        workflow.set_entry_point("forecast")
        workflow.add_edge("forecast", "analysis")
        workflow.add_edge("analysis", "response")
        workflow.add_edge("response", END)
        
        return workflow.compile()
    
    def _generate_fallback_response(self, forecast_data: dict, analysis: dict, user_query: str) -> str:
        """Generate a basic response without LLM"""
        if "error" in forecast_data:
            return f"❌ Error generating forecast: {forecast_data['error']}"
        
        if "error" in analysis:
            return f"❌ Error analyzing forecast: {analysis['error']}"
        
        # Basic response template
        response = f"""📊 Forecast Analysis for: {user_query}

🔮 Forecast Summary:
- Forecast period: {forecast_data.get('steps', 'N/A')} days
- Average value: {forecast_data.get('summary', {}).get('mean', 'N/A'):.2f}
- Trend: {forecast_data.get('summary', {}).get('trend', 'N/A')}

📈 Analysis Results:
- Total periods: {analysis.get('total_periods', 'N/A')}
- Volatility: {analysis.get('volatility', 'N/A'):.2f}
- Key insights: {', '.join(analysis.get('key_insights', []))}

⚠️ Note: This is a basic analysis. For detailed insights, please configure OpenAI API.
"""
        return response
    
    def process_query(self, user_query: str, steps: int = 30) -> str:
        """Process user query using LangGraph workflow"""
        
        initial_state = AgentState(
            messages=[{"role": "user", "content": user_query}],
            forecast_data={},
            analysis={},  # Initialize analysis field
            user_query=user_query,
            steps=max(1, min(steps, 365)),  # Validate steps
            analysis_complete=False
        )
        
        try:
            # Run the graph
            result = self.graph.invoke(initial_state)
            
            # Extract the final response
            if result.get("messages") and len(result["messages"]) > 0:
                return result["messages"][-1]["content"]
            else:
                return "Error: No response generated"
        except Exception as e:
            return f"❌ Error processing query: {str(e)}"
    
    def chat_interface(self):
        """Interactive chat interface"""
        print("🤖 Forecast Agent with LangChain & LangGraph")
        print("Type 'quit' to exit, 'help' for commands")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    print("""
Available commands:
- Ask any forecasting question (e.g., "forecast sales for next 30 days")
- 'quit' - Exit the chat
- 'clear' - Clear conversation memory
- 'test' - Run a test forecast
- 'status' - Check system status
                    """)
                    continue
                elif user_input.lower() == 'clear':
                    self.memory.clear()
                    print("🗑️ Memory cleared!")
                    continue
                elif user_input.lower() == 'test':
                    print("🧪 Running test forecast...")
                    response = self.process_query("Generate a 7-day forecast", 7)
                    print(f"\n🤖 Agent: {response}")
                    continue
                elif user_input.lower() == 'status':
                    print(f"📊 System Status:")
                    print(f"- Model loaded: {'✅' if self.forecast_tool.model else '❌'}")
                    print(f"- LLM available: {'✅' if self.llm else '❌'}")
                    print(f"- Tools: {len(self.tools)} available")
                    continue
                
                if user_input:
                    print("🔮 Generating forecast...")
                    response = self.process_query(user_input)
                    print(f"\n🤖 Agent: {response}")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    def get_forecast_dataframe(self, steps: int = 30) -> pd.DataFrame:
        """Get forecast as DataFrame"""
        forecast_result = self.forecast_tool._run(str(steps))
        
        try:
            data = json.loads(forecast_result)
            
            if "error" in data:
                return pd.DataFrame({"error": [data["error"]]})
            
            df = pd.DataFrame({
                'date': pd.to_datetime(data['forecast_dates']),
                'forecast': data['forecast_values'],
                'lower_bound': data['lower_bound'],
                'upper_bound': data['upper_bound']
            })
            
            return df
            
        except Exception as e:
            return pd.DataFrame({"error": [f"Error creating DataFrame: {str(e)}"]})

def main():
    """Main function"""
    print("🚀 Initializing Forecast Agent with LangChain & LangGraph...")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment variables")
        print("The agent will work with limited functionality (no LLM responses)")
        print("To enable full functionality, set your OpenAI API key")
    
    try:
        agent = ForecastAgent()
        print("✅ Agent initialized successfully!")
        
        # Start interactive interface
        agent.chat_interface()
        
    except Exception as e:
        print(f"❌ Error initializing agent: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()