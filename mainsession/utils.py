import json
import os
import re
import cv2
import time
from typing import Dict, List, Any
from typing import List
from config import HISTORY_FILE
from datetime import datetime, timezone, date


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
        return {"text": "", "emotions": [], "raw": raw}

    s = raw.replace("\r\n", "\n").strip()

    # find emotion block
    em_match = re.search(r'Kabu_emotion\s*:\s*\[([^\]]*)\]', s, re.IGNORECASE)
    emotions: List[str] = []
    if em_match:
        emotions = [e.strip() for e in em_match.group(1).split(',') if e.strip()]

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

    return {"text": text, "emotions": emotions, "raw": raw}

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