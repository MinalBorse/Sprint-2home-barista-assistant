# ==========================================================
# step05_agent_loop.py
# ==========================================================
# Goal: run the FULL agent loop by hand, step by step.
#
#   1. The AI decides it needs a tool, and ASKS for it
#   2. OUR code runs the tool
#   3. We send the tool's result back to the AI
#   4. The AI reads the result and writes the final answer
#
# In Part 4, create_agent() will do all of this for us
# automatically. Doing it by hand first shows us what
# create_agent() is really doing behind the scenes.
#
# REQUIREMENT: "Tool calling" (complete flow)
# ==========================================================

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.llm import get_llm
from src.tools import brew_ratio_calculator

# ----------------------------------------------------------
# SETUP
# ----------------------------------------------------------
llm = get_llm()

# Tell the AI that this tool exists
llm_with_tools = llm.bind_tools([brew_ratio_calculator])

# The conversation starts with the system prompt and the user's question
user_question = "I use 15 g of coffee in my V60. How much water at 1:16?"

messages = []
messages.append(SystemMessage("You are a friendly home barista assistant."))
messages.append(HumanMessage(user_question))

print("USER:", user_question)
print()


# ----------------------------------------------------------
# STEP 1: the AI decides what to do
# ----------------------------------------------------------
first_response = llm_with_tools.invoke(messages)

# Save the AI's request in the conversation.
# The AI must see its own request later, so it understands
# which question the tool result belongs to.
messages.append(first_response)

print("STEP 1 - The AI asked for a tool:")
for tool_call in first_response.tool_calls:
    print("   tool name:", tool_call["name"])
    print("   arguments:", tool_call["args"])
print()


# ----------------------------------------------------------
# STEP 2 + 3: run each tool and send the result back
# ----------------------------------------------------------
# The AI can ask for more than one tool at once,
# so we go through the requests one by one.
for tool_call in first_response.tool_calls:
    # The inputs the AI wants to send,
    # for example {"coffee_grams": 15, "ratio": 16}
    tool_arguments = tool_call["args"]

    # STEP 2: OUR code runs the tool.
    # The AI never runs code - it only asks.
    tool_result = brew_ratio_calculator.invoke(tool_arguments)

    print("STEP 2 - Our code ran the tool. Result:")
    print("  ", tool_result)
    print()

    # STEP 3: put the result in a ToolMessage and add it to the conversation.
    # tool_call_id links this result to the request it answers
    # (important when the AI asks for several tools at once).
    tool_message = ToolMessage(content=tool_result, tool_call_id=tool_call["id"])
    messages.append(tool_message)

print("STEP 3 - We sent the result back to the AI as a ToolMessage")
print()


# ----------------------------------------------------------
# STEP 4: the AI reads the tool result and writes the answer
# ----------------------------------------------------------
final_response = llm_with_tools.invoke(messages)
messages.append(final_response)

print("STEP 4 - The AI's final answer:")
print("  ", final_response.content)
print()


# ----------------------------------------------------------
# Every message in the conversation, in order
# ----------------------------------------------------------
print("========== FULL CONVERSATION ==========")
message_number = 1
for message in messages:
    message_type = type(message).__name__
    print(f"{message_number}. {message_type}")
    message_number = message_number + 1
