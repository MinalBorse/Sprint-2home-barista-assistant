# ==========================================================
# src/tools.py
# ==========================================================
# This file contains the TOOLS our chatbot can use.
#
# What is a tool?
#   A normal Python function that the AI is allowed to ask for.
#   The AI decides WHEN to use it, but OUR code actually runs it.
#
# Why do we need tools?
#   AI models are good with words, but they can make mistakes with math.
#   Tools give exact answers because real code does the calculation.
#
# REQUIREMENT: "Implement at least 3 different tool calls"
#   Tool 1: brew_ratio_calculator   (done - below)
#   Tool 2: caffeine_estimator      (coming in Part 4)
#   Tool 3: cost_per_cup            (coming in Part 4)
# ==========================================================

from langchain_core.tools import tool


# ----------------------------------------------------------
# Limits for valid input
# ----------------------------------------------------------
# We store the limits in variables at the top of the file.
# If we ever want to change a limit, we change it here only.
# (Names in CAPITALS mean "this value never changes".)

MIN_COFFEE_GRAMS = 1       # less than 1 g of coffee makes no sense
MAX_COFFEE_GRAMS = 1000    # more than 1 kg is not a home brew

MIN_RATIO = 1              # 1:1 would be extremely strong
MAX_RATIO = 30             # 1:30 would be extremely weak

DEFAULT_RATIO = 16         # 1:16 is a common, balanced ratio


# ----------------------------------------------------------
# TOOL 1: brew_ratio_calculator
# ----------------------------------------------------------
# @tool turns this normal function into a tool the AI can use.
# LangChain reads 3 things from the function and shows them to the AI:
#   1. the function NAME      -> the tool's name
#   2. the DOCSTRING (""" """) -> the tool's description
#   3. the INPUTS and types   -> what the AI must send
# The AI never sees the code inside the function.

@tool
def brew_ratio_calculator(coffee_grams: float, ratio: float = DEFAULT_RATIO) -> str:
    """Calculate how much water to use for a given amount of ground coffee.
    Use this when the user asks how much water they need for brewing.

    coffee_grams: amount of ground coffee in grams, for example 18
    ratio: water-to-coffee ratio, for example 16 means 1:16
    """

    # ---- Step 1: check the coffee amount ----
    # REQUIREMENT: "Include user input validation"
    # If the number is too small or too big, we stop here
    # and return a friendly error message.
    if coffee_grams < MIN_COFFEE_GRAMS or coffee_grams > MAX_COFFEE_GRAMS:
        error_message = (
            f"Error: coffee amount must be between "
            f"{MIN_COFFEE_GRAMS} and {MAX_COFFEE_GRAMS} grams. "
            f"You sent {coffee_grams} g."
        )
        return error_message

    # ---- Step 2: check the ratio ----
    if ratio < MIN_RATIO or ratio > MAX_RATIO:
        error_message = (
            f"Error: ratio must be between {MIN_RATIO} and {MAX_RATIO}. "
            f"You sent {ratio}. Example: for 1:16, send 16."
        )
        return error_message

    # ---- Step 3: do the calculation ----
    # Example: 18 g of coffee x 16 = 288 g of water
    water_grams = coffee_grams * ratio

    # ---- Step 4: build a clear answer ----
    # :.0f means "show the number with 0 decimals" (288.0 -> 288)
    # :g means "show the number without useless zeros" (18.0 -> 18)
    answer = (
        f"Use {water_grams:.0f} g of water "
        f"for {coffee_grams:g} g of coffee "
        f"(ratio 1:{ratio:g})."
    )
    return answer