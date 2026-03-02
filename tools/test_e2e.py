#!/usr/bin/env python3
"""End-to-end test: upload → ingest → clarify → edit → render.

Usage:
    # Start backend first:  uvicorn server.main:app --port 8080 --reload
    # Start sandbox:        docker run -d --name sandbox -p 9876:9876 -v "$(pwd)/data:/workspace/data" autovid-sandbox:latest
    # Then run:             python tools/test_e2e.py data/IMG_1103.MOV data/IMG_1107.MOV

    # Or with a custom prompt:
    python tools/test_e2e.py data/IMG_1103.MOV --prompt "make a 15 second highlight reel"
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

BASE = "http://localhost:8080/api"
POLL_INTERVAL = 5  # seconds


def main():
    parser = argparse.ArgumentParser(description="E2E test: upload → render")
    parser.add_argument("videos", nargs="+", help="Paths to .mp4/.mov files")
    parser.add_argument("--prompt", default=None, help="Custom edit prompt (skips clarify)")
    parser.add_argument("--length", default="short", choices=["short", "long"])
    parser.add_argument("--style", default="highlights", choices=["vlog", "tutorial", "highlights", "cinematic", "story"])
    parser.add_argument("--base", default=BASE, help="API base URL")
    args = parser.parse_args()

    client = httpx.Client(timeout=300.0, base_url=args.base)

    # ── Step 1: Upload ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"STEP 1: Uploading {len(args.videos)} video(s)...")
    print(f"{'='*60}")

    files = []
    for path in args.videos:
        files.append(("files", (path.split("/")[-1], open(path, "rb"), "video/mp4")))

    resp = client.post("/projects/upload", files=files)
    resp.raise_for_status()
    project = resp.json()
    project_id = project["id"]
    print(f"Project created: {project_id}")
    print(f"Videos: {[v['filename'] for v in project['videos']]}")

    # ── Step 2: Wait for ingestion ────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 2: Waiting for ingestion (ASR + VLM + summary)...")
    print(f"{'='*60}")

    while True:
        resp = client.get(f"/projects/{project_id}")
        resp.raise_for_status()
        status = resp.json()

        current = status["status"]
        videos = status.get("videos", [])
        ingestion_states = [v.get("ingestion_status", "?") for v in videos]
        summaries = [v.get("summary", "")[:80] for v in videos]

        print(f"  Status: {current} | Videos: {ingestion_states}")
        for i, s in enumerate(summaries):
            if s:
                print(f"    Video {i+1} summary: {s}...")

        if current == "ready_for_clarify":
            print("Ingestion complete!")
            break
        elif current == "error":
            print(f"ERROR: {status.get('error', 'unknown')}")
            sys.exit(1)

        time.sleep(POLL_INTERVAL)

    # ── Step 3: Clarify ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 3: Submitting clarifying answers...")
    print(f"{'='*60}")

    answers = {
        "length": args.length,
        "style": args.style,
    }
    if args.prompt:
        answers["specific_request"] = args.prompt

    print(f"  Answers: {json.dumps(answers, indent=2)}")

    resp = client.post(f"/projects/{project_id}/clarify", json={"answers": answers})
    resp.raise_for_status()
    clarify_result = resp.json()

    structured_prompt = clarify_result.get("structured_prompt", "")
    print(f"  Clarify status: {clarify_result.get('status')}")
    print(f"  Structured prompt ({len(structured_prompt)} chars):")
    # Show first/last few lines
    lines = structured_prompt.split("\n")
    for line in lines[:10]:
        print(f"    {line}")
    if len(lines) > 15:
        print(f"    ... ({len(lines) - 15} more lines) ...")
        for line in lines[-5:]:
            print(f"    {line}")

    # ── Step 4: Start editing ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 4: Starting editing agent (GPT-5.2 → Remotion)...")
    print(f"{'='*60}")

    resp = client.post(f"/projects/{project_id}/edit", json={
        "structured_prompt": structured_prompt,
    })
    resp.raise_for_status()
    print(f"  Edit started: {resp.json()}")

    # ── Step 5: Wait for render ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 5: Waiting for render...")
    print(f"{'='*60}")

    while True:
        resp = client.get(f"/projects/{project_id}")
        resp.raise_for_status()
        status = resp.json()

        current = status["status"]
        print(f"  Status: {current}")

        if current == "complete":
            output = status.get("output_uri", "")
            print(f"\nDONE! Output: {output}")
            print(f"Open with: open {output}")
            break
        elif current == "error":
            print(f"\nERROR: {status.get('error', 'unknown')}")
            sys.exit(1)

        time.sleep(POLL_INTERVAL)

    print(f"\n{'='*60}")
    print("E2E TEST COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
