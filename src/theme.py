# ==========================================================
# src/theme.py
# ==========================================================
# Purpose: give the app a cosy coffee-shop look, with NO images.
#
# Everything is drawn with CSS (the styling language of web pages):
#   - warm lamp glows      -> radial gradients (soft circles of light)
#   - brick wall           -> faint repeating stripes
#   - wooden counter       -> wood-brown chat bubbles with brass edges
#   - chalkboard menu      -> a dark green sidebar with a handwriting font
#   - patterned floor      -> a tiled pattern behind the chat input
#
# Streamlit lets us add our own CSS with st.markdown(..., unsafe_allow_html=True).
# "data-testid" names are labels Streamlit puts on its parts of the page,
# so the CSS can find them.
# ==========================================================

import streamlit as st


CAFE_CSS = """
<style>
/* ---------- Fonts (from Google Fonts) ---------- */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Lora:wght@400;500&family=Caveat:wght@500;600&display=swap');

/* ---------- Colour palette, in one place ---------- */
:root {
    --espresso: #1B130E;
    --wood: #3A2618;
    --wood-light: #5A3A22;
    --brass: #D9A05B;
    --cream: #F3E6D3;
    --leaf: #4F6B3A;
    --chalkboard: #1F2A24;
}

/* ---------- The whole page: brick wall + lamp glows ---------- */
[data-testid="stAppViewContainer"] {
    background-color: var(--espresso);
    background-image:
        /* two warm lamps glowing at the top */
        radial-gradient(circle at 18% -5%, rgba(255, 176, 86, 0.22), transparent 38%),
        radial-gradient(circle at 82% -5%, rgba(255, 166, 76, 0.18), transparent 34%),
        /* brick wall: horizontal and vertical mortar lines, very faint */
        repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.28) 0 2px, transparent 2px 30px),
        repeating-linear-gradient(90deg, rgba(0, 0, 0, 0.16) 0 2px, transparent 2px 64px),
        /* brick colour fading into dark espresso */
        linear-gradient(180deg, #3B2116 0%, #24170F 45%, var(--espresso) 100%);
}

/* The top bar: transparent, so the wall shows through */
[data-testid="stHeader"] {
    background: transparent;
}

/* ---------- Text ---------- */
html, body, [data-testid="stMarkdownContainer"] p, li {
    font-family: 'Lora', Georgia, serif;
}

/* The title: like a café sign, glowing brass */
h1 {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: var(--brass) !important;
    letter-spacing: 0.5px;
    text-shadow: 0 0 18px rgba(217, 160, 91, 0.35);
}

/* ---------- Chat bubbles: the wooden counter ---------- */
[data-testid="stChatMessage"] {
    background: rgba(58, 38, 24, 0.82);
    border: 1px solid rgba(217, 160, 91, 0.25);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
}

/* The user's messages: a lighter, warmer wood */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(90, 58, 34, 0.85);
}

/* ---------- Sidebar: the chalkboard menu ---------- */
[data-testid="stSidebar"] {
    background-color: var(--chalkboard);
    background-image:
        radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.04), transparent 40%),
        radial-gradient(circle at 70% 80%, rgba(255, 255, 255, 0.03), transparent 40%);
    border-right: 10px solid var(--wood);   /* the wooden frame */
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Caveat', cursive !important;
    font-size: 1.9rem !important;
    color: #F4F1E8 !important;               /* chalk white */
}

[data-testid="stSidebar"] li,
[data-testid="stSidebar"] p {
    font-family: 'Caveat', cursive;
    font-size: 1.25rem;
    color: #E8E4D8;
}

/* ---------- Buttons: wood with a brass edge ---------- */
.stButton > button {
    background: var(--wood);
    color: var(--cream);
    border: 1px solid var(--brass);
    border-radius: 10px;
}
.stButton > button:hover {
    background: var(--brass);
    color: var(--espresso);
    border-color: var(--brass);
}

/* ---------- Status boxes, Sources panel: framed in brass ---------- */
[data-testid="stExpander"] {
    border: 1px solid rgba(217, 160, 91, 0.35);
    border-radius: 10px;
    background: rgba(27, 19, 14, 0.55);
}

/* ---------- Tool result cards: like a little receipt ---------- */
[data-testid="stAlert"] {
    background: rgba(79, 107, 58, 0.22);
    border-left: 4px solid var(--brass);
    border-radius: 8px;
}

/* ---------- Bottom area: the patterned tile floor ---------- */
[data-testid="stBottom"] > div {
    background-color: #241A14;
    background-image:
        repeating-conic-gradient(#2E221A 0% 25%, #211812 0% 50%);
    background-size: 26px 26px;
}

/* The chat input box itself */
[data-testid="stChatInput"] textarea {
    font-family: 'Lora', Georgia, serif;
}
[data-testid="stChatInput"] {
    border: 1px solid var(--brass);
    border-radius: 14px;
}
</style>
"""


def apply_cafe_theme():
    """Add the coffee-shop styling to the page. Call it once, near the top of app.py."""
    st.markdown(CAFE_CSS, unsafe_allow_html=True)
