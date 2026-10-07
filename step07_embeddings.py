# ==========================================================
# step07_embeddings.py
# ==========================================================
# Goal: see that embeddings understand MEANING, not just words.
#
# In step06, "My coffee tastes harsh" FAILED with keyword search,
# because the word "harsh" isn't in any note.
# Here we compare MEANING instead, using embeddings.
#
# This matches the course's Part 2, Lab 1:
# "Generate and explore embeddings".
# ==========================================================

import math
from src.embeddings import get_embeddings


# ----------------------------------------------------------
# The same 5 coffee notes as in step06
# (Later they will come from real documents in a data/ folder.)
# ----------------------------------------------------------
KNOWLEDGE_BASE = [
    {
        "source": "troubleshooting_guide",
        "text": "Bitter, harsh or burnt-tasting coffee is usually over-extracted. "
                "Use a coarser grind, slightly cooler water, or a shorter brew time. "
                "For a French press, steep for about 4 minutes, not longer.",
    },
    {
        "source": "troubleshooting_guide",
        "text": "Sour coffee is usually under-extracted. "
                "Try a finer grind, hotter water, or a longer brew time.",
    },
    {
        "source": "v60_guide",
        "text": "For a V60, use a medium-fine grind and water at 92 to 96 degrees Celsius. "
                "Bloom the coffee with twice its weight in water for 30 to 45 seconds.",
    },
    {
        "source": "beans_guide",
        "text": "Light roasts keep more fruity and floral flavours. "
                "Dark roasts taste more chocolatey and smoky.",
    },
    {
        "source": "storage_guide",
        "text": "Store coffee beans in an airtight container away from light and heat. "
                "Beans taste best within 2 to 4 weeks after the roast date.",
    },
]


# ----------------------------------------------------------
# Cosine similarity: how similar are two vectors?
# ----------------------------------------------------------
def cosine_similarity(vector_a, vector_b):
    """
    Compare two vectors and return one number.
    Higher number = more similar meaning.

    Formula: (a . b) / (length of a * length of b)
    """

    # 1. Multiply matching numbers and add them up ("dot product")
    dot_product = 0
    for number_a, number_b in zip(vector_a, vector_b):
        dot_product = dot_product + (number_a * number_b)

    # 2. The "length" of each vector
    length_a = math.sqrt(sum(number * number for number in vector_a))
    length_b = math.sqrt(sum(number * number for number in vector_b))

    # 3. Divide to get a score that doesn't depend on vector length
    similarity = dot_product / (length_a * length_b)
    return similarity


# ----------------------------------------------------------
# STEP 1: embed all notes (done ONCE, like building a knowledge base)
# ----------------------------------------------------------
embeddings_model = get_embeddings()

# Put only the texts in a list, because the model needs plain texts
note_texts = []
for note in KNOWLEDGE_BASE:
    note_texts.append(note["text"])

print("Embedding the 5 notes...")

# embed_documents() embeds MANY texts in one call (for the knowledge base)
note_vectors = embeddings_model.embed_documents(note_texts)

print(f"Done. Each note is now a vector of {len(note_vectors[0])} numbers.")
print()


# ----------------------------------------------------------
# STEP 2: embed a question and compare it with every note
# ----------------------------------------------------------
def compare_question_with_notes(question):
    """Embed one question and rank all notes by similarity."""

    print("==================================================")
    print("QUESTION:", question)
    print()

    # embed_query() embeds ONE text (for the user's question)
    question_vector = embeddings_model.embed_query(question)

    # Score every note
    results = []
    for index in range(len(KNOWLEDGE_BASE)):
        note = KNOWLEDGE_BASE[index]
        note_vector = note_vectors[index]

        score = cosine_similarity(question_vector, note_vector)
        results.append({"score": score, "note": note})

    # Sort: most similar first
    results.sort(key=lambda item: item["score"], reverse=True)

    # Print the ranking with a simple bar chart made of # symbols
    rank = 1
    for item in results:
        score = item["score"]
        bar = "#" * int(score * 40)
        short_text = item["note"]["text"][:55]
        print(f"{rank}. {score:.3f} {bar}")
        print(f"   [{item['note']['source']}] {short_text}...")
        rank = rank + 1

    print()


# Test 1: the question that FAILED with keyword search.
# "harsh" is not in any note, but it MEANS bitter.
compare_question_with_notes("My coffee tastes harsh and burnt, how can I fix it?")

# Test 2: a different word for sour ("tangy" / "acidic")
compare_question_with_notes("Why does my brew taste too acidic and tangy?")

# Test 3: a topic that is NOT in our notes.
# All scores should be low - nothing is really relevant.
compare_question_with_notes("How do I make latte art?")