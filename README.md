# StudyBuddy - Free AI Assistant for Students

A Streamlit chatbot that answers any subject using Google Gemini (online) or Ollama (offline).

## Features
- Answers any subject, with chat memory and streaming replies
- Upload images, PDF, Word, PPT, text, audio and video (Gemini mode)
- Create a PowerPoint, PDF or Word file on any topic, from your last answer, or from your files
- One-click Summarize, Quiz, Flashcards and Study plan
- Web search for current information (DuckDuckGo)
- Voice questions
- Saved chat history (SQLite)
- Settings hidden from students; open `/?admin=1` to see them

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
