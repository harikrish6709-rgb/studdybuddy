# StudyBuddy - Free AI Assistant for Students

A Streamlit chatbot that answers any subject using Google Gemini (online) or Ollama (offline).

## Features
- Answers any subject, with chat memory and streaming replies
- White, ChatGPT-style interface: light theme, right-aligned grey bubble for your messages,
  plain left-aligned assistant replies, "+" attach button, round send button
- Sidebar: new chat, search your past chats, Projects / Artifacts / Plugins nav (placeholders -
  not built yet, they tell you so when clicked instead of silently doing nothing), chat history
- Upload images, PDF, Word, PPT, text, audio and video (Gemini mode)
- Create a PowerPoint, PDF or Word file on any topic, from your last answer, or from your files
- One-click Summarize, Quiz, Flashcards and Study plan
- **Current information**: Gemini decides for itself, per question, whether it needs a live
  Google Search before answering (news, scores, prices, elections, versions, etc.) - this is
  Google's own "Grounding with Google Search" tool, not scraping. See "Current information" below.
- Voice questions
- Saved chat history (SQLite)
- Settings hidden from students; open `/?admin=1` to see them

## Current information (why answers were stale, and the fix)
The previous version tried to guess (with a keyword list) when a question needed fresh
information, then scraped DuckDuckGo and pasted a few snippets into the prompt. That broke
silently whenever the scrape returned nothing, and the keyword list missed many "current"
questions. This version instead gives Gemini Google Search as a tool and lets the model decide,
per question, whether to use it - the same mechanism ChatGPT/Gemini's own apps use.

**Important - this needs billing enabled on your Gemini API key.** Google Search grounding is
*not available at all* on a pure free-tier key; it requires a Google Cloud billing account
linked to your API key. Once billing is enabled you still get **5,000 free grounded requests per
month** before Google starts charging (about $14 per extra 1,000 requests, with a 1,500/day cap on
some older models) - see https://ai.google.dev/gemini-api/docs/pricing for the current numbers,
since Google changes these periodically.

If your key doesn't have billing enabled, StudyBuddy automatically falls back to the old
DuckDuckGo-based search instead of crashing - you'll still get an answer, just a less reliable
one. To get the full benefit, enable billing for your Google Cloud project at
https://aistudio.google.com/ (Billing / "Set up billing"). You do not have to actually spend
anything to get the free monthly grounding allowance - you only pay if you go over it.

## Files
- app.py: the screen and chat logic
- llm.py: talks to Gemini or Ollama
- prompts.py: personality, levels, quick study prompts
- files.py: reads uploaded files
- export.py: builds PPT / PDF / Word files
- search.py: web search
- database.py: saved chats

## Run
```
pip install -r requirements.txt
streamlit run app.py
```
Put your key in `.streamlit/secrets.toml`:
```
GEMINI_API_KEY = "your-key-here"
```
Never upload secrets.toml to GitHub.
