"""Checks the scoring rules against the 2026 평가편람 conversion tables.

Extracts the pure scoring block from artifact.html and runs it in Node.
Run: python3 tests/scoring_test.py   (needs Node.js)
"""
import json, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / 'artifact.html').read_text(encoding='utf-8')
js = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]
score = js[js.index('/*score-start*/'):js.index('/*score-end*/')]
rows = js[js.index('var R = ['):js.index('var Q = {')]
docs = sorted(set(re.findall(r"d:'([^']+)'", rows)) | {'희망이음' + m for m in re.findall(r"d:HI \+ '([^']+)'", rows)})

# case name -> (changes applied to an all-full-marks checklist, expected total)
CASES = r'''
var cases = [
  ['blank checklist (4-6 starts at 4)', null, 4],
  ['everything at full marks', function (V) {}, 100],
  ['1-1 no pledge', function (V) { V['1-1_c2'] = 0; }, 97],
  ['1-1 no rights class in 2024', function (V) { V['1-1_c3_y1'] = 0; }, 99],
  ['2-1 no opinion gathering in any year', function (V) { V['2-1_c3_y0'] = V['2-1_c3_y1'] = V['2-1_c3_y2'] = 0; }, 97],
  ['2-1 필수 조건 failed in 2023', function (V) { V['2-1_g_y0'] = 0; }, 94],
  ['2-2 every quality item rated 1', function (V) { for (var y = 0; y < 3; y++) ['c1','c2','c4','c5','c6'].forEach(function (c) { V['2-2_' + c + '_y' + y] = 1; }); }, 93],
  ['3-1 every 아동카드 complete but not updated', function (V) { V['3-1_c1'] = 3; V['3-1_c1_b'] = 3; }, 94],
  ['3-1 weakest 아동카드 not updated, best two current', function (V) { V['3-1_c1'] = 3; }, 98],
  ['3-1 older data with no best-files value', function (V) { delete V['3-1_c1_b']; }, 100],
  ['3-3 weakest file thin', function (V) { V['3-3_c2'] = 0; }, 98],
  ['3-2 필수 조건 failed in 2025', function (V) { V['3-2_g_y2'] = 0; }, 94],
  ['4-2 no 운영위원회 review in any year', function (V) { V['4-2_c2_y0'] = V['4-2_c2_y1'] = V['4-2_c2_y2'] = 0; }, 99],
  ['4-5 의무교육 missing in 2023', function (V) { V['4-5_c1_y0'] = 0; }, 96],
  ['4-6 one open 개선명령', function (V) { V['4-6_p6'] = 1; }, 97],
  ['4-7 donations, 5 of 6 conditions', function (V) { V['4-7_s'] = 1; V['4-7_c6'] = 0; }, 96],
  ['4-7 donations, all 6 conditions', function (V) { V['4-7_s'] = 1; }, 100],
  ['4-7 no donations, account open', function (V) { V['4-7_s'] = 2; }, 98],
  ['3-5 average 4.3, too few responses', function (V) { V['3-5_s'] = 5; V['3-5_r'] = 0; }, 98],
  ['confirmed abuse case', function (V) { V['abuse'] = 1; }, 85]
];
function best() {
  var V = {};
  IND.forEach(function (ind) { ind.items.forEach(function (it) {
    if (it.pen) return;
    if (it.per === 'year' || it.per === 'all') for (var y = 0; y < 3; y++) V[keyOf(ind, it, y)] = it.max;
    else { V[keyOf(ind, it)] = it.max; if (it.per === 'child') V[keyOf(ind, it) + '_b'] = it.max; }
  }); });
  V['4-7_s'] = 4;
  return V;
}
var bad = [];
IND.forEach(function (ind) {
  (ind.docs || []).concat.apply(ind.docs || [], ind.items.map(function (it) { return it.docs; })).forEach(function (d) { if (DOCS.indexOf(d) < 0) bad.push(ind.id + ': ' + d); });
});
var fails = 0;
if (bad.length) { fails++; console.log('FAIL scorecard links to unknown documents: ' + bad.join(', ')); }
cases.forEach(function (c) {
  var V = c[1] ? best() : {};
  if (c[1]) c[1](V);
  var got = scoreAll(function (k) { return V[k] || 0; }).total;
  var pass = got === c[2];
  if (!pass) fails++;
  console.log((pass ? 'PASS ' : 'FAIL ') + c[0] + ' => ' + got + (pass ? '' : ' (expected ' + c[2] + ')'));
});
console.log('SUMMARY ' + (cases.length + 1 - fails) + ' passed of ' + (cases.length + 1));
process.exit(fails ? 1 : 0);
'''
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
    f.write(score + '\nvar DOCS = ' + json.dumps(docs, ensure_ascii=False) + ';\n' + CASES)
sys.exit(subprocess.run(['node', f.name]).returncode)
