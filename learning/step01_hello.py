from langchain_core.messages import SystemMessage, HumanMessage
from src.llm import get_llm

llm = get_llm()

messages = [
    SystemMessage("You are a friendly home barista assistant. Keep answers short."),
    HumanMessage("Which brewer did I say I own?"),
]

response = llm.invoke(messages)
print(response.content)

