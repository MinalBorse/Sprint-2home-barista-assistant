# src/llm.py
# Purpose: create the chat model (the "brain" of our chatbot).
# Every other file gets the model from here by calling get_llm().
# That way, if we change the model, we only change it in ONE place.
#
# LEARNING NOTES (Module 1, Lessons 2-3)
#
# Who calls get_llm():
#   - app.py, load_resources(): get_llm()              -> the agent and the planner (0.2)
#   - app.py:                   get_llm(temperature=0) -> the LLM security guard (0)
#   - build_knowledge_base.py:  get_llm()              -> LLM topic tagging of chunks
#   - evaluate_rag.py, tests/:  get_llm()              -> the same model, for testing
# The app creates the model ONCE and passes it into other functions
# ("passed in, not created"), e.g. plan_search(question, llm).
#
# Changing the model = one line in .env (MODEL_NAME), then restart the app.
# No rebuild needed: only a change of EMBEDDING model needs a rebuild.

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load the values from the .env file (API key, model name)
# into the environment, so os.getenv() can read them.
load_dotenv()
# LEARNING NOTE: load_dotenv() runs when this file is IMPORTED, not when
# get_llm() is called. So as soon as any file does "from src.llm import get_llm",
# the .env values are already loaded. "import os" gives us os.getenv("NAME").


# OpenRouter's web address.
# OpenRouter uses the same format as OpenAI,
# so we can use LangChain's ChatOpenAI class and just change the address.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# LEARNING NOTE: same LANGUAGE (the OpenAI format), different ADDRESS.
# ChatOpenAI builds an OpenAI-style request; base_url only decides where it is
# sent. Because every caller uses get_llm(), this one address covers the agent,
# the planner, the guard and the topic tagger.

# The model to use if MODEL_NAME is missing from .env
DEFAULT_MODEL_NAME = "openai/gpt-4o-mini"
# LEARNING NOTE: this is only the FALLBACK. In os.getenv("MODEL_NAME", default),
# the value in .env WINS; the default is used only if .env has no MODEL_NAME line.
# Capital letters = a constant (a convention for people; Python doesn't require it).


def get_llm(temperature=0.2):
    """
    Create and return the chat model, connected to OpenRouter.

    temperature controls randomness:
      - low (0.0 - 0.3) = focused, consistent answers (good for facts)
      - high (0.7 - 1.0) = more creative, more random answers
    """

    # LEARNING NOTE: this docstring is for PEOPLE (VS Code hover, help(get_llm)).
    # The model never sees it. Only docstrings of @tool functions are sent to the
    # model, as the tool's description (see src/tools.py and src/agent.py).
    #
    # Why temperature is a parameter with a default:
    #   - 0.2 (default): the agent writes answers for people; a little variety
    #     keeps the wording natural, while the FACTS come from the guides and tools.
    #   - 0: the guard makes block-or-allow decisions, which should be as
    #     consistent as possible. (Even 0 is not fully identical every time:
    #     the guard's REASONS varied between runs, but its decisions never did.)
    #   - Honest note: 0.2 is a sensible default, not a tuned value. The planner
    #     also makes decisions, so it could reasonably use 0 as well.

    # 1. Read the API key from .env
    api_key = os.getenv("OPENROUTER_API_KEY")

    # 2. Stop early with a clear message if the key is missing
    #    (much easier to understand than a crash deep inside LangChain)
    # LEARNING NOTE: "fail early, with a helpful message". The KEY is required:
    # without it nothing can work, so we stop here. The MODEL NAME has a sensible
    # default, so a missing name is not an error.
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing. Add it to your .env file.")

    # 3. Read the model name from .env (or use the default)
    model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME)

    # 4. Create the model object
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=temperature,
    )

    return llm
