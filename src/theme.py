# ==========================================================
# src/theme.py
# ==========================================================
# Purpose: the elegant "Home Barista Assistant" look - inspired by premium coffee
# photography: dark slate surfaces, roasted beans, golden crema.
#
# Everything is drawn with code, no photos:
#   - the page          -> espresso black with a very faint pattern of beans
#   - the welcome card  -> the "Home Barista Assistant" wordmark in a refined serif,
#                          with a hand-drawn cup of espresso seen from above
#                          (SVG: shapes described in code)
#   - gold details      -> thin champagne-gold lines and borders
#   - the sidebar       -> deep roasted brown with a gold edge
#
# The bean emblem used as logo and avatar, and the coffee-bar scene in the
# background, are image files in assets/, also drawn in code.
#
# Streamlit lets us add our own CSS/HTML with st.markdown(..., unsafe_allow_html=True).
# "data-testid" names are labels Streamlit puts on its parts of the page,
# so the CSS can find them.
# ==========================================================

import base64
import os

import streamlit as st

# The bean emblem (made in code, saved as image files)
LOGO_IMAGE = "assets/logo_bean.png"
AVATAR_IMAGE = "assets/barista_avatar.png"

# The background scene: a coffee bar seen from above (drawn in code)
BACKGROUND_IMAGE = "assets/cafe_background.jpg"


# A tiny, very faint pattern of coffee beans for the page background
BEAN_PATTERN = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22220%22%20height%3D%22220%22%3E%3Cg%20transform%3D%22translate%2840%2050%29%20rotate%28-30%29%22%3E%3Cellipse%20rx%3D%229%22%20ry%3D%226%22%20fill%3D%22%23C8A36A%22%20fill-opacity%3D%220.05%22/%3E%3Cpath%20d%3D%22M%20-7%200.5%20C%20-3%20-3%2C%203%203.5%2C%207%20-0.5%22%20fill%3D%22none%22%20stroke%3D%22%23C8A36A%22%20stroke-opacity%3D%220.07%22%20stroke-width%3D%221.3%22%20stroke-linecap%3D%22round%22/%3E%3C/g%3E%3Cg%20transform%3D%22translate%28160%2030%29%20rotate%2840%29%22%3E%3Cellipse%20rx%3D%229%22%20ry%3D%226%22%20fill%3D%22%23C8A36A%22%20fill-opacity%3D%220.05%22/%3E%3Cpath%20d%3D%22M%20-7%200.5%20C%20-3%20-3%2C%203%203.5%2C%207%20-0.5%22%20fill%3D%22none%22%20stroke%3D%22%23C8A36A%22%20stroke-opacity%3D%220.07%22%20stroke-width%3D%221.3%22%20stroke-linecap%3D%22round%22/%3E%3C/g%3E%3Cg%20transform%3D%22translate%28110%20120%29%20rotate%2810%29%22%3E%3Cellipse%20rx%3D%229%22%20ry%3D%226%22%20fill%3D%22%23C8A36A%22%20fill-opacity%3D%220.05%22/%3E%3Cpath%20d%3D%22M%20-7%200.5%20C%20-3%20-3%2C%203%203.5%2C%207%20-0.5%22%20fill%3D%22none%22%20stroke%3D%22%23C8A36A%22%20stroke-opacity%3D%220.07%22%20stroke-width%3D%221.3%22%20stroke-linecap%3D%22round%22/%3E%3C/g%3E%3Cg%20transform%3D%22translate%2830%20175%29%20rotate%2865%29%22%3E%3Cellipse%20rx%3D%229%22%20ry%3D%226%22%20fill%3D%22%23C8A36A%22%20fill-opacity%3D%220.05%22/%3E%3Cpath%20d%3D%22M%20-7%200.5%20C%20-3%20-3%2C%203%203.5%2C%207%20-0.5%22%20fill%3D%22none%22%20stroke%3D%22%23C8A36A%22%20stroke-opacity%3D%220.07%22%20stroke-width%3D%221.3%22%20stroke-linecap%3D%22round%22/%3E%3C/g%3E%3Cg%20transform%3D%22translate%28185%20160%29%20rotate%28-50%29%22%3E%3Cellipse%20rx%3D%229%22%20ry%3D%226%22%20fill%3D%22%23C8A36A%22%20fill-opacity%3D%220.05%22/%3E%3Cpath%20d%3D%22M%20-7%200.5%20C%20-3%20-3%2C%203%203.5%2C%207%20-0.5%22%20fill%3D%22none%22%20stroke%3D%22%23C8A36A%22%20stroke-opacity%3D%220.07%22%20stroke-width%3D%221.3%22%20stroke-linecap%3D%22round%22/%3E%3C/g%3E%3C/svg%3E"


