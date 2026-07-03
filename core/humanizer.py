"""
Humanizer
---------
Rule-based, fully offline rewriting engine that:
  1. Swaps stock AI phrasing for casual equivalents
  2. Varies sentence length/rhythm (splits long uniform sentences, merges short ones)
  3. Adds contractions
  4. Injects light hedges / opinion markers / emotional asides ("intensity" controlled)
  5. Breaks up repetitive sentence openers
  6. Occasionally opens a paragraph with a conversational lead-in

This is intentionally deterministic-but-randomized (seeded) rule-based text
transformation — no external API or model is required, so it stays 100%
portable. An optional hook (`llm_rewrite_fn`) lets you plug in a call to
Claude/OpenAI/etc. for a stronger pass if you want to wire one in later.
"""
import json
import os
import random
import re

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ai_phrases.json")

with open(_DATA_PATH, "r", encoding="utf-8") as f:
    _BANK = json.load(f)

_CONTRACTIONS = [
    (r"\bit is\b", "it's"), (r"\bIt is\b", "It's"),
    (r"\bthat is\b", "that's"), (r"\bThat is\b", "That's"),
    (r"\bthere is\b", "there's"), (r"\bThere is\b", "There's"),
    (r"\bdo not\b", "don't"), (r"\bDo not\b", "Don't"),
    (r"\bdoes not\b", "doesn't"), (r"\bDoes not\b", "Doesn't"),
    (r"\bdid not\b", "didn't"), (r"\bDid not\b", "Didn't"),
    (r"\bcan not\b", "can't"), (r"\bcannot\b", "can't"),
    (r"\bwill not\b", "won't"), (r"\bWill not\b", "Won't"),
    (r"\bwould not\b", "wouldn't"), (r"\bshould not\b", "shouldn't"),
    (r"\bI am\b", "I'm"), (r"\bthey are\b", "they're"), (r"\bThey are\b", "They're"),
    (r"\byou are\b", "you're"), (r"\bYou are\b", "You're"),
    (r"\bwe are\b", "we're"), (r"\bWe are\b", "We're"),
    (r"\bI have\b", "I've"), (r"\bthey have\b", "they've"),
    (r"\bwe have\b", "we've"), (r"\bhas not\b", "hasn't"),
    (r"\bwas not\b", "wasn't"), (r"\bwere not\b", "weren't"),
]


def _split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text.strip()) if s.strip()]


def _words(s):
    return re.findall(r"[A-Za-z']+", s)


