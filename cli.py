#!/usr/bin/env python3
"""
TechWokx AI Text Toolkit — CLI
Detect likely AI-written text and/or humanize it, from the terminal.
No dependencies beyond the Python standard library.

Usage:
  python cli.py detect -f input.txt
  python cli.py detect -t "some text right here"
  python cli.py humanize -f input.txt -o output.txt --intensity 0.7 --tone casual
  echo "some text" | python cli.py humanize
"""
import argparse
import sys

from core.detector import AIDetector
from core.humanizer import Humanizer


def _read_input(args):
    if getattr(args, "text", None):
        return args.text
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def cmd_detect(args):
    text = _read_input(args)
    result = AIDetector().analyze(text)
    if result["score"] is None:
        print(result["detail"])
        return
    print(f"AI-likelihood score: {result['score']}/100  ->  {result['verdict']}")
    print(result["detail"])
    print()
    print("Signal breakdown:")
    for name, sig in result["signals"].items():
        print(f"  - {name.replace('_', ' '):22s} {sig['ai_score']:3d}%   {sig.get('note', '')}")


def cmd_humanize(args):
    text = _read_input(args)
    out = Humanizer(seed=args.seed).humanize(text, intensity=args.intensity, tone=args.tone)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Written to {args.output}")
    else:
        print(out)


def main():
    parser = argparse.ArgumentParser(description="TechWokx AI Text Toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect", help="Score text for likely AI authorship")
    p_detect.add_argument("-t", "--text", help="Text to analyze")
    p_detect.add_argument("-f", "--file", help="Path to a text file to analyze")
    p_detect.set_defaults(func=cmd_detect)

    p_hum = sub.add_parser("humanize", help="Rewrite text to read more human")
    p_hum.add_argument("-t", "--text", help="Text to rewrite")
    p_hum.add_argument("-f", "--file", help="Path to a text file to rewrite")
    p_hum.add_argument("-o", "--output", help="Write result to this file instead of stdout")
    p_hum.add_argument("--intensity", type=float, default=0.6, help="0.0-1.0, default 0.6")
    p_hum.add_argument("--tone", default="neutral", choices=Humanizer.TONES)
    p_hum.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    p_hum.set_defaults(func=cmd_humanize)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