CAFE_CSS = """
<style>
/* ---------- Fonts (from Google Fonts) ---------- */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500&display=swap');

/* ---------- Colour palette, in one place ---------- */
:root {
    --espresso: #0E0B09;     /* page background */
    --slate: #17120F;        /* cards */
    --roast: #2A1D15;        /* guest messages */
    --gold: #C8A36A;         /* champagne gold, like crema */
    --gold-light: #E6C98F;
    --ivory: #F2EBDD;        /* text */
    --mocha: #A88B70;        /* quiet text */
}

/* ---------- The page: espresso black, warm light, faint beans ---------- */
[data-testid="stAppViewContainer"] {
    background-color: var(--espresso);
    background-image:
        radial-gradient(ellipse at 50% -10%, rgba(200, 163, 106, 0.10), transparent 55%),
        url("BEAN_PATTERN_URI");
    background-attachment: fixed;
}

[data-testid="stHeader"] {
    background: transparent;
}

/* ---------- Text ---------- */
html, body, [data-testid="stMarkdownContainer"] p, li, label {
    font-family: 'Inter', system-ui, sans-serif;
}

[data-testid="stCaptionContainer"] {
    color: var(--mocha) !important;
}

/* ---------- The welcome card ---------- */
.rc-hero {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    padding: 1.8rem 2rem;
    margin-bottom: 1.2rem;
    border-radius: 6px;
    background: linear-gradient(135deg, rgba(23, 18, 15, 0.92), rgba(14, 11, 9, 0.92));
    border: 1px solid rgba(200, 163, 106, 0.28);
}

.rc-hero-text {
    flex: 1 1 260px;
}

.rc-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.32em;
    color: var(--gold);
    text-transform: uppercase;
}

.rc-wordmark {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-weight: 600;
    font-size: 3.4rem;
    line-height: 1.05;
    color: var(--ivory);
    margin-top: 0.3rem;
}

.rc-rule {
    width: 64px;
    height: 1px;
    background: var(--gold);
    margin: 0.9rem 0;
}

.rc-welcome {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.2rem;
    line-height: 1.5;
    color: var(--ivory);
    opacity: 0.88;
}

.rc-hero-art {
    flex: 0 0 240px;
    height: 180px;
}

/* ---------- Chat messages ---------- */
[data-testid="stChatMessage"] {
    background: rgba(23, 18, 15, 0.88);
    border: 1px solid rgba(200, 163, 106, 0.16);
    border-radius: 6px;
    padding: 1rem 1.1rem;
}

/* The guest's messages: a warmer roasted brown */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(42, 29, 21, 0.9);
}

/* ---------- Sidebar: deep roasted brown with a thin gold edge ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #15100C 0%, #0F0B08 100%);
    /* an inset shadow draws the gold edge WITHOUT changing the layout
       (a thick border did, which pushed the text out of view) */
    box-shadow: inset -1px 0 0 rgba(200, 163, 106, 0.35);
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    font-weight: 600 !important;
    font-size: 1.35rem !important;
    letter-spacing: 0.04em;
    color: var(--gold) !important;
    border-bottom: 1px solid rgba(200, 163, 106, 0.2);
    padding-bottom: 0.3rem;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] label {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    color: var(--ivory);
}

.rc-side-brand {
    text-align: center;
    padding: 0.2rem 0 1rem 0;
}
.rc-side-brand .rc-side-name {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.9rem;
    font-weight: 600;
    color: var(--ivory);
}
.rc-side-brand .rc-side-tag {
    font-size: 0.68rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--gold);
}

/* ---------- Buttons: thin gold outline, filled on hover ---------- */
.stButton > button {
    background: transparent;
    color: var(--ivory);
    border: 1px solid rgba(200, 163, 106, 0.55);
    border-radius: 4px;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
}
.stButton > button:hover {
    background: var(--gold);
    color: var(--espresso);
    border-color: var(--gold);
}

/* ---------- Status boxes and the Sources panel ---------- */
[data-testid="stExpander"] {
    border: 1px solid rgba(200, 163, 106, 0.22);
    border-radius: 6px;
    background: rgba(14, 11, 9, 0.6);
}

/* ---------- Tool result cards ---------- */
[data-testid="stAlert"] {
    background: rgba(200, 163, 106, 0.08);
    border-left: 2px solid var(--gold);
    border-radius: 4px;
}

/* ---------- Bottom area: calm, with a thin gold line on top ---------- */
[data-testid="stBottom"] > div {
    background: var(--espresso);
    border-top: 1px solid rgba(200, 163, 106, 0.18);
}

[data-testid="stChatInput"] {
    border: 1px solid rgba(200, 163, 106, 0.45);
    border-radius: 6px;
}
[data-testid="stChatInput"] textarea {
    font-family: 'Inter', sans-serif;
}
</style>
""".replace("BEAN_PATTERN_URI", BEAN_PATTERN)


