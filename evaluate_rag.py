# ==========================================================
# evaluate_rag.py
# ==========================================================
# Evaluates our RAG pipeline with RAGAs.
#
# For every question in the test set, we:
#   1. run our RAG (rewrite -> retrieve -> answer)
#   2. ask a JUDGE LLM to score the result on 4 metrics:
#        faithfulness       -> is the answer supported by the chunks?   (generation)
#        answer_relevancy   -> does the answer address the question?    (generation)
#        context_precision  -> were the retrieved chunks relevant?      (retrieval)
#        context_recall     -> did we retrieve everything needed?       (retrieval)
#
# We run it TWICE: with query translation ON and OFF,
# so we can compare them with real numbers (an A/B test).
#
# Results are printed AND saved to eval_results/ as CSV files.
#
# OPTIONAL TASK (hard): "Implement an evaluation of your RAG system, using RAGAs"
#
# Cost and time: about 200 small LLM calls in total.
# Expect a few minutes and a few cents.
# ==========================================================

import asyncio
import csv
import math
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.embeddings import OpenAIEmbeddings as RagasEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from src.eval_test_set import TEST_SET
from src.llm import get_llm
from src.rag import answer_with_rag
from src.vector_store import KNOWLEDGE_BASE_COLLECTION, get_vector_store

load_dotenv()


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
RESULTS_FOLDER = "eval_results"
METRIC_NAMES = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

# The two versions of our RAG we compare
MODES = [
    {"name": "with_rewrite", "use_rewrite": True},
    {"name": "without_rewrite", "use_rewrite": False},
]


# ==========================================================
# STEP 1: set up the JUDGE (the LLM that gives the scores)
# ==========================================================
# RAGAs talks to the OpenAI-style API directly, so we give it
# an OpenAI client pointed at OpenRouter (same key as our app).
#
# It must be the ASYNC client (AsyncOpenAI): RAGAs runs its judge calls
# "asynchronously", meaning several calls can wait for answers at the
# same time instead of one after another. That is also faster.
openrouter_client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

judge_llm = llm_factory(os.getenv("MODEL_NAME", "openai/gpt-4o-mini"), client=openrouter_client)
judge_embeddings = RagasEmbeddings(
    client=openrouter_client,
    model=os.getenv("EMBEDDING_MODEL_NAME", "openai/text-embedding-3-small"),
)

faithfulness_metric = Faithfulness(llm=judge_llm)
relevancy_metric = AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings)
precision_metric = ContextPrecision(llm=judge_llm)
recall_metric = ContextRecall(llm=judge_llm)


# ==========================================================
# STEP 2: helper functions
# ==========================================================
async def safe_score(metric, **inputs):
    """
    Run one metric and return its number.
    If the judge fails (or returns 'not a number'), return None,
    so one problem doesn't stop the whole evaluation.

    "async def" and "await" are Python's way of saying:
    "this function waits for something (the judge LLM), and while it
    waits, other work may run". You only need them where RAGAs needs them.
    """
    try:
        result = await metric.ascore(**inputs)
        value = result.value
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(value)
    except Exception as error:
        print(f"      ({metric.name} could not be scored: {error})")
        return None


async def score_one_case(question, reference, rag_result):
    """Score one test case on all 4 metrics, at the same time."""
    contexts = []
    for source in rag_result["sources"]:
        contexts.append(source["text"])

    answer = rag_result["answer"]

    # asyncio.gather runs the 4 judge calls at the same time
    # and waits until all of them are finished.
    results = await asyncio.gather(
        safe_score(
            faithfulness_metric,
            user_input=question, response=answer, retrieved_contexts=contexts,
        ),
        safe_score(
            relevancy_metric,
            user_input=question, response=answer,
        ),
        safe_score(
            precision_metric,
            user_input=question, reference=reference, retrieved_contexts=contexts,
        ),
        safe_score(
            recall_metric,
            user_input=question, reference=reference, retrieved_contexts=contexts,
        ),
    )

    return {
        "faithfulness": results[0],
        "answer_relevancy": results[1],
        "context_precision": results[2],
        "context_recall": results[3],
    }


def format_score(value):
    """Show a score with 2 decimals, or '-' if it's missing."""
    if value is None:
        return "  - "
    return f"{value:.2f}"


def average(values):
    """Average of the numbers in a list, ignoring missing (None) values."""
    numbers = []
    for value in values:
        if value is not None:
            numbers.append(value)
    if len(numbers) == 0:
        return None
    return sum(numbers) / len(numbers)


# ==========================================================
# STEP 3 and 4: run the evaluation and compare the results
# ==========================================================
# Everything below lives inside one async function, run once
# at the very end with asyncio.run(...).
async def main():
    vector_store = get_vector_store(KNOWLEDGE_BASE_COLLECTION)
    rag_llm = get_llm()
    os.makedirs(RESULTS_FOLDER, exist_ok=True)

    summary = {}   # mode name -> average of each metric

    for mode in MODES:
        print("=" * 70)
        print(f"MODE: {mode['name']}  ({len(TEST_SET)} questions)")
        print("=" * 70)
        print(f"{'#':<3}{'faith':>7}{'relev':>7}{'prec':>7}{'recall':>8}   question")

        rows = []
        case_number = 1
        for test_case in TEST_SET:
            question = test_case["question"]
            reference = test_case["reference"]

            # Run OUR RAG pipeline
            rag_result = answer_with_rag(
                question, vector_store, rag_llm, use_rewrite=mode["use_rewrite"]
            )

            # Let the judge score it
            scores = await score_one_case(question, reference, rag_result)

            print(
                f"{case_number:<3}"
                f"{format_score(scores['faithfulness']):>7}"
                f"{format_score(scores['answer_relevancy']):>7}"
                f"{format_score(scores['context_precision']):>7}"
                f"{format_score(scores['context_recall']):>8}   "
                f"{question[:40]}"
            )

            rows.append({
                "question": question,
                "search_query": rag_result["search_query"],
                "answer": rag_result["answer"],
                "faithfulness": scores["faithfulness"],
                "answer_relevancy": scores["answer_relevancy"],
                "context_precision": scores["context_precision"],
                "context_recall": scores["context_recall"],
            })
            case_number = case_number + 1

        # Save every row to a CSV file (open it in Excel or VS Code)
        csv_path = os.path.join(RESULTS_FOLDER, f"ragas_{mode['name']}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved details to {csv_path}\n")

        # Average of each metric for this mode
        summary[mode["name"]] = {}
        for metric_name in METRIC_NAMES:
            values = []
            for row in rows:
                values.append(row[metric_name])
            summary[mode["name"]][metric_name] = average(values)


    # ==========================================================
    # STEP 4: the final comparison
    # ==========================================================
    print("=" * 70)
    print("SUMMARY (averages)")
    print("=" * 70)
    print(f"{'mode':<18}{'faith':>8}{'relev':>8}{'prec':>8}{'recall':>8}")
    for mode_name, averages in summary.items():
        print(
            f"{mode_name:<18}"
            f"{format_score(averages['faithfulness']):>8}"
            f"{format_score(averages['answer_relevancy']):>8}"
            f"{format_score(averages['context_precision']):>8}"
            f"{format_score(averages['context_recall']):>8}"
        )
    print()
    print("Course guidelines: faithfulness >= 0.8 is a good target; below 0.6 means")
    print("a hallucination problem. Context scores below 0.7 suggest retrieval issues.")
    print("Always open the CSV and look at the low-scoring questions before changing anything.")


asyncio.run(main())
