from langchain_core.messages import SystemMessage, HumanMessage
from src.llm import get_llm

llm = get_llm()

# Lesson 2: a conversation is a list of messages with roles
messages = [
    SystemMessage("You are a friendly home barista assistant. Only answer coffee questions. Keep answers short."),
    HumanMessage("What's the difference between a V60 and a French press?"),
]
response = llm.invoke(messages)   # response is an AIMessage
print(response.content)           # .content = the text