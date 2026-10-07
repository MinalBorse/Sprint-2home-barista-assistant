# src/llm.py
# Purpose: create the chat model (the "brain" of our chatbot).
# Every other file gets the model from here by calling get_llm().
# That way, if we change the model, we only change it in ONE place.

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# Load the values from the .env file (API key, model name)
# into the environment, so os.getenv() can read them.
load_dotenv()


# OpenRouter's web address.
# OpenRouter uses the same format as OpenAI,
# so we can use LangChain's ChatOpenAI class and just change the address.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# The model to use if MODEL_NAME is missing from .env
DEFAULT_MODEL_NAME = "openai/gpt-4o-mini"


def get_llm(temperature=0.2):
    """
    Create and return the chat model, connected to OpenRouter.

    temperature controls randomness:
      - low (0.0 - 0.3) = focused, consistent answers (good for facts)
      - high (0.7 - 1.0) = more creative, more random answers
    """

    # 1. Read the API key from .env
    api_key = os.getenv("OPENROUTER_API_KEY")

    # 2. Stop early with a clear message if the key is missing
    #    (much easier to understand than a crash deep inside LangChain)
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