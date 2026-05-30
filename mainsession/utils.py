import json
import os
import re
import cv2
import time
from typing import Dict, List, Any
from typing import List
from .config import HISTORY_FILE
from datetime import datetime, timezone, date
from kivy.logger import Logger


def load_history(path: str = HISTORY_FILE) -> List[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # default system message placeholder; main program will set proper system message
        return []


def save_history(messages: List[dict], path: str = HISTORY_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# --- Topic memory helpers (compact topic-only memory) ---
TOPICS_FILE = os.path.join(os.path.dirname(__file__), "topic_memory.json")
DEFAULT_TOPIC_COUNT = 3
MAX_TOPIC_COUNT = 5


def load_topic_memory() -> dict:
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    # Ensure proper structure
    if "current_active_topic" not in data:
        data["current_active_topic"] = None
    if "avoided_topics" not in data:
        data["avoided_topics"] = {}
    return data


def save_topic_memory(mem: dict) -> None:
    try:
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def reset_topic_memory() -> None:
    """Reset the topic memory file to the default empty structure."""
    mem = {"current_active_topic": None, "avoided_topics": {}}
    try:
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
    except Exception:
        # fallback: try save_topic_memory
        try:
            save_topic_memory(mem)
        except Exception:
            pass


def switch_topic(new_topic: str) -> bool:
    """Switch to a new topic, marking the old one as avoided. Returns True if switched."""
    if not new_topic:
        return False
    new_lower = str(new_topic).strip().lower()
    mem = load_topic_memory()
    current = mem.get("current_active_topic")
    
    # If same topic, just reset countdown and return False (no switch)
    if current and is_same_topic(current, new_lower):
        mem["current_active_topic"] = new_lower
        mem["avoided_topics"][new_lower] = DEFAULT_TOPIC_COUNT
        save_topic_memory(mem)
        return False
    
    # Different topic: mark old as avoided, activate new
    if current:
        mem["avoided_topics"][current] = 0  # Mark old as AVOID
    
    mem["current_active_topic"] = new_lower
    mem["avoided_topics"][new_lower] = DEFAULT_TOPIC_COUNT
    save_topic_memory(mem)
    return True


def is_same_topic(topic1: str, topic2: str) -> bool:
    """Check if two topics are the same (case-insensitive)."""
    if not topic1 or not topic2:
        return False
    return str(topic1).strip().lower() == str(topic2).strip().lower()


def get_current_active_topic() -> str | None:
    """Get the currently active topic."""
    mem = load_topic_memory()
    return mem.get("current_active_topic")


def update_topic_on_reply(topic: str, set_to: int | None = None) -> None:
    """Register a topic mentioned by Kabu. If different from current active, switch to it."""
    if not topic:
        return
    switched = switch_topic(topic)
    if switched:
        Logger.info("🔄 Topic switched to: %s", topic)


def increment_topic_on_user_mention(topic: str, amount: int = 1) -> None:
    """User mentioned a topic. If it's current active, keep it. If different, switch to it."""
    if not topic:
        return
    t = str(topic).strip().lower()
    mem = load_topic_memory()
    current = mem.get("current_active_topic")
    
    if is_same_topic(current, t):
        # Same topic: reset countdown slightly
        mem["avoided_topics"][t] = max(mem["avoided_topics"].get(t, 0), 2)
    else:
        # Different topic: switch
        if current:
            mem["avoided_topics"][current] = 0
        mem["current_active_topic"] = t
        mem["avoided_topics"][t] = DEFAULT_TOPIC_COUNT
    
    save_topic_memory(mem)


def decrement_topic_counts() -> None:
    """Decrement the active topic countdown. When it reaches 0, mark for topic suggestion."""
    mem = load_topic_memory()
    current = mem.get("current_active_topic")
    
    if current and mem.get("avoided_topics", {}).get(current, 0) > 0:
        mem["avoided_topics"][current] = max(0, mem["avoided_topics"][current] - 1)
        if mem["avoided_topics"][current] == 0:
            Logger.info("⏰ Topic '%s' expired (countdown reached 0)", current)
        save_topic_memory(mem)


def get_topic_system_message() -> str:
    """Build a system hint about current topic status and avoided topics."""
    mem = load_topic_memory()
    current = mem.get("current_active_topic")
    avoided = mem.get("avoided_topics", {})
    
    parts = []
    
    # Check if current topic is at 0 (expired)
    if current and avoided.get(current, 1) == 0:
        parts.append(f"The child seems to have moved past the topic of '{current}'. Gently suggest moving to a different, more engaging topic.")
    
    # List avoided topics (countdown at 0)
    avoided_list = [k for k, v in avoided.items() if v == 0 and k != current]
    if avoided_list:
        parts.append("Soft-avoid these finished topics: " + ", ".join(avoided_list) + ".")
    
    return " ".join(parts)


def trim_history(messages: List[dict], char_limit: int = 6000) -> List[dict]:
    if not messages:
        return messages
    system = messages[0]
    rest = messages[1:]
    while sum(len(m.get("content", "")) for m in [system] + rest) > char_limit and rest:
        rest.pop(0)
    return [system] + rest


def reset_history(path: str = HISTORY_FILE, system_message: dict | None = None) -> None:
    if system_message is None:
        system_message = {"role": "system", "content": "Kabu system message"}
    save_history([system_message], path)


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_kabu_reply(raw: str) -> Dict[str, Any]:
    if not raw:
        return {"text": "", "emotions": [], "topic": None, "raw": raw}

    s = raw.replace("\r\n", "\n").strip()

    # find emotion block
    em_match = re.search(r'Kabu_emotion\s*:\s*\[([^\]]*)\]', s, re.IGNORECASE)
    emotions: List[str] = []
    if em_match:
        emotions = [e.strip() for e in em_match.group(1).split(',') if e.strip()]

    # find topic block (if present)
    topic = None
    t_match = re.search(r'Topic\s*Mentioned\s*:\s*(.+)', s, re.IGNORECASE)
    if t_match:
        topic_raw = t_match.group(1).strip()
        topic = topic_raw.splitlines()[0].strip().strip('.') if topic_raw else None
        s = re.sub(r'Topic\s*Mentioned\s*:\s*.+$', '', s, flags=re.IGNORECASE).strip()

    # find the last "Kabu:" label and take the text after it up to the emotion block (if any)
    kabu_iter = list(re.finditer(r'Kabu\s*:\s*', s, re.IGNORECASE))
    if kabu_iter:
        last = kabu_iter[-1]
        start = last.end()
        end = em_match.start() if em_match else len(s)
        text = s[start:end].strip()
    else:
        # fallback: everything before the emotion block or whole string
        text = s[: em_match.start()].strip() if em_match else s

    # remove any accidental leading "Kabu:" left in the extracted text
    text = re.sub(r'^\s*Kabu\s*:\s*', '', text, flags=re.IGNORECASE).strip()

    return {"text": text, "emotions": emotions, "topic": (topic.lower() if topic else None), "raw": raw}

def parse_kabu_reply_final(text: str) -> Dict[str, Any]:
    if not text:
        return {
            "recommendations": [],
            "disliked_foods": {},
            "recommendation_line": "",
            "alternative_line": "",
            "raw": text,
        }

    norm = text.replace("\r\n", "\n").strip()

    # Locate sections
    rec_match = re.search(
        r"Conversation Recommendations:\s*(.*?)(?:\n\s*Disliked Foods:|\Z)",
        norm,
        re.DOTALL | re.IGNORECASE,
    )
    dis_match = re.search(r"Disliked Foods:\s*(.*)$", norm, re.DOTALL | re.IGNORECASE)

    rec_text = rec_match.group(1).strip() if rec_match else ""
    dis_text = dis_match.group(1).strip() if dis_match else ""

    # Parse recommendations
    recommendations: List[str] = []
    if rec_text:
        for line in rec_text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(
                r"^(Recommendation\s*\d+\s*:|\d+\s*[\).\-\:]\s*|-)\s*",
                "",
                line,
                flags=re.IGNORECASE,
            )
            if line:
                recommendations.append(line)
    if not recommendations and rec_text:
        recommendations = [ln.strip() for ln in rec_text.splitlines() if ln.strip()]

    # Parse disliked foods -> alternatives (avoid splitting on commas inside parentheses)
    disliked_foods: Dict[str, List[str]] = {}
    if dis_text:
        lines = [ln.strip() for ln in dis_text.splitlines() if ln.strip()]
        if len(lines) == 1 and re.search(r"[;,|]", lines[0]):
            lines = re.split(r"[;|]", lines[0])

        for line in lines:
            m = re.match(r"^(?P<food>[^:]+)\s*:\s*(?P<alts>.+)$", line)
            if m:
                food = m.group("food").strip()
                alts_raw = m.group("alts").strip()
                # Prefer splitting by semicolon, pipe, " - ", or " or ". If none present, keep full RHS intact
                if re.search(r";|\||\s-\s|\bor\b", alts_raw):
                    alts = [a.strip() for a in re.split(r";|\||\s-\s|\bor\b", alts_raw) if a.strip()]
                else:
                    # keep the whole RHS as one alternative (preserves commas in descriptions)
                    alts = [alts_raw]
                disliked_foods[food] = alts
            else:
                disliked_foods[line] = []

    # Build requested formatted lines
    recommendation_line = ""
    if recommendations:
        recommendation_line = "Recommendation: " + ", ".join(recommendations)

    alternative_entries = []
    for food, alts in disliked_foods.items():
        if alts:
            # join multiple alternatives for this food with " | " to keep descriptions readable
            alts_joined = " | ".join(alts)
            alternative_entries.append(f"{food}: {alts_joined}")
        else:
            alternative_entries.append(f"{food}: (no alternatives provided)")

    alternative_line = ""
    if alternative_entries:
        alternative_line = "Alternative: " + " , ".join(alternative_entries)

    return {
        "recommendations": recommendations,
        "disliked_foods": disliked_foods,
        "recommendation_line": recommendation_line,
        "alternative_line": alternative_line,
        "raw": text,
    }


def time_format(start_dt):
    time_now = datetime.now(timezone.utc) - start_dt
    total = int(time_now.total_seconds())
    minutes = total // 60
    seconds = total % 60
    return f"{minutes:02d}:{seconds:02d}"

def compute_age_from(value) -> int:
    if isinstance(value, str):
        value = datetime.strptime(value, "%m/%d/%Y").date()
    if not isinstance(value, date):
        raise TypeError("expected datetime.date or MM/DD/YYYY string")
    today = datetime.now().date()
    years = today.year - value.year
    if (today.month, today.day) < (value.month, value.day):
        years -= 1
    return years


def extract_topic_robust(raw_text: str) -> str | None:
    """
    Robustly extract topic from LLM response.
    Tries multiple patterns to find the topic without verbose logging.
    """
    if not raw_text:
        return None
    
    s = raw_text.replace("\r\n", "\n").strip()
    
    # Pattern 1: Look for "Topic Mentioned:" format (original)
    t_match = re.search(r'Topic\s*Mentioned\s*:\s*(.+)', s, re.IGNORECASE)
    if t_match:
        topic_raw = t_match.group(1).strip()
        topic = topic_raw.splitlines()[0].strip().strip('.') if topic_raw else None
        return topic.lower() if topic else None
    
    # Pattern 2: Look for "Topic:" format
    t_match = re.search(r'^Topic\s*:\s*(.+)$', s, re.IGNORECASE | re.MULTILINE)
    if t_match:
        topic = t_match.group(1).strip().strip('.,')
        return topic.lower() if topic else None
    
    # Pattern 3: Look for "Topic about:" or "Talking about:"
    t_match = re.search(r'(?:topic|talking|discussing)\s+(?:about|is)\s*:\s*(.+)', s, re.IGNORECASE)
    if t_match:
        topic = t_match.group(1).strip().strip('.,')
        return topic.lower() if topic else None
    
    # Pattern 4: Look for JSON-like format {"topic": "..."}
    json_match = re.search(r'"topic"\s*:\s*"([^"]+)"', s, re.IGNORECASE)
    if json_match:
        topic = json_match.group(1).strip()
        return topic.lower() if topic else None
    
    # Pattern 5: Look for "[food|topic]" format (brackets)
    bracket_match = re.search(r'\[(?:food|topic):\s*([^\]]+)\]', s, re.IGNORECASE)
    if bracket_match:
        topic = bracket_match.group(1).strip()
        return topic.lower() if topic else None
    
    # Pattern 6: Look for any "mentioned" text
    mentioned_match = re.search(r'(?:mentioned|discussed|about|regarding)\s+([a-zA-Z\s]+?)(?:\.|,|;|$)', s, re.IGNORECASE)
    if mentioned_match:
        topic = mentioned_match.group(1).strip()
        if len(topic) < 50:  # Sanity check - topic shouldn't be a whole sentence
            return topic.lower() if topic else None
    
    # Pattern 7: Extract between common markers
    cap_match = re.search(r"(?:about|discussing|eating)\s+'([^']+)'", s, re.IGNORECASE)
    if cap_match:
        topic = cap_match.group(1).strip()
        return topic.lower() if topic else None
    
    return None