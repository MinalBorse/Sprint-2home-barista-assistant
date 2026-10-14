# ==========================================================
# step06_rag_by_hand.py
# ==========================================================
# Goal: build RAG (Retrieval-Augmented Generation) by hand,
#       so we understand every step before using real tools.
#
#   Step 1: a knowledge base (here: a small Python list)
#   Step 2: the user asks a question
#   Step 3: RETRIEVE the most relevant notes
#   Step 4: AUGMENT the prompt with those notes, and GENERATE an answer
#
# Warning: our search here only matches WORDS.
# At the end we'll see why that is not good enough.
# ==========================================================

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm

# ==========================================================
# STEP 1: the knowledge base
# ==========================================================
# REQUIREMENT: "Create a knowledge base relevant to your domain"
# Each note is a dictionary with:
#   "source" -> where the text came from (we show it to the user)
#   "text"   -> the actual information
# Later, these notes will come from real documents in a data/ folder.

KNOWLEDGE_BASE = [
    {
        "source": "troubleshooting_guide",
        "text": "Bitter French press coffee is usually over-extracted. "
        "Use a coarser grind and steep for about 4 minutes, not longer.",
    },
    {
        "source": "troubleshooting_guide",
        "text": "Sour coffee is usually under-extracted. Try a finer grind, hotter water, or a longer brew time.",
    },
    {
        "source": "v60_guide",
        "text": "For a V60, use a medium-fine grind and water at 92 to 96 degrees Celsius. "
        "Bloom the coffee with twice its weight in water for 30 to 45 seconds.",
    },
    {
        "source": "beans_guide",
        "text": "Light roasts keep more fruity and floral flavours. Dark roasts taste more chocolatey and smoky.",
    },
    {
        "source": "storage_guide",
        "text": "Store coffee beans in an airtight container away from light and heat. "
        "Beans taste best within 2 to 4 weeks after the roast date.",
    },
]

# Common words that appear everywhere and don't help the search.
# If we counted them, "my" or "is" would match almost every note.
IGNORED_WORDS = ["why", "is", "my", "the", "a", "how", "do", "i", "what", "to", "and", "for", "it", "so"]

# How many notes to give the AI
NUMBER_OF_NOTES_TO_USE = 2


# ==========================================================
# STEP 3: RETRIEVE - find the most relevant notes
# ==========================================================
def clean_words(text):
    """
    Turn a sentence into a list of useful lowercase words.
    "Why is my coffee bitter?" -> ["coffee", "bitter"]
    """
    text = text.lower()

    # Remove punctuation so "bitter?" becomes "bitter"
    for symbol in [".", ",", "?", "!"]:
        text = text.replace(symbol, "")

    useful_words = []
    for word in text.split():
        if word not in IGNORED_WORDS:
            useful_words.append(word)

    return useful_words


def retrieve_notes(question):
    """
    Give every note a score = how many question words it contains.
    Return the notes with the highest scores.
    """
    question_words = clean_words(question)

    scored_notes = []
    for note in KNOWLEDGE_BASE:
        note_words = clean_words(note["text"])

        # Count how many question words appear in this note
        score = 0
        for word in question_words:
            if word in note_words:
                score = score + 1

        scored_notes.append({"note": note, "score": score})

    # Sort: highest score first
    scored_notes.sort(key=lambda item: item["score"], reverse=True)

    # Keep the best notes, but only if they matched at least 1 word
    best_notes = []
    for item in scored_notes[:NUMBER_OF_NOTES_TO_USE]:
        if item["score"] > 0:
            best_notes.append(item["note"])
            print(f"   found (score {item['score']}) from [{item['note']['source']}]")

    return best_notes


# ==========================================================
# STEP 4: AUGMENT the prompt and GENERATE the answer
# ==========================================================
# REQUIREMENT: "Implement domain-specific prompts"
# This system prompt tells the AI to use ONLY our notes.
# That's what "grounded" means: the answer comes from our data,
# not from the AI's memory.
SYSTEM_PROMPT = (
    "You are a friendly home barista assistant. "
    "Answer ONLY using the coffee notes provided. "
    "At the end, say which source(s) you used, like: (Source: v60_guide). "
    "If the notes don't contain the answer, say: "
    "'I don't have information about that in my coffee notes.'"
)


def answer_with_rag(question):
    """Run the full RAG flow for one question."""
    print("==================================================")
    print("USER:", question)
    print()

    # --- Retrieve ---
    print("STEP 3 - Retrieving notes...")
    notes = retrieve_notes(question)
    if not notes:
        print("   no matching notes found")
    print()

    # --- Augment: build the text that goes into the prompt ---
    notes_text = ""
    for note in notes:
        notes_text = notes_text + f"[{note['source']}] {note['text']}\n"

    augmented_question = f"Coffee notes:\n{notes_text}\nQuestion: {question}"

    print("STEP 4a - The prompt we send to the AI:")
    print(augmented_question)
    print()

    # --- Generate ---
    llm = get_llm()
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(augmented_question)]
    response = llm.invoke(messages)

    print("STEP 4b - The AI's answer:")
    print(response.content)
    print()


# ==========================================================
# STEP 2: the user asks questions
# ==========================================================

# Test 1: uses the same word as our notes ("bitter") -> should work
answer_with_rag("Why is my French press coffee bitter?")

# Test 2: a topic that is NOT in our notes -> should say "I don't know"
answer_with_rag("How do I make latte art?")

# Test 3: same problem as Test 1, but with a DIFFERENT word ("harsh").
# Our word-matching search will struggle. Watch what happens!
answer_with_rag("My coffee tastes harsh, how do I fix it?")
