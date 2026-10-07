import re

_DEVANAGARI = re.compile(r"[\u0900-\u097f]")
_BENGALI = re.compile(r"[\u0980-\u09ff]")
_NEPALI_LATIN = re.compile(r"\b(cha|chha|chhu|chhau|garna|garchu|malai|tapai|k xa|ke cha)\b", re.I)
_HINDI_LATIN = re.compile(r"\b(hai|hain|hoon|kya|kaise|mera|mujhe|nahi)\b", re.I)
_MAITHILI_LATIN = re.compile(r"\b(achi|chhi|hamra|tohar|ahank|ki haal)\b", re.I)
_NEPALI_SCRIPT = re.compile(r"(छु|छन्|होइन|मलाई|तपाईं|गर्नु)")
_HINDI_SCRIPT = re.compile(r"(हूँ|हैं|है|नहीं|मुझे|आपको|क्या)")


def detect_language(text: str) -> str:
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if _BENGALI.search(text):
        return "Bengali or Maithili; preserve the user's script and wording"
    if _DEVANAGARI.search(text):
        if has_latin:
            return "Hindi/Nepali code-switch; follow the user's own mix"
        return "Hindi or Nepali in Devanagari; infer from context and match the user"
    if _MAITHILI_LATIN.search(text):
        return "Maithili, with natural code-switching if the user does so"
    if _NEPALI_LATIN.search(text):
        return "Romanized Nepali, with natural English code-switching if present"
    if _HINDI_LATIN.search(text):
        return "Romanized Hindi, with natural English code-switching if present"
    if has_latin:
        return "English unless the conversation context clearly indicates otherwise"
    return "the language and script used in the current conversation"


def control_language(text: str) -> str:
    """Choose a best-effort language for fixed control-command acknowledgements."""
    if _BENGALI.search(text):
        return "other"
    if _NEPALI_LATIN.search(text):
        return "nepali_latin"
    if _HINDI_LATIN.search(text):
        return "hindi_latin"
    if _MAITHILI_LATIN.search(text):
        return "maithili_latin"
    if _DEVANAGARI.search(text):
        if _NEPALI_SCRIPT.search(text):
            return "nepali"
        if _HINDI_SCRIPT.search(text):
            return "hindi"
        return "nepali"
    return "english"
