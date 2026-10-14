# ==========================================================
# src/embeddings.py
# ==========================================================
# Purpose: create the EMBEDDING model.
#
# What is an embedding model?
#   A model that turns text into a list of numbers (a "vector").
#   Texts with similar MEANING get similar numbers.
#   Example: "harsh coffee" and "bitter coffee" end up close together.
#
# This is a DIFFERENT model from the chat model in llm.py:
#   - chat model (llm.py)        -> reads messages, writes answers
#   - embedding model (this file) -> reads text, returns numbers
#
# IMPORTANT RULE:
#   Documents and questions must use the SAME embedding model.
#   Each model creates its own "map of meaning", and you can't
#   compare positions from two different maps.
#   That's why every file gets the model from get_embeddings().
# ==========================================================

import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# Load the values from the .env file
load_dotenv()


# OpenRouter's address (same as in llm.py)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# The embedding model to use if EMBEDDING_MODEL_NAME is missing from .env
DEFAULT_EMBEDDING_MODEL_NAME = "openai/text-embedding-3-small"


def get_embeddings():
    """
    Create and return the embedding model, connected to OpenRouter.
    """

    # 1. Read the API key from .env (the same key as the chat model)
    api_key = os.getenv("OPENROUTER_API_KEY")

    # 2. Stop early with a clear message if the key is missing
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing. Add it to your .env file.")

    # 3. Read the embedding model name from .env (or use the default)
    model_name = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_EMBEDDING_MODEL_NAME)

    # 4. Create the embedding model object
    embeddings = OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        # By default, LangChain converts text into "tokens" (number IDs)
        # before sending it. That trick only works with OpenAI directly.
        # OpenRouter expects plain text, so we turn the trick off.
        check_embedding_ctx_length=False,
    )

    return embeddings
