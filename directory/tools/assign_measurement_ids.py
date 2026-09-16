#!/usr/bin/env python3
"""Assign stable Phase A measurement IDs without changing any existing bytes.

This is the only live-data change authorized for schema Phase A. It inserts a
local `measurements[].id` into every setup measurement that does not already
have one, preserves all existing prose/values/formatting byte-for-byte, and
prints a reproducible proof report.

Usage:
    python3 directory/tools/assign_measurement_ids.py          # apply
    python3 directory/tools/assign_measurement_ids.py --check  # dry run

Proof:
    1. the only textual diff lines are inserted `"id": "m###",` lines;
    2. removing exactly those inserted lines reproduces the original bytes;
    3. removing the inserted ids from the parsed new JSON reproduces the
       parsed original JSON exactly.
"""
from __future__ import annotations

import argparse
import copy
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SETUPS = os.path.normpath(os.path.join(HERE, os.pardir, "data", "setups"))
MEASUREMENTS_RE = re.compile(r'^(\s*)"measurements"\s*:\s*\[\s*$')
DECODER = json.JSONDecoder()


def line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def offset_to_line(starts: list[int], pos: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo


def measurement_object_spans(text: str, data: dict) -> list[tuple[int, int, dict]]:
    measurements = data.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        return []

    starts = line_starts(text)
    array_start = None
    for i, line in enumerate(text.splitlines()):
        if MEASUREMENTS_RE.match(line):
            array_start = starts[i] + line.index("[") + 1
            break
    if array_start is None:
        raise RuntimeError("measurements array was not found in the expected one-object-per-line form")

    spans = []
    pos = array_start
    for expected in measurements:
        while pos < len(text) and text[pos] in " \t\r\n,":
            pos += 1
        if pos >= len(text):
            raise RuntimeError("ran out of text while locating measurements")
        obj, end = DECODER.raw_decode(text, pos)
        if obj != expected:
            raise RuntimeError("located measurement does not match parsed measurements array")
        spans.append((pos, end, obj))
        pos = end
    return spans


def insert_ids(path: str, text: str, data: dict, apply: bool) -> dict:
    spans = measurement_object_spans(text, data)
    starts = line_starts(text)
    lines = text.splitlines(keepends=True)
    insertions = []

    for i, (start, _end, obj) in enumerate(spans, start=1):
        if isinstance(obj, dict) and "id" in obj:
            continue
        brace_line = offset_to_line(starts, start)
        line = lines[brace_line]
        prefix = line[:start - starts[brace_line]]
        if line.rstrip("\r\n") != prefix + "{":
            raise RuntimeError(f"{path}: measurement {i} does not open with a bare '{{' line")
        new_id = f"m{i:03d}"
        insert_line = f"{prefix}  \"id\": \"{new_id}\",\n"
        insertions.append((brace_line + 1, insert_line, new_id))

    if not insertions:
        return {
            "path": path,
            "measurements": len(spans),
            "inserted": 0,
            "changed": False,
            "new_text": text,
            "ids": [],
            "inserted_positions": [],
        }

    new_lines = list(lines)
    for pos, (line_no, insert_line, _new_id) in enumerate(insertions):
        new_lines.insert(line_no + pos, insert_line)
    new_text = "".join(new_lines)
    inserted_positions = {line_no + pos for pos, (line_no, _insert_line, _new_id) in enumerate(insertions)}

    if apply:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)

    return {
        "path": path,
        "measurements": len(spans),
        "inserted": len(insertions),
        "changed": True,
        "new_text": new_text,
        "ids": [new_id for _line_no, _insert_line, new_id in insertions],
        "inserted_positions": sorted(inserted_positions),
    }


def proof(rel: str, original_text: str, result: dict) -> None:
    new_text = result["new_text"]
    if not result["changed"]:
        if new_text != original_text:
            raise AssertionError(f"{rel}: unchanged file text differs")
        return

    new_lines = new_text.splitlines(keepends=True)
    reconstructed = "".join(
        line for i, line in enumerate(new_lines) if i not in set(result["inserted_positions"])
    )
    if reconstructed != original_text:
        raise AssertionError(f"{rel}: removing inserted id lines did not reproduce the original bytes")

    diff = list(difflib.unified_diff(
        original_text.splitlines(keepends=True),
        new_lines,
        fromfile=f"a/{rel}",
        tofile=f"b/{rel}",
        n=0,
    ))
    added = [line for line in diff if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in diff if line.startswith("-") and not line.startswith("---")]
    if removed:
        raise AssertionError(f"{rel}: expected zero removed/changed lines, got {len(removed)}")
    if len(added) != result["inserted"]:
        raise AssertionError(f"{rel}: expected {result['inserted']} added id lines, got {len(added)}")
    for line in added:
        if not re.match(r'^\+\s*"id": "m\d{3}",\n$', line):
            raise AssertionError(f"{rel}: unexpected added line {line!r}")

    original_data = json.loads(original_text)
    new_data = json.loads(new_text)
    stripped = copy.deepcopy(new_data)
    inserted_ids = set(result["ids"])
    for measurement in stripped.get("measurements") or []:
        if isinstance(measurement, dict) and measurement.get("id") in inserted_ids:
            measurement.pop("id", None)
    if stripped != original_data:
        raise AssertionError(f"{rel}: parsed data changed beyond inserted measurement ids")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="dry run; do not write files")
    args = ap.parse_args()

    names = sorted(n for n in os.listdir(SETUPS) if n.endswith(".json") and not n.startswith("_"))
    total_measurements = 0
    total_inserted = 0
    changed_files = []

    for name in names:
        path = os.path.join(SETUPS, name)
        rel = os.path.join("directory/data/setups", name)
        with open(path, encoding="utf-8", newline="") as fh:
            original_text = fh.read()
        data = json.loads(original_text)
        result = insert_ids(path, original_text, data, apply=not args.check)
        total_measurements += result["measurements"]
        total_inserted += result["inserted"]
        if result["inserted"]:
            changed_files.append((rel, result["inserted"], result["ids"][0], result["ids"][-1]))
        proof(rel, original_text, result)

    print("measurement ID assignment proof")
    print(f"mode: {'check' if args.check else 'apply'}")
    print(f"setup files scanned: {len(names)}")
    print(f"measurements scanned: {total_measurements}")
    print(f"id lines inserted: {total_inserted}")
    print(f"files changed: {len(changed_files)}")
    print("removed/changed existing lines: 0")
    print("byte-equality after removing inserted id lines: verified")
    print("parsed-equality after stripping inserted ids: verified")
    if changed_files:
        print("\nchanged files:")
        for rel, count, first, last in changed_files:
            print(f"  {rel}: +{count} ids ({first}..{last})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