class Humanizer:
    TONES = ["neutral", "enthusiastic", "reflective", "skeptical", "casual"]

    def __init__(self, seed=None, llm_rewrite_fn=None):
        self.rng = random.Random(seed)
        self.llm_rewrite_fn = llm_rewrite_fn  # optional callable(text) -> text

    # ---- public API -----------------------------------------------------
    def humanize(self, text: str, intensity: float = 0.6, tone: str = "neutral") -> str:
        """
        intensity: 0.0 (barely touched) - 1.0 (heavy rewrite)
        tone: one of Humanizer.TONES
        """
        if not text or not text.strip():
            return text

        if self.llm_rewrite_fn:
            text = self.llm_rewrite_fn(text)

        text = self._replace_cliches(text, intensity)
        text = self._add_contractions(text, intensity)
        sentences = _split_sentences(text)
        sentences = self._vary_openers(sentences, intensity)
        sentences = self._vary_rhythm(sentences, intensity)
        sentences = self._inject_emotion(sentences, intensity, tone)
        result = " ".join(sentences)
        result = self._paragraph_lead_in(result, intensity, tone)
        return result

    # ---- steps ------------------------------------------------------------
    def _replace_cliches(self, text, intensity):
        for entry in _BANK["cliches"]:
            phrase = entry["phrase"]
            options = entry["casual"]
            if not options:
                continue
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)

            def _sub(m, options=options):
                if self.rng.random() > (0.4 + 0.5 * intensity):
                    return m.group(0)  # leave some untouched for variety
                choice = self.rng.choice(options)
                if m.group(0)[0].isupper() and choice:
                    choice = choice[0].upper() + choice[1:]
                return choice

            text = pattern.sub(_sub, text)
        # collapse accidental double spaces from empty replacements
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        return text

    def _add_contractions(self, text, intensity):
        if intensity < 0.25:
            return text
        for pattern, repl in _CONTRACTIONS:
            if self.rng.random() < (0.3 + 0.6 * intensity):
                text = re.sub(pattern, repl, text)
        return text

    def _vary_openers(self, sentences, intensity):
        starters = set(_BANK["starters_to_vary"])
        seen_recent = []
        out = []
        for s in sentences:
            w = _words(s)
            if not w:
                out.append(s)
                continue
            first = w[0].lower()
            if first in starters and self.rng.random() < (0.3 + 0.5 * intensity):
                # drop the throat-clearing connective, or move it mid-sentence
                rest = s.split(" ", 1)[1] if " " in s else s
                if self.rng.random() < 0.5:
                    s = rest[0].upper() + rest[1:] if rest else s
                else:
                    s = rest
            seen_recent.append(first)
            out.append(s)
        return out

    def _vary_rhythm(self, sentences, intensity):
        out = []
        i = 0
        while i < len(sentences):
            s = sentences[i]
            wc = len(_words(s))
            # split long sentences occasionally
            if wc > 24 and self.rng.random() < (0.25 + 0.4 * intensity):
                parts = re.split(r",\s+(?:and|but|which|who|so)\s+", s, maxsplit=1)
                if len(parts) == 2:
                    a, b = parts
                    a = a.strip()
                    b = b.strip()
                    if not a.endswith((".", "!", "?")):
                        a += "."
                    b = b[0].upper() + b[1:]
                    out.append(a)
                    out.append(b)
                    i += 1
                    continue
            # merge two short sentences occasionally
            if wc < 8 and i + 1 < len(sentences) and len(_words(sentences[i + 1])) < 10 \
                    and self.rng.random() < (0.15 + 0.3 * intensity):
                nxt = sentences[i + 1]
                joiner = self.rng.choice([", and", " —", ", so"])
                merged = s.rstrip(".!?") + joiner + " " + nxt[0].lower() + nxt[1:]
                out.append(merged)
                i += 2
                continue
            out.append(s)
            i += 1
        return out

    def _inject_emotion(self, sentences, intensity, tone):
        if intensity < 0.15 or not sentences:
            return sentences
        hedges = list(_BANK["hedges"])
        markers = list(_BANK["emotion_markers"])
        tone_bias = {
            "enthusiastic": ["and honestly, that's exciting", "which is genuinely great to see"],
            "reflective": ["which gives you something to think about", "and it's worth sitting with that"],
            "skeptical": ["though that's worth double-checking", "which I'd take with a grain of salt"],
            "casual": ["no big deal, but", "just saying"],
            "neutral": [],
        }
        markers = markers + tone_bias.get(tone, [])

        out = list(sentences)
        n = len(out)
        # sprinkle a hedge at the start of ~1 sentence per 4-6, scaled by intensity
        every = max(2, int(6 - intensity * 4))
        for idx in range(0, n, every):
            if self.rng.random() < (0.3 + 0.5 * intensity):
                hedge = self.rng.choice(hedges)
                s = out[idx]
                out[idx] = hedge[0].upper() + hedge[1:] + ", " + s[0].lower() + s[1:]
        # append an emotional aside to a sentence here and there
        for idx in range(0, n):
            if self.rng.random() < (0.08 + 0.18 * intensity):
                marker = self.rng.choice(markers) if markers else None
                if marker:
                    s = out[idx].rstrip(".!?")
                    out[idx] = f"{s}, {marker}."
        return out

    def _paragraph_lead_in(self, text, intensity, tone):
        if intensity < 0.4:
            return text
        if self.rng.random() < (0.2 + 0.3 * intensity):
            opener = self.rng.choice(_BANK["openers"])
            text = f"{opener} {text[0].lower()}{text[1:]}"
        return text
