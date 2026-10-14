# ==========================================================
# step09_hybrid_eval.py
# ==========================================================
# Goal:
#   1. Build HYBRID search = keyword search (BM25) + embeddings
#   2. MEASURE which search method finds the right notes,
#      using precision@k and recall@k (course Part 2, Lab 2)
#
# Why measure?
#   Judging results "by eye" is unreliable. A test set with
#   known correct answers gives us real numbers to compare.
# ==========================================================

import math

from rank_bm25 import BM25Okapi

from src.embeddings import get_embeddings
from src.sample_notes import SAMPLE_NOTES

# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
TOP_K = 2  # how many notes we retrieve per question

RRF_CONSTANT = 60  # standard value for Reciprocal Rank Fusion
EMBEDDING_WEIGHT = 0.6  # how much we trust meaning (embeddings)
BM25_WEIGHT = 0.4  # how much we trust exact words (BM25)


# ----------------------------------------------------------
# The TEST SET: questions + the note(s) that SHOULD be found
# ----------------------------------------------------------
# We wrote these by hand, so we KNOW the correct answers.
TEST_SET = [
    {"question": "My coffee tastes harsh and burnt, how can I fix it?", "relevant_ids": ["bitter"]},
    {"question": "Why does my brew taste too acidic and tangy?", "relevant_ids": ["sour"]},
    {"question": "What water temperature should I use for a V60?", "relevant_ids": ["v60"]},
    {"question": "How should I keep my beans fresh?", "relevant_ids": ["storage"]},
    {"question": "Which roast tastes chocolatey?", "relevant_ids": ["roast"]},
    {"question": "My pour-over tastes weak and sharp, what should I change?", "relevant_ids": ["sour"]},
]


# ==========================================================
# PART 1: the three search methods
# Each one returns a list of note ids, best first,
# for example ["bitter", "sour", "v60", "roast", "storage"]
# ==========================================================

# ---------- Method A: BM25 (keyword search) ----------


def tokenize(text):
    """Turn text into a list of lowercase words."""
    text = text.lower()
    for symbol in [".", ",", "?", "!", "-", "(", ")"]:
        text = text.replace(symbol, " ")
    return text.split()


# Build the BM25 index once
tokenized_notes = []
for note in SAMPLE_NOTES:
    tokenized_notes.append(tokenize(note["text"]))
bm25 = BM25Okapi(tokenized_notes)


def rank_with_bm25(question):
    """Return note ids ranked by BM25 keyword score."""
    scores = bm25.get_scores(tokenize(question))

    results = []
    for index in range(len(SAMPLE_NOTES)):
        results.append({"id": SAMPLE_NOTES[index]["id"], "score": scores[index]})

    results.sort(key=lambda item: item["score"], reverse=True)

    ranked_ids = []
    for item in results:
        ranked_ids.append(item["id"])
    return ranked_ids


# ---------- Method B: embeddings (meaning search) ----------


def cosine_similarity(vector_a, vector_b):
    """Higher number = more similar meaning."""
    dot_product = 0
    for number_a, number_b in zip(vector_a, vector_b, strict=True):
        dot_product = dot_product + (number_a * number_b)
    length_a = math.sqrt(sum(number * number for number in vector_a))
    length_b = math.sqrt(sum(number * number for number in vector_b))
    return dot_product / (length_a * length_b)


# Embed all notes once
embeddings_model = get_embeddings()
note_texts = []
for note in SAMPLE_NOTES:
    note_texts.append(note["text"])
print("Embedding the notes...")
note_vectors = embeddings_model.embed_documents(note_texts)
print("Done.")
print()


def rank_with_embeddings(question):
    """Return note ids ranked by cosine similarity."""
    question_vector = embeddings_model.embed_query(question)

    results = []
    for index in range(len(SAMPLE_NOTES)):
        score = cosine_similarity(question_vector, note_vectors[index])
        results.append({"id": SAMPLE_NOTES[index]["id"], "score": score})

    results.sort(key=lambda item: item["score"], reverse=True)

    ranked_ids = []
    for item in results:
        ranked_ids.append(item["id"])
    return ranked_ids


# ---------- Method C: hybrid (both combined with RRF) ----------


