import re


_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def detect_language(text: str) -> str:
    if _CYRILLIC_RE.search(text):
        return "ru"
    return "en"