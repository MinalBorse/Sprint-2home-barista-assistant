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
# REQUIREMENT: "Functions should be relevant to your domain"
#   Tool 1: brew_ratio_calculator  -> water needed for a coffee dose
#   Tool 2: caffeine_estimator     -> caffeine in a drink + health note
#   Tool 3: cost_per_cup           -> how much each cup costs
#
# REQUIREMENT: "Include user input validation"
#   Every tool checks its inputs and returns a friendly error message
#   instead of crashing. The AI can read the error and explain it.
# ==========================================================

from langchain_core.tools import tool


# ==========================================================
# TOOL 1: brew_ratio_calculator
# ==========================================================
MIN_COFFEE_GRAMS = 1       # less than 1 g of coffee makes no sense
MAX_COFFEE_GRAMS = 1000    # more than 1 kg is not a home brew
MIN_RATIO = 1              # 1:1 would be extremely strong
MAX_RATIO = 30             # 1:30 would be extremely weak
DEFAULT_RATIO = 16         # 1:16 is a common, balanced ratio


@tool
def brew_ratio_calculator(coffee_grams: float, ratio: float = DEFAULT_RATIO) -> str:
    """Calculate how much water to use for a given amount of ground coffee.
    Use this when the user asks how much water they need for brewing.

    coffee_grams: amount of ground coffee in grams, for example 18
    ratio: water-to-coffee ratio, for example 16 means 1:16
    """
    # ---- Step 1: check the coffee amount ----
    if coffee_grams < MIN_COFFEE_GRAMS or coffee_grams > MAX_COFFEE_GRAMS:
        return (
            f"Error: coffee amount must be between {MIN_COFFEE_GRAMS} and "
            f"{MAX_COFFEE_GRAMS} grams. You sent {coffee_grams} g."
        )

    # ---- Step 2: check the ratio ----
    if ratio < MIN_RATIO or ratio > MAX_RATIO:
        return (
            f"Error: ratio must be between {MIN_RATIO} and {MAX_RATIO}. "
            f"You sent {ratio}. Example: for 1:16, send 16."
        )

    # ---- Step 3: calculate and answer ----
    water_grams = coffee_grams * ratio
    return (
        f"Use {water_grams:.0f} g of water for {coffee_grams:g} g of coffee "
        f"(ratio 1:{ratio:g})."
    )


# ==========================================================
# TOOL 2: caffeine_estimator
# ==========================================================
# Typical caffeine per 100 ml. These are ESTIMATES: real values
# depend on the beans, the roast, the dose and the recipe.
CAFFEINE_MG_PER_100ML = {
    "espresso": 210,
    "moka pot": 130,
    "cold brew": 70,
    "aeropress": 60,
    "french press": 45,
    "pour-over": 40,
    "drip": 40,
    "instant": 30,
    "decaf": 1,
}

MIN_SIZE_ML = 10
MAX_SIZE_ML = 2000

# General guidance for healthy adults (for example from the
# European Food Safety Authority). Shown as a note, not as advice.
DAILY_LIMIT_MG = 400
SINGLE_DOSE_LIMIT_MG = 200
PREGNANCY_DAILY_LIMIT_MG = 200


@tool
def caffeine_estimator(drink: str, size_ml: float) -> str:
    """Estimate how much caffeine is in a coffee drink of a given size.
    Use this when the user asks how much caffeine is in their coffee.

    drink: one of: espresso, moka pot, cold brew, aeropress, french press,
           pour-over, drip, instant, decaf
    size_ml: size of the drink in millilitres, for example 250
    """
    # ---- Step 1: check the drink ----
    drink_key = drink.strip().lower()
    if drink_key not in CAFFEINE_MG_PER_100ML:
        allowed = ", ".join(CAFFEINE_MG_PER_100ML.keys())
        return f"Error: unknown drink '{drink}'. Choose one of: {allowed}."

    # ---- Step 2: check the size ----
    if size_ml < MIN_SIZE_ML or size_ml > MAX_SIZE_ML:
        return (
            f"Error: size must be between {MIN_SIZE_ML} and {MAX_SIZE_ML} ml. "
            f"You sent {size_ml} ml."
        )

    # ---- Step 3: calculate ----
    caffeine_mg = CAFFEINE_MG_PER_100ML[drink_key] * size_ml / 100
    percent_of_daily = caffeine_mg / DAILY_LIMIT_MG * 100

    answer = (
        f"A {size_ml:g} ml {drink_key} has roughly {caffeine_mg:.0f} mg of caffeine "
        f"(an estimate; beans, dose and recipe change it). "
        f"That is about {percent_of_daily:.0f}% of the {DAILY_LIMIT_MG} mg daily amount "
        f"generally considered safe for healthy adults."
    )

    # ---- Step 4: health note (a domain safety measure) ----
    # REQUIREMENT: "Add relevant security measures for your domain"
    if caffeine_mg > SINGLE_DOSE_LIMIT_MG:
        answer = answer + (
            f" Note: this is more than {SINGLE_DOSE_LIMIT_MG} mg in one drink, "
            f"the single amount generally advised for adults."
        )
    answer = answer + (
        f" During pregnancy, the usual advice is under {PREGNANCY_DAILY_LIMIT_MG} mg a day. "
        f"This is general information, not medical advice."
    )
    return answer


# ==========================================================
# TOOL 3: cost_per_cup
# ==========================================================
MAX_BAG_GRAMS = 10000      # 10 kg is already a café-sized bag
MAX_BAG_PRICE = 10000


@tool
def cost_per_cup(bag_price: float, bag_grams: float, dose_grams: float) -> str:
    """Calculate how much one cup of coffee costs, and how many cups a bag makes.
    Use this when the user asks about the cost or value of their coffee beans.

    bag_price: price of the bag, for example 18 (any currency)
    bag_grams: weight of the bag in grams, for example 250
    dose_grams: coffee used per cup in grams, for example 15
    """
    # ---- Step 1: check the inputs ----
    if bag_price <= 0 or bag_price > MAX_BAG_PRICE:
        return f"Error: bag price must be more than 0 and at most {MAX_BAG_PRICE}. You sent {bag_price}."
    if bag_grams <= 0 or bag_grams > MAX_BAG_GRAMS:
        return f"Error: bag weight must be more than 0 and at most {MAX_BAG_GRAMS} g. You sent {bag_grams} g."
    if dose_grams < MIN_COFFEE_GRAMS or dose_grams > bag_grams:
        return (
            f"Error: dose per cup must be between {MIN_COFFEE_GRAMS} g and the bag weight "
            f"({bag_grams:g} g). You sent {dose_grams} g."
        )

    # ---- Step 2: calculate ----
    cups_per_bag = bag_grams / dose_grams
    cost = bag_price / cups_per_bag

    return (
        f"Each cup costs about {cost:.2f} (in the same currency as the bag price). "
        f"The {bag_grams:g} g bag makes about {cups_per_bag:.0f} cups at {dose_grams:g} g per cup."
    )


# ==========================================================
# All calculator tools in one list, so the agent can use them
# ==========================================================
CALCULATOR_TOOLS = [brew_ratio_calculator, caffeine_estimator, cost_per_cup]
