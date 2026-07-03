"""
TechWokx AI Text Toolkit — Web App (Streamlit)

Run locally:
    pip install streamlit
    streamlit run streamlit_app.py

Deploy free on Streamlit Community Cloud:
    1. Push this repo to GitHub.
    2. Go to share.streamlit.io, connect the repo, set main file to
       streamlit_app.py.
"""
import streamlit as st

from core.detector import AIDetector
from core.humanizer import Humanizer
from core.file_io import extract_text, UnsupportedFileType

st.set_page_config(page_title="TechWokx AI Text Toolkit", page_icon="✍️", layout="wide")

st.title("✍️ TechWokx AI Text Toolkit")
st.caption(
    "Offline heuristic AI-likelihood scoring + a rule-based writing humanizer. "
    "For polishing AI-assisted drafts, not for disguising authorship in contexts "
    "where that matters (academic submissions, bylines, etc.)."
)

detector = AIDetector()

tab_detect, tab_humanize = st.tabs(["🔍 Detector", "🪄 Humanizer"])

with tab_detect:
    col_in, col_out = st.columns(2)
    with col_in:
        uploaded = st.file_uploader("Upload .txt / .docx / .pdf", type=["txt", "docx", "pdf"], key="detect_upload")
        default_text = ""
        if uploaded is not None:
            with open(f"/tmp/{uploaded.name}", "wb") as f:
                f.write(uploaded.getbuffer())
            try:
                default_text = extract_text(f"/tmp/{uploaded.name}")
            except (UnsupportedFileType, ImportError) as e:
                st.error(str(e))
        text = st.text_area("Or paste text here", value=default_text, height=350, key="detect_text")
        run = st.button("Analyze", type="primary")
    with col_out:
        if run and text.strip():
            result = detector.analyze(text)
            if result["score"] is None:
                st.info(result["detail"])
            else:
                score = result["score"]
                color = "🔴" if score >= 70 else ("🟡" if score >= 40 else "🟢")
                st.metric("AI-likelihood score", f"{score}/100")
                st.subheader(f"{color} {result['verdict']}")
                st.write(result["detail"])
                st.divider()
                for name, sig in result["signals"].items():
                    st.write(f"**{name.replace('_', ' ').title()}** — {sig['ai_score']}%  \n{sig.get('note', '')}")
        else:
            st.info("Paste or upload text, then click Analyze.")

with tab_humanize:
    col_in, col_out = st.columns(2)
    with col_in:
        uploaded_h = st.file_uploader("Upload .txt / .docx / .pdf", type=["txt", "docx", "pdf"], key="hum_upload")
        default_text_h = ""
        if uploaded_h is not None:
            with open(f"/tmp/{uploaded_h.name}", "wb") as f:
                f.write(uploaded_h.getbuffer())
            try:
                default_text_h = extract_text(f"/tmp/{uploaded_h.name}")
            except (UnsupportedFileType, ImportError) as e:
                st.error(str(e))
        hum_text = st.text_area("Or paste text here", value=default_text_h, height=280, key="hum_text")
        tone = st.selectbox("Tone", Humanizer.TONES, index=0)
        intensity = st.slider("Intensity", 0.0, 1.0, 0.6, 0.05)
        go = st.button("Humanize", type="primary")
    with col_out:
        if go and hum_text.strip():
            out = Humanizer().humanize(hum_text, intensity=intensity, tone=tone)
            st.text_area("Result", value=out, height=380)
            st.download_button("Download as .txt", out, file_name="humanized.txt")
            if st.button("Re-check score on result"):
                r = detector.analyze(out)
                if r["score"] is not None:
                    st.metric("New AI-likelihood score", f"{r['score']}/100", delta=None)
                    st.write(r["verdict"])
        else:
            st.info("Paste or upload text, then click Humanize.")

st.divider()
st.caption("Runs entirely on local heuristics — no external API calls, no data retention. TechWokx IT Solutions.")
