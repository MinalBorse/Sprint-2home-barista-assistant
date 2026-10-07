# ==========================================================
# step03_memory.py
# ==========================================================
# Goal: see that the AI has NO memory of its own,
#       and that OUR CODE creates memory.
#
# How memory works:
#   Every time we call the AI, it only knows the messages
#   we send in THAT call. To "remember", we keep a list of
#   the whole conversation and send the full list every time.
#
# Later (Part 4) a "checkpointer" will do this for us
# automatically. Here we do it by hand to understand it.
# ==========================================================

from langchain_core.messages import SystemMessage, HumanMessage
from src.llm import get_llm


# Create the AI model
llm = get_llm()

# The system prompt: the bot's role and rules.
# We reuse it in both tests below.
system_prompt = SystemMessage(
    "You are a friendly home barista assistant. Keep answers to 2 sentences."
)

# The two things the user says, in order
first_user_message = "I brew with a V60 and use 15 g of coffee."
follow_up_question = "Which brewer and how much coffee did I say I use?"


# ==========================================================
# TEST 1: WITHOUT memory
# ==========================================================
# Each call gets a NEW list with only the current message.
# The AI never sees the first message when answering the second.

print("========== TEST 1: WITHOUT MEMORY ==========")
print()

# Call 1: tell the bot about our setup
call_1_messages = [system_prompt, HumanMessage(first_user_message)]
llm.invoke(call_1_messages)

# Call 2: ask the follow-up in a brand new list
# (the first message is NOT included)
call_2_messages = [system_prompt, HumanMessage(follow_up_question)]
answer = llm.invoke(call_2_messages)

print("USER:", follow_up_question)
print("BOT: ", answer.content)
print()


# ==========================================================
# TEST 2: WITH memory
# ==========================================================
# We keep ONE list for the whole conversation.
# After every turn, we add BOTH the user's message
# and the AI's reply to that list.

print("========== TEST 2: WITH MEMORY ==========")
print()

# This list IS the memory. It starts with only the system prompt.
conversation_history = [system_prompt]

# ---- Turn 1 ----
conversation_history.append(HumanMessage(first_user_message))
reply_1 = llm.invoke(conversation_history)

# Important: also save the AI's reply,
# otherwise the AI won't know what IT said before.
conversation_history.append(reply_1)

print("USER:", first_user_message)
print("BOT: ", reply_1.content)
print()

# ---- Turn 2 ----
conversation_history.append(HumanMessage(follow_up_question))
reply_2 = llm.invoke(conversation_history)
conversation_history.append(reply_2)

print("USER:", follow_up_question)
print("BOT: ", reply_2.content)
print()


# ==========================================================
# What was in the memory at the end?
# ==========================================================
print("========== CONVERSATION HISTORY ==========")
print()

message_number = 1
for message in conversation_history:
    message_type = type(message).__name__
    print(f"{message_number}. {message_type}")
    message_number = message_number + 1

print()
print("Notice: the list grows with every turn.")
print("Long chats = long lists = slower and more expensive.")
print("That's why real apps trim or summarise old messages.")