def rank_with_hybrid(bm25_ranking, embedding_ranking):
    """
    Combine two rankings using weighted Reciprocal Rank Fusion.
    We only use POSITIONS (1st, 2nd, ...), not the raw scores,
    because BM25 and cosine scores are on different scales.
    """
    hybrid_scores = {}

    # Points from the embedding ranking
    position = 1
    for note_id in embedding_ranking:
        points = EMBEDDING_WEIGHT * (1 / (RRF_CONSTANT + position))
        hybrid_scores[note_id] = hybrid_scores.get(note_id, 0) + points
        position = position + 1

    # Points from the BM25 ranking
    position = 1
    for note_id in bm25_ranking:
        points = BM25_WEIGHT * (1 / (RRF_CONSTANT + position))
        hybrid_scores[note_id] = hybrid_scores.get(note_id, 0) + points
        position = position + 1

    # Sort note ids by their total points, highest first
    ranked_ids = sorted(hybrid_scores, key=lambda note_id: hybrid_scores[note_id], reverse=True)
    return ranked_ids


# ==========================================================
# PART 2: the measurements
# ==========================================================


def precision_at_k(ranked_ids, relevant_ids, k):
    """
    Of the top k results, what fraction are relevant?
    Example: top 2 = [bitter, sour], relevant = [bitter] -> 1/2 = 0.5
    """
    top_k = ranked_ids[:k]
    relevant_found = 0
    for note_id in top_k:
        if note_id in relevant_ids:
            relevant_found = relevant_found + 1
    return relevant_found / k


def recall_at_k(ranked_ids, relevant_ids, k):
    """
    Of all relevant notes, what fraction did we find in the top k?
    Example: relevant = [bitter], top 2 contains bitter -> 1/1 = 1.0
    """
    top_k = ranked_ids[:k]
    relevant_found = 0
    for note_id in relevant_ids:
        if note_id in top_k:
            relevant_found = relevant_found + 1
    return relevant_found / len(relevant_ids)


# ==========================================================
# PART 3: run every question through every method
# ==========================================================

# Running totals, so we can calculate averages at the end
totals = {
    "BM25": {"precision": 0, "recall": 0, "first_correct": 0},
    "Embeddings": {"precision": 0, "recall": 0, "first_correct": 0},
    "Hybrid": {"precision": 0, "recall": 0, "first_correct": 0},
}

for test in TEST_SET:
    question = test["question"]
    relevant_ids = test["relevant_ids"]

    # Get the three rankings
    bm25_ranking = rank_with_bm25(question)
    embedding_ranking = rank_with_embeddings(question)
    hybrid_ranking = rank_with_hybrid(bm25_ranking, embedding_ranking)

    rankings = {
        "BM25": bm25_ranking,
        "Embeddings": embedding_ranking,
        "Hybrid": hybrid_ranking,
    }

    print("==================================================")
    print("QUESTION:", question)
    print("CORRECT: ", relevant_ids)

    for method_name, ranking in rankings.items():
        precision = precision_at_k(ranking, relevant_ids, TOP_K)
        recall = recall_at_k(ranking, relevant_ids, TOP_K)

        # Is the #1 result correct?
        if ranking[0] in relevant_ids:
            first_correct = 1
            mark = "OK  "
        else:
            first_correct = 0
            mark = "MISS"

        top_results = ", ".join(ranking[:TOP_K])
        print(
            f"   {mark} {method_name:<11} top {TOP_K}: {top_results:<18} "
            f"P@{TOP_K}={precision:.2f}  R@{TOP_K}={recall:.2f}"
        )

        totals[method_name]["precision"] += precision
        totals[method_name]["recall"] += recall
        totals[method_name]["first_correct"] += first_correct

    print()


# ==========================================================
# PART 4: the final scoreboard
# ==========================================================
number_of_questions = len(TEST_SET)

print("==================== SCOREBOARD ====================")
print(f"{'Method':<12} {'#1 correct':<12} {'P@' + str(TOP_K):<8} {'R@' + str(TOP_K):<8}")
for method_name, numbers in totals.items():
    first_correct_count = numbers["first_correct"]
    avg_precision = numbers["precision"] / number_of_questions
    avg_recall = numbers["recall"] / number_of_questions
    print(f"{method_name:<12} {first_correct_count}/{number_of_questions:<10} {avg_precision:<8.2f} {avg_recall:<8.2f}")
print()
print("Note: each question has only 1 correct note, so the best possible")
print(f"P@{TOP_K} is {1 / TOP_K:.2f} (1 correct out of {TOP_K} retrieved).")
