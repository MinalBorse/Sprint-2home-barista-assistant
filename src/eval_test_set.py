# ==========================================================
# src/eval_test_set.py
# ==========================================================
# The TEST SET for evaluating our RAG with RAGAs.
#
# Each test case has:
#   "question"  -> what a user might ask
#   "reference" -> the CORRECT answer, written by us from our own guides
#
# Why do we need reference answers?
#   Context recall asks: "did retrieval find ALL the information
#   needed?" RAGAs can only check that if it knows what the
#   complete, correct answer looks like.
#
# The mix on purpose:
#   - clear questions, vague or slang questions,
#   - questions about each brew method,
#   - and one OFF-TOPIC question (the right answer is "I don't know").
# ==========================================================

TEST_SET = [
    {
        "question": "My coffee tastes harsh and burnt, how can I fix it?",
        "reference": "Harsh or burnt-tasting coffee is usually over-extracted. Use a coarser grind, "
        "slightly cooler water around 90 to 93 degrees Celsius, or a shorter brew time. "
        "For a French press, steep about 4 minutes and pour the coffee out right away.",
    },
    {
        "question": "why's my cup so meh?",
        "reference": "Flat or dull coffee is usually caused by old or badly stored beans. Use beans "
        "within 2 to 4 weeks of the roast date, grind just before brewing, and store "
        "beans in an airtight container away from light, heat and moisture.",
    },
    {
        "question": "it's kinda puckery and thin, help",
        "reference": "Sour, thin coffee is usually under-extracted and may use too little coffee. "
        "Use a finer grind, hotter water between 92 and 96 degrees Celsius, a longer "
        "brew time, and more coffee, for example a 1:16 ratio.",
    },
    {
        "question": "How hot should the water be for pour over?",
        "reference": "For pour-over or V60, use water between 92 and 96 degrees Celsius. Without a "
        "thermometer, boil the water and let it rest for about 30 seconds.",
    },
    {
        "question": "How long should I steep a French press?",
        "reference": "Steep a French press for about 4 minutes with a coarse grind and a 1:15 ratio. "
        "Stir after 1 minute, press slowly, and pour all the coffee out right away.",
    },
    {
        "question": "Why does my moka pot coffee taste burnt?",
        "reference": "Burnt-tasting moka pot coffee is usually caused by overheating. Use hot water in "
        "the base, brew on medium-low heat with the lid open, take it off the heat when "
        "it starts to sputter, and cool the base under cold water.",
    },
    {
        "question": "What ratio should I use for espresso?",
        "reference": "Espresso uses about a 1:2 ratio, for example 18 grams of ground coffee to get "
        "36 grams of espresso, with a fine grind and a shot time of about 25 to 30 seconds.",
    },
    {
        "question": "How do I make cold brew?",
        "reference": "Use a coarse grind and about a 1:8 ratio for a concentrate, for example 100 grams "
        "of coffee for 800 grams of water. Steep 12 to 24 hours, filter it, and dilute "
        "about one to one with water or milk.",
    },
    {
        "question": "My espresso shot runs really fast and tastes sour",
        "reference": "A fast, sour espresso shot is under-extracted. Grind finer so the shot takes "
        "about 25 to 30 seconds.",
    },
    {
        "question": "How do I make latte art?",
        "reference": "The coffee notes do not cover latte art, so the assistant should say it does "
        "not have information about that.",
    },
]
