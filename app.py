#!/usr/bin/env python3
"""
TechWokx AI Text Toolkit — Desktop App
Detect likely AI-written text and humanize it. 100% offline, no API keys.

Run:      python app.py
Package:  pyinstaller --onefile --windowed --name "TechWokx-AI-Toolkit" app.py
"""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.detector import AIDetector
from core.humanizer import Humanizer
from core.file_io import extract_text, chunk_text, UnsupportedFileType

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "TechWokx AI Text Toolkit"
BRAND = "TechWokx IT Solutions"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.detector = AIDetector()
        self.hum_chunks = []
        self.hum_chunk_idx = 0
        self.save_dir = ""
        self.save_filename = "humanized_output.txt"

        self._build_header()
        self._build_tabs()
        self._build_footer()

    # ---------------------------------------------------------------- UI --
    def _build_header(self):
        header = ctk.CTkFrame(self, height=64, corner_radius=0)
        header.pack(side="top", fill="x")
        ctk.CTkLabel(
            header, text=APP_TITLE, font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left", padx=20, pady=14)
        ctk.CTkLabel(
            header, text=BRAND, font=ctk.CTkFont(size=13), text_color="gray70"
        ).pack(side="right", padx=20)

    def _build_footer(self):
        footer = ctk.CTkFrame(self, height=28, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        ctk.CTkLabel(
            footer,
            text="Fully offline — no data leaves this machine.",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        ).pack(pady=4)

    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(8, 8))
        self.tabs.add("Detector")
        self.tabs.add("Humanizer")
        self._build_detector_tab(self.tabs.tab("Detector"))
        self._build_humanizer_tab(self.tabs.tab("Humanizer"))

    # ------------------------------------------------------------ Detector
    def _build_detector_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8), pady=8)
        left.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(bar, text="Load .txt", width=100, command=self._load_into_detector).pack(side="left")
        ctk.CTkButton(bar, text="Clear", width=80, fg_color="gray30",
                      command=lambda: self.detect_input.delete("1.0", "end")).pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Analyze", width=100, command=self._run_detect).pack(side="right")

        self.detect_input = ctk.CTkTextbox(left, wrap="word", font=ctk.CTkFont(size=13))
        self.detect_input.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.detect_input.insert("1.0", "Paste text here to check how AI-written it reads...")

        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0), pady=8)

        self.score_label = ctk.CTkLabel(right, text="—", font=ctk.CTkFont(size=42, weight="bold"))
        self.score_label.pack(pady=(24, 0))
        self.verdict_label = ctk.CTkLabel(right, text="Run an analysis", font=ctk.CTkFont(size=16))
        self.verdict_label.pack(pady=(0, 16))

        self.signals_box = ctk.CTkTextbox(right, wrap="word", font=ctk.CTkFont(size=12), state="disabled")
        self.signals_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _load_into_detector(self):
        self._load_file(self.detect_input)

    def _load_file(self, textbox):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        textbox.delete("1.0", "end")
        textbox.insert("1.0", content)

    def _run_detect(self):
        text = self.detect_input.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(APP_TITLE, "Paste or load some text first.")
            return
        result = self.detector.analyze(text)
        if result["score"] is None:
            self.score_label.configure(text="—")
            self.verdict_label.configure(text=result["detail"])
            self._set_signals_text("")
            return

        score = result["score"]
        self.score_label.configure(text=f"{score}", text_color=self._score_color(score))
        self.verdict_label.configure(text=result["verdict"])

        lines = [result["detail"], "", "Signal breakdown:"]
        for name, sig in result["signals"].items():
            lines.append(f"  {name.replace('_', ' '):22s} {sig['ai_score']:>3}%   {sig.get('note', '')}")
        stats = result.get("stats", {})
        if stats:
            lines.append("")
            lines.append(f"Words: {stats['words']}   Sentences: {stats['sentences']}   Paragraphs: {stats['paragraphs']}")
        self._set_signals_text("\n".join(lines))

    def _set_signals_text(self, text):
        self.signals_box.configure(state="normal")
        self.signals_box.delete("1.0", "end")
        self.signals_box.insert("1.0", text)
        self.signals_box.configure(state="disabled")

    @staticmethod
    def _score_color(score):
        if score >= 70:
            return "#e05a5a"
        if score >= 40:
            return "#e0b84a"
        return "#5ac97a"

    # ----------------------------------------------------------- Humanizer
    def _build_humanizer_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8), pady=8)
        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(bar, text="Paste clipboard", width=110, command=self._paste_clipboard).pack(side="left")
        ctk.CTkButton(bar, text="Upload file", width=100, command=self._upload_document).pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Clear", width=80, fg_color="gray30",
                      command=self._clear_humanizer_input).pack(side="left")

        self.page_label = ctk.CTkLabel(left, text="", font=ctk.CTkFont(size=11), text_color="gray60")
        self.page_label.pack(anchor="w", padx=8)

        page_nav = ctk.CTkFrame(left, fg_color="transparent")
        page_nav.pack(fill="x", padx=8)
        ctk.CTkButton(page_nav, text="◀ Prev page", width=90, command=self._prev_chunk).pack(side="left")
        ctk.CTkButton(page_nav, text="Next page ▶", width=90, command=self._next_chunk).pack(side="left", padx=6)

        self.hum_input = ctk.CTkTextbox(left, wrap="word", font=ctk.CTkFont(size=13))
        self.hum_input.pack(fill="both", expand=True, padx=8, pady=(6, 8))
        self.hum_input.insert("1.0", "Paste text here, paste from clipboard, or upload a .txt/.docx/.pdf...")

        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        right.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(right, text="Tone").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 0))
        self.tone_var = tk.StringVar(value="neutral")
        ctk.CTkOptionMenu(right, values=Humanizer.TONES, variable=self.tone_var).grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkLabel(right, text="Intensity").grid(row=0, column=1, sticky="w", padx=12, pady=(12, 0))
        self.intensity_var = tk.DoubleVar(value=0.6)
        self.intensity_slider = ctk.CTkSlider(right, from_=0.0, to=1.0, variable=self.intensity_var,
                                               command=self._on_intensity_change)
        self.intensity_slider.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 4))
        self.intensity_value_label = ctk.CTkLabel(right, text="0.60", font=ctk.CTkFont(size=11))
        self.intensity_value_label.grid(row=2, column=1, sticky="e", padx=12)

        ctk.CTkButton(right, text="Humanize", height=40, font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._run_humanize).grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))

        ctk.CTkLabel(right, text="Auto-save folder (optional)").grid(
            row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 0))
        save_row = ctk.CTkFrame(right, fg_color="transparent")
        save_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        self.save_dir_label = ctk.CTkLabel(save_row, text="Not set", text_color="gray60",
                                            font=ctk.CTkFont(size=11), anchor="w")
        self.save_dir_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(save_row, text="Choose folder", width=110, command=self._choose_save_folder).pack(side="right")

        out_frame = ctk.CTkFrame(tab)
        out_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 8))
        out_frame.grid_rowconfigure(1, weight=1)
        out_frame.grid_columnconfigure(0, weight=1)

        out_bar = ctk.CTkFrame(out_frame, fg_color="transparent")
        out_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(out_bar, text="Copy", width=90, command=self._copy_output).pack(side="left")
        ctk.CTkButton(out_bar, text="Save as .txt", width=110, command=self._save_output).pack(side="left", padx=6)
        ctk.CTkButton(out_bar, text="Re-check score", width=130, command=self._recheck_output).pack(side="right")

        self.hum_output = ctk.CTkTextbox(out_frame, wrap="word", font=ctk.CTkFont(size=13))
        self.hum_output.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def _on_intensity_change(self, value):
        self.intensity_value_label.configure(text=f"{float(value):.2f}")

    def _clear_humanizer_input(self):
        self.hum_input.delete("1.0", "end")
        self.hum_chunks = []
        self.hum_chunk_idx = 0
        self.page_label.configure(text="")

    def _paste_clipboard(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo(APP_TITLE, "Clipboard is empty or doesn't contain text.")
            return
        self._load_chunks_from_text(text)

    def _upload_document(self):
        path = filedialog.askopenfilename(
            filetypes=[("Documents", "*.txt *.docx *.pdf"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            text = extract_text(path)
        except (UnsupportedFileType, ImportError) as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Couldn't read that file:\n{e}")
            return
        base = os.path.splitext(os.path.basename(path))[0]
        self.save_filename = f"humanized_{base}.txt"
        self._load_chunks_from_text(text)

    def _load_chunks_from_text(self, text):
        # For long documents, split into ~500-word pages so they're easy to
        # review and process incrementally in the UI.
        self.hum_chunks = chunk_text(text, words_per_chunk=500)
        self.hum_chunk_idx = 0
        if not self.hum_chunks:
            messagebox.showinfo(APP_TITLE, "No text found.")
            return
        self._load_chunk_into_input()

    def _load_chunk_into_input(self):
        self.hum_input.delete("1.0", "end")
        self.hum_input.insert("1.0", self.hum_chunks[self.hum_chunk_idx])
        total = len(self.hum_chunks)
        self.page_label.configure(text=f"Page {self.hum_chunk_idx + 1} of {total}")

    def _prev_chunk(self):
        if not self.hum_chunks:
            return
        self.hum_chunk_idx = max(0, self.hum_chunk_idx - 1)
        self._load_chunk_into_input()

    def _next_chunk(self):
        if not self.hum_chunks:
            return
        self.hum_chunk_idx = min(len(self.hum_chunks) - 1, self.hum_chunk_idx + 1)
        self._load_chunk_into_input()

    def _choose_save_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.save_dir = folder
        self.save_dir_label.configure(text=folder, text_color="white")

    def _run_humanize(self):
        text = self.hum_input.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(APP_TITLE, "Paste or load some text first.")
            return
        tone = self.tone_var.get()
        intensity = self.intensity_var.get()

        def work():
            out = Humanizer().humanize(text, intensity=intensity, tone=tone)
            self.after(0, lambda: self._set_output(out))

        threading.Thread(target=work, daemon=True).start()

    def _set_output(self, text):
        self.hum_output.delete("1.0", "end")
        self.hum_output.insert("1.0", text)
        if self.save_dir:
            path = os.path.join(self.save_dir, self.save_filename)
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(text + "\n\n")
            except OSError as e:
                messagebox.showerror(APP_TITLE, f"Couldn't auto-save:\n{e}")
                return
            messagebox.showinfo(APP_TITLE, f"Page appended to:\n{path}")

    def _copy_output(self):
        text = self.hum_output.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo(APP_TITLE, "Copied to clipboard.")

    def _save_output(self):
        text = self.hum_output.get("1.0", "end").strip()
        if not text:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo(APP_TITLE, f"Saved to {path}")

    def _recheck_output(self):
        text = self.hum_output.get("1.0", "end").strip()
        if not text:
            return
        result = self.detector.analyze(text)
        score = result.get("score")
        verdict = result.get("verdict", "")
        if score is None:
            messagebox.showinfo(APP_TITLE, result.get("detail", "Not enough text."))
        else:
            messagebox.showinfo(APP_TITLE, f"New AI-likelihood score: {score}/100\n{verdict}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
