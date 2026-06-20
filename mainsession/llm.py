import random
import time
from groq import Groq
import os

from .utils import load_history, save_history, trim_history

# Initialize Groq client (using same API key as STT)
GROQ_API_KEY = ""
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

FALLBACK_QUESTIONS = [
    "What's your favorite thing to eat right now?",
    "Can you tell me one food you tried that was tasty?",
    "Do you like crunchy or soft foods more?",
    "What color is your favorite snack?",
    "If you could eat any yummy thing tonight, what would it be?",
]


def _extract_reply_text(completion) -> str:
    try:
        content = completion.choices[0].message.content
        if content is None:
            return ""
        if isinstance(content, str):
            return content.strip()
        return str(content).strip()
    except Exception:
        return ""


def _chat_completion(messages, model: str, max_tokens: int, temperature: float = 0.85) -> str:
    if client is None:
        print("ERROR: Groq client not initialized. Check GROQ_API_KEY.")
        return random.choice(FALLBACK_QUESTIONS)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=temperature,
            top_p=1,
        )
        reply = _extract_reply_text(completion)
        if reply:
            return reply
    except Exception as e:
        print(f"LLM error: {e}")
        import traceback
        traceback.print_exc()

    return ""


def get_direct_response(prompt: str, model: str = "openai/gpt-oss-120b", max_tokens: int = 512) -> str:
    messages = [{"role": "user", "content": prompt}]
    reply = _chat_completion(messages, model=model, max_tokens=max_tokens, temperature=0.3)
    if reply:
        return reply
    return random.choice(FALLBACK_QUESTIONS)

def get_kabu_response(prompt: str, model: str = "openai/gpt-oss-120b", max_tokens: int = 512) -> str:
    messages = load_history()
    # ensure system message present
    if not messages:
        messages = [{"role": "system", "content": "You are Kabu, a helpful assistant."}]

    messages.append({"role": "user", "content": prompt})
    messages = trim_history(messages)

    reply = _chat_completion(messages, model=model, max_tokens=max_tokens, temperature=0.85)
    if not reply:
        reply = random.choice(FALLBACK_QUESTIONS)

    messages.append({"role": "assistant", "content": reply})
    save_history(messages)
    return reply
