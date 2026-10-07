# ==========================================================
# src/security.py
# ==========================================================
# Purpose: an INPUT GUARD that checks every user message
#          BEFORE it reaches the AI.
#
# It blocks common "prompt injection" attempts - messages that try
# to make the AI ignore its rules, reveal its instructions, or
# switch to a different role.
#
# Why check in plain Python, before the AI?
#   - a blocked message never reaches the AI, so it can't be talked around
#   - it costs nothing (no API call)
#
# This is ONE layer of our security. The others are:
#   - secrets in .env (never uploaded, thanks to .gitignore)
#   - a fixed list of trusted sources (src/knowledge_sources.py)
#   - input validation inside every tool (src/tools.py)
#   - the caffeine health note (src/tools.py)
#   - safety rules in the agent's instructions (src/agent.py)
#
# Honest limitation: a pattern list catches COMMON attacks, not every
# possible one. That's why it's one layer of several.
#
# REQUIREMENT: "Add relevant security measures for your domain"
# OPTIONAL TASK (medium): "Protect your app against prompt injection"
# ==========================================================

import re


# ----------------------------------------------------------
# Attack patterns
# ----------------------------------------------------------
# Each pattern is a "regular expression" (a text pattern).
# Useful pieces:
#   (a|b)   -> "a" or "b"
#   ?       -> the part before it is optional
#   \s+     -> one or more spaces
# They target the ATTACK PHRASING, not single words, so normal coffee
# questions like "should I ignore the bloom?" are NOT blocked.
INJECTION_PATTERNS = [
    # "ignore all previous instructions", "ignore your rules", ...
    (r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|your\s+|my\s+)?"
     r"(previous\s+|prior\s+|above\s+|earlier\s+|original\s+)?(instructions|rules|prompts?|guidelines)",
     "tries to override the assistant's instructions"),

    # "reveal your system prompt", "what is your hidden prompt", ...
    (r"\b(system|hidden|initial|original|secret)\s+(prompt|instructions)",
     "asks about the assistant's hidden instructions"),
    (r"\b(reveal|print|repeat|output|dump)\s+(your|the)\s+(instructions|rules|prompt)",
     "asks the assistant to reveal its instructions"),

    # role switching: "you are now ...", "developer mode", "jailbreak"
    (r"\byou\s+are\s+now\b", "tries to change the assistant's role"),
    (r"\b(developer|dan|god|admin)\s+mode\b", "tries to switch the assistant to a special mode"),
    (r"\bjailbreak", "jailbreak attempt"),
    (r"\bpretend\s+(to\s+be|you\s+are)\b", "tries to change the assistant's role"),
    (r"\bnew\s+instructions\s*:", "tries to give the assistant new instructions"),

    # hidden markup that could be used to fake a system message
    (r"<\s*/?\s*(system|script|assistant)\b", "contains suspicious markup"),
]

# The reply shown when a message is blocked
BLOCKED_REPLY = (
    "I can't help with that request. I'm a home barista assistant, so I can "
    "answer questions about brewing, taste problems, caffeine and coffee costs."
)


def check_message(message):
    """
    Check one user message.

    Returns (is_safe, reason):
      (True, "")                  -> the message is fine
      (False, "why it's blocked") -> the message looks like an attack
    """
    text = message.lower()

    for pattern, reason in INJECTION_PATTERNS:
        if re.search(pattern, text):
            # Log it, so attacks can be monitored in the terminal
            print(f"[SECURITY] Blocked message ({reason}): {message[:80]}")
            return False, reason

    return True, ""
