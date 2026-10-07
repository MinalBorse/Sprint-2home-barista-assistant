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


# The allowed values. "general" = not about one specific method.
BREW_METHODS = [
    "pour-over",
    "french press",
    "aeropress",
    "moka pot",
    "espresso",
    "cold brew",
]

GENERAL = "general"     # chunks that apply to every method
ANY = "any"             # the planner's answer when no method is mentioned


# Words that reveal each method.
# ORDER MATTERS: "moka pot" comes before "espresso", because our
# moka pot section is called "Moka pot (stovetop espresso maker)".
BREW_METHOD_KEYWORDS = [
    ("moka pot", ["moka", "stovetop"]),
    ("cold brew", ["cold brew"]),
    ("aeropress", ["aeropress"]),
    ("french press", ["french press", "cafetiere", "cafetière", "press pot", "plunger"]),
    ("pour-over", ["pour-over", "pour over", "v60", "drip", "filter coffee"]),
    ("espresso", ["espresso"]),
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
    text = (title + " " + section).lower()

    for method, keywords in BREW_METHOD_KEYWORDS:
        for keyword in keywords:
            if keyword in text:
                return method

    return GENERAL
