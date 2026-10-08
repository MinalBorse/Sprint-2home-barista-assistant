# ==========================================================
# step10_rag_with_template.py
# ==========================================================
# Goal: a proper RAG flow, combining everything so far:
#   - RETRIEVE with embeddings (the best method in step09)
#   - AUGMENT with a LangChain prompt template
#   - GENERATE a grounded answer with sources
#
# REQUIREMENTS covered:
#   - "Implement standard document retrieval with embeddings"
#   - "Use similarity search"
#   - "Implement domain-specific prompts"
#   - "Show relevant context and sources"
# ==========================================================

import math
from langchain_core.prompts import ChatPromptTemplate
from src.llm import get_llm
from src.embeddings import get_embeddings
from src.sample_notes import SAMPLE_NOTES


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
TOP_K = 2   # how many notes to give the AI


# ==========================================================
# PART 1: RETRIEVE (embedding search)
# ==========================================================
# Note: in the next lesson, ChromaDB will replace this part.
# Here we still do it by hand so every step is visible.

def cosine_similarity(vector_a, vector_b):
    """Higher number = more similar meaning."""
    dot_product = 0
    for number_a, number_b in zip(vector_a, vector_b):
        dot_product = dot_product + (number_a * number_b)
    length_a = math.sqrt(sum(number * number for number in vector_a))
    length_b = math.sqrt(sum(number * number for number in vector_b))
    return dot_product / (length_a * length_b)


# Embed all notes ONCE (preparing the knowledge base)
embeddings_model = get_embeddings()

note_texts = []
for note in SAMPLE_NOTES:
    note_texts.append(note["text"])

print("Embedding the knowledge base...")
note_vectors = embeddings_model.embed_documents(note_texts)
print("Done.")
print()


def retrieve_notes(question):
    """Return the TOP_K most similar notes, each with its score."""
    question_vector = embeddings_model.embed_query(question)

    results = []
    for index in range(len(SAMPLE_NOTES)):
        score = cosine_similarity(question_vector, note_vectors[index])
        results.append({"note": SAMPLE_NOTES[index], "score": score})

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:TOP_K]


# ==========================================================
# PART 2: AUGMENT (the prompt template)
# ==========================================================
# REQUIREMENT: "Implement domain-specific prompts"
#
# The 4 parts of a good RAG prompt:
#   1. Role         -> who the bot is
#   2. Grounding    -> use only the notes
#   3. Fallback     -> what to say if the notes don't cover it
#   4. Citations    -> name the sources
#
# This is the BALANCED version: it allows connecting similar
# words (harsh -> bitter), which the strict version in step06 refused.

SYSTEM_PROMPT = """You are a friendly home barista assistant.

Rules:
1. Answer the question using ONLY the coffee notes provided.
2. You may connect words with similar meaning. For example, "harsh" can mean "bitter", and "sharp" can mean "sour".
3. If the notes do not cover the topic at all, say exactly: "I don't have information about that in my coffee notes." Do not use outside knowledge.
4. Keep the answer short and practical.
5. End with the sources you used, like: (Sources: troubleshooting_guide). If you said you don't have information, do NOT list any sources."""

# The template has two messages:
#   - "system": the rules above (always the same)
#   - "human": the notes + the question, with {placeholders}
#     that get filled in for every new question
prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Coffee notes:\n{context}\n\nQuestion: {question}"),
])


def build_context(retrieved_items):
    """
    Turn the retrieved notes into one text block, each labeled with its source:
    [troubleshooting_guide] Bitter, harsh or burnt-tasting coffee is...
    """
    context = ""
    for item in retrieved_items:
        note = item["note"]
        context = context + f"[{note['source']}] {note['text']}\n"
    return context


# ==========================================================
# PART 3: GENERATE (the chain)
# ==========================================================
llm = get_llm()

# The pipe | connects the steps: fill the template -> send to the LLM
rag_chain = prompt_template | llm


def ask(question):
    """Run the full RAG flow for one question and show every step."""
    print("==================================================")
    print("QUESTION:", question)
    print()

    # --- RETRIEVE ---
    retrieved_items = retrieve_notes(question)

    # REQUIREMENT: "Show relevant context and sources"
    print("RETRIEVED CONTEXT (what the AI will read):")
    for item in retrieved_items:
        note = item["note"]
        print(f"   {item['score']:.3f}  [{note['source']}] {note['text'][:60]}...")
    print()

    # --- AUGMENT + GENERATE ---
    # invoke() fills {context} and {question} in the template,
    # then sends the finished prompt to the LLM.
    response = rag_chain.invoke({
        "context": build_context(retrieved_items),
        "question": question,
    })

    print("ANSWER:")
    print(response.content)
    print()


# ==========================================================
# The tests
# ==========================================================

# 1. The question the STRICT prompt refused in step06
ask("My coffee tastes harsh, how can I fix it?")

# 2. Synonyms only - embeddings should find the sour note
ask("Why does my brew taste too acidic and tangy?")

# 3. Not in our notes - must say "I don't have information"
#    (retrieval still returns notes, so the PROMPT has to handle it)
ask("How do I make latte art?")

# 4. Exact topic in the notes
ask("What water temperature should I use for a V60?")