# 지역아동센터 Evaluation Scorecard

A self-check tool for 지역아동센터 (community child center) directors preparing for the **5기 정기평가** (2024–2026 cycle, existing centers). It lists every scored item in the evaluation, lets a center mark what it meets year by year, and estimates the score out of 100 using the conversion tables in the *2026년 지역아동센터 평가사업 안내* (평가편람).

## What it does

The page has three views:

- **Scorecard.** One card per indicator (1-1 to 4-7), with every scored criterion as a row. Yearly items have columns for 2023, 2024 and 2025; quality items are rated 0, 1 or 2; per-child records are rated for the two best files and the weakest file, because evaluators check two files the center chooses and one picked at random. 필수 조건 (gate conditions), the 4-6 accounting deductions, the 4-7 donation rules and the abuse-case deduction are all applied.
- **Priority.** Every item not at full marks, sorted into four groups: do on time, fix now (yes-or-no items), raise quality (graded items), and cannot be fixed (past years and penalties). Each item shows how many points it is worth on its own, and the top shows the highest score still reachable.
- **Documents and actions.** All 47 documents and actions behind the scored items, with how often each is needed, whether it is kept online (희망이음) or on paper, whether it is kept or submitted, what it must contain, and the specific required fields. It can be filtered and sorted by area, type, fix window, 필수 조건, scoring type, who checks it (현장평가, 지도점검 or the survey) and number of copies.

## Files

| File | What it is |
|---|---|
| `artifact.html` | The page as published as a claude.ai artifact. This is the source of truth. |
| `index.html` | The same page wrapped as a standalone HTML file, so it opens directly in a browser or on GitHub Pages. |
| `tests/scoring_test.py` | Runs the scoring rules on 20 sample checklists and compares the totals with the handbook tables. Needs Node.js. |
| `tests/ui_audit.py` | Browser audit with Playwright: saving against a mock shared store, scoring through the interface, all three views, filters and sorting, and phone layout. |

## How saving works

- **As a claude.ai artifact:** the page uses the artifact's database to keep **one shared checklist per center**. Everyone the page is shared with at Contributor level or higher sees and edits the same marks; view-only people see them read-only. A second center needs its own copy of the page.
- **Opened as a plain file (`index.html`):** there is no shared store, so marks are saved in that browser only (`localStorage`).

The "Current year" setting in the Priority view is always saved in the browser only.

## Running the tests

```bash
python3 tests/scoring_test.py      # needs node
pip install playwright && python3 -m playwright install chromium
python3 tests/ui_audit.py
```

## Scoring interpretations

The handbook does not spell these out, so the tool takes the stricter reading:

- A program year that fails its 필수 조건 earns nothing for that year.
- If any checked child file fails a 필수 조건, the whole indicator scores 0.
- For 종사자 의무교육, an item counts only if all three years are met.
- For 후원금, a failed condition costs all 4 points, although fixing it before the 지도점검 can reduce the loss to 1 or 2.

## Limitations

- Built for the **5기 cycle and existing centers** only. New centers (신규시설) score differently, and the 6기 cycle from 2027 may change the indicators.
- The score is a **self-estimate**. Evaluators judge quality, so the real score can be lower.
- The required-field lists come from the example forms in a 2024-based 시도지원단 운영 매뉴얼, and the 희망이음 rules from the 2023 지원사업 안내. They should be confirmed with the local 시도지원단 and 시·군·구.
- The interface is in English with Korean terms.

## Sources

- [2026년 지역아동센터 평가사업 안내 (아동권리보장원)](https://ncrc.or.kr/upload/ncrc/2026%EB%85%84%20%EC%A7%80%EC%97%AD%EC%95%84%EB%8F%99%EC%84%BC%ED%84%B0%20%ED%8F%89%EA%B0%80%EC%82%AC%EC%97%85%20%EC%95%88%EB%82%B4.pdf)
- [지역아동센터 운영 매뉴얼 (시도지원단)](http://www.icarejb.or.kr/main/filedown.php?menu=59&no=979)
- [2023년 지역아동센터 지원사업 안내 (보건복지부)](https://www.mohw.go.kr/kor/download/07/005.pdf)
