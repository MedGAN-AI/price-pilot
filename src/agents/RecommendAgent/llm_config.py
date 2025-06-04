from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

llm = OllamaLLM(model="llama3.2:1b")

prompt = PromptTemplate.from_template(
    "Given the following product description: '{product_description}', generate a short, friendly recommendation summary."
)

# Modern LangChain chaining syntax
summary_chain = prompt | llm
