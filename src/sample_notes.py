# ==========================================================
# src/sample_notes.py
# ==========================================================
# A small set of coffee notes we use for LEARNING and TESTING
# retrieval (keyword search, embeddings, hybrid search).
#
# Why is this in its own file?
#   Several scripts use the same notes. If each script had its own
#   copy, the copies could become different without us noticing,
#   and our tests would compare different data.
#   One shared file = one source of truth.
#
# Later (Part 3), the real knowledge base will come from
# coffee documents in the data/ folder instead.
# ==========================================================


# Each note has:
#   "id"     -> a short unique name, so tests can say which note is correct
#   "source" -> where the text came from (shown to the user)
#   "text"   -> the information itself

SAMPLE_NOTES = [
    {
        "id": "bitter",
        "source": "troubleshooting_guide",
        "text": "Bitter, harsh or burnt-tasting coffee is usually over-extracted. "
                "Use a coarser grind, slightly cooler water, or a shorter brew time. "
                "For a French press, steep for about 4 minutes, not longer.",
    },
    {
        "id": "sour",
        "source": "troubleshooting_guide",
        "text": "Sour coffee is usually under-extracted. "
                "Try a finer grind, hotter water, or a longer brew time.",
    },
    {
        "id": "v60",
        "source": "v60_guide",
        "text": "For a V60, use a medium-fine grind and water at 92 to 96 degrees Celsius. "
                "Bloom the coffee with twice its weight in water for 30 to 45 seconds.",
    },
    {
        "id": "roast",
        "source": "beans_guide",
        "text": "Light roasts keep more fruity and floral flavours. "
                "Dark roasts taste more chocolatey and smoky.",
    },
    {
        "id": "storage",
        "source": "storage_guide",
        "text": "Store coffee beans in an airtight container away from light and heat. "
                "Beans taste best within 2 to 4 weeks after the roast date.",
    },
]