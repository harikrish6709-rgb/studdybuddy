import hashlib
import os
import sys
import traceback

import streamlit as st

import database as db
from export import FORMATS, generate_document, safe_name
from files import ALLOWED_TYPES, make_attachment
from llm import stream_reply
from prompts import LEVELS, QUICK_ACTIONS, build_system_prompt
from search import search_web

# ---------------- Default settings (change them here, never shown on screen) ----------------
PROVIDER = "gemini"           # "gemini" (online) or "ollama" (offline)
MODEL = "gemini-3.6-flash"    # for ollama use e.g. "llama3.1:8b"
TONE = "Friendly Tutor"       # Friendly Tutor / Strict Examiner / Fun Mode
LEVEL = "School"              # Like I'm 10 / School / College / Expert
DEEP_THINK = False
MAX_HISTORY = 20              # only send the last N messages to the model

st.set_page_config(
    page_title="StudyBuddy - Student AI Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)

# ---------------- Look and feel: dark space theme ----------------
CSS = """
<style>
:root {
  --sb-text: #e8ecff; --sb-muted: #9aa6d6; --sb-accent: #6c8cff; --sb-accent2: #8b5cf6;
  --sb-border: rgba(130,150,255,.24); --sb-glass: rgba(12,18,52,.62);
}
html, body { color-scheme: dark; }

/* Deep black-blue galaxy with subtle stars */
.stApp {
  color: var(--sb-text);
  background-color: #02030a;
  background-image:
    radial-gradient(circle at 20% 30%, rgba(255,255,255,.90) 0, rgba(255,255,255,0) 1.4px),
    radial-gradient(circle at 70% 80%, rgba(200,215,255,.75) 0, rgba(255,255,255,0) 1.2px),
    radial-gradient(circle at 90% 15%, rgba(255,255,255,.90) 0, rgba(255,255,255,0) 1.6px),
    radial-gradient(circle at 10% 70%, rgba(255,255,255,.70) 0, rgba(255,255,255,0) 1.2px),
    radial-gradient(circle at 55% 25%, rgba(190,205,255,.80) 0, rgba(255,255,255,0) 1.4px),
    radial-gradient(circle at 85% 60%, rgba(255,255,255,.65) 0, rgba(255,255,255,0) 1.2px),
    radial-gradient(circle at 35% 55%, rgba(255,255,255,.60) 0, rgba(255,255,255,0) 1.1px),
    radial-gradient(circle at 65% 10%, rgba(255,255,255,.85) 0, rgba(255,255,255,0) 1.5px),
    radial-gradient(circle at 5% 95%, rgba(210,225,255,.70) 0, rgba(255,255,255,0) 1.2px),
    radial-gradient(ellipse 80% 55% at 12% -5%, rgba(58,84,210,.38), transparent 70%),
    radial-gradient(ellipse 70% 50% at 100% 105%, rgba(96,52,190,.28), transparent 70%),
    linear-gradient(180deg, #01020a 0%, #040a22 55%, #071340 100%);
  background-size: 260px 260px, 260px 260px, 260px 260px,
                   340px 340px, 340px 340px, 340px 340px,
                   470px 470px, 470px 470px, 470px 470px,
                   100% 100%, 100% 100%, 100% 100%;
  background-attachment: fixed;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main,
[data-testid="stHeader"] { background: transparent !important; }

/* Hide Streamlit menu, deploy button and footer (the sidebar button stays visible) */
#MainMenu, footer, [data-testid="stToolbarActions"], [data-testid="stMainMenu"],
[data-testid="stAppDeployButton"], .stAppDeployButton, .stDeployButton,
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }

/* History button (top-left): show a 3-line menu icon */
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] { visibility: visible !important; z-index: 1000002; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button { position: relative; }
[data-testid="stExpandSidebarButton"] svg, [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapsedControl"] button svg, [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"],
[data-testid="collapsedControl"] button svg, [data-testid="collapsedControl"] [data-testid="stIconMaterial"] {
  opacity: 0 !important; }
[data-testid="stExpandSidebarButton"]::after, [data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after {
  content: "☰"; position: absolute; inset: 0; display: flex; align-items: center;
  justify-content: center; font-size: 1.5rem; color: #e8ecff; pointer-events: none; }

/* History sidebar */
[data-testid="stSidebar"] { background: rgba(5,8,30,.97) !important;
  border-right: 1px solid var(--sb-border); }
[data-testid="stSidebar"] .stButton button { justify-content: flex-start; text-align: left; }
[data-testid="stSidebar"] .stButton button p { white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.stButton button[data-testid="stBaseButton-primary"] { background: rgba(108,140,255,.28);
  border-color: var(--sb-accent); }
.sb-side-title { font-weight: 700; font-size: 1.05rem; margin: 0 0 .4rem; }

.block-container { max-width: 860px; padding: 2rem 1.2rem 8rem; }

/* Header */
.sb-hero { text-align: center; margin: .3rem 0 1.3rem; }
.sb-logo { font-size: 2.4rem; filter: drop-shadow(0 0 14px rgba(108,140,255,.75)); }
.sb-title { font-size: 2.5rem; font-weight: 800; letter-spacing: -.02em; margin: .1rem 0 .2rem;
  background: linear-gradient(90deg,#ffffff,#9db4ff 55%,#c4a8ff);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.sb-sub { color: var(--sb-muted); font-size: 1rem; max-width: 560px; margin: 0 auto; }

/* Buttons */
.stButton button, .stDownloadButton button {
  background: var(--sb-glass); color: var(--sb-text); border: 1px solid var(--sb-border);
  border-radius: 12px; padding: .5rem .9rem; backdrop-filter: blur(8px);
  transition: all .18s ease; }
.stButton button:hover, .stDownloadButton button:hover {
  color: #fff; border-color: var(--sb-accent); transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(60,90,230,.28); }

/* Panels and inputs */
[data-testid="stExpander"] { background: var(--sb-glass); border: 1px solid var(--sb-border);
  border-radius: 14px; backdrop-filter: blur(8px); }
[data-testid="stExpander"] details { border: none !important; background: transparent !important; }
.stTextInput input, [data-baseweb="select"] > div, [data-baseweb="input"] {
  background: rgba(8,12,40,.72) !important; color: var(--sb-text) !important;
  border-color: var(--sb-border) !important; border-radius: 10px !important; }
[data-testid="stAlert"] { border-radius: 12px; backdrop-filter: blur(6px); }
pre, [data-testid="stCode"] pre { background: rgba(4,8,30,.88) !important;
  border: 1px solid var(--sb-border); border-radius: 10px; }
.stMarkdown table { display: block; overflow-x: auto; }
img { max-width: 100%; }

/* Chat messages: clearly different for You and the AI */
.sb-marker { display: none; }
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .sb-marker),
.element-container:has(> .stMarkdown .sb-marker) { display: none !important; }
[data-testid="stChatMessage"] { border-radius: 18px; padding: .85rem 1.05rem; margin: .55rem 0;
  border: 1px solid rgba(255,255,255,.08); backdrop-filter: blur(8px); }
[data-testid="stChatMessage"]:has(.sb-user) {
  background: linear-gradient(135deg, rgba(79,110,255,.34), rgba(124,77,255,.24));
  border-color: rgba(130,150,255,.42); flex-direction: row-reverse; margin-left: 12%;
  border-bottom-right-radius: 6px; }
[data-testid="stChatMessage"]:has(.sb-ai) {
  background: rgba(255,255,255,.045); border-color: rgba(255,255,255,.11);
  margin-right: 6%; border-bottom-left-radius: 6px;
  box-shadow: inset 3px 0 0 rgba(108,140,255,.55); }

/* Thinking indicator */
.sb-thinking { display: inline-flex; align-items: center; gap: .45rem; color: var(--sb-muted);
  font-style: italic; padding: .2rem 0; }
.sb-thinking .dot { width: 7px; height: 7px; border-radius: 50%; background: #8fa8ff;
  animation: sb-bounce 1.2s infinite ease-in-out both; }
.sb-thinking .dot:nth-child(2) { animation-delay: .15s; }
.sb-thinking .dot:nth-child(3) { animation-delay: .30s; }
@keyframes sb-bounce { 0%,80%,100% { transform: scale(.5); opacity: .4; }
                       40% { transform: scale(1); opacity: 1; } }

/* Input box and send button */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {
  background: transparent !important; }
[data-testid="stBottom"] { background: linear-gradient(180deg, transparent, rgba(2,3,10,.88) 45%) !important; }
[data-testid="stChatInput"] { background: rgba(10,16,48,.88); border: 1px solid rgba(120,140,255,.40);
  border-radius: 28px; box-shadow: 0 8px 30px rgba(0,0,0,.5), 0 0 24px rgba(70,100,255,.14);
  transition: border-color .2s, box-shadow .2s; }
[data-testid="stChatInput"]:focus-within { border-color: #7d9bff;
  box-shadow: 0 0 0 3px rgba(108,140,255,.24), 0 8px 30px rgba(0,0,0,.5); }
[data-testid="stChatInput"] > div { background: transparent !important; border: none !important; }
[data-testid="stChatInput"] textarea { background: transparent !important; color: var(--sb-text) !important;
  caret-color: #9db4ff; font-size: 1rem; }
[data-testid="stChatInput"] textarea::placeholder { color: rgba(170,185,235,.62); }
[data-testid="stChatInput"] button { border-radius: 50% !important; }
[data-testid="stChatInputSubmitButton"] { background: linear-gradient(135deg,#5b7cff,#8b5cf6) !important;
  color: #fff !important; box-shadow: 0 4px 14px rgba(91,124,255,.45); }
[data-testid="stChatInputSubmitButton"]:disabled { opacity: .45; box-shadow: none; }

/* Mobile */
@media (max-width: 640px) {
  .block-container { padding: 1.2rem .7rem 8rem; }
  .sb-title { font-size: 1.85rem; } .sb-sub { font-size: .92rem; }
  [data-testid="stChatMessage"]:has(.sb-user) { margin-left: 4%; }
  [data-testid="stChatMessage"]:has(.sb-ai) { margin-right: 0; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: .5rem !important; }
  [data-testid="stColumn"], [data-testid="column"] {
    min-width: calc(50% - .5rem) !important; flex: 1 1 calc(50% - .5rem) !important; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

USER_MARK = '<span class="sb-marker sb-user"></span>'
AI_MARK = '<span class="sb-marker sb-ai"></span>'


def mark(role: str):
    st.markdown(USER_MARK if role == "user" else AI_MARK, unsafe_allow_html=True)


def thinking_html(label: str) -> str:
    return ('<div class="sb-thinking"><span class="dot"></span><span class="dot"></span>'
            f'<span class="dot"></span><span>{label}…</span></div>')


# ---------------- Errors: details go to the CMD window, never to the page ----------------
SAFE_PREFIXES = ("The AI did not", "The AI returned", "The assistant is not", "Google could not")


def friendly_error(e: Exception) -> str:
    print("\n[StudyBuddy] An error occurred (shown here only, never on the web page):",
          file=sys.stderr)
    traceback.print_exception(type(e), e, e.__traceback__)
    msg = str(e)
    if isinstance(e, ValueError) and msg.startswith(SAFE_PREFIXES):
        return msg
    low = msg.lower()
    if any(k in low for k in ("429", "quota", "resource_exhausted", "rate limit")):
        return "Too many requests right now. Please wait a minute and try again."
    if any(k in low for k in ("api key", "api_key", "401", "403", "permission", "unauthenticated")):
        return "The assistant is not available right now. Please try again later."
    if any(k in low for k in ("404", "not_found", "no longer available")):
        return "The assistant is temporarily unavailable. Please try again later."
    if any(k in low for k in ("timeout", "timed out", "connect", "getaddrinfo", "network",
                              "503", "unavailable", "overloaded")):
        return "I couldn't reach the AI service. Please check your internet and try again."
    return "Something went wrong. Please try again."


def get_key() -> str:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.environ.get("GEMINI_API_KEY", "")


api_key = get_key()

# ---------------- Session state ----------------
ss = st.session_state
if not ss.get("db_ready"):  # set up the history database once, not on every click
    db.init()
    ss.db_ready = True
ss.setdefault("messages", [])      # chat shown on screen
ss.setdefault("attachments", [])   # files attached to this chat
ss.setdefault("chat_id", None)     # id in the saved-history database
ss.setdefault("queued", None)      # prompt from a quick-action button
ss.setdefault("last_audio", None)  # to avoid answering the same voice note twice
ss.setdefault("generated", None)   # last PPT / PDF / Word file made


def last_answer() -> str:
    for m in reversed(ss.messages):
        if m["role"] == "assistant":
            return m["content"]
    return ""


def reset_chat():
    ss.messages, ss.attachments, ss.chat_id, ss.generated = [], [], None, None


def open_chat(cid):
    reset_chat()
    ss.chat_id = cid
    ss.messages = [{"role": r, "content": c} for r, c in db.load_messages(cid)]


def delete_current_chat():
    if ss.chat_id is not None:
        db.delete_chat(ss.chat_id)
    reset_chat()


def render_message(m):
    with st.chat_message(m["role"]):
        mark(m["role"])
        for f in m.get("files", []):
            if f["kind"] == "image" and f.get("data"):
                st.image(f["data"], width=260)
            else:
                st.caption(f"📎 {f['name']}")
        st.markdown(m["content"])


# ---------------- Sidebar: chat history (open it with the 3-line button, top-left) ----------------
with st.sidebar:
    st.markdown('<div class="sb-side-title">🎓 StudyBuddy</div>', unsafe_allow_html=True)
    st.button("➕ New chat", use_container_width=True, on_click=reset_chat, key="new_chat")
    st.caption("Chat history")
    saved_chats = db.list_chats(50)
    if not saved_chats:
        st.caption("No saved chats yet. Your chats will appear here.")
    for cid, title in saved_chats:
        st.button("💬 " + title, key=f"chat_{cid}", use_container_width=True,
                  type="primary" if cid == ss.chat_id else "secondary",
                  on_click=open_chat, args=(cid,))
    if ss.chat_id is not None:
        st.button("🗑️ Delete this chat", use_container_width=True,
                  on_click=delete_current_chat, key="del_chat")


# ---------------- Header ----------------
st.markdown(
    '<div class="sb-hero"><div class="sb-logo">🎓</div><div class="sb-title">StudyBuddy</div>'
    '<div class="sb-sub">Your free AI study assistant. Ask anything, attach files, '
    'and turn answers into slides, PDFs and notes.</div></div>',
    unsafe_allow_html=True,
)

if PROVIDER == "gemini" and not api_key:
    if not ss.get("warned_key"):
        print("[StudyBuddy] GEMINI_API_KEY is missing. Add it to .streamlit/secrets.toml",
              file=sys.stderr)
        ss.warned_key = True
    st.error("The assistant is not available right now. Please try again later.")
    st.stop()

# Quick study tools
cols = st.columns(len(QUICK_ACTIONS))
for col, (label, text) in zip(cols, QUICK_ACTIONS.items()):
    if col.button(label, use_container_width=True):
        ss.queued = text

use_web = st.toggle("🌐 Search the web for my questions (current information)")

# ---------------- Tools panels ----------------
with st.expander("📄 Create a PPT / PDF / Word file"):
    source = st.radio("Make it from",
                      ["A topic I type", "My last chat answer", "My attached files"],
                      horizontal=True)
    topic = st.text_input("Topic", placeholder="e.g. Photosynthesis") \
        if source == "A topic I type" else ""
    c1, c2 = st.columns(2)
    fmt = c1.selectbox("Format", list(FORMATS))
    n_sections = c2.slider("Slides / sections", 3, 12, 6)
    if fmt.startswith("PDF"):
        st.caption("PDF supports English letters only. Use PowerPoint or Word for other languages.")

    if st.button("✨ Create file"):
        problem = None
        if source == "A topic I type" and not topic.strip():
            problem = "Please type a topic first."
        elif source == "My last chat answer" and not last_answer():
            problem = "There is no chat answer yet. Ask something first."
        elif source == "My attached files" and not ss.attachments:
            problem = "No files attached yet. Use the + button in the chat box."
        if problem:
            st.warning(problem)
        else:
            kind = {"A topic I type": "topic", "My last chat answer": "answer"}.get(source, "files")
            text = topic.strip() if kind == "topic" else last_answer()
            with st.spinner("Creating your file... this can take up to a minute"):
                try:
                    data = generate_document(
                        PROVIDER, MODEL, api_key, kind, text, n_sections,
                        LEVELS[LEVEL], ss.attachments if kind == "files" else None)
                    builder, ext, mime = FORMATS[fmt]
                    ss.generated = {"name": f"{safe_name(data['title'])}.{ext}",
                                    "bytes": builder(data), "mime": mime}
                except Exception as e:
                    ss.generated = None
                    st.error(friendly_error(e))

    if ss.generated:
        st.success("Your file is ready.")
        st.download_button("⬇️ Download " + ss.generated["name"], ss.generated["bytes"],
                           file_name=ss.generated["name"], mime=ss.generated["mime"])

with st.expander("🎤 Ask by voice"):
    audio = st.audio_input("Record your question") if hasattr(st, "audio_input") else None
    if not hasattr(st, "audio_input") or PROVIDER != "gemini":
        st.caption("Voice input is not available right now.")

if ss.attachments:
    st.caption("📎 Attached to this chat: " + ", ".join(a["name"] for a in ss.attachments))
    if PROVIDER == "ollama" and any(not a["text"] for a in ss.attachments):
        st.warning("Offline mode can read text, PDF, Word and PPT files only. "
                   "Images, audio and video need the online engine.")
    if st.button("Remove attachments"):
        ss.attachments = []
        st.rerun()

# ---------------- New input ----------------
value = st.chat_input("Ask StudyBuddy anything...", accept_file="multiple", file_type=ALLOWED_TYPES)
typed, new_files = "", []
if isinstance(value, str):
    typed = value.strip()
elif value:
    typed = (value["text"] or "").strip()
    new_files = list(value["files"] or [])

# Voice note (only the first time we see a new recording)
voice_att = []
if audio is not None:
    data = audio.getvalue()
    digest = hashlib.md5(data).hexdigest()
    if digest != ss.last_audio:
        ss.last_audio = digest
        if PROVIDER == "gemini":
            voice_att = [make_attachment("voice.wav", data)]

queued, ss.queued = ss.queued, None

prompt = typed or None
shown_files = []
for f in new_files:
    att = make_attachment(f.name, f.getvalue(), read_pdf_text=(PROVIDER == "ollama"))
    if not any(a["name"] == att["name"] and len(a["data"]) == len(att["data"])
               for a in ss.attachments):
        ss.attachments.append(att)
    shown_files.append({"name": att["name"], "kind": att["kind"],
                        "data": att["data"] if att["kind"] == "image" else None})
if not prompt and new_files:
    prompt = "Please explain the attached file(s) and tell me the key points."
if not prompt and voice_att:
    prompt = ("🎤 Voice question: first write what I said in one short line, "
              "then answer it.")
if not prompt and queued:
    prompt = queued

if prompt:
    ss.messages.append({"role": "user", "content": prompt, "files": shown_files})

# ---------------- Chat: ONE container, every message drawn the same way ----------------
answered = False
chat_area = st.container()
with chat_area:
    for m in ss.messages:
        render_message(m)

    if prompt:
        with st.chat_message("assistant"):
            mark("assistant")
            holder = st.empty()  # the "Thinking..." indicator lives here until the first words arrive
            busy = "Reading your files" if (ss.attachments or voice_att) else "Thinking"
            holder.markdown(thinking_html(busy), unsafe_allow_html=True)
            try:
                system = build_system_prompt(TONE, LEVEL, DEEP_THINK)
                sources = []
                if use_web and typed:
                    holder.markdown(thinking_html("Searching the web"), unsafe_allow_html=True)
                    sources = search_web(typed)
                    if sources:
                        system += ("\n\nWeb search results (reference only, may be incomplete or wrong; "
                                   "mention the source name when you use them):\n" + "\n".join(
                                       f"- {r['title']}: {r['snippet']} ({r['url']})" for r in sources))
                    holder.markdown(thinking_html(busy), unsafe_allow_html=True)

                history = [{"role": m["role"], "content": m["content"]}
                           for m in ss.messages[-MAX_HISTORY:]]
                stream = stream_reply(PROVIDER, history, system, MODEL, api_key,
                                      ss.attachments + voice_att)
                first = next(stream, "")  # waits for the first words (file uploads happen here)
                holder.empty()

                def pieces():
                    yield first
                    yield from stream

                reply = st.write_stream(pieces())
                if not reply.strip():
                    raise ValueError("The AI did not return an answer. Please try rephrasing your question.")
                if sources:
                    src = "\n\n**Sources:**\n" + "\n".join(
                        f"- [{r['title']}]({r['url']})" for r in sources if r["url"])
                    st.markdown(src)
                    reply += src
                ss.messages.append({"role": "assistant", "content": reply})

                try:  # saving history must never break the chat
                    if ss.chat_id is None:
                        ss.chat_id = db.new_chat(prompt)
                    db.add_message(ss.chat_id, "user", prompt)
                    db.add_message(ss.chat_id, "assistant", reply)
                except Exception:
                    traceback.print_exc()
                answered = True
            except Exception as e:
                holder.empty()
                st.error(friendly_error(e))
                ss.messages.pop()  # remove the unanswered question

# After a good answer, redraw once from saved messages so old answers stay put
# and the new chat shows up in the sidebar history.
if answered:
    st.rerun()