# The welcome card: eyebrow line, wordmark, gold rule, greeting, artwork.
HERO_HTML = """
<div class="rc-hero">
  <div class="rc-hero-text">
    <div class="rc-eyebrow">Specialty coffee · Your home barista</div>
    <div class="rc-wordmark">Home Barista Assistant</div>
    <div class="rc-rule"></div>
    <div class="rc-welcome">
      Good evening, and welcome. Take a seat; I'll help you brew a better cup,
      rescue one that tastes wrong, check your caffeine, or work out what each cup costs.
    </div>
  </div>
  <div class="rc-hero-art"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240" width="100%" height="100%" aria-hidden="true"> <defs>   <radialGradient id="crema" cx="45%" cy="42%" r="60%">     <stop offset="0%" stop-color="#D9A86C"/><stop offset="45%" stop-color="#A86E3A"/>     <stop offset="80%" stop-color="#6B4022"/><stop offset="100%" stop-color="#3E2312"/>   </radialGradient>   <radialGradient id="porcelain" cx="40%" cy="35%" r="70%">     <stop offset="0%" stop-color="#FBF8F2"/><stop offset="100%" stop-color="#DCD3C4"/>   </radialGradient>   <linearGradient id="bean" x1="0" y1="0" x2="1" y2="1">     <stop offset="0%" stop-color="#6A4128"/><stop offset="100%" stop-color="#2A170D"/>   </linearGradient> </defs> <g transform="translate(40 40) rotate(-25) scale(1.0)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(70 195) rotate(30) scale(1.1)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(250 40) rotate(15) scale(0.9)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(280 180) rotate(-40) scale(1.15)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(30 140) rotate(70) scale(0.9)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(290 110) rotate(10) scale(0.95)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(95 30) rotate(55) scale(0.85)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(225 215) rotate(-15) scale(1.0)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(60 95) rotate(-60) scale(0.8)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(265 75) rotate(80) scale(0.8)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(120 215) rotate(40) scale(0.85)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g><g transform="translate(200 25) rotate(-35) scale(0.8)"><ellipse rx="10" ry="6.8" fill="url(#bean)"/><path d="M -8 0.5 C -3 -3.5, 3 4, 8 -0.5" fill="none" stroke="#1A0E08" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="-3" cy="-3.2" rx="4" ry="1.4" fill="#FFFFFF" opacity="0.18"/></g> <ellipse cx="164" cy="128" rx="80" ry="80" fill="#000" opacity="0.35"/> <circle cx="160" cy="122" r="80" fill="url(#porcelain)"/> <circle cx="160" cy="122" r="66" fill="none" stroke="#CFC5B3" stroke-width="1.2"/> <rect x="210" y="112" width="44" height="20" rx="10" fill="url(#porcelain)" transform="rotate(-25 210 122)"/> <circle cx="160" cy="122" r="56" fill="url(#porcelain)"/> <circle cx="160" cy="122" r="47" fill="url(#crema)"/> <path d="M 160 92 C 182 98, 186 122, 168 134 C 154 143, 140 132, 146 120 C 151 110, 166 112, 165 122" fill="none" stroke="#E8C28E" stroke-width="2.4" stroke-linecap="round" opacity="0.55"/> <circle cx="160" cy="122" r="47" fill="none" stroke="#2A170D" stroke-width="1.2" opacity="0.6"/> </svg></div>
</div>
"""

