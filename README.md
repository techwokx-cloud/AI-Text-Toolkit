# TechWokx AI Text Toolkit

A portable, fully offline Python tool with two parts:

1. **Detector** — scores text on several linguistic signals associated with
   LLM-generated prose (sentence-length uniformity, stock AI phrasing,
   repetitive openers, punctuation patterns, paragraph uniformity) and gives
   a 0–100 "AI-likelihood" reading with a signal-by-signal breakdown.
2. **Humanizer** — rewrites stiff, cliche-heavy text into more natural,
   conversational prose: swaps stock phrases ("delve into", "in conclusion",
   "leverage") for plain-language equivalents, varies sentence rhythm, adds
   contractions, and (optionally) light conversational asides.

No API keys, no external services, no data leaves your machine — everything
runs from a local phrase bank and rule set.

## What this is for

Cleaning up AI-assisted drafts (blog posts, proposals, portfolio copy,
client emails) so they read naturally instead of sounding templated. It's a
style/editing aid, not a certification of authorship.

## What this is *not* for

This is **not** built or intended to defeat academic-integrity tools
(Turnitin, etc.) or to misrepresent the origin of writing in a context where
that origin matters — job applications, published bylines, academic
submissions, and so on. Use it to *improve* writing, not to *disguise* it in
a setting where the source of the text is materially relevant to the reader.

## Running it

### Desktop app (CustomTkinter GUI)
```bash
pip install -r requirements.txt
python app.py
```
Features: paste or upload `.txt` / `.docx` / `.pdf`, clipboard paste,
page-by-page view for long documents, adjustable humanize intensity/tone,
optional auto-save to a folder you choose, and a one-click re-check of the
detector score on your output.

### CLI (zero GUI dependencies — stdlib only)
```bash
python cli.py detect -f draft.txt
python cli.py humanize -f draft.txt -o draft_humanized.txt --intensity 0.7 --tone casual
```

### Web app (Streamlit — for online deployment)
```bash
pip install streamlit
streamlit run streamlit_app.py
```
Deploy for free on [Streamlit Community Cloud](https://streamlit.io/cloud)
by connecting this GitHub repo and pointing it at `streamlit_app.py`.

## Packaging as a portable .exe / binary

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "TechWokx-AI-Toolkit" app.py
```
The result lands in `dist/` as a single-file executable you can share
directly — no Python install required on the target machine.

## Project structure
```
ai_text_toolkit/
├── app.py              # Desktop GUI (CustomTkinter)
├── cli.py               # Command-line interface
├── streamlit_app.py      # Web app for online deployment
├── core/
│   ├── detector.py        # AI-likelihood scoring
│   ├── humanizer.py       # Rewriting engine
│   └── file_io.py         # .txt/.docx/.pdf import + chunking
├── data/
│   └── ai_phrases.json    # Cliche bank, hedges, tone markers
└── requirements.txt
```

## How the detector actually works

It's a transparent, inspectable heuristic model — not a trained classifier
and not affiliated with any commercial detector (GPTZero, Turnitin,
Copyleaks, etc.). Treat the score as a directional style signal, not a
verdict. No offline, dependency-free tool can reliably replicate what those
services do internally, and this one doesn't try to.

— TechWokx IT Solutions
