import os

# Audio / recording
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
DURATION = float(os.getenv("DURATION", "10"))
PROCESS_TIMEOUT = float(os.getenv("PROCESS_TIMEOUT", "3.0"))

# Camera
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# Conversation/history
HISTORY_FILE = os.getenv("HISTORY_FILE", "conversation_history.json")

# LLM / API keys (do not hardcode keys in source)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
