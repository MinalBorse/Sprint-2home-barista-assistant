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
#
# LEARNING NOTES (Module 3, Lessons 3-4)
#
# When does each part run?
#   - detect_taste_problem(): BUILD time, once per chunk.
#     Called by src/document_splitter.py.
#   - tag_topics(): BUILD time, once for all chunks (160 LLM calls per build).
#     Called by build_knowledge_base.py (step 3, after splitting).
#   - TASTE_PROBLEMS, TOPICS, HISTORY, NONE: used EVERY TIME THE APP RUNS,
#     by src/rag.py, to check the planner's answer and to build the filters.
#   While chatting, the labels are only READ from chroma_db/. Nothing in this
#   file labels chunks during a chat.
#
# Two ways of labelling, for two kinds of text:
#   - taste_problem: KEYWORDS. Our own headings are predictable (we wrote
#     them), so exact word matching is free and reliable.
#   - topic: an LLM. Wikipedia chunks have no useful heading, and "history"
#     can be written in many ways, so only something that UNDERSTANDS the
#     text can tell.
#
# Chunk labels vs question values:
#   These keywords label the CHUNKS. The user's QUESTION is read by the
#   planner (an LLM in src/rag.py), so slang like "so-so", "meh" or "blah"
#   does NOT need to be in TASTE_KEYWORDS: the planner maps it to "flat".
# ==========================================================

from pydantic import BaseModel, Field

NONE = "none"
# LEARNING NOTE: "none" = "not about a taste problem" (most chunks). The planner
# also uses it for questions that name no taste problem. Then there is no boost.

# ----------------------------------------------------------
# taste_problem: detected from the section heading
# ----------------------------------------------------------
TASTE_PROBLEMS = ["bitter", "sour", "weak", "strong", "flat"]
# LEARNING NOTE: the single source of truth for taste problems. src/rag.py
# checks the planner's taste_problem against this list: an invented value like
# "salty" becomes "none". Our guide has EXACTLY ONE section per problem, which
# the TASTE BOOST relies on: it pins that one section first in the results.

# The words in our troubleshooting guide's headings, per problem
# LEARNING NOTE: the same (label, [keywords]) structure as BREW_METHOD_KEYWORDS.
# The keywords are exactly the synonyms in our headings, e.g.
# "## Bitter, harsh, burnt or astringent coffee". Headings and keywords were
# written together, so matching is reliable. User slang is handled elsewhere:
# in the planner prompt, with a FIRM rule ("puckery becomes sour"), which worked
# better than "for example" hints (the puckery lesson).
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
    # LEARNING NOTE: almost identical to detect_brew_method(), but it looks at the
    # HEADING only (not the title). The text of a section may mention other
    # problems in passing ("...unlike sour coffee..."); the heading says what the
    # section is really about. It returns a LABEL, and the first match wins.
    # Known weakness (AI review #24): "keyword in text" matches INSIDE words:
    # "thin" in "anything", "flat" in "flat white", "strong" in "stronger".
    # Current headings don't trigger it; whole-word matching would be safer.
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
# LEARNING NOTE: TOPICS is the single source of truth for the 7 topics.
#   - HISTORY powers the "Hide history and trivia" filter (topic != "history").
#     The planner's own "topic" field (for the QUESTION) can lift that filter
#     when the question IS about history ("the question wins").
#   - OTHER is the SAFE FALLBACK when tagging fails or gives an unknown answer.


# LEARNING NOTE: a Pydantic class = a form with labelled boxes. This one has ONE
# box: topic. with_structured_output() makes the LLM fill it in. The Field
# description IS READ BY THE MODEL ("Exactly one of: ..."), and building it with
# ", ".join(TOPICS) means it can never fall out of date with the list.
# Our three Pydantic forms: TopicTag (here, build time), SearchPlan (src/rag.py,
# every search) and GuardDecision (src/security.py, every message).
class TopicTag(BaseModel):
    """The shape of the LLM's answer: one topic name."""

    topic: str = Field(description="Exactly one of: " + ", ".join(TOPICS))


# LEARNING NOTE: the prompt DEFINES the three most confusable topics (history,
# brewing, troubleshooting) so the model doesn't guess. Inside the brackets,
# Python joins strings written next to each other into one string. The chunk's
# text is added after "Text:" in tag_topics().
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
    # LEARNING NOTE (Module 3, Lesson 4, the librarian with 7 stickers):
    # an LLM reads each chunk and puts ONE topic sticker on it. Steps:
    #   1. tagger: the LLM, told to always answer by filling in the TopicTag form
    #   2. prompts: one question per chunk, in the SAME ORDER as the chunks
    #   3. batch: ask them all, 8 at a time
    #   4. zip: go through chunks and answers side by side, and store the sticker
    # Runs only at BUILD time, so it adds no time or cost to chats.
    tagger = llm.with_structured_output(TopicTag)

    # LEARNING NOTE: chunk.page_content[:1500] = at most 1,500 characters of the
    # chunk. Our chunks are at most 1,000 characters, so this is a safety limit.
    prompts = []
    for chunk in chunks:
        prompts.append(TOPIC_PROMPT + chunk.page_content[:1500])

    # return_exceptions=True: one failed chunk doesn't stop the others
    # LEARNING NOTE: .batch() sends all the prompts and collects all the answers;
    # max_concurrency 8 = 8 calls in parallel, so 160 chunks take seconds, not
    # minutes. With return_exceptions=True, a failed call becomes an ERROR OBJECT
    # in its place in the results, instead of stopping the whole batch.
    # Result: a list of answers in the same order: each a filled TopicTag form, or an error.
    results = tagger.batch(prompts, config={"max_concurrency": 8}, return_exceptions=True)

    # LEARNING NOTE: zip() walks through BOTH lists side by side (chunk 1 with
    # answer 1...). strict=True stops with an error if the two lists ever have
    # different lengths, instead of silently dropping items (a ruff B905 fix).
    # Three layers of safety, like the planner:
    #   1. the FORM: the answer must be one text box
    #   2. the CHECK: tidy it (.strip().lower()) and accept it only if in TOPICS
    #   3. the FALLBACK: every chunk STARTS as "other", replaced only by a valid answer
    #   isinstance(result, TopicTag) asks: "did this call succeed?"
    # Honest limits: if the key is wrong or the API is down, EVERY chunk silently
    # becomes "other" (AI review #23), and "Hide history" quietly stops working.
    # And a chunk gets only ONE topic, even if it mixes, say, a definition and dates.
    for chunk, result in zip(chunks, results, strict=True):
        topic = OTHER
        if isinstance(result, TopicTag):
            candidate = result.topic.strip().lower()
            if candidate in TOPICS:
                topic = candidate
        chunk.metadata["topic"] = topic

    return chunks