# The brand block at the top of the sidebar
SIDEBAR_BRAND_HTML = """
<div class="rc-side-brand">
  <div class="rc-side-name">Home Barista Assistant</div>
  <div class="rc-side-tag">Your home barista</div>
</div>
"""


# ==========================================================
# The background scene behind the chat
# ==========================================================
@st.cache_data
def image_as_data_uri(path):
    """
    Turn an image file into text that CSS can use directly.
    (CSS in Streamlit can't read files from our folders, so we put
    the image INSIDE the CSS, encoded as text: a "data URI".)
    @st.cache_data: read and encode the file only once.
    """
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    return "data:image/jpeg;base64," + encoded


def background_css():
    """
    CSS that shows the coffee-bar scene around the chat, and puts
    the chat itself on a dark panel, so the text stays easy to read.
    If the image is missing, we simply keep the plain background.
    """
    if not os.path.exists(BACKGROUND_IMAGE):
        return ""

    image_uri = image_as_data_uri(BACKGROUND_IMAGE)
    return """
<style>
/* The scene, slightly darkened so it stays in the background */
[data-testid="stAppViewContainer"] {
    background-image:
        linear-gradient(rgba(8, 6, 4, 0.30), rgba(8, 6, 4, 0.55)),
        url("IMAGE_URI");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* The chat column: a dark, softly framed panel in the middle */
[data-testid="stMainBlockContainer"], .block-container {
    background: rgba(14, 11, 9, 0.90);
    border: 1px solid rgba(200, 163, 106, 0.22);
    border-radius: 10px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(4px);
    margin-top: 2.5rem;
    margin-bottom: 1rem;
}

/* The bottom strip: let the wood show, and frame only the input area */
[data-testid="stBottom"] > div {
    background: transparent;
    border-top: none;
}
[data-testid="stBottomBlockContainer"] {
    background: rgba(14, 11, 9, 0.94);
    border: 1px solid rgba(200, 163, 106, 0.22);
    border-bottom: none;
    border-radius: 10px 10px 0 0;
}
</style>
""".replace("IMAGE_URI", image_uri)


def apply_cafe_theme():
    """Add the Home Barista Assistant styling and logo. Call it once, near the top of app.py."""
    st.markdown(CAFE_CSS, unsafe_allow_html=True)
    st.markdown(background_css(), unsafe_allow_html=True)
    # st.logo fills the logo spot at the top of the sidebar
    st.logo(LOGO_IMAGE, size="large", icon_image=LOGO_IMAGE)


def show_welcome_banner():
    """Show the Home Barista Assistant welcome card at the top of the page."""
    st.markdown(HERO_HTML, unsafe_allow_html=True)


def show_sidebar_brand():
    """Show the Home Barista Assistant name at the top of the sidebar. Call it inside 'with st.sidebar'."""
    st.markdown(SIDEBAR_BRAND_HTML, unsafe_allow_html=True)
