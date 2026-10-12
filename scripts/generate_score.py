#!/usr/bin/env python3
"""Generate an original instrumental score for Prism Break."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_prism_break import generate_music  # reuse only our original score generator


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--duration",type=float,default=291.318)
    parser.add_argument("--sample-rate",type=int,default=22050)
    args=parser.parse_args()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    generate_music(out,args.duration,args.sample_rate)
    if not out.is_file() or out.stat().st_size < args.duration*1000:
        raise RuntimeError("Original music generation returned an empty/short audio file.")
    print(f"ORIGINAL_SCORE_READY {out} bytes={out.stat().st_size} duration={args.duration}")


if __name__=="__main__":
    main()
