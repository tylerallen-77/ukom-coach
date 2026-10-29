#!/usr/bin/env python3
"""Merge data/parts/*.json into data/questions.json and data/questions.js, validating as it goes."""
import glob
import re
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SUBS = {"c": "Pengawasan", "p": "Pemeriksaan", "t": "Penagihan"}

# Unit Kompetensi pada Standar Kompetensi Teknis (7 unit) + penagihan di luar daftar itu.
ADV, POT, KEP, PRO, EKS, PMR, RSK, LUAR = ("Advokasi Kebijakan Perpajakan", "Analisis Potensi Pajak", "Analisis Kepatuhan Wajib Pajak",
    "Profiling Wajib Pajak", "Ekstensifikasi Perpajakan", "Pemeriksaan Pajak", "Analis Profil Risiko Wajib Pajak", "Penagihan (di luar 7 unit)")
UNIT_BY_TOPIC = {
    "Analisis Potensi Pajak": POT, "PP 20/2026": POT, "Analisis Potensi: Bank": POT,
    "CRM Sektor Rokok": RSK, "CRM Sektor Otomotif": RSK, "CRM Penagihan": RSK,
    "Pengawasan WP Belum Terdaftar": EKS,
    "PMK 111/2025 (Pengawasan)": KEP, "Coretax & ND Pengawasan": KEP, "WP Non Aktif (NA TD)": KEP, "Imbauan Massal & NATD": KEP,
    "PMK 172/2023 (PKKU)": KEP,
    "Profiling WP": PRO, "Profiling WP (KPDL)": PRO, "Profiling Penanggung Pajak": PRO,
    "KUP – Pemeriksaan": PMR, "PMK 15/2025 (Pemeriksaan)": PMR, "Pemeriksaan PBB": PMR, "Data Konkret (PER-18/PJ/2025)": PMR,
    "Pengusulan Pemeriksaan": PMR,
    "Dasar Hukum Penagihan": ADV, "Pengertian Penagihan": ADV, "Utang Pajak dan Biaya Penagihan": ADV, "Dasar Penagihan": ADV,
    "Penanggung Pajak": ADV, "Upaya Hukum Gugatan Penagihan": ADV,
}
UNIT_DEFAULT = {"Pengawasan": ADV, "Pemeriksaan": PMR, "Penagihan": LUAR}
SRC_RE = re.compile(r"^(Part\s?(\d)|Penagihan|Pemeriksaan P(\d))\s*(?:s\.|slide)\s*([\d,\-– ]+)")
LEAD_RE = re.compile(r"^(?:Part\s?\d|Penagihan|Pemeriksaan P\d)?\s*(?:slide|s\.)\s*[\d,\-– ]+(?:dan\s*[\d]+)?[.;:]?\s*", re.I)

def ref_of(src):
    m = SRC_RE.match(src or "")
    if not m:
        return None
    nums = m.group(4).strip().rstrip(",-– ")
    word = "Slide" if re.search(r"[,\-–]", nums) is None else "Slide"
    if m.group(2):
        where = f"Part {m.group(2)}"
    elif m.group(3):
        where = f"materi Pemeriksaan Part {m.group(3)}"
    else:
        where = "materi Penagihan"
    return f"{word} {nums} {where}"

def statement(it):
    q, o, a = it["q"].strip(), it["o"], it["a"]
    ans = o[a].rstrip(".")
    others = [x.rstrip(".") for i, x in enumerate(o) if i != a]
    suffix = f" Pilihan lain ({'; '.join(others)}) tidak tepat."
    if re.search(r"KECUALI\W*$", q):
        head = re.split(r",?\s*KECUALI", q)[0].rstrip(" ,.:…")
        return f"{head}: yang BUKAN termasuk adalah \"{ans}\". Yang termasuk: " + "; ".join(others) + "."
    if " ... " in q:
        return q.replace(" ... ", f" {ans} ", 1).rstrip(" .") + "." + suffix
    if q.endswith("...") or q.endswith("…"):
        return f"{q[:-3].rstrip()}: {ans}." + suffix
    return f"{q.rstrip()} {ans}." + suffix

def enrich(it):
    e = it.get("e", "").strip()
    if "(referensi di" in e:
        return e
    body = LEAD_RE.sub("", e).strip()
    body = body.rstrip(".") + "." if len(body) >= 80 else statement(it)
    ref = ref_of(it.get("src", ""))
    return f"{body} (referensi di {ref})" if ref else body

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
        it["sub"] = it.get("sub") or SUBS[name[0]]
        it["unit"] = it.get("unit") or UNIT_BY_TOPIC.get(it.get("topic"), UNIT_DEFAULT[it["sub"]])
        it["lvl"] = it.get("lvl", "standar")
        it["e"] = enrich(it)
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
