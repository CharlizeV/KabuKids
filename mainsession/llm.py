import random
import time
from groq import Groq
import os

from .utils import load_history, save_history, trim_history

# Initialize Groq client (using same API key as STT)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or ""
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

FALLBACK_QUESTIONS = [
    "What's your favorite thing to eat right now?",
    "Can you tell me one food you tried that was tasty?",
    "Do you like crunchy or soft foods more?",
    "What color is your favorite snack?",
    "If you could eat any yummy thing tonight, what would it be?",
]

def get_kabu_response(prompt: str, model: str = "openai/gpt-oss-120b", max_tokens: int = 512) -> str:
    if client is None:
        print("ERROR: Groq client not initialized. Check GROQ_API_KEY.")
        return random.choice(FALLBACK_QUESTIONS)
    
    messages = load_history()
    # ensure system message present
    if not messages:
        messages = [{"role": "system", "content": "You are Kabu, a helpful assistant."}]

    messages.append({"role": "user", "content": prompt})
    messages = trim_history(messages)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=max_tokens,
            temperature=0.85,
            top_p=1,
        )
        reply = completion.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"LLM error: {e}")
        import traceback
        traceback.print_exc()
        reply = random.choice(FALLBACK_QUESTIONS)

    messages.append({"role": "assistant", "content": reply})
    save_history(messages)
    return reply
