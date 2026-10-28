#!/usr/bin/env python3
"""Merge data/parts/*.json into data/questions.json and data/questions.js, validating as it goes."""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SUBS = {"c": "Pengawasan", "p": "Pemeriksaan", "t": "Penagihan"}
parts = sorted(glob.glob(os.path.join(ROOT, "data", "parts", "*.json")))
questions, errors, seen = [], [], set()

for path in parts:
    name = os.path.basename(path)[:-5]
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    for n, it in enumerate(items, 1):
        qid = f"{name}-{n:03d}"
        where = f"{name}#{n}"
        for k in ("topic", "src", "q", "o", "a", "e"):
            if k not in it:
                errors.append(f"{where}: missing '{k}'")
        o = it.get("o", [])
        if len(o) != 4 or len(set(o)) != 4:
            errors.append(f"{where}: needs 4 distinct options")
        if not isinstance(it.get("a"), int) or not 0 <= it.get("a", -1) < len(o):
            errors.append(f"{where}: answer index out of range")
        if it.get("q") in seen:
            errors.append(f"{where}: duplicate question text")
        seen.add(it.get("q"))
        it["id"] = qid
        it["sub"] = SUBS[name[0]]
        questions.append(it)

if errors:
    print("\n".join(errors[:50]))
    print(f"{len(errors)} problem(s)")
    sys.exit(1)

with open(os.path.join(ROOT, "data", "questions.json"), "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=1)
with open(os.path.join(ROOT, "data", "questions.js"), "w", encoding="utf-8") as f:
    f.write("window.QUESTIONS=" + json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + ";\n")

topics = {}
for q in questions:
    topics[q["topic"]] = topics.get(q["topic"], 0) + 1
print(f"{len(questions)} questions from {len(parts)} part file(s), {len(topics)} topics")
