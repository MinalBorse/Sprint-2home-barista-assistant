# ☕ Home Barista Assistant

**A coffee chatbot that answers brewing and taste questions from its own trusted guides, calculates recipes, caffeine and costs with tools, remembers the conversation, and shows exactly where every answer came from.**

Built for **Turing College, AI Engineering, Sprint 2**: *Building Applications with LangChain, RAGs, and Streamlit*.

| | |
|---|---|
| **Domain** | home coffee brewing: 11 brew methods, 5 taste problems |
| **Stack** | Python 3.12 · LangChain (`create_agent`, LangGraph runtime) · OpenRouter · ChromaDB · Streamlit · RAGAs |
| **Models** | `openai/gpt-4o-mini` (chat) · `openai/text-embedding-3-small` (embeddings), both through OpenRouter |
| **Knowledge base** | 2 guides I wrote + 6 openly licensed Wikipedia pages → **160 labelled chunks** |
| **Tools** | knowledge search (RAG) · brew ratio calculator (both directions) · caffeine estimator · cost per cup |
| **Security** | 7 layers, including a pattern guard and an LLM guard (7/7 unseen attacks blocked, 0 false alarms) |
| **Code quality** | dependencies managed with `uv` (`pyproject.toml` + `uv.lock`) · `ruff` lint and format · an AI code review with every finding assessed ([docs/ai_critique.md](docs/ai_critique.md)) |
| **Course requirements** | all 16 core requirements ✅ · bonus (2 medium + 1 hard) ✅ · [full checklist](#15-course-requirements-done-and-not-done) |

---

## Contents

1. [What the assistant does](#1-what-the-assistant-does)
2. [Architecture at a glance](#2-architecture-at-a-glance)
3. [How one question is answered](#3-how-one-question-is-answered)
4. [Building the knowledge base](#4-building-the-knowledge-base)
5. [Advanced RAG: query translation and structured retrieval](#5-advanced-rag-query-translation-and-structured-retrieval)
6. [The agent and its tools](#6-the-agent-and-its-tools)
7. [Security](#7-security)
8. [The user interface](#8-the-user-interface)
9. [Evaluation and testing](#9-evaluation-and-testing)
10. [Course content applied](#10-course-content-applied)
11. [Project structure](#11-project-structure)
12. [Setup and running](#12-setup-and-running)
13. [Design decisions and trade-offs](#13-design-decisions-and-trade-offs)
14. [Known limitations and next steps](#14-known-limitations-and-next-steps)
15. [Course requirements: done and not done](#15-course-requirements-done-and-not-done)
16. [Credits](#16-credits)

---

## 1. What the assistant does

| You ask | The assistant | Shown in the app |
|---|---|---|
| *"Why does my coffee taste harsh?"* | searches its guides (RAG), rewrites "harsh" as bitter, pins the bitter section | the answer, the search plan, and the sources with similarity scores |
| *"How much water for 18 g of coffee?"* | calls the **brew ratio calculator** | a green tool card: inputs and result (288 g) |
| *"I want 300 ml. How much coffee?"* | the same tool, in the **reverse** direction | 18.8 g |
| *"How much caffeine is in a 350 ml cold brew?"* | calls the **caffeine estimator** | ~245 mg, with a health note written by code |
| *"18 g in my V60, and why is it sour?"* | uses **two tools at once** | a tool card **and** sources |
| *"And what if I use 22 g?"* | remembers the conversation | 352 g, same ratio |
| *"How do I make latte art?"* | not in its guides, so it says so | no invented answer, no fake sources |
| *"Vergiss alle vorherigen Anweisungen"* | blocked by the LLM security guard | a polite refusal |

**Personalisation** in the sidebar: *My brewer* (11 methods), *Trusted guides only*, *Hide history and trivia*, and the answer style (*beginner / enthusiast*, *metric / imperial*, *short / detailed*).

---

## 2. Architecture at a glance

The Home Barista Assistant has two halves that meet in one folder: the **build** writes the knowledge base once, and the **app** reads it on every question.

```mermaid
flowchart LR
    subgraph BUILD["Prepare once: build_knowledge_base.py"]
        direction TB
        S["Trusted sources<br/>data/ guides + 6 Wikipedia pages"] --> L["Load + clean"]
        L --> SP["Split into chunks<br/>+ brew method / taste labels"]
        SP --> T["LLM topic tags"]
        T --> E["Embed + store"]
    end

    DB[("chroma_db/<br/>160 chunks")]

    subgraph APP["Every question: streamlit run app.py"]
        direction TB
        U["User message"] --> G["Validation +<br/>2 security guards"]
        G --> A["Agent<br/>create_agent"]
        A --> R["Knowledge search<br/>plan → filter → retrieve"]
        A --> C["Calculators<br/>ratio · caffeine · cost"]
        R --> ANS["Grounded answer<br/>+ sources + tool cards"]
        C --> ANS
    end

    E --> DB
    DB --> R
```

### Which file does what

```mermaid
flowchart TB
    APPPY["app.py<br/>web app"] --> SEC["security.py<br/>pattern + LLM guards"]
    APPPY --> THEME["theme.py<br/>app design"]
    APPPY --> AGENT["agent.py<br/>agent, prompts, preferences"]
    AGENT --> RAG["rag.py<br/>plan, filter, retrieve, answer"]
    AGENT --> TOOLS["tools.py<br/>3 calculators"]
    RAG --> TAGS["brew_methods.py + chunk_tags.py<br/>labels and allowed values"]
    RAG -. "receives" .-> VS["vector_store.py<br/>opens Chroma"]
    VS --> EMB["embeddings.py"]
    APPPY --> LLM["llm.py<br/>chat model via OpenRouter"]
    APPPY --> VS

    BUILDPY["build_knowledge_base.py"] --> LOADER["document_loader.py"]
    LOADER --> SRC["knowledge_sources.py<br/>trusted list"]
    BUILDPY --> SPLIT["document_splitter.py"]
    SPLIT --> TAGS
    BUILDPY --> VS
    BUILDPY --> LLM

    EVAL["evaluate_rag.py"] --> RAG
    EVAL --> TESTSET["eval_test_set.py"]
```

Three patterns run through the code:

- **One file, one area of responsibility.** To change the model, open `llm.py`; a security rule, `security.py`; a calculator, `tools.py`.
- **Shared doorways.** `get_llm()`, `get_embeddings()` and `get_vector_store()` hold their settings in one place, so the build, the app and the evaluation can never silently disagree (for example, on the database folder or the embedding model).
- **Passed in, not created.** `rag.py`, `chunk_tags.py` and `security.py` receive the LLM (and `rag.py` the database) as arguments, so the same code runs in the app, the build, the evaluation and the tests.

An interactive version of the file map is in [`docs/codebase_map.html`](docs/codebase_map.html).

---

## 3. How one question is answered

```mermaid
sequenceDiagram
    actor User
    participant App as app.py
    participant Guards as security.py
    participant Agent as agent (create_agent)
    participant Search as search_coffee_knowledge
    participant DB as Chroma
    participant Calc as tools.py

    User->>App: "18 g in my V60, and why is it sour?"
    App->>App: validate_question() (empty? over 500 chars?)
    App->>Guards: check_message(): patterns, free and instant
    App->>Guards: llm_check_message(): meaning, about 1 s
    Guards-->>App: safe
    App->>Agent: ask_agent(question, thread_id, preferences)
    Note over Agent: middleware builds the system prompt<br/>(rules + answer style)
    Agent->>Calc: brew_ratio_calculator(coffee_grams=18)
    Calc-->>Agent: "Use 288 g of water..."
    Agent->>Search: "why does my V60 taste sour?"
    Search->>Search: plan: query, brew = pour-over, taste = sour
    Search->>DB: taste boost + filtered meaning search (k = 4)
    DB-->>Search: 4 chunks + scores
    Search-->>Agent: labelled notes (ToolMessage)
    Agent-->>App: grounded answer
    App-->>User: answer + tool card + search caption + sources
```

The checkpointer saves the whole conversation under the session's `thread_id`, so the next question (*"and with 22 g?"*) is understood in context.

---

## 4. Building the knowledge base

`python build_knowledge_base.py` runs RAG's **"prepare once"** phase:

```mermaid
flowchart TB
    A["1. Load and clean<br/>document_loader.py"] --> B["2. Split and label<br/>document_splitter.py"]
    B --> C{"Any chunks?"}
    C -- "no" --> STOP["Stop: keep the old database"]
    C -- "yes" --> D["3. Tag topics with the LLM<br/>chunk_tags.py, 8 at a time"]
    D --> E["4. Empty the collection<br/>reset_collection()"]
    E --> F["5. Embed and store with fixed ids<br/>add_documents(chunks, ids)"]
    F --> G["6. Test search<br/>'harsh and burnt' → bitter section, 0.742"]
```

### Sources: only what I'm allowed to use

| Source | Licence | Why |
|---|---|---|
| `data/troubleshooting_guide.md` | written by me | 5 taste problems (sour, bitter, weak, strong, flat), each with synonyms in its heading |
| `data/brewing_guide.md` | written by me | 11 brew methods with grind, ratio, temperature, time and steps, plus a quick-reference table |
| 6 Wikipedia pages (French press, AeroPress, Espresso, Moka pot, Coffee roasting, Coffee preparation) | CC BY-SA, credited in the Sources panel | background and depth |

Commercial coffee sites were deliberately **not** scraped: their text is copyrighted, many forbid scraping, and unvetted community content is a prompt-injection risk. I use expert sites as references for writing my own guides instead.

### Loading and cleaning (`src/document_loader.py`)

| Step | How | Why |
|---|---|---|
| guides | `DirectoryLoader` + `TextLoader`, `glob="**/*.md"`, UTF-8 | new sections are picked up automatically |
| Wikipedia | `WebBaseLoader` with `SoupStrainer(id="mw-content-text")` | article text only, no menus |
| errors | `try/except` per URL | one failed page doesn't stop the build |
| cleaning | remove "See also / References / External links", hatnotes, `[12]` markers | the French press page went from **13,893 to 6,963** characters |

### Splitting (`src/document_splitter.py`)

```mermaid
flowchart LR
    G["Own guides"] --> H["MarkdownHeaderTextSplitter<br/>one ## section = one chunk<br/>strip_headers=False"]
    W["Wikipedia"] --> R["RecursiveCharacterTextSplitter<br/>1,000 chars, 150 overlap<br/>paragraphs → lines → words"]
    H --> X["Drop chunks under 100 chars"]
    R --> X
    X --> Y["Add chunk_id, brew_method, taste_problem"]
```

- **`strip_headers=False`** keeps each heading inside its chunk. Only the text is embedded, so a heading like *"Bitter, harsh, burnt or astringent coffee"* makes all of those words searchable.
- **Fixed ids** (`brewing_guide-9`) mean a re-run replaces records instead of duplicating them; **emptying the collection first** removes chunks of sections that were deleted or renamed.

### The labels on every chunk

| Label | Values | Set by | Used for |
|---|---|---|---|
| `brew_method` | 11 methods, or `general` | ordered keyword rules on the title and heading | the brew filter |
| `taste_problem` | bitter, sour, weak, strong, flat, or `none` | the troubleshooting guide's headings | the taste boost |
| `topic` | brewing, history, equipment, beans and roasting, troubleshooting, storage, other | an LLM, at build time | *Hide history and trivia* |
| `source_type` | own guide, Wikipedia | the loader | *Trusted guides only* |

**Keyword order matters.** The first matching method wins, so more specific methods come first:

| Heading | Trap word | Would wrongly be | Protected by |
|---|---|---|---|
| Moka pot (stovetop **espresso** maker) | espresso | espresso | moka pot listed before espresso |
| South Indian **filter coffee** (filter kaapi) | filter coffee | pour-over | south indian filter listed before pour-over |
| Vietnamese phin (**drip** filter) | drip | pour-over | vietnamese phin listed before pour-over |
| Percolator (**stovetop** or electric) | stovetop | moka pot | percolator listed before moka pot |

### What a stored record looks like

```mermaid
flowchart LR
    subgraph REC["One record in Chroma (160 in total)"]
        direction TB
        I["id: troubleshooting_guide-3"]
        T["text: '## Bitter, harsh, burnt...'<br/>embedded and searched by meaning"]
        V["embedding: 1,536 numbers"]
        M["metadata: brew_method, taste_problem,<br/>topic, source, title, section<br/>NOT embedded: filters + Sources panel"]
    end
```

**Knowledge base health check** (measured with the metadata):

- every taste problem has **exactly one** troubleshooting section (as designed)
- about **30%** of chunks are tagged **history** (46 of 155 when measured), which is why *Hide history and trivia* exists
- most chunks come from Wikipedia; my own guides are the smaller but best-matching part (the bitter section scores **0.742** for "harsh and burnt")

---

## 5. Advanced RAG: query translation and structured retrieval

The task asks for **advanced RAG with query translation and structured retrieval**. In this project, **one LLM call** (the planner) does both, by filling in a form:

```mermaid
flowchart TB
    Q["'my stovetop thing tastes bitter'"] --> P["Planner (structured output)<br/>SearchPlan form"]
    P --> F1["search_query: moka pot makes bitter coffee<br/>(query translation)"]
    P --> F2["brew_method: moka pot<br/>(structured retrieval)"]
    P --> F3["taste_problem: bitter<br/>(structured retrieval)"]
    P --> F4["topic: troubleshooting<br/>(lifts 'Hide history' if history)"]
    F2 --> CHK{"Python check:<br/>allowed value?"}
    F3 --> CHK
    CHK -- "no" --> ANY["'any' / 'none' = no filter"]
    CHK -- "yes" --> FIL["Filter: moka pot + general<br/>+ sidebar: trusted only, no history"]
    PREF["Sidebar preferences<br/>(My brewer only if the question names none)"] --> FIL
    F1 --> BOOST["A. Taste boost: bitter section pinned first"]
    F1 --> MAIN["B. Meaning search inside the filter, k = 4"]
    FIL --> MAIN
    BOOST --> MERGE["Merge: boost first, no duplicates, max 4"]
    MAIN --> MERGE
```

Chroma filter built by `build_filter()`:

```python
{"$and": [
    {"brew_method": {"$in": ["moka pot", "general"]}},   # this method + general tips
    {"source_type": "own guide"},                         # "Trusted guides only"
    {"topic": {"$ne": "history"}},                        # "Hide history and trivia"
]}
```

| Design choice | Reason |
|---|---|
| **"general" is always included** with a brew filter | the troubleshooting guide applies to every brewer |
| **the taste problem is a boost, not a filter** | a filter would throw away method-specific advice (like the moka pot's "cool the base"); a boost only adds |
| **Python checks every planner value** | the LLM can never invent a brew method or break the search |
| **if the planner fails, the original question is used** | a failed call makes the search less focused, never broken |
| **"the question wins"** | *My brewer* applies only when no brewer is named; *Hide history* is lifted for history questions |

**Evidence** (`tests/step15_query_translation.py`):

| Question | Original query | After rewriting |
|---|---|---|
| *why's my cup so meh?* | flat section not in the top 3 (top result: weak, 0.389) | flat section **first** (0.657; 0.408 in the latest run, still first) |
| *it's kinda puckery and thin* | weak only | **sour #1 (0.659)**, weak #2 |
| *my stovetop thing makes bitter stuff* | generic results | **Moka pot section #1 (0.689)** |

A firmer rule ("*puckery* **becomes** sour" instead of "for example...") fixed the puckery rewrite. Re-running the whole test set showed the side effects of each prompt change.

---

## 6. The agent and its tools

The chat runs on an **agent** built with LangChain's `create_agent`. For each message, it **decides** what to do: search, calculate, use several tools, or just answer.

```python
agent = create_agent(
    model=llm,                              # the chat model (get_llm)
    tools=[search_coffee_knowledge,         # RAG
           brew_ratio_calculator, caffeine_estimator, cost_per_cup],
    middleware=[personalised_prompt],       # builds the system prompt before every model call
    checkpointer=InMemorySaver(),           # memory, one thread per session
    context_schema=UserPreferences,         # sidebar preferences, per request
)
```

### The agent loop

```mermaid
flowchart LR
    M["New message"] --> MW["Middleware<br/>system prompt + answer style"]
    MW --> LLM["Model decides"]
    LLM -- "tool request(s)" --> T["Your code runs the tools<br/>(tools read runtime.context)"]
    T -- "ToolMessage(s)" --> MW
    LLM -- "text, no tool calls" --> ANS["Final answer"]
    CP[("Checkpointer<br/>loads + saves the thread")] <--> LLM
```

| Message | The agent's decision |
|---|---|
| *"Hi!"* | no tool |
| *"Why is my French press bitter?"* | `search_coffee_knowledge` |
| *"How much water for 20 g at 1:15?"* | `brew_ratio_calculator(coffee_grams=20, ratio=15)` |
| *"18 g in my V60, and why is it sour?"* | two tools at once |
| *"Write me a poem about cats"* | no tool, politely declines |

### Three kinds of information

| | Holds | Saved in memory? | In this project |
|---|---|---|---|
| **state** | the messages | ✅ by the checkpointer | the conversation |
| **config** | settings for this run | ❌ | `thread_id` |
| **context** | extra info for this request | ❌ | `UserPreferences`: brewer, filters, answer style |

Preferences travel as **context**, not as a message, so a user can't talk their way around them (*"ignore my trusted-guides setting"* changes nothing), and the AI never sees `runtime` as a tool input.

### The tools

| Tool | Inputs | Example result | Design details |
|---|---|---|---|
| `search_coffee_knowledge` | `question` (+ hidden `runtime`) | 4 labelled chunks | `content_and_artifact`: text for the AI, sources and plan for the UI; its description lists every covered brew method |
| `brew_ratio_calculator` | `coffee_grams` **or** `water_ml`, `ratio=16` | *"Use 288 g of water for 18 g..."* / *"Use about 18.8 g of coffee for 300 ml..."* | works both ways; exactly one amount required; helpful errors (*"for 1:16, send 16"*) |
| `caffeine_estimator` | `drink`, `size_ml` | *"~245 mg... health note"* | estimate per 100 ml, scaled; the health note is written by code |
| `cost_per_cup` | `bag_price`, `bag_grams`, `dose_grams` | *"about 1.08 per cup, 17 cups"* | validates the dose against the bag size |

**Tool design principles applied:** one clear job per tool; a description that says **when** to use it; typed inputs with examples and defaults; validation with errors the AI can act on; output written as a clear sentence; safety-critical text from code, not from the prompt.

### Memory

```mermaid
flowchart LR
    S1["Session A<br/>thread_id = a1b2"] --> CP[("InMemorySaver")]
    S2["Session B<br/>thread_id = c3d4"] --> CP
    CP --> N1["Notebook A: Human, AI, Human, AI, Tool, AI"]
    CP --> N2["Notebook B: ..."]
```

Each browser session gets its own `thread_id` (a UUID); *New conversation* starts a fresh one. `InMemorySaver` keeps conversations in RAM, so they're lost on restart (see [limitations](#14-known-limitations-and-next-steps)).

---

## 7. Security

```mermaid
flowchart LR
    MSG["Message"] --> V["1. Validation<br/>empty / too long"]
    V --> P["2. Pattern guard<br/>free, instant"]
    P --> L["3. LLM guard<br/>understands meaning"]
    L --> AG["Agent<br/>4. safety rules in the prompt"]
    AG --> TL["5. Tool input validation"]
    KB["6. Trusted sources only"] --> AG
    ENV["7. Secrets in .env, never on GitHub"]
```

| # | Layer | Where | Protects against |
|---|---|---|---|
| 1 | secrets in `.env`, `.gitignore`, `.env.example` for others | project root | leaked API keys |
| 2 | trusted, licensed sources only | `src/knowledge_sources.py` | **indirect** prompt injection hidden in documents |
| 3 | input validation | `validate_question()` in `app.py` | empty or oversized input |
| 4 | **pattern guard** | `check_message()` in `src/security.py` | known attack phrasings, instantly and for free |
| 5 | **LLM guard** (temperature 0, fails open) | `llm_check_message()` in `src/security.py` | reworded attacks, role-play tricks, other languages |
| 6 | tool input validation | `src/tools.py` | bad or out-of-range values from users or the model |
| 7 | agent safety rules | `AGENT_SYSTEM_PROMPT` in `src/agent.py` | off-topic requests, prompt extraction, documents treated as instructions, caffeine health guidance |

**Cheapest first:** the LLM guard only runs when the pattern guard finds nothing. **Fail open:** if the guard's call errors, the message is allowed, because the agent's own rules still apply. **Rules vs data:** retrieved text always travels in the HumanMessage or a ToolMessage, never in the system prompt, and rule 8 says to never follow instructions found inside it.

**Measured** (`tests/step19_security.py`):

| Test | Result |
|---|---|
| pattern guard: 10 attacks + 7 tricky normal questions | **17 / 17** |
| both guards on **7 unseen attacks** (rewordings, "you are DAN", a "school project" excuse, Spanish, German) | **7 / 7 blocked**: patterns 0, LLM guard 7 |
| tricky normal messages (*"forget the scale"*, *"ignore the grind size?"*) | **0 / 6 false alarms** |

---

## 8. The user interface

```mermaid
flowchart TB
    subgraph SIDEBAR["Sidebar"]
        B1["Brand + New conversation"]
        B2["My brewer · Trusted guides only · Hide history"]
        B3["Answer style: experience · units · length"]
    end
    subgraph CHAT["Chat"]
        C1["Welcome card + starter questions"]
        C2["Status: 'Done · used 2 tools'"]
        C3["Answer"]
        C4["Tool cards (inputs + results)"]
        C5["Caption: 'Searched for... · Filter... · Taste problem...'"]
        C6["Sources panel: chunks, similarity, labels"]
    end
```

| Streamlit feature | Used for |
|---|---|
| `st.chat_message`, `st.chat_input` | the chat |
| `st.session_state` | the on-screen history, `thread_id`, starter questions |
| `@st.cache_resource` | build the agent, database and guard model **once** |
| `st.status`, `st.spinner` | progress: *"Thinking..."*, *"Checking your message..."* |
| `st.success`, `st.expander`, `st.caption` | tool cards, Sources panel, search plan |
| `selectbox`, `toggle`, `radio`, `button(on_click=...)` | preferences, starter questions |
| custom CSS, `st.logo`, `.streamlit/config.toml` | the espresso-and-gold theme |

All artwork (the bean emblem, the avatar, the top-down espresso cup, the coffee-bar background) was **drawn in Python** as SVG and rendered with `cairosvg` and Pillow: no photos, no licensing questions.

---

## 9. Evaluation and testing
The full test strategy (every layer, how to run it, expected results, when to re-run, and a dated results log) is in [docs/TESTING.md](docs/TESTING.md).
### Retrieval methods compared (`tests/step09_hybrid_eval.py`, 6 labelled questions)

| Method | #1 correct | Precision@2 | Recall@2 |
|---|---|---|---|
| BM25 (keyword) | 4 / 6 | 0.33 | 0.67 |
| **Embeddings** | **5 / 6** | **0.50** | **1.00** |
| Hybrid (RRF, 0.6 / 0.4) | 5 / 6 | 0.50 | 1.00 |

BM25 missed synonym questions (*"acidic and tangy"*). Hybrid fixed *"harsh and burnt"* but broke *"pour-over weak and sharp"* ("over" matched "over-extracted"). **Decision:** embeddings, with structure (filters + taste boost) instead of keywords.

### RAGAs: A/B test of query rewriting (`evaluate_rag.py`, 10 questions)

**Run 1: 2026-10-07 (155 chunks)**

| Mode | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---|---|---|---|
| with query rewriting | **0.91** | **0.72** | **0.84** | **0.90** |
| without query rewriting | 0.88 | 0.71 | 0.79 | 0.78 |

**Run 2: 2026-10-09 (160 chunks)**: after adding five brew method sections, a pour-over section, an updated quick reference, and a firmer rewriting rule.

| Mode | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---|---|---|---|
| with query rewriting | 0.81 | **0.72** | **0.82** | 0.90 |
| without query rewriting | **0.91** | 0.71 | 0.68 | 0.90 |

**Run 3: 2026-10-20 (160 chunks)**: a repeat run with no changes, to check how stable the scores are.

| Mode | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---|---|---|---|
| with query rewriting | 0.92 | **0.72** | **0.82** | 0.90 |
| without query rewriting | 0.92 | 0.70 | 0.73 | **1.00** |

**Run 4: 2026-10-20 (160 chunks), independent judge**: the same app, but RAGAs judged with **gpt-4o** instead of gpt-4o-mini (`JUDGE_MODEL_NAME` in `.env`), so the app no longer grades its own answers. A stricter judge scores lower overall, so modes are compared within this run, not with runs 1 to 3.

| Mode | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---|---|---|---|
| with query rewriting | **0.79** | **0.73** | **0.78** | **1.00** |
| without query rewriting | 0.78 | 0.72 | 0.74 | 0.95 |

```mermaid
flowchart LR
    Q["Question"] -- "answer relevancy" --- A["Answer"]
    A -- "faithfulness" --- C["Retrieved contexts"]
    C -- "context precision + recall" --- R["Reference answer"]
```

**What the four runs show:**
- **better guides raised the baseline:** recall without rewriting went from 0.78 to 0.90
- **the planner consistently improves precision:** 0.84 vs 0.79, 0.82 vs 0.68 and 0.82 vs 0.73 in the three runs (*"meh"*: 0.42 → 1.00 in runs 2 and 3)
- **the faithfulness drop is mostly one row:** an espresso answer scored 0.25, but on inspection every piece of advice was in the guides, and precision and recall were 1.00. The judge had counted the user's own description, repeated in the answer, as unsupported claims. With 10 questions, one answer moves an average by up to 0.1, so low-scoring rows are always inspected before changing anything.
- the latte art row scores 0 on relevancy, precision and recall **by design**: the bot correctly refused (faithfulness 1.00)
- **run 3's recall gap is one row:** without rewriting, recall is 1.00 vs 0.90, entirely because of the off-topic latte art question (0.00 with rewriting, 1.00 without); on the other nine questions, recall is 1.00 in both modes
- **the judge varies between runs:** the espresso row scored 0.25 in run 2 and 0.57 in run 3 with the same app, which is why low-scoring rows are read, not trusted
- **an independent judge confirms the planner:** with gpt-4o judging, the planner is ahead on all four metrics (*"meh"*: precision 0.42 → 1.00, recall 0.50 → 1.00). Faithfulness is 0.79, just under the 0.8 target, because this judge scores the correct latte art refusal 0.00; without that row it is about 0.88 with rewriting and 0.86 without

**Two honest caveats** (found in the AI code review, findings #4 and #5):
- the *"without query rewriting"* mode also switches off the planner's **brew filter and taste boost**, so this A/B test compares the **whole planner** (rewriting + filters + boost) against plain search, not rewriting alone
- RAGAs evaluates the **RAG chain** (`answer_with_rag()`), which shares the planner and retrieval with the app, but the app's **answers** are written by the agent with its own prompt. Retrieval scores transfer; answer scores only partly

### Automated tests

| Script | Checks | Result |
|---|---|---|
| `uv run ruff check .` | PEP 8 style, import order, common bug patterns | **All checks passed** |
| `python -m tests.step17_tools` | all 3 calculators, including bad inputs and both directions | **14 passed** |
| `python -m tests.step18_agent` | tool choice, two tools at once, memory, off-topic, prompt extraction, **regression tests** (the siphon refusal, the one-way ratio tool) | **12 scenarios, all correct** |
| `python -m tests.step19_security` | pattern guard + both guards together | **17 / 17**, **7 / 7**, **0** false alarms |
| `python -m tests.step15_query_translation` | original vs rewritten queries | see section 5 |
| `python -m tests.step16_structured_retrieval` | results with and without the brew filter | on the test questions, the filter never removed a relevant chunk |

All results above were **re-run on 2026-10-14 after the review fixes**, and no tested decision changed.

**Bugs found by testing, and fixed:**

| Bug | Cause | Fix | Guarded by |
|---|---|---|---|
| the agent refused siphon questions **without searching** (under-calling) | the search tool's description didn't list the covered brew methods | list every method in the description; *"never refuse without searching first"* | regression test in `step18` |
| *"I want 300 ml, how much coffee?"* forced the model to do maths itself | the tool only worked coffee → water | the tool works both ways, exactly one amount required | `step17` + `step18` |
| *"puckery"* wasn't rewritten | the rewriting rule only gave examples | firmer rule: *"X becomes Y"* | `step15` |
| a failed knowledge search **crashed** the agent, and could break the conversation | the search tool had no `try/except`; LangGraph's default handler re-raises such errors | `retrieve_safely()` catches the error and the tool returns a friendly error message, like the calculators | reproduced before and after the fix by forcing `retrieve` to fail |

### AI code review

I ran a code review with **Claude Code** and assessed every finding myself, with a check or a test for each:

| | Count |
|---|---|
| findings from the AI | 30 |
| extra findings I found while checking | 5 |
| real | 27 |
| not reproduced when tested | 2 |
| partly a deliberate design choice | 1 |
| fixed so far | 5 (the search tool crash above, plus four prompt-text issues) |

Two examples of why each finding was verified before fixing: the AI suspected that "filter" and "drip" questions were misrouted to pour-over, but the planner routed all four test questions correctly, twice. And while re-testing after the fixes, I found that *"tell me about latte art"* is answered **without searching**, while *"How do I make latte art?"* searches (2 of 2 times each), because rule 1 lists specific topics and milk drinks aren't among them.

The full report, my verdict on every finding, the exact commands I ran, and the planned fixes are in [docs/ai_critique.md](docs/ai_critique.md).

---

## 10. Course content applied

### Part 1: Introduction to LangChain

| Lesson | Idea | Where in this project |
|---|---|---|
| Why LangChain | one standard interface to any model | `src/llm.py`: `ChatOpenAI` pointed at OpenRouter; model name in `.env` |
| Models and messages | System, Human, AI and Tool messages; the model reads the list and writes the next one | middleware builds the SystemMessage; the question becomes a HumanMessage; `isinstance` reads the results |
| Tools | the model requests functions it never sees | `src/tools.py`, the search tool, the tool cards |
| Memory | the model remembers nothing; history is re-sent | `InMemorySaver` + `thread_id` |
| Agents | reason → act → observe, until a text answer | `create_agent` in `src/agent.py` |

### Part 2: Retrieval-Augmented Generation

| Lesson | Idea | Where in this project |
|---|---|---|
| What RAG is | prepare once, look up before answering | `build_knowledge_base.py` + the search tool |
| Embeddings | text → 1,536 numbers; same model for documents and questions | `src/embeddings.py` |
| Retrieval | keyword (BM25), vector (cosine), hybrid; precision and recall | `retrieve()` in `src/rag.py`, `tests/step09_hybrid_eval.py` |
| Augmented generation | notes in the prompt; grounding, fallback, citations | `answer_prompt`, `build_context()`, agent rules |
| Vector databases | store text + embeddings + metadata; filter | `src/vector_store.py`, `chroma_db/` |

### Part 3: Integrating RAG with LangChain

| Lesson | Idea | Where in this project |
|---|---|---|
| Loading | loaders → `Document` objects; clean before splitting | `src/document_loader.py` |
| Splitting | chunk size, overlap, structure-aware splitting | `src/document_splitter.py` |
| Embedding and storing | embed once; fixed ids; no stale chunks | `build_knowledge_base.py` |
| Query translation and structured retrieval | rewrite + metadata filters (self-querying) | `plan_search()`, `build_filter()`, `retrieve()` (`tests/step15`, `tests/step16`) |
| Evaluation with RAGAs | LLM judge; retrieval vs generation metrics; A/B testing | `evaluate_rag.py`, `src/eval_test_set.py` |

### Part 4: Function calling and beyond

| Lesson | Idea | Where in this project |
|---|---|---|
| Function calling | tool schemas, `tool_calls` with ids, parallel calls; structured output uses the same mechanism | `with_structured_output` for the planner and the LLM guard |
| Agents with `create_agent` | middleware, runtime context, checkpointer | `@dynamic_prompt`, `ToolRuntime[UserPreferences]`, `InMemorySaver` |
| Designing good tools | one job, clear description, typed inputs, validation, helpful errors | `src/tools.py`; the two-way ratio tool; the siphon description fix |
| Evaluating tool calling | right tool, right inputs; under- and over-calling; regression tests | `tests/step17_tools.py`, `tests/step18_agent.py` |
| MCP | a standard protocol for sharing tools, resources and prompts | not needed for a single app; the calculators could be shared through a thin MCP server wrapper |

### "RAG from scratch" notebooks

| Notebook topic | In this project |
|---|---|
| 1–4: indexing, retrieval, generation basics | ✅ the core pipeline; the notebook's custom OpenRouter embeddings wrapper is replaced by `check_embedding_ctx_length=False` |
| 5–9: multi-query, RAG-fusion, decomposition, step-back, HyDE | single-call query rewriting; RRF used in `step09`; the agent decomposes multi-part questions into several tool calls |
| 10–11: routing and query construction | the agent routes to tools; the planner constructs metadata filters |
| 12–14: multi-representation, RAPTOR, ColBERT | not used; LLM topic labels added at build time, a lighter idea in the same spirit |
| 15–18: re-ranking, CRAG, Self-RAG, long context | rule-based taste boost; the fallback rule instead of web search; RAGAs offline; RAG chosen over long context (about 30× fewer tokens per question) |

---

## 11. Project structure

```
home-barista-assistant/
├── app.py                      # the Streamlit app (run this)
├── build_knowledge_base.py     # builds chroma_db/ (run once, and after source changes)
├── evaluate_rag.py             # RAGAs A/B evaluation
├── README.md
├── pyproject.toml              # the project and its 15 direct dependencies, plus ruff settings
├── uv.lock                     # exact versions of all 148 packages (uv sync)
├── requirements.txt            # generated from uv.lock, for pip users
├── .env.example                # copy to .env and add your key
├── .streamlit/config.toml      # base theme colours
├── assets/                     # bean emblem, avatar, background (drawn in Python)
├── data/
│   ├── troubleshooting_guide.md
│   └── brewing_guide.md
├── docs/
│   ├── codebase_map.html       # interactive map of every file
│   └── ai_critique.md          # AI code review, my verdicts and checks
    │   └── TESTING.md              # test strategy, commands, expected results, results log
├── eval_results/               # RAGAs results, one CSV per mode
├── src/
│   ├── llm.py                  # get_llm()
│   ├── embeddings.py           # get_embeddings()
│   ├── vector_store.py         # get_vector_store()
│   ├── knowledge_sources.py    # the trusted source list
│   ├── document_loader.py      # load + clean
│   ├── document_splitter.py    # split + label
│   ├── brew_methods.py         # 11 brew methods + ordered keywords
│   ├── chunk_tags.py           # taste problems, LLM topic tagging
│   ├── rag.py                  # planner, filters, retrieval, answers
│   ├── tools.py                # 3 calculators
│   ├── agent.py                # create_agent, prompts, preferences, search tool
│   ├── security.py             # pattern guard + LLM guard
│   ├── theme.py                # the app's design
│   ├── eval_test_set.py        # 10 RAGAs questions
│   └── sample_notes.py         # 5 small practice notes (not used by the app)
└── tests/                      # step09, step15–step19: evaluations and tests
```

---

## 12. Setup and running

### 1. Install

```powershell
git clone <this-repository-url>
cd home-barista-assistant
uv sync                          # creates .venv with the exact versions from uv.lock
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
```

Without uv: `pip install -r requirements.txt` (generated from `uv.lock` with `uv export`).

### 2. Configure

Copy `.env.example` to `.env` and fill in your key:

```
OPENROUTER_API_KEY=sk-or-...
MODEL_NAME=openai/gpt-4o-mini
EMBEDDING_MODEL_NAME=openai/text-embedding-3-small
USER_AGENT=HomeBaristaAssistant/1.0 (student learning project)
```

### 3. Build the knowledge base

```powershell
python build_knowledge_base.py
```

It needs an internet connection (Wikipedia), takes about a minute (LLM topic tagging), and costs well under a cent. It ends with a test search.

### 4. Run the app

```powershell
streamlit run app.py
```

Open http://localhost:8501. Keep that terminal for Streamlit and use a second one for other commands.

### 5. Run the tests and the evaluation

```powershell
uv run ruff check .               # style and bug patterns (free, instant)
uv run ruff format .              # tidy the layout
python -m tests.step17_tools      # free, instant
python -m tests.step18_agent      # live model, a few cents
python -m tests.step19_security   # part 1 free, part 2 uses the LLM guard
python evaluate_rag.py            # a few minutes, a few cents
```

Scripts in `tests/` are run as modules (`python -m folder.script`) from the project root, so they can import `src`.

---

## 13. Design decisions and trade-offs

| Decision | Alternative | Why |
|---|---|---|
| **embeddings + filters + boost** | hybrid search | same recall in testing, and hybrid introduced false keyword matches |
| **one planner call fills a 4-field form** | separate calls per technique | cheaper and faster; Python validates every field |
| **taste problem as a boost** | a strict filter | adds the right section without removing method-specific advice |
| **headings kept inside chunks** | headings only as metadata | only text is embedded, so heading synonyms must be in the text |
| **keyword labels for chunks, an LLM for questions** | the same method for both | headings are predictable; user language isn't |
| **empty the collection before each build** | incremental updates | removed or renamed sections can never leave stale chunks; costs under a cent |
| **an agent for the app, a fixed chain for RAGAs** | the agent everywhere | RAGAs measures retrieval and grounding without the agent's choices in the way; the trade-off is that the agent's own answer wording isn't scored (see section 14) |
| **`uv` + `ruff`** | `pip` and no linter | one command reproduces the exact environment; style and common bugs are checked automatically |
| **preferences as runtime context** | preferences in the message | can't be overridden by user text; never stored in the history |
| **two input guards, cheapest first** | only one guard | patterns are free and instant; the LLM guard catches what patterns can't |
| **the LLM guard fails open** | fail closed | a network hiccup shouldn't block every user; other layers still protect |
| **sources from database metadata** | the model's own citation line | the model once invented a source title; metadata can't |
| **own guides + openly licensed Wikipedia only** | scraping coffee websites | copyright, terms of use, and prompt-injection risk |
| **RAG** | sending the whole knowledge base (~30,000 tokens) | about 30× cheaper per question, more focused, and traceable sources |

---

## 14. Known limitations and next steps

| Limitation | Evidence | Next step |
|---|---|---|
| **recognising a device isn't knowing about it** | a Chemex answer was routed correctly, but its specific grind wasn't in the guide | write deeper sections (pour-over and cold brew have one chunk each) and a milk drinks guide (latte art) |
| **detailed answers can drift beyond the notes** | the "detailed" style added facts from the model's memory | style rule: *"add detail only from the notes"*; a Self-RAG-style answer check |
| **the agent doesn't know the user's brewer** | with *My brewer = phin*, a general answer included a French press tip | pass the brewer into the system prompt |
| **one topic label per chunk** | the French press introduction (a definition with dates) was tagged history | several labels per chunk, or a stricter tagging rule |
| **LLM variability** | rewrites changed between runs; the RAGAs judge misjudged one answer | re-run tests after every change; run evaluations several times |
| **small test sets** | 10 RAGAs questions, 6 retrieval questions | grow the test sets; save retrieved contexts in the RAGAs CSV |
| **memory is lost on restart, and never trimmed** | `InMemorySaver`, shared by all sessions; long chats re-send the whole history | `SqliteSaver`, plus trimming or summarising old messages |
| **the evaluation doesn't fully measure the app** | RAGAs scores the RAG chain, not the agent; the A/B test changes the planner, not only rewriting (review #4, #5) | evaluate through `ask_agent()`; add a mode that changes only the rewrite |
| **a failed rebuild empties the knowledge base** | `reset_collection()` runs before `add_documents()` (review #3) | build into a new collection, then switch |
| **some phrasings skip the search** | *"tell me about latte art"* answered without searching, 2 of 2 times (review #35) | widen rule 1 to every coffee question; add a regression test |
| **failed searches are worded as missing information** | after the crash fix, a failed search reads as *"I don't have information"* plus general tips (review #34) | make the tool's error text tell the agent exactly what to say |
| **Wikipedia is fetched live at build time** | the source list controls which pages, not their content at that moment (review #10) | save reviewed snapshots in `data/` |
| **no real automated test suite** | the test scripts print PASS/FAIL but never fail, and nothing mocks the LLM (review #1) | `pytest` tests with mocked LLM calls; tool-selection accuracy scores like the course's Lab 2 |
| **no login or rate limiting** | anyone with access could use the API budget | user accounts and per-user limits |
| **leftover Wikipedia editor notes** | `[circular reference]` markers remain | extend the cleaner to all bracketed notes |

The full list of review findings and planned fixes is in [docs/ai_critique.md](docs/ai_critique.md).

Further ideas: token usage and cost display, conversation export (JSON/CSV), a model selector, a CRAG-style relevance grader, step-back queries for extraction questions, a parent document retriever for long Wikipedia pages, a personal coffee journal (SQLite + two agent tools).

---

## 15. Course requirements: done and not done

This section follows the Sprint 2 project page item by item.

**Legend:** ✅ done · ⏳ partly done · ❌ not done

### Status at a glance

| Part of the task | Status |
|---|---|
| The four goals of the chatbot | ✅ 4 / 4 |
| Core requirements | ✅ 16 / 16 |
| Bonus points: at least 2 medium + 1 hard optional task | ✅ met (2 medium + 2 hard) |
| Optional tasks in total | ✅ 7 done · ⏳ 6 partly · ❌ 8 not done |
| Evaluation criteria | ✅ evidence for all 10 (below) |
| Submission to the Turing College repository | ⏳ see the end of this section |

### Task description: the chatbot will...

| # | Goal | Status | How the assistant does it |
|---|---|---|---|
| 1 | implement advanced RAG with **query translation** and **structured retrieval** | ✅ | one planner call rewrites the question **and** fills metadata filters (brew method, taste problem, topic); see [section 5](#5-advanced-rag-query-translation-and-structured-retrieval) |
| 2 | include tool calling for practical tasks | ✅ | 4 tools: knowledge search, brew ratio (both directions), caffeine, cost per cup |
| 3 | focus on a specific domain or use case | ✅ | home coffee brewing: 11 brew methods, 5 taste problems |
| 4 | provide detailed, context-aware responses | ✅ | grounded answers with sources, conversation memory, answer-style preferences |

### Core requirements

**1. RAG implementation**

| Requirement | Status | Where |
|---|---|---|
| Create a knowledge base relevant to your domain | ✅ | `data/` guides + 6 Wikipedia pages → 160 labelled chunks in `chroma_db/` |
| Implement standard document retrieval with embeddings | ✅ | `src/embeddings.py`, `retrieve()` in `src/rag.py` |
| Use chunking strategies and similarity search | ✅ | `src/document_splitter.py` (Markdown headings + recursive, 1,000 / 150); cosine similarity in Chroma |

**2. Tool calling**

| Requirement | Status | Where |
|---|---|---|
| Implement at least 3 different tool calls | ✅ | 4 tools: `src/tools.py` + `search_coffee_knowledge` in `src/agent.py` |
| Functions relevant to your domain | ✅ | brewing recipe, caffeine, cost, coffee knowledge |
| Examples: data analysis, calculations, API integrations | ✅ | calculations (and RAG search) |

**3. Domain specialisation**

| Requirement | Status | Where |
|---|---|---|
| Choose a specific domain or use case | ✅ | home barista assistant |
| Create a focused knowledge base | ✅ | trusted, licensed sources only (`src/knowledge_sources.py`) |
| Implement domain-specific prompts and responses | ✅ | agent, planner, answer and guard prompts |
| Add relevant security measures for your domain | ✅ | 7 layers, including two input guards and a caffeine health note; see [section 7](#7-security) |

**4. Technical implementation**

| Requirement | Status | Where |
|---|---|---|
| Use LangChain with OpenRouter (OpenAI-compatible SDK) | ✅ | `src/llm.py`, `src/embeddings.py` |
| Implement proper error handling | ✅ | `try/except` with fallbacks: per web page, planner, LLM guard (fails open), build safety check, app-level error message |
| Include user input validation | ✅ | `validate_question()` (empty, over 500 characters), tool input validation, security guards |

**5. User interface**

| Requirement | Status | Where |
|---|---|---|
| Create an intuitive interface using Streamlit or Next.js | ✅ | Streamlit: the Home Barista Assistant app |
| Show relevant context and sources | ✅ | Sources panel (chunks, similarity, labels) + search caption |
| Display tool call results | ✅ | tool cards with inputs and results |
| Include progress indicators for long operations | ✅ | `st.status` ("Done · used 2 tools") and spinners |

### Optional tasks

**Easy**

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Add conversation history and export functionality | ⏳ | history ✅ (memory per session, on-screen chat, *New conversation*); **export ❌** |
| 2 | Add visualisation of RAG process | ✅ | status box, search caption (query, filters, taste problem), Sources panel with scores |
| 3 | Include source citations in responses | ✅ | *"(Sources: ...)"* in answers + the Sources panel from database metadata |
| 4 | Add an interactive help feature or chatbot guide | ✅ | barista greeting with starter questions; *"On the menu tonight"* in the sidebar |

**Medium**

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Implement multi-model support (OpenAI, Anthropic, etc.) | ⏳ | any OpenRouter model works by changing `MODEL_NAME` in `.env`; **no model selector in the app** |
| 2 | Add real-time data updates to knowledge base | ❌ | the knowledge base is rebuilt by hand |
| 3 | **Protect your app against prompt injection** | ✅ | pattern guard + LLM guard; 17 / 17, 7 / 7 unseen attacks, 0 false alarms |
| 4 | Add user authentication and personalisation | ⏳ | personalisation ✅ (My brewer, filters, answer style); **authentication ❌** |
| 5 | Calculate and display token usage and costs | ❌ | not shown in the app |
| 6 | **Add visualisation of tool call results** | ✅ | tool cards with inputs and results |
| 7 | Implement conversation export in various formats (PDF, CSV, JSON) | ❌ | |
| 8 | Connect to tools from a publicly available remote MCP server | ❌ | MCP studied in theory ([section 10](#10-course-content-applied)) |
| 9 | Implement rate limiting and API key management | ⏳ | key kept in `.env` with `.env.example`; **no rate limiting** |
| 10 | Add logging and monitoring | ⏳ | `[SECURITY]` and error lines printed to the terminal; no log file or dashboard |

**Hard**

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | Employ hybrid search | ⏳ | built and measured (BM25 + embeddings with RRF) in `tests/step09_hybrid_eval.py`; **not used in the app**, by choice (see [section 13](#13-design-decisions-and-trade-offs)) |
| 2 | **Implement A/B testing for different RAG strategies** | ✅ | with vs. without query rewriting (RAGAs, two runs); BM25 vs. embeddings vs. hybrid |
| 3 | Add automated knowledge base updates | ❌ | |
| 4 | Add multi-language support | ❌ | the LLM guard understands other languages, but the bot is designed for English |
| 5 | Implement advanced analytics dashboard | ❌ | |
| 6 | Implement your tools (functions) as MCP servers | ❌ | a thin wrapper around `src/tools.py` would be possible |
| 7 | **Implement an evaluation of your RAG system, using RAGAs or otherwise** | ✅ | `evaluate_rag.py`: faithfulness, answer relevancy, context precision and recall; see [section 9](#9-evaluation-and-testing) |

**Bonus points:** *"For maximum points, the learner should implement at least 2 medium and 1 hard optional task."*

| Needed | Done |
|---|---|
| 2 medium | ✅ prompt-injection protection · ✅ tool call result visualisation |
| 1 hard | ✅ RAGAs evaluation · ✅ A/B testing of RAG strategies |

### Evaluation criteria

| Criterion | Status | Evidence in this project |
|---|---|---|
| Understands the basic principles of how RAG works | ✅ | the two-phase pipeline ([sections 3–5](#3-how-one-question-is-answered)); retrieval methods compared; RAGAs |
| Can explain tool calling implementation clearly | ✅ | the agent loop ([section 6](#6-the-agent-and-its-tools)), built with `create_agent` |
| Demonstrates good code organisation practices | ✅ | one area per file, shared doorways, `uv` with a lockfile, `ruff` lint and format, a `tests/` folder, [`docs/codebase_map.html`](docs/codebase_map.html) |
| Can identify potential error scenarios and edge cases | ✅ | fallbacks and validation; the keyword-order traps; bugs found by testing, including the search tool crash reproduced before and after its fix ([section 9](#9-evaluation-and-testing)) |
| Knows how to use a front-end library | ✅ | Streamlit chat, caching, session state, status, custom theme ([section 8](#8-the-user-interface)) |
| The project works as intended | ✅ | chat with the app; all automated tests pass |
| Has created a relevant knowledge base for their domain | ✅ | trusted sources, cleaned and labelled; gaps found and filled ([section 4](#4-building-the-knowledge-base)) |
| Has implemented appropriate security considerations | ✅ | 7 layers, measured ([section 7](#7-security)) |
| Understands the potential problems with the application | ✅ | [section 14](#14-known-limitations-and-next-steps) and the AI code review: 35 findings assessed ([docs/ai_critique.md](docs/ai_critique.md)) |
| Can offer suggestions on improving the code and the project | ✅ | [section 14](#14-known-limitations-and-next-steps), each based on a measurement or observation |

### Topics from the project page

| Topic | Status | Where |
|---|---|---|
| Advanced RAG implementation | ✅ | planner, filters, taste boost |
| Tool calling | ✅ | 4 tools, `create_agent` |
| ChatGPT | ✅ | OpenAI's `gpt-4o-mini` through OpenRouter |
| Prompt engineering | ✅ | agent rules, planner rules ("X becomes Y"), grounded answer prompt, guard prompt |
| Streamlit | ✅ | the Home Barista Assistant app |
| LangChain | ✅ | loaders, splitters, Chroma, structured output, `create_agent`, middleware |
| Vector databases | ✅ | ChromaDB |

### Submission and review

| Step | Status |
|---|---|
| Code, README and evaluation results on GitHub | ✅ |
| Project in the GitHub repository created by Turing College | ⏳ to do |
| Project review scheduled | ⏳ to do |

---

## 16. Credits

- Wikipedia articles (French press, AeroPress, Espresso, Moka pot, Coffee roasting, Coffee preparation) are used under **CC BY-SA**, and every chunk keeps its source URL, shown in the Sources panel.
- The brewing and troubleshooting guides were written for this project.
- All images were generated in Python code for this project.
- Built with [LangChain](https://python.langchain.com/), [OpenRouter](https://openrouter.ai/), [ChromaDB](https://www.trychroma.com/), [Streamlit](https://streamlit.io/) and [RAGAs](https://docs.ragas.io/).