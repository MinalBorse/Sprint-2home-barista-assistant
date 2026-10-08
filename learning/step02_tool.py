# ==========================================================
# step02_tool.py
# ==========================================================
# Goal: test our tool ON ITS OWN, without the AI.
#
# Why test without the AI?
#   - It's free (no API call) and instant.
#   - If something breaks later, we already know the tool works,
#     so the problem must be somewhere else.
#
# REQUIREMENT: "Include user input validation"
#   We test that bad inputs are caught by the tool.
# ==========================================================

from src.tools import brew_ratio_calculator


# ----------------------------------------------------------
# A small helper to run one test and say PASS or FAIL
# ----------------------------------------------------------
def run_test(test_name, tool_inputs, expected_text):
    """
    Run the tool with tool_inputs and check if the result
    contains expected_text.
    """
    # .invoke() runs the tool. We send the inputs as a dictionary,
    # exactly the way the AI will send them later.
    result = brew_ratio_calculator.invoke(tool_inputs)

    # Check if the expected text appears in the result
    if expected_text in result:
        status = "PASS"
    else:
        status = "FAIL"

    print(f"[{status}] {test_name}")
    print(f"       inputs: {tool_inputs}")
    print(f"       result: {result}")
    print()


# ----------------------------------------------------------
# Part 1: normal use (the tool should calculate)
# ----------------------------------------------------------
print("========== NORMAL USE ==========")
print()

# 18 g x 16 = 288 g of water
run_test(
    test_name="18 g at 1:16",
    tool_inputs={"coffee_grams": 18, "ratio": 16},
    expected_text="288 g of water",
)

# No ratio sent -> the default ratio (16) is used: 22 x 16 = 352
run_test(
    test_name="22 g with the default ratio",
    tool_inputs={"coffee_grams": 22},
    expected_text="352 g of water",
)


# ----------------------------------------------------------
# Part 2: bad inputs (the tool should return an error, not crash)
# ----------------------------------------------------------
print("========== BAD INPUTS ==========")
print()

# Negative coffee amount
run_test(
    test_name="negative coffee",
    tool_inputs={"coffee_grams": -5},
    expected_text="Error",
)

# Way too much coffee
run_test(
    test_name="too much coffee",
    tool_inputs={"coffee_grams": 5000},
    expected_text="Error",
)

# The AI misread "1:16" as 116
run_test(
    test_name="ratio too big (116 instead of 16)",
    tool_inputs={"coffee_grams": 18, "ratio": 116},
    expected_text="Error",
)


# ----------------------------------------------------------
# Part 3: what the AI "sees" about this tool
# ----------------------------------------------------------
# This is ALL the AI knows about the tool.
# It never sees the code inside the function.
print("========== WHAT THE AI SEES ==========")
print()
print("Name:")
print(brew_ratio_calculator.name)
print()
print("Description:")
print(brew_ratio_calculator.description)
print()
print("Inputs:")
print(brew_ratio_calculator.args)