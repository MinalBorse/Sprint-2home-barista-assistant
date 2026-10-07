# ==========================================================
# src/theme.py
# ==========================================================
# Purpose: the "R Café" look - a cosy café at night - with NO images.
#
# Everything is drawn with CSS and a tiny bit of SVG (drawing code):
#   - red neon sign "R Café"  -> layered red text-shadows + a gentle flicker
#   - warm bokeh lights       -> soft radial gradients (circles of light)
#   - steaming coffee cup     -> a small SVG drawing with animated steam
#   - wooden tables           -> warm chat bubbles
#   - chalkboard menu         -> the sidebar
#   - tiled floor             -> a pattern behind the chat input
#
# Streamlit lets us add our own CSS/HTML with st.markdown(..., unsafe_allow_html=True).
# "data-testid" names are labels Streamlit puts on its parts of the page,
# so the CSS can find them.
# ==========================================================

import streamlit as st


CAFE_CSS = """
<style>
/* ---------- Fonts (from Google Fonts) ---------- */
@import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Playfair+Display:wght@600;700&family=Lora:wght@400;500&family=Caveat:wght@500;600&display=swap');

/* ---------- Colour palette, in one place ---------- */
:root {
    --night: #120C0B;
    --wine: #2A1514;
    --wood: #3A2618;
    --neon: #FF3B3B;
    --amber: #FFB45A;
    --cream: #F6E7DA;
    --chalkboard: #1E2622;
}

/* ---------- The whole page: night café with bokeh lights ---------- */
[data-testid="stAppViewContainer"] {
    background-color: var(--night);
    background-image:
        /* red glow from the neon sign */
        radial-gradient(ellipse at 50% -10%, rgba(255, 59, 59, 0.22), transparent 45%),
        /* bokeh: soft warm lights out of focus */
        radial-gradient(circle at 8% 12%, rgba(255, 180, 90, 0.30), transparent 40px),
        radial-gradient(circle at 22% 6%, rgba(255, 200, 120, 0.22), transparent 28px),
        radial-gradient(circle at 35% 18%, rgba(255, 170, 80, 0.18), transparent 50px),
        radial-gradient(circle at 63% 8%, rgba(255, 190, 110, 0.25), transparent 34px),
        radial-gradient(circle at 76% 16%, rgba(255, 160, 70, 0.20), transparent 46px),
        radial-gradient(circle at 91% 7%, rgba(255, 200, 130, 0.28), transparent 30px),
        radial-gradient(circle at 12% 55%, rgba(255, 170, 80, 0.10), transparent 70px),
        radial-gradient(circle at 88% 60%, rgba(255, 150, 70, 0.10), transparent 80px),
        /* the room: warm red-brown fading into the night */
        linear-gradient(180deg, #2B1513 0%, #1A0F0D 50%, var(--night) 100%);
    background-attachment: fixed;
}

[data-testid="stHeader"] {
    background: transparent;
}

/* ---------- Text ---------- */
html, body, [data-testid="stMarkdownContainer"] p, li {
    font-family: 'Lora', Georgia, serif;
}

/* ---------- The welcome banner ---------- */
.r-cafe-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    border-radius: 18px;
    background: rgba(18, 12, 11, 0.55);
    border: 1px solid rgba(255, 59, 59, 0.30);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}

/* The neon sign */
.r-cafe-sign {
    font-family: 'Pacifico', cursive;
    font-size: 3.2rem;
    line-height: 1.2;
    color: #FFE5E5;
    text-shadow:
        0 0 4px #FFFFFF,
        0 0 10px var(--neon),
        0 0 22px var(--neon),
        0 0 42px #E00000,
        0 0 80px #B80000;
    animation: neon-flicker 6s infinite;
}

/* A gentle, realistic neon flicker (most of the time it's steady) */
@keyframes neon-flicker {
    0%, 18%, 22%, 25%, 53%, 57%, 100% { opacity: 1; }
    20%, 24%, 55% { opacity: 0.55; }
}

/* People who prefer less motion get a steady sign */
@media (prefers-reduced-motion: reduce) {
    .r-cafe-sign, .r-cafe-steam path { animation: none !important; }
}

.r-cafe-open {
    display: inline-block;
    margin-top: 0.3rem;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.8rem;
    letter-spacing: 1px;
    color: #CFF5C9;
    border: 1px solid rgba(120, 220, 110, 0.5);
}

.r-cafe-welcome {
    margin-top: 0.6rem;
    color: var(--cream);
    font-size: 1.02rem;
    opacity: 0.92;
}

/* Steam rising from the cup */
.r-cafe-steam path {
    animation: steam-rise 3s ease-in-out infinite;
}
.r-cafe-steam path:nth-child(2) { animation-delay: 0.8s; }
.r-cafe-steam path:nth-child(3) { animation-delay: 1.6s; }

@keyframes steam-rise {
    0%   { opacity: 0;   transform: translateY(6px); }
    40%  { opacity: 0.8; }
    100% { opacity: 0;   transform: translateY(-10px); }
}

/* ---------- Chat bubbles: warm tables in the lamplight ---------- */
[data-testid="stChatMessage"] {
    background: rgba(42, 21, 20, 0.85);
    border: 1px solid rgba(255, 180, 90, 0.20);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.40);
}

/* The guest's messages: a lighter, warmer wood */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(70, 40, 28, 0.88);
}

/* ---------- Sidebar: the chalkboard menu ---------- */
[data-testid="stSidebar"] {
    background-color: var(--chalkboard);
    background-image:
        radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.04), transparent 40%),
        radial-gradient(circle at 70% 80%, rgba(255, 255, 255, 0.03), transparent 40%);
    border-right: 10px solid var(--wood);
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Caveat', cursive !important;
    font-size: 1.9rem !important;
    color: #F4F1E8 !important;
}

[data-testid="stSidebar"] li,
[data-testid="stSidebar"] p {
    font-family: 'Caveat', cursive;
    font-size: 1.25rem;
    color: #E8E4D8;
}

/* ---------- Buttons: warm wood with a soft neon edge ---------- */
.stButton > button {
    background: var(--wine);
    color: var(--cream);
    border: 1px solid rgba(255, 59, 59, 0.45);
    border-radius: 999px;
}
.stButton > button:hover {
    background: var(--neon);
    color: #FFFFFF;
    border-color: var(--neon);
}

/* ---------- Status boxes, Sources panel ---------- */
[data-testid="stExpander"] {
    border: 1px solid rgba(255, 180, 90, 0.30);
    border-radius: 10px;
    background: rgba(18, 12, 11, 0.55);
}

/* ---------- Tool result cards: like a little receipt ---------- */
[data-testid="stAlert"] {
    background: rgba(255, 180, 90, 0.12);
    border-left: 4px solid var(--amber);
    border-radius: 8px;
}

/* ---------- Bottom area: the tiled floor ---------- */
[data-testid="stBottom"] > div {
    background-color: #1C1210;
    background-image: repeating-conic-gradient(#251815 0% 25%, #180F0D 0% 50%);
    background-size: 26px 26px;
}

[data-testid="stChatInput"] {
    border: 1px solid rgba(255, 59, 59, 0.55);
    border-radius: 14px;
}
[data-testid="stChatInput"] textarea {
    font-family: 'Lora', Georgia, serif;
}
</style>
"""


