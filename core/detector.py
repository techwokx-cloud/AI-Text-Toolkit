"""
AIDetector
----------
Fully offline heuristic AI-text detector. No model downloads, no API keys,
no internet required — works anywhere Python runs.

It does NOT claim forensic accuracy (no local heuristic tool can match a
trained classifier). It scores several independent signals research has
linked to LLM-generated prose and blends them into a 0-100 "AI likelihood"
score with a breakdown so the user can see *why*.

Signals used:
  1. Burstiness       - humans vary sentence length a lot; LLMs are steadier.
  2. Cliche density    - stock AI phrasing ("delve into", "in conclusion"...).
  3. Lexical diversity  - type-token ratio; LLM prose tends to reuse words.
  4. Repetitive openers - same sentence-starter word/phrase reused often.
  5. Punctuation signature - heavy, uniform use of semicolons/em-dashes/colons.
  6. Paragraph uniformity - LLMs often produce very evenly sized paragraphs.
"""
import json
import os
import re
import statistics
from collections import Counter

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ai_phrases.json")


def _load_phrase_bank():
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_PHRASE_BANK = _load_phrase_bank()
_CLICHES = [c["phrase"] for c in _PHRASE_BANK["cliches"]]


def _split_sentences(text):
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text)
    return [p.strip() for p in parts if p.strip()]


def _split_paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras


def _words(text):
    return re.findall(r"[A-Za-z']+", text.lower())


class AIDetector:
    def __init__(self):
        self.phrase_bank = _PHRASE_BANK

    def analyze(self, text: str) -> dict:
        text = text or ""
        sentences = _split_sentences(text)
        paragraphs = _split_paragraphs(text)
        words = _words(text)

        if len(words) < 25 or len(sentences) < 2:
            return {
                "score": None,
                "verdict": "Not enough text",
                "detail": "Paste at least a couple of sentences (25+ words) for a meaningful reading.",
                "signals": {},
            }

        signals = {}

        # 1. Burstiness (sentence length std-dev relative to mean; low = more AI-like)
        lengths = [len(_words(s)) for s in sentences if _words(s)]
        mean_len = statistics.mean(lengths) if lengths else 0
        stdev_len = statistics.pstdev(lengths) if len(lengths) > 1 else 0
        burstiness = (stdev_len / mean_len) if mean_len else 0
        # Human prose typically lands ~0.4-0.9+. Below ~0.35 reads as AI-steady.
        burst_score = max(0.0, min(1.0, (0.55 - burstiness) / 0.55))
        signals["burstiness"] = {
            "value": round(burstiness, 2),
            "ai_score": round(burst_score * 100),
            "note": "Low variation in sentence length" if burst_score > 0.5 else "Healthy variation in sentence length",
        }

        # 2. Cliche density
        lowered = text.lower()
        hits = [c for c in _CLICHES if c in lowered]
        cliche_rate = len(hits) / max(1, len(sentences))
        cliche_score = max(0.0, min(1.0, cliche_rate / 0.5))
        signals["cliches"] = {
            "value": hits[:8],
            "ai_score": round(cliche_score * 100),
            "note": f"{len(hits)} stock AI phrase(s) found" if hits else "No stock AI phrases found",
        }

        # 3. Lexical diversity (type-token ratio) — very high AND very uniform can both read as synthetic;
        # here we flag unusually low diversity (repetitive vocabulary), common in longer LLM output.
        ttr = len(set(words)) / len(words)
        diversity_score = max(0.0, min(1.0, (0.45 - ttr) / 0.45)) if len(words) > 60 else 0.0
        signals["lexical_diversity"] = {
            "value": round(ttr, 2),
            "ai_score": round(diversity_score * 100),
            "note": "Vocabulary is fairly repetitive" if diversity_score > 0.5 else "Vocabulary looks varied",
        }

        # 4. Repetitive sentence openers
        openers = [s.split()[0].lower().strip(",.") for s in sentences if s.split()]
        opener_counts = Counter(openers)
        most_common_count = opener_counts.most_common(1)[0][1] if opener_counts else 0
        opener_repeat_rate = most_common_count / len(sentences)
        opener_score = max(0.0, min(1.0, (opener_repeat_rate - 0.15) / 0.35))
        signals["repetitive_openers"] = {
            "value": opener_counts.most_common(3),
            "ai_score": round(opener_score * 100),
            "note": "Sentences often start the same way" if opener_score > 0.5 else "Sentence openers vary well",
        }

        # 5. Punctuation signature (semicolons / em-dashes / colons per 1000 words)
        semi = lowered.count(";")
        dash = text.count("—") + text.count(" - ")
        colon = text.count(":")
        rate = (semi + dash + colon) / max(1, len(words)) * 1000
        punct_score = max(0.0, min(1.0, (rate - 4) / 12))
        signals["punctuation"] = {
            "value": round(rate, 1),
            "ai_score": round(punct_score * 100),
            "note": "Heavy, uniform use of semicolons/dashes/colons" if punct_score > 0.5 else "Punctuation looks natural",
        }

        # 6. Paragraph uniformity
        if len(paragraphs) >= 3:
            plens = [len(_words(p)) for p in paragraphs]
            pmean = statistics.mean(plens)
            pstd = statistics.pstdev(plens)
            puniformity = 1 - min(1.0, (pstd / pmean) if pmean else 0)
            para_score = max(0.0, min(1.0, (puniformity - 0.55) / 0.35))
        else:
            para_score = 0.0
        signals["paragraph_uniformity"] = {
            "ai_score": round(para_score * 100),
            "note": "Paragraphs are suspiciously even in length" if para_score > 0.5 else "Paragraph lengths vary naturally",
        }

        weights = {
            "burstiness": 0.25,
            "cliches": 0.25,
            "lexical_diversity": 0.15,
            "repetitive_openers": 0.15,
            "punctuation": 0.10,
            "paragraph_uniformity": 0.10,
        }
        total = sum(signals[k]["ai_score"] * weights[k] for k in weights)
        total = round(total)

        if total >= 70:
            verdict = "Likely AI-generated"
        elif total >= 40:
            verdict = "Mixed / uncertain"
        else:
            verdict = "Likely human-written"

        return {
            "score": total,
            "verdict": verdict,
            "detail": self._explain(total, signals),
            "signals": signals,
            "stats": {
                "words": len(words),
                "sentences": len(sentences),
                "paragraphs": len(paragraphs) or 1,
            },
        }

    @staticmethod
    def _explain(score, signals):
        drivers = sorted(signals.items(), key=lambda kv: kv[1]["ai_score"], reverse=True)
        top = [f"{k.replace('_', ' ')} ({v['ai_score']}%)" for k, v in drivers[:2] if v["ai_score"] > 0]
        if not top:
            return "No strong AI-style signals detected."
        return "Biggest contributors: " + ", ".join(top) + "."
