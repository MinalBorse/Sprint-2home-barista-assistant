# ==========================================================
# step08_bm25.py
# ==========================================================
# Goal: try BM25, a professional KEYWORD search.
#
# BM25 is smarter than our simple word count in step06:
#   1. RARE words count MORE   ("harsh" is in 1 note -> strong signal)
#      COMMON words count LESS ("coffee" is in 4 notes -> weak signal)
#   2. Repeating a word many times only helps a little.
#
# But it's still KEYWORD search: it cannot understand that
# "acidic" means "sour". We'll see that weakness below.
# ==========================================================

from rank_bm25 import BM25Okapi

from src.sample_notes import SAMPLE_NOTES


# ----------------------------------------------------------
# Turn text into a list of words ("tokens")
# ----------------------------------------------------------
def tokenize(text):
    """
    "Bitter, harsh or burnt-tasting coffee." ->
    ["bitter", "harsh", "or", "burnt", "tasting", "coffee"]
    """
    text = text.lower()

    # Replace punctuation with spaces.
    # The "-" matters: "burnt-tasting" must become "burnt" + "tasting",
    # otherwise the word "burnt" would never match.
    for symbol in [".", ",", "?", "!", "-", "(", ")"]:
        text = text.replace(symbol, " ")

    return text.split()


# ----------------------------------------------------------
# STEP 1: build the BM25 index (done ONCE)
# ----------------------------------------------------------
# BM25 needs every note as a list of words.
tokenized_notes = []
for note in SAMPLE_NOTES:
    tokenized_notes.append(tokenize(note["text"]))

# This counts how often each word appears in each note,
# and how rare each word is across all notes.
bm25 = BM25Okapi(tokenized_notes)


# ----------------------------------------------------------
# How much is each word "worth"? (IDF = rarity score)
# ----------------------------------------------------------
print("========== WORD VALUES (higher = rarer = stronger signal) ==========")
words_to_check = ["coffee", "grind", "harsh", "burnt", "sour", "v60"]
for word in words_to_check:
    # bm25.idf is a dictionary: word -> rarity score
    value = bm25.idf.get(word, 0)
    print(f"   {word:<8} {value:.3f}")
print()


# ----------------------------------------------------------
# STEP 2: search with a question
# ----------------------------------------------------------
def bm25_search(question):
    """Score every note for the question and print the ranking."""

    print("==================================================")
    print("QUESTION:", question)
    print()

    question_words = tokenize(question)

    # One score per note, in the same order as SAMPLE_NOTES
    scores = bm25.get_scores(question_words)

    # Pair each note with its score
    results = []
    for index in range(len(SAMPLE_NOTES)):
        results.append({"score": scores[index], "note": SAMPLE_NOTES[index]})

    # Highest score first
    results.sort(key=lambda item: item["score"], reverse=True)

    rank = 1
    for item in results:
        score = item["score"]
        bar = "#" * int(score * 5)
        print(f"{rank}. {score:.3f} {bar}")
        print(f"   [{item['note']['id']}] {item['note']['text'][:55]}...")
        rank = rank + 1

    print()


# Test 1: the words "harsh" and "burnt" ARE in the bitter note
bm25_search("My coffee tastes harsh and burnt, how can I fix it?")

# Test 2: "acidic" and "tangy" are NOT in any note (they mean "sour")
bm25_search("Why does my brew taste too acidic and tangy?")

# Test 3: an exact name - keyword search should be strong here
bm25_search("What water temperature should I use for a V60?")
