# ==========================================================
# src/embeddings.py
# ==========================================================
# LEARNING NOTES (Module 1, Lesson 4)
#
# - 1,536: text-embedding-3-small always returns exactly 1,536 numbers per
#   text, short or long. That size is fixed by the MODEL (set by OpenAI when it
#   was trained), not by us. Other models use other sizes (e.g. 3,072).
#   Our 160 chunks x 1,536 = 245,760 numbers stored in chroma_db/.
#
# - The round trip: we send TEXT to OpenRouter, the embedding model runs on the
#   server, and the 1,536 numbers come BACK. Chunks are embedded ONCE (build);
#   each question is embedded at search time (then thrown away). Comparing the
#   question with the chunks happens LOCALLY, in Chroma.
#
# - Change EMBEDDING_MODEL_NAME -> you MUST rebuild the knowledge base
#   (a different model = a different map, and maybe a different size).
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


# LEARNING NOTE: same pattern as get_llm() in llm.py (load .env, check the key,
# .env wins over the default, return the object), with two differences:
#   - OpenAIEmbeddings instead of ChatOpenAI: text -> numbers, not text -> text
#   - NO temperature: an embedding model doesn't CHOOSE words, it CALCULATES
#     numbers, so there is nothing random to control. Same text -> same numbers,
#     which is exactly what we need to compare questions with chunks.
# Who calls it: src/vector_store.py gives it to Chroma, which calls it
# automatically when chunks are added and when a question is searched.
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
        # LEARNING NOTE: two kinds of "numbers":
        #   - token IDs: the text cut into pieces, one ID number per piece (no meaning)
        #   - embeddings: 1,536 numbers describing the MEANING (made on the server)
        # By default, LangChain cuts the text into token IDs on OUR computer, to check
        # its length, and sends the IDs. OpenRouter rejects token IDs, so we skip that
        # step and send plain text. Nothing important is lost: our chunks (at most 1,000
        # characters, about 250 tokens) are far below the model's limit (~8,000 tokens).
        check_embedding_ctx_length=False,
    )

    return embeddings
