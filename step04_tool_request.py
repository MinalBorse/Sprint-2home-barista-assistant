# ==========================================================
# step04_tool_request.py
# ==========================================================
# Goal: see that the AI only ASKS for a tool.
#       It never runs the tool itself.
#
# This is STEP 1 of the "agent loop":
#   1. The AI decides if it needs a tool   <-- this file
#   2. Our code runs the tool
#   3. We send the result back to the AI
#   4. The AI writes the final answer
#
# REQUIREMENT: "Tool calling"
#   This shows HOW the AI chooses a tool.
# ==========================================================

from langchain_core.messages import SystemMessage, HumanMessage
from src.llm import get_llm
from src.tools import brew_ratio_calculator


# ----------------------------------------------------------
# SETUP
# ----------------------------------------------------------
llm = get_llm()

# bind_tools() gives the AI the tool's name, description and inputs.
# Now the AI knows this tool exists and can ask for it.
llm_with_tools = llm.bind_tools([brew_ratio_calculator])

system_prompt = SystemMessage("You are a friendly home barista assistant.")


# ----------------------------------------------------------
# A helper to send one question and show what the AI decided
# ----------------------------------------------------------
def ask_and_show_decision(test_name, user_question):
    """
    Send one question to the AI and print:
      - the text answer (if any)
      - the tool calls it requested (if any)
    """
    messages = [system_prompt, HumanMessage(user_question)]
    response = llm_with_tools.invoke(messages)

    print(f"========== {test_name} ==========")
    print("USER:", user_question)
    print()

    # Did the AI ask for a tool?
    if response.tool_calls:
        print("DECISION: the AI asked for a tool")
        for tool_call in response.tool_calls:
            print("   tool name:", tool_call["name"])
            print("   arguments:", tool_call["args"])
        print("   text answer: (empty - the AI is waiting for the tool result)")
    else:
        print("DECISION: no tool needed, the AI answered directly")
        print("   text answer:", response.content)

    print()


# ----------------------------------------------------------
# The tests
# ----------------------------------------------------------

# Case 1: needs a calculation -> should ask for the tool
ask_and_show_decision(
    test_name="CASE 1: calculation",
    user_question="I use 15 g of coffee in my V60. How much water at 1:16?",
)

# Case 2: just a greeting -> should NOT use a tool
ask_and_show_decision(
    test_name="CASE 2: greeting",
    user_question="Hi! What can you help me with?",
)

# Case 3: a knowledge question -> should NOT use the water calculator
# (Later, RAG will answer questions like this from our coffee documents.)
ask_and_show_decision(
    test_name="CASE 3: knowledge question",
    user_question="Why does my French press coffee taste bitter?",
)