# ==========================================================
# src/brew_methods.py
# ==========================================================
# The brew methods our knowledge base knows about, in ONE place.
#
# Used by:
#   - src/document_splitter.py -> to TAG every chunk with a brew_method
#   - src/rag.py               -> to CHECK the method the planner chose
#
# This structured metadata is what makes "structured retrieval" possible:
# we can search only inside one brew method instead of everywhere.
# ==========================================================
#
# LEARNING NOTES: WHEN IS EACH PART OF THIS FILE USED?
#
#   This file has two parts, used at two different times:
#
#   1. detect_brew_method() + BREW_METHOD_KEYWORDS
#      -> used ONLY during the BUILD (python build_knowledge_base.py),
#         once for every chunk, to give each chunk a brew_method LABEL.
#         The labels are saved in chroma_db/ with the chunks.
#
#   2. BREW_METHODS, GENERAL and ANY
#      -> used EVERY TIME THE APP RUNS:
#           - src/rag.py: checks the planner's brew_method, and builds the filter
#           - app.py:     fills the "My brewer" dropdown (with a safety check)
#
#   When the app starts, Python only IMPORTS this file (it creates the lists
#   in memory). No detection runs while the app is answering questions:
#   the chunks were already labelled during the build.
#
#   Keywords label the CHUNKS (build time).
#   The planner, an LLM, labels the QUESTION (answer time).
#   The filter matches the two labels; the agent answers from the chunk's text.
# ==========================================================


# The allowed values. "general" = not about one specific method.
#
# LEARNING NOTE: this is the single source of truth for brew method names.
# Every other file uses these exact spellings (lowercase, with spaces), so a
# dropdown value like "Pour over" can never silently mismatch a chunk label
# like "pour-over". If you add a method here, also add its keywords below,
# write its section in data/brewing_guide.md, and REBUILD the knowledge base.
BREW_METHODS = [
    "pour-over",
    "french press",
    "aeropress",
    "moka pot",
    "espresso",
    "cold brew",
    "turkish coffee",
    "siphon",
    "vietnamese phin",
    "percolator",
    "south indian filter",
]

# LEARNING NOTE: GENERAL vs ANY (easy to mix up)
#
#   GENERAL is a label for a CHUNK:    "this chunk applies to every brewer"
#                                      (e.g. the troubleshooting sections)
#   ANY     is a value for a QUESTION: "the user named no brewer, so don't
#                                      filter by brewer"
#
#   No chunk is ever labelled "any", and no question is ever "general".
#   With a brewer named, the filter keeps that brewer's chunks + "general" ones.
#   With ANY, there is no brew filter: all chunks are searched.
#   ANY is also the default for "My brewer: Not set", and the value that
#   src/rag.py uses when the planner returns an unknown method (e.g. "kettle").
GENERAL = "general"  # chunks that apply to every method
ANY = "any"  # the planner's answer when no method is mentioned


# 07/10/2026 Words that reveal each method.
# ORDER MATTERS: "moka pot" comes before "espresso", because our
# moka pot section is called "Moka pot (stovetop espresso maker)".
# 09/10/2026 ORDER MATTERS: the first matching method wins, so more specific methods
# come before methods whose words they contain:
#   "Moka pot (stovetop espresso maker)"  -> moka pot must come before espresso
#   "South Indian filter coffee"          -> before pour-over ("filter coffee")
#   "Vietnamese phin (drip filter)"       -> before pour-over ("drip")
#   "Stovetop percolator"                 -> before moka pot ("stovetop")
#
# LEARNING NOTE: the structure of this list
#   - It is a LIST, so it has a fixed ORDER (the order the methods are checked in).
#   - Each item is a PAIR (a tuple): ("method name", [keywords that reveal it]).
#   - Brand and device names map to their METHOD: a Chemex is a pour-over,
#     a Bialetti is a moka pot, a lever machine makes espresso.
#   - Rule for adding a method: check its heading for "trap words" that belong
#     to another method, and place it ABOVE that method.
BREW_METHOD_KEYWORDS = [
    ("south indian filter", ["south indian", "filter kaapi", "kaapi"]),
    ("vietnamese phin", ["vietnamese", "phin"]),
    ("turkish coffee", ["turkish", "cezve", "ibrik"]),
    ("siphon", ["siphon", "syphon", "vacuum pot", "vacuum brewer"]),
    ("percolator", ["percolator"]),
    ("moka pot", ["moka", "stovetop", "brikka", "bialetti"]),
    ("cold brew", ["cold brew"]),
    ("aeropress", ["aeropress"]),
    ("french press", ["french press", "cafetiere", "cafetière", "press pot", "plunger"]),
    ("pour-over", ["pour-over", "pour over", "v60", "drip", "filter coffee", "chemex", "kalita", "melitta", "origami"]),
    ("espresso", ["espresso", "lever"]),
]


def detect_brew_method(title, section):
    """
    Decide which brew method a chunk is about, using only its
    TITLE and SECTION (not the full text, which often mentions
    several methods in passing).

    Examples:
      ("Moka pot", "")                               -> "moka pot"
      ("brewing guide", "French press (cafetiere...)") -> "french press"
      ("troubleshooting guide", "Sour, sharp...")    -> "general"
    """
    # LEARNING NOTE: this function runs at BUILD time, once per chunk.
    # It is called by src/document_splitter.py. It returns a LABEL (a string),
    # not a chunk. It never looks at the user's question.

    # Join the title and the heading, in lowercase, so "V60" matches "v60".
    text = (title + " " + section).lower()

    # Check the methods IN ORDER, and each method's keywords one by one.
    # The FIRST keyword found ends the function with that method:
    # "first match wins", which is why the order of the list matters.
    for method, keywords in BREW_METHOD_KEYWORDS:
        for keyword in keywords:
            # LEARNING NOTE (known weakness, AI review #24): "keyword in text"
            # also matches INSIDE other words ("lever" in "Clever Dripper",
            # "phin" in "dolphin"). The current headings don't trigger this.
            # Matching whole words only would be safer.
            if keyword in text:
                return method

    # No keyword matched: the chunk is not about one specific method.
    return GENERAL
