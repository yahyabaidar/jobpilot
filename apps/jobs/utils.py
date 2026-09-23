import re
import unicodedata
from datetime import UTC, datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.utils.dateparse import parse_datetime

DISALLOWED_DOMAINS = {"linkedin.com", "rekrute.com", "indeed.com", "indeed.fr"}

_STOPWORDS = {
    "fr": {
        "le",
        "la",
        "les",
        "des",
        "une",
        "un",
        "et",
        "pour",
        "dans",
        "avec",
        "vous",
        "nous",
        "notre",
        "votre",
        "est",
        "sont",
        "de",
        "du",
        "en",
        "au",
        "aux",
    },
    "en": {
        "the",
        "and",
        "for",
        "with",
        "you",
        "our",
        "your",
        "is",
        "are",
        "of",
        "to",
        "in",
        "a",
        "an",
        "we",
    },
    "de": {
        "der",
        "die",
        "das",
        "und",
        "für",
        "mit",
        "wir",
        "ihr",
        "ist",
        "sind",
        "von",
        "zu",
        "ein",
        "eine",
        "du",
    },
}


def clean_html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def detect_language(text: str) -> str:
    words = re.findall(r"[a-zà-öø-ÿ]+", text.lower())
    if not words:
        return ""
    scores = {lang: sum(1 for w in words if w in wordset) for lang, wordset in _STOPWORDS.items()}
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_lang if best_score > 0 else "en"


def parse_iso_datetime(value: str | None):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def parse_unix_timestamp(value) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def deduce_contract_type(label: str = "", is_alternance: bool = False) -> str:
    """Best-effort contract type from a free-text label (French or English).

    Some sources (e.g. France Travail) flag postings as "alternance" even when the title is
    explicitly a "Stage de fin d'études / Alternance" — a dual-purpose listing. An explicit
    "stage" mention in the label is checked first so these still surface as stages, since that
    is the more specific and, for this app's audience, more relevant category.
    """
    stripped = unicodedata.normalize("NFKD", label or "").encode("ascii", "ignore").decode("ascii")
    normalized = stripped.strip().lower()

    if any(kw in normalized for kw in ("stage", "intern")):
        return "stage"
    if is_alternance:
        return "alternance"
    if not normalized:
        return "inconnu"
    if any(kw in normalized for kw in ("alternance", "apprentissage", "professionnalisation")):
        return "alternance"
    if any(kw in normalized for kw in ("interim", "mission interimaire", "travail temporaire")):
        return "interim"
    if any(kw in normalized for kw in ("cdi", "indetermin", "permanent", "full_time", "full-time")):
        return "cdi"
    if any(kw in normalized for kw in ("cdd", "determin", "temporary", "fixed-term", "fixed term")):
        return "cdd"
    if any(kw in normalized for kw in ("freelance", "independant", "contract")):
        return "freelance"
    return "inconnu"


def is_disallowed_source(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return any(host == domain or host.endswith(f".{domain}") for domain in DISALLOWED_DOMAINS)