# The welcome banner: neon sign, "open" badge, greeting, and a steaming cup.
# The cup is SVG: shapes described with code (an ellipse saucer, a cup,
# a handle, and three wavy steam lines that float upwards).
HERO_HTML = """
<div class="r-cafe-hero">
  <div>
    <div class="r-cafe-sign">R Café</div>
    <span class="r-cafe-open">● OPEN · BREWING NOW</span>
    <div class="r-cafe-welcome">
      Welcome in! Pull up a chair by the window. I'm your barista tonight:
      ask me how to brew, fix a cup that tastes wrong, check caffeine, or work out what your coffee costs.
    </div>
  </div>
  <svg width="110" height="110" viewBox="0 0 110 110" aria-hidden="true">
    <g class="r-cafe-steam" fill="none" stroke="#F6E7DA" stroke-width="3" stroke-linecap="round" opacity="0.8">
      <path d="M40 38 C34 30, 46 24, 40 14"/>
      <path d="M55 38 C49 30, 61 24, 55 14"/>
      <path d="M70 38 C64 30, 76 24, 70 14"/>
    </g>
    <ellipse cx="55" cy="92" rx="44" ry="8" fill="#3A2618"/>
    <path d="M25 46 H85 V70 C85 82, 75 90, 63 90 H47 C35 90, 25 82, 25 70 Z" fill="#F6E7DA"/>
    <path d="M85 54 C98 54, 98 76, 84 74" fill="none" stroke="#F6E7DA" stroke-width="6"/>
    <ellipse cx="55" cy="47" rx="30" ry="5" fill="#5A2E1C"/>
  </svg>
</div>
"""


def apply_cafe_theme():
    """Add the R Café styling to the page. Call it once, near the top of app.py."""
    st.markdown(CAFE_CSS, unsafe_allow_html=True)


def show_welcome_banner():
    """Show the neon sign and welcome message at the top of the page."""
    st.markdown(HERO_HTML, unsafe_allow_html=True)
