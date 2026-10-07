# ==========================================================
# src/chunk_tags.py
# ==========================================================
# Extra STRUCTURED METADATA for every chunk, used by structured retrieval:
#
#   taste_problem -> "bitter", "sour", "weak", "strong", "flat" or "none"
#                    (from the section heading, free and exact)
#   topic         -> "troubleshooting", "brewing", "equipment",
#                    "beans and roasting", "storage", "history" or "other"
#                    (chosen by the LLM for each chunk, while building)
#
# The brew method tag lives in src/brew_methods.py.
# ==========================================================

from pydantic import BaseModel, Field


NONE = "none"

# ----------------------------------------------------------
# taste_problem: detected from the section heading
# ----------------------------------------------------------
TASTE_PROBLEMS = ["bitter", "sour", "weak", "strong", "flat"]

# The words in our troubleshooting guide's headings, per problem
TASTE_KEYWORDS = [
    ("bitter", ["bitter", "harsh", "burnt", "astringent"]),
    ("sour", ["sour", "sharp", "acidic", "tangy"]),
    ("weak", ["weak", "watery", "thin"]),
    ("strong", ["strong", "heavy", "overpowering"]),
    ("flat", ["flat", "dull", "stale"]),
]


def detect_taste_problem(section):
    """
    Which taste problem a section is about, from its heading.
    "Sour, sharp, acidic or tangy coffee" -> "sour"
    "Moka pot (stovetop espresso maker)"  -> "none"
    """
    text = section.lower()
    for problem, keywords in TASTE_KEYWORDS:
        for keyword in keywords:
            if keyword in text:
                return problem
    return NONE


# ----------------------------------------------------------
# topic: chosen by the LLM for each chunk (while building)
# ----------------------------------------------------------
TOPICS = [
    "troubleshooting",
    "brewing",
    "equipment",
    "beans and roasting",
    "storage",
    "history",
    "other",
]
HISTORY = "history"
OTHER = "other"


class TopicTag(BaseModel):
    """The shape of the LLM's answer: one topic name."""
    topic: str = Field(description="Exactly one of: " + ", ".join(TOPICS))


TOPIC_PROMPT = (
    "Which topic is this coffee text mainly about? Answer with exactly one of: "
    + ", ".join(TOPICS)
    + ".\n'history' means inventors, dates, companies or how something developed over time. "
    "'brewing' means how to make coffee (recipes, ratios, steps). "
    "'troubleshooting' means fixing taste problems.\n\nText:\n"
)


def tag_topics(chunks, llm):
    """
    Ask the LLM for the topic of every chunk, and store it in the
    chunk's metadata. Many chunks are tagged at the same time (batch),
    which is much faster than one by one.
    If the LLM fails for a chunk, it gets the topic "other" (error handling).
    """
    tagger = llm.with_structured_output(TopicTag)

    prompts = []
    for chunk in chunks:
        prompts.append(TOPIC_PROMPT + chunk.page_content[:1500])

    # return_exceptions=True: one failed chunk doesn't stop the others
    results = tagger.batch(prompts, config={"max_concurrency": 8}, return_exceptions=True)

    for chunk, result in zip(chunks, results):
        topic = OTHER
        if isinstance(result, TopicTag):
            candidate = result.topic.strip().lower()
            if candidate in TOPICS:
                topic = candidate
        chunk.metadata["topic"] = topic

    return chunks
