"""Builds docs/traceability.md from requirements.md + test_cases.md + results.json.

results.json format: {"TC-LM-05": {"21": "PASS", "23": "FAIL", "bugs": ["BUG-003"]}}
Fully regenerated every run so it can't drift from the sources.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"
REQ_ROW_RE = re.compile(r"^\|\s*([A-Z]+-\d+[a-z]?)\s*\|(.*)\|\s*$")
TC_ROW_RE = re.compile(r"^\|\s*(TC-[A-Z]+-\d+)\s*\|\s*([^|]+?)\s*\|")
RESULT_ICON = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLOCKED", "PARTIAL": "PARTIAL", "N/A": "N/A"}


def split_cells(text: str) -> list[str]:
    """Split a table row on unescaped '|' (a cell value can contain an escaped '\\|')."""
    placeholder = "\x00"
    cells = text.replace("\\|", placeholder).split("|")
    return [c.replace(placeholder, "|").strip() for c in cells]


def parse_requirements() -> dict[str, dict[str, str]]:
    """{req_id: {ver, prio, kind}} from requirements.md tables."""
    reqs: dict[str, dict[str, str]] = {}
    for line in (DOCS / "requirements.md").read_text(encoding="utf-8").splitlines():
        m = REQ_ROW_RE.match(line)
        if not m:
            continue
        cells = split_cells(m.group(2))
        # cols after ID: text, Ver, P, Type[, notes]; rows w/o Ver/P still have 4+ cells
        if len(cells) < 4:
            continue
        reqs[m.group(1)] = {"ver": cells[1], "prio": cells[2], "kind": cells[3]}
    return reqs


def parse_test_cases() -> dict[str, list[str]]:
    """{tc_id: [req_id, ...]} from test_cases.md."""
    cases: dict[str, list[str]] = {}
    for line in (DOCS / "test_cases.md").read_text(encoding="utf-8").splitlines():
        m = TC_ROW_RE.match(line)
        if m:
            cases[m.group(1)] = [r.strip() for r in m.group(2).split(",") if r.strip()]
    return cases


def load_results() -> dict[str, dict]:
    path = DOCS / "results.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def cell(tcs: list[str], results: dict[str, dict], key: str) -> str:
    """Roll up per-version status across all TCs covering one requirement."""
    statuses = [results.get(tc, {}).get(key) for tc in tcs]
    known = [s for s in statuses if s]
    if not known:
        return "—"
    if "FAIL" in known:
        return "FAIL"
    if "PARTIAL" in known or "BLOCKED" in known or len(known) < len(statuses):
        return "PARTIAL"
    return "PASS" if all(s == "PASS" for s in known) else known[0]


def main() -> None:
    reqs = parse_requirements()
    cases = parse_test_cases()
    results = load_results()

    by_req: dict[str, list[str]] = {r: [] for r in reqs}
    orphan_tcs: list[tuple[str, str]] = []
    for tc, rs in cases.items():
        for r in rs:
            if r in by_req:
                by_req[r].append(tc)
            else:
                orphan_tcs.append((tc, r))

    uncovered = [r for r, tcs in by_req.items() if not tcs and reqs[r]["prio"] != "—"]
    lines = [
        "# Матриця трасабіліті SENTRY SWM-2",
        "",
        "> Файл генерується: `python framework/tools/gen_traceability.py`. Не редагувати вручну.",
        "> Джерела: `requirements.md`, `test_cases.md`, `results.json`.",
        "",
        "## Зведення покриття",
        "",
        f"- Вимог: **{len(reqs)}**; з тест-кейсами: **{len(reqs) - len(uncovered)}**; без кейсів: **{len(uncovered)}**",
        f"- Тест-кейсів: **{len(cases)}**; «осиротілих» посилань на неіснуючі вимоги: **{len(orphan_tcs)}**",
        f"- Виконано кейсів (є результат): **{sum(1 for tc in cases if tc in results)}** з {len(cases)}",
        "",
        "## Матриця",
        "",
        "| Req | Ver | P | Тип | Тест-кейси | 2.1.0 | 2.3.0 | Баги |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r, meta in reqs.items():
        tcs = by_req[r]
        bugs = sorted({b for tc in tcs for b in results.get(tc, {}).get("bugs", [])})
        lines.append(
            f"| {r} | {meta['ver']} | {meta['prio']} | {meta['kind']} | "
            f"{', '.join(tcs) or '**НЕМАЄ**'} | {cell(tcs, results, '21')} | {cell(tcs, results, '23')} | "
            f"{', '.join(bugs) or '—'} |"
        )
    if uncovered:
        lines += ["", "## Вимоги без тест-кейсів", ""] + [f"- {r}" for r in uncovered]
    if orphan_tcs:
        lines += ["", "## Кейси з невідомою вимогою", ""] + [f"- {tc} → {r}" for tc, r in orphan_tcs]
    (DOCS / "traceability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"reqs={len(reqs)} tcs={len(cases)} uncovered={len(uncovered)} orphans={len(orphan_tcs)}")
    for r in uncovered:
        print("UNCOVERED", r)
    for tc, r in orphan_tcs:
        print("ORPHAN", tc, r)


if __name__ == "__main__":
    main()
