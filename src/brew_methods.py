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
    "turkish coffee",
    "siphon",
    "vietnamese phin",
    "percolator",
    "south indian filter",
]

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
    text = (title + " " + section).lower()

    for method, keywords in BREW_METHOD_KEYWORDS:
        for keyword in keywords:
            if keyword in text:
                return method

    return GENERAL
