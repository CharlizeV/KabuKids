import random
import time
import ollama

from utils import load_history, save_history, trim_history

FALLBACK_QUESTIONS = [
    "What's your favorite thing to eat right now?",
    "Can you tell me one food you tried that was tasty?",
    "Do you like crunchy or soft foods more?",
    "What color is your favorite snack?",
    "If you could eat any yummy thing tonight, what would it be?",
]

def get_kabu_response(prompt: str) -> str:
    messages = load_history()
    # ensure system message present
    if not messages:
        messages = [{"role": "system", "content": "You are Kabu, a helpful assistant."}]

    messages.append({"role": "user", "content": prompt})
    messages = trim_history(messages)

    ollama_msgs = [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        response = ollama.chat(
            model='qwen2.5:7b',
            messages=ollama_msgs,
            options={'temperature': 0.85, 'num_predict': 256}
        )
        reply = response['message']['content'].strip()
    except Exception as e:
        print("LLM error:", e)
        reply = random.choice(FALLBACK_QUESTIONS)

    messages.append({"role": "assistant", "content": reply})
    save_history(messages)
    return reply
