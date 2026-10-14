# ==========================================================
# step17_tools.py
# ==========================================================
# Goal: test ALL THREE tools on their own, without the AI.
#
# Why test without the AI?
#   - It's free (no API call) and instant.
#   - If the agent gives a wrong number later, and these tests pass,
#     we know the problem is the AI's choice of inputs, not the math.
#
# REQUIREMENT: "Implement at least 3 different tool calls"
# REQUIREMENT: "Include user input validation"
# ==========================================================

from src.tools import CALCULATOR_TOOLS, brew_ratio_calculator, caffeine_estimator, cost_per_cup

passed = 0
failed = 0


def run_test(test_name, tool_function, tool_inputs, expected_text):
    """Run one tool and check that its answer contains expected_text."""
    global passed, failed

    result = tool_function.invoke(tool_inputs)
    if expected_text in result:
        status = "PASS"
        passed = passed + 1
    else:
        status = "FAIL"
        failed = failed + 1

    print(f"[{status}] {test_name}")
    print(f"       result: {result}")
    print()


print("========== TOOL 1: brew_ratio_calculator ==========\n")
run_test("18 g at 1:16", brew_ratio_calculator, {"coffee_grams": 18, "ratio": 16}, "288 g of water")
run_test("bad ratio (116)", brew_ratio_calculator, {"coffee_grams": 18, "ratio": 116}, "Error")
run_test("300 ml of water -> coffee", brew_ratio_calculator, {"water_ml": 300}, "18.8 g of coffee")
run_test("500 ml at 1:15 -> coffee", brew_ratio_calculator, {"water_ml": 500, "ratio": 15}, "33.3 g of coffee")
run_test("both amounts given", brew_ratio_calculator, {"coffee_grams": 18, "water_ml": 300}, "Error")
run_test("no amount given", brew_ratio_calculator, {}, "Error")

print("========== TOOL 2: caffeine_estimator ==========\n")
run_test("250 ml pour-over", caffeine_estimator, {"drink": "pour-over", "size_ml": 250}, "100 mg")
run_test("big cold brew (health note)", caffeine_estimator, {"drink": "cold brew", "size_ml": 350}, "more than 200 mg")
run_test("drink name with capitals", caffeine_estimator, {"drink": "Espresso", "size_ml": 30}, "63 mg")
run_test("unknown drink", caffeine_estimator, {"drink": "energy drink", "size_ml": 250}, "Error")
run_test("size too big", caffeine_estimator, {"drink": "espresso", "size_ml": 5000}, "Error")

print("========== TOOL 3: cost_per_cup ==========\n")
run_test("18 for 250 g, 15 g per cup", cost_per_cup, {"bag_price": 18, "bag_grams": 250, "dose_grams": 15}, "1.08")
run_test("dose bigger than the bag", cost_per_cup, {"bag_price": 18, "bag_grams": 250, "dose_grams": 300}, "Error")
run_test("negative price", cost_per_cup, {"bag_price": -5, "bag_grams": 250, "dose_grams": 15}, "Error")

print("========== WHAT THE AI SEES (names and descriptions) ==========\n")
for tool_function in CALCULATOR_TOOLS:
    first_line = tool_function.description.split("\n")[0]
    print(f"- {tool_function.name}: {first_line}")
    print(f"  inputs: {list(tool_function.args.keys())}")
print()

print(f"RESULT: {passed} passed, {failed} failed")
