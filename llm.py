"""One function, two engines. Swap the AI brain without touching the UI."""
import io
import time
from typing import Iterator

INLINE_LIMIT = 3 * 1024 * 1024  # bigger files are uploaded once (Files API) and reused

_CLIENTS = {}  # one reusable connection per key = faster replies


def _get_client(api_key):
    from google import genai
    if api_key not in _CLIENTS:
        _CLIENTS[api_key] = genai.Client(api_key=api_key)
    return _CLIENTS[api_key]


def _gemini_part(client, types, att):
    """Convert one attachment into a Gemini 'part'."""
    kind = att["kind"]
    if kind == "text":
        return types.Part(text=f"[Attached file: {att['name']}]\n{att['text']}")

    too_big = len(att["data"]) > INLINE_LIMIT
    if kind == "video" or too_big:
        if not att.get("ref"):  # upload once, then reuse
            f = client.files.upload(
                file=io.BytesIO(att["data"]),
                config=types.UploadFileConfig(mime_type=att["mime"], display_name=att["name"]),
            )
            while f.state is not None and f.state.name == "PROCESSING":
                time.sleep(1)
                f = client.files.get(name=f.name)
            if f.state is not None and f.state.name == "FAILED":
                raise ValueError(f"Google could not process the file '{att['name']}'. Please try a different file.")
            att["ref"] = (f.uri, f.mime_type or att["mime"])
        uri, mime = att["ref"]
        return types.Part.from_uri(file_uri=uri, mime_type=mime)

    return types.Part.from_bytes(data=att["data"], mime_type=att["mime"])


def _stream_gemini(messages, system, model, api_key, attachments) -> Iterator[str]:
    from google.genai import types

    client = _get_client(api_key)
    last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
    contents = []
    for i, m in enumerate(messages):
        parts = []
        if i == last_user and attachments:
            parts += [_gemini_part(client, types, a) for a in attachments]
        parts.append(types.Part(text=m["content"]))
        contents.append(types.Content(
            role="user" if m["role"] == "user" else "model", parts=parts))

    config = types.GenerateContentConfig(system_instruction=system)
    for chunk in client.models.generate_content_stream(
        model=model, contents=contents, config=config
    ):
        if chunk.text:
            yield chunk.text


def _stream_ollama(messages, system, model, attachments) -> Iterator[str]:
    import ollama

    docs = [f"[Attached file: {a['name']}]\n{a['text']}" for a in attachments if a["text"]]
    skipped = [a["name"] for a in attachments if not a["text"]]
    system2 = system
    if docs:
        system2 += "\n\nThe student attached these files:\n\n" + "\n\n".join(docs)
    if skipped:
        system2 += ("\n\nThese files cannot be read in offline mode: "
                    + ", ".join(skipped) + ". Tell the student if they matter.")
    msgs = [{"role": "system", "content": system2}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]
    for chunk in ollama.chat(model=model, messages=msgs, stream=True,
                             options={"num_ctx": 8192}):
        yield chunk["message"]["content"]


def stream_reply(provider, messages, system, model, api_key=None,
                 attachments=None) -> Iterator[str]:
    """Yield the reply piece by piece so the UI can show it as it is written."""
    attachments = attachments or []
    if provider == "gemini":
        if not api_key:
            raise ValueError("The assistant is not configured yet.")
        return _stream_gemini(messages, system, model, api_key, attachments)
    if provider == "ollama":
        return _stream_ollama(messages, system, model, attachments)
    raise ValueError(f"Unknown provider: {provider}")


def generate_text(provider, prompt, system, model, api_key=None, attachments=None) -> str:
    """Get a complete answer in one piece (used for making PPT / PDF / Word files)."""
    messages = [{"role": "user", "content": prompt}]
    return "".join(stream_reply(provider, messages, system, model, api_key, attachments))
