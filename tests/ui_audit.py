"""Browser audit of the scorecard: saving against a mock shared store, scoring through the UI,
the Documents and actions view, the Priority view and phone layout.

Run: python3 tests/ui_audit.py   (needs Playwright with Chromium)
"""
import json, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(tempfile.mkdtemp(prefix='eval-audit-'))
from playwright.sync_api import sync_playwright
src = (ROOT / 'artifact.html').read_text(encoding='utf-8')
os.chdir(WORK)
skel = '<!doctype html><html><head><meta charset="utf8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + src + '</body></html>'
out = WORK / 'page.html'; out.write_text(skel, encoding='utf-8')
MOCK = r'''
(function(){
 var cfg = window.__cfg || {}; window.__calls = [];
 var store = cfg.doc ? JSON.parse(JSON.stringify(cfg.doc)) : null, subs = [];
 function snap(){ var d = store ? JSON.parse(JSON.stringify(store)) : undefined; return {id:'state', exists: !!store, data: function(){ return d; }, metadata:{}}; }
 function emit(){ subs.forEach(function(f){ setTimeout(function(){ f(snap()); }, 0); }); }
 function merge(t, s){ Object.keys(s).forEach(function(k){ if (s[k] && typeof s[k]==='object' && !Array.isArray(s[k])) { if (!t[k] || typeof t[k] !== 'object') t[k] = {}; merge(t[k], s[k]); } else t[k] = s[k]; }); }
 var failQ = (cfg.fail || []).slice();
 function fail(){ if (failQ.length) { var c = failQ.shift(); if (c) return Promise.reject({code:c, message:c}); } return null; }
 var ref = { id:'state', path:'center/state',
  get: function(){ __calls.push(['get']); return Promise.resolve(snap()); },
  set: function(data){ __calls.push(['set', JSON.parse(JSON.stringify(data))]); var f = fail(); if (f) return f; return new Promise(function(res){ setTimeout(function(){ store = JSON.parse(JSON.stringify(data)); emit(); res(); }, cfg.delay||30); }); },
  update: function(data){ __calls.push(['update', JSON.parse(JSON.stringify(data))]); var f = fail(); if (f) return f; if (!store) return Promise.reject({code:'invalid_argument'}); return new Promise(function(res){ setTimeout(function(){ merge(store, data); emit(); res(); }, cfg.delay||30); }); },
  onSnapshot: function(next){ subs.push(next); setTimeout(function(){ next(snap()); }, 20); return function(){}; } };
 window.__remote = function(data){ if (!store) store = {v:{}}; merge(store, data); emit(); };
 window.__store = function(){ return store; };
 window.claude = { use: function(name){ if (name==='db') return Promise.resolve(cfg.nodb ? null : { doc: function(p){ __calls.push(['doc', p]); return ref; } }); if (name==='user') return Promise.resolve({ can: function(){ return Promise.resolve(cfg.can === undefined ? true : cfg.can); } }); return Promise.resolve(null); } };
})();'''
res = []
def ok(name, cond, detail=''):
    res.append((name, bool(cond), detail)); print(('PASS ' if cond else 'FAIL ') + name + ((' :: ' + str(detail)) if (detail and not cond) else ''))
errs = []
def page(b, cfg, w=1360, h=900, scheme='light'):
    ctx = b.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme)
    pg = ctx.new_page()
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'ERR_' not in m.text and 'fonts.g' not in m.text and 'Failed to load resource' not in m.text else None)
    pg.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
    if cfg is not None: pg.add_init_script('window.__cfg = ' + json.dumps(cfg) + ';' + MOCK)
    pg.goto(out.as_uri()); pg.wait_for_timeout(300)
    return pg
def calls(pg, kind=None):
    c = pg.evaluate('window.__calls'); return [x for x in c if (kind is None or x[0] == kind)]
S = lambda pg: pg.inner_text('#save-status')
C = lambda k: '[id="c-%s"]' % k
with sync_playwright() as p:
    b = p.chromium.launch()
    # A: no shared doc yet
    pg = page(b, {})
    ok('A1 empty store status', 'Nothing is saved yet' in S(pg), S(pg))
    ok('A2 blank total is 4 (4-6 starts at 4)', pg.inner_text('#total') == '4' and pg.inner_text('#open') == '96')
    pg.check(C('1-1_c1')); pg.wait_for_timeout(900)
    st = calls(pg, 'set')
    ok('A3 first change creates doc with set', len(st) == 1 and st[0][1]['v'] == {'1-1_c1': 1} and calls(pg, 'update') == [], st)
    ok('A4 saved status', S(pg).startswith('Saved'), S(pg))
    pg.check(C('1-1_c2')); pg.wait_for_timeout(900)
    up = calls(pg, 'update')
    ok('A5 later change sends only the changed key', len(up) == 1 and up[0][1]['v'] == {'1-1_c2': 1}, up)
    pg.uncheck(C('1-1_c2')); pg.wait_for_timeout(900)
    ok('A6 untick writes 0', calls(pg, 'update')[-1][1]['v'] == {'1-1_c2': 0})
    pg.check(C('1-1_c4')); pg.check(C('1-1_c5')); pg.select_option(C('4-1_c1'), '2'); pg.wait_for_timeout(900)
    ok('A7 rapid changes coalesce into one write', len(calls(pg, 'update')) == 3 and calls(pg, 'update')[-1][1]['v'] == {'1-1_c4': 1, '1-1_c5': 1, '4-1_c1': 2}, calls(pg, 'update')[-1])
    pg.fill('#center-name', '행복한 지역아동센터'); pg.press('#center-name', 'Tab'); pg.wait_for_timeout(900)
    ok('A8 center name saved', pg.evaluate('window.__store().name') == '행복한 지역아동센터')
    ok('A9 store matches screen', pg.evaluate('window.__store().v') == {'1-1_c1': 1, '1-1_c2': 0, '1-1_c4': 1, '1-1_c5': 1, '4-1_c1': 2}, pg.evaluate('window.__store().v'))
    pg.close()
    # B: existing doc incl. garbage; remote updates; pairs; in-flight overlay
    pg = page(b, {'doc': {'v': {'1-1_c1': 1, '2-1_c1_y0': 2, '3-1_c1': 5, 'bogus': 7, '1-1_c2': 'yes', '4-7_s': 9, '3-1_c2': 2.5, '1-2_c1': 2}, 'name': 'Test Center'}, 'delay': 500})
    ok('B1 loads remote values', pg.is_checked(C('1-1_c1')) and pg.input_value(C('2-1_c1_y0')) == '2' and pg.input_value('#center-name') == 'Test Center')
    ok('B2 ignores invalid remote values', (not pg.is_checked(C('1-1_c2'))) and pg.input_value(C('4-7_s')) == '0' and pg.input_value(C('3-1_c2')) == '0' and not pg.is_checked(C('1-2_c1')))
    ok('B3 old weakest-only value fills best files too', pg.input_value(C('3-1_c1_b')) == '5' and pg.input_value(C('3-1_c1')) == '5')
    pg.evaluate("window.__remote({v: {'1-1_c2': 1}})"); pg.wait_for_timeout(200)
    ok('B4 another person\'s change appears live', pg.is_checked(C('1-1_c2')))
    pg.select_option(C('3-1_c1_b'), '3'); pg.wait_for_timeout(100)
    ok('B5 lowering best files lowers weakest too', pg.input_value(C('3-1_c1')) == '3')
    pg.select_option(C('3-1_c1'), '5'); pg.wait_for_timeout(100)
    ok('B6 raising weakest raises best files too', pg.input_value(C('3-1_c1_b')) == '5')
    pg.wait_for_timeout(1400)
    pg.check(C('1-1_c4')); pg.wait_for_timeout(800)   # write now in flight (500ms delay)
    pg.evaluate("window.__remote({v: {'1-1_c5': 1}})"); pg.wait_for_timeout(100)
    ok('B7 in-flight change survives an incoming snapshot', pg.is_checked(C('1-1_c4')) and pg.is_checked(C('1-1_c5')))
    pg.wait_for_timeout(900)
    ok('B8 settles saved and consistent', S(pg).startswith('Saved') and pg.evaluate("window.__store().v['1-1_c4']") == 1, S(pg))
    pg.close()
    # C: view-only
    pg = page(b, {'can': False, 'doc': {'v': {'1-1_c1': 1}}})
    dis = pg.evaluate("Array.prototype.every.call(document.querySelectorAll('#cards [data-k]'), function (e) { return e.disabled; })")
    ok('C1 view-only disables every control', dis and pg.is_disabled('#center-name') and 'View only' in S(pg), S(pg))
    ok('C2 view-only still shows shared values', pg.is_checked(C('1-1_c1')))
    pg.close()
    # D: write refused
    pg = page(b, {'can': None, 'doc': {'v': {'1-1_c1': 1}}, 'fail': ['invalid_argument']})
    pg.check(C('1-1_c2')); pg.wait_for_timeout(1000)
    ok('D1 refused write turns view-only and reverts the change', 'View only' in S(pg) and not pg.is_checked(C('1-1_c2')) and pg.is_checked(C('1-1_c1')) and pg.is_disabled(C('1-1_c2')), S(pg))
    pg.close()
    # E: transient failure retries once
    pg = page(b, {'doc': {'v': {}}, 'fail': ['unavailable']})
    pg.check(C('1-1_c2')); pg.wait_for_timeout(900)
    ok('E1 transient failure message', 'Could not save' in S(pg), S(pg))
    pg.wait_for_timeout(7200)
    ok('E2 retry succeeds', S(pg).startswith('Saved') and pg.evaluate("window.__store().v['1-1_c2']") == 1 and len(calls(pg, 'update')) == 2, S(pg))
    pg.close()
    # F: no shared store, local only; reload persistence; full marks; only-open
    pg = page(b, {'nodb': True})
    ok('F1 local-only status', 'this browser only' in S(pg), S(pg))
    pg.evaluate("""Array.prototype.forEach.call(document.querySelectorAll('#cards [data-k]'), function (e) {
      var k = e.dataset.k; if (/^4-6_p/.test(k) || k === 'abuse') return;
      if (e.type === 'checkbox') { if (!e.checked) { e.checked = true; e.dispatchEvent(new Event('change', {bubbles: true})); } }
      else { e.value = e.options[e.options.length - 1].value; e.dispatchEvent(new Event('change', {bubbles: true})); } });""")
    ok('F2 everything at best gives 100', pg.inner_text('#total') == '100' and '통과' in pg.inner_text('#verdict') and pg.inner_text('#open') == '0', pg.inner_text('#total'))
    sums = pg.evaluate("['rights','program','child','ops'].map(function (a) { return document.getElementById('ta-' + a).textContent + '|' + document.getElementById('as-' + a).textContent; })")
    ok('F3 area subtotals', sums == ['15 of 15|15 of 15', '30 of 30|30 of 30', '30 of 30|30 of 30', '25 of 25|25 of 25'], sums)
    pg.check('#only-open')
    ok('F4 only-open at full marks shows the done message', pg.locator('article.ind:visible').count() == 0 and pg.locator('#all-done').is_visible() and pg.locator('.area-h:visible').count() == 0)
    pg.uncheck('#only-open')
    pg.select_option(C('abuse'), '1')
    ok('F5 abuse case deducts 15 and says so', pg.inner_text('#total') == '85' and pg.locator('#deduct').is_visible())
    pg.select_option(C('abuse'), '2')
    ok('F6 serious abuse forces 미통과', '미통과' in pg.inner_text('#verdict'))
    pg.select_option(C('abuse'), '0')
    pg.select_option(C('4-7_s'), '2')
    ok('F7 donation conditions disabled unless donations received', pg.is_disabled(C('4-7_c1')) and pg.inner_text('[id="sc-4-7"]') == '2')
    pg.select_option(C('4-7_s'), '1')
    ok('F8 donation conditions enabled when donations received', (not pg.is_disabled(C('4-7_c1'))) and pg.inner_text('[id="sc-4-7"]') == '4')
    pg.uncheck(C('2-1_g_y1'))
    ok('F9 a failed program year drops 문화 to 4', pg.inner_text('[id="sc-2-1"]') == '4' and pg.inner_text('[id="rw-2-1"]') == 'raw 24 of 36', pg.inner_text('[id="rw-2-1"]'))
    pg.reload(); pg.wait_for_timeout(400)
    ok('F10 reload keeps local marks', pg.inner_text('[id="sc-2-1"]') == '4' and pg.input_value(C('4-7_s')) == '1' and pg.is_checked(C('1-1_c1')))
    nolabel = pg.evaluate("Array.prototype.filter.call(document.querySelectorAll('#cards [data-k]'), function (e) { return !e.getAttribute('aria-label'); }).length")
    dup = pg.evaluate("(function () { var s = {}, d = []; Array.prototype.forEach.call(document.querySelectorAll('[id]'), function (e) { if (s[e.id]) d.push(e.id); s[e.id] = 1; }); return d; })()")
    ok('F11 every control has an accessible name; no duplicate ids', nolabel == 0 and dup == [], (nolabel, dup[:5]))
    # G: documents view
    pg.click('#tab-docs'); dflt = pg.input_value('#cols'); allvis = all(pg.locator('#head-row th').nth(i).is_visible() for i in range(16)); pg.click('#tab-score')
    ok('G0 documents view opens with all 16 columns, description and fields included', dflt == 'all' and allvis and pg.locator('#head-row th').count() == 16, (dflt, allvis))
    pg.locator('.docbtn[data-doc="운영규정"]').first.click(); pg.wait_for_timeout(150)
    ok('G1 document button shows exactly that document', pg.locator('#view-docs').is_visible() and pg.locator('#rows tr').count() == 1 and pg.locator('#rows .doc-ko').inner_text() == '운영규정' and pg.locator('#only-banner').is_visible())
    pg.fill('#q', '상담'); pg.wait_for_timeout(100)
    ok('G2 typing a search drops the single-document filter', (not pg.locator('#only-banner').is_visible()) and pg.locator('#rows tr').count() >= 2, pg.locator('#rows tr').count())
    pg.click('#clear'); pg.select_option('#cols', 'all')
    total_rows = pg.locator('#rows tr').count()
    ok('G3 clear shows all 47 documents', total_rows == 47 and pg.inner_text('#count') == '47', total_rows)
    bad = []
    for key in ['area', 'doc', 'type', 'ind', 'pts', 'fix', 'gate', 'sco', 'by', 'per', 'freq', 'fmt', 'act', 'where', 'req']:
        for _ in range(2):
            pg.click('.th-btn[data-key="%s"]' % key)
            if pg.locator('#rows tr').count() != 47: bad.append(key)
        if pg.input_value('#sort-key') != key: bad.append('select:' + key)
    ok('G4 every column sorts both ways without losing rows', bad == [], bad)
    pg.click('.th-btn[data-key="pts"]'); pg.click('.th-btn[data-key="pts"]')
    first = pg.locator('#rows tr').first.locator('.pts').inner_text(); last = pg.locator('#rows tr').last.locator('.pts').inner_text()
    ok('G5 points sort keeps unscored rows last', last.strip() == '—', (first, last))
    counts = {}
    for sel in ['#f-area', '#f-type', '#f-fix', '#f-gate', '#f-sco', '#f-by', '#f-per', '#f-freq', '#f-fmt', '#f-act', '#f-req']:
        vals = pg.evaluate("Array.prototype.map.call(document.querySelector('%s').options, function (o) { return o.value; })" % sel)
        tot = 0
        for v in vals[1:]:
            pg.select_option(sel, v); n = pg.locator('#rows tr').count(); tot += n
            if n == 0: counts[sel + ':' + v] = 0
        pg.select_option(sel, 'all'); counts[sel] = tot
    ok('G6 filters partition the list (area, type, freq, format, fields each sum to 47)', counts.get('#f-area') == 47 and counts.get('#f-type') == 47 and counts.get('#f-fix') == 47 and counts.get('#f-gate') == 47 and counts.get('#f-sco') == 47 and counts.get('#f-by') == 47 and counts.get('#f-per') == 47 and counts.get('#f-freq') == 47 and counts.get('#f-fmt') == 47 and counts.get('#f-req') == 47 and not [k for k in counts if ':' in k], counts)
    pg.select_option('#f-type', 'action'); n_act = pg.locator('#rows tr').count(); pg.select_option('#f-type', 'all')
    ok('G7 six actions, and action buttons are marked on the scorecard', n_act == 6 and pg.locator('#count-label').inner_text().endswith('41 documents, 6 actions') and pg.locator('.docbtn.act').count() >= 6 and pg.locator('#scorebar').count() == 0, (n_act, pg.locator('#count-label').inner_text(), pg.locator('.docbtn.act').count()))
    pg.click('.tile[data-ind="3-1"]'); pg.wait_for_timeout(150)
    ok('G8 tile returns to the scorecard', pg.locator('#view-score').is_visible() and not pg.locator('#view-docs').is_visible())
    pg.locator('[id="ind-1-2"]').scroll_into_view_if_needed(); pg.screenshot(path='a-card12.png'); pg.click('#tab-docs'); pg.select_option('#f-type', 'action'); pg.locator('.filters').scroll_into_view_if_needed(); pg.screenshot(path='a-docs.png'); pg.select_option('#f-type', 'all'); pg.click('#tab-score')
    pg.evaluate('window.scrollTo(0, 0)'); pg.screenshot(path='a-top.png')
    pg.close()
    # P: priority view and column sets
    pg = page(b, {'nodb': True})
    pg.click('#tab-prio'); pg.select_option('#cur-year', '3')
    tiers = lambda: [pg.locator('#prio .tier').nth(i).locator('.prow').count() for i in range(4)]
    t0 = tiers()
    ok('P1 blank + closed period: nothing can be done on time; reach is 35', pg.inner_text('#reach') == '35' and t0[0] == 0 and t0[1] > 0 and t0[2] > 0 and t0[3] > 0, (pg.inner_text('#reach'), t0))
    pg.select_option('#cur-year', '2')
    t1 = tiers()
    ok('P2 with 2025 still open: on-time items appear; reach is 48', pg.inner_text('#reach') == '48' and t1[0] > 0 and t1[3] < t0[3], (pg.inner_text('#reach'), t1))
    gates_first = pg.locator('#prio .tier').nth(0).locator('.prow').first.locator('.pill').count() == 1
    ok('P3 필수 조건 items are listed first in a group', gates_first)
    pg.reload(); pg.wait_for_timeout(300); pg.click('#tab-prio')
    ok('P4 current-year choice survives reload', pg.input_value('#cur-year') == '2')
    pg.locator('#prio .tier').nth(1).locator('[data-goto]').first.click(); pg.wait_for_timeout(150)
    ok('P5 "Open in scorecard" returns to the scorecard', pg.locator('#view-score').is_visible() and not pg.locator('#view-prio').is_visible())
    pg.check(C('1-2_c1')); pg.check(C('1-2_c2')); pg.check(C('1-2_c3')); pg.check(C('1-2_c4'))
    pg.click('#tab-prio')
    ok('P6 fixed items leave the list and the reach is unchanged', pg.inner_text('#reach') == '48' and tiers()[1] == t1[1] - 4, (pg.inner_text('#reach'), tiers(), t1))
    pg.locator('#prio .docbtn[data-doc]').first.click(); pg.wait_for_timeout(150)
    ok('P7 document button in the priority list opens that document', pg.locator('#view-docs').is_visible() and pg.locator('#rows tr').count() == 1 and pg.input_value('#cols') == 'con')
    vis = lambda label: pg.locator('#head-row th', has_text=label).first.is_visible()
    ok('P8 content columns: fields shown, priority columns hidden', vis('Required fields') and not vis('Fix window'))
    pg.select_option('#cols', 'pri')
    ok('P9 changing columns keeps the single-document filter; description and fields stay visible', pg.locator('#rows tr').count() == 1 and vis('Fix window') and vis('Checked by') and vis('Required fields') and vis('What it must contain') and not vis('Where'))
    pg.select_option('#cols', 'fil')
    ok('P9b filing set also keeps description and fields', vis('Where') and vis('Required fields') and vis('What it must contain') and not vis('Fix window'))
    pg.click('#only-clear'); pg.select_option('#f-gate', 'yes')
    ok('P10 nine 필수 조건 documents', pg.locator('#rows tr').count() == 9, pg.locator('#rows tr').count())
    pg.screenshot(path='a-docs-pri.png')
    pg.click('#tab-score')
    pg.evaluate("""Array.prototype.forEach.call(document.querySelectorAll('#cards [data-k]'), function (e) {
      var k = e.dataset.k; if (/^4-6_p/.test(k) || k === 'abuse') return;
      if (e.type === 'checkbox') { if (!e.checked) { e.checked = true; e.dispatchEvent(new Event('change', {bubbles: true})); } }
      else { e.value = e.options[e.options.length - 1].value; e.dispatchEvent(new Event('change', {bubbles: true})); } });""")
    pg.click('#tab-prio')
    ok('P11 at full marks the priority list is empty and reach is 100', pg.inner_text('#reach') == '100' and tiers() == [0, 0, 0, 0], (pg.inner_text('#reach'), tiers()))
    pg.click('#tab-score'); pg.uncheck(C('3-2_g_y0')); pg.check(C('4-6_p6')); pg.click('#tab-prio')
    lost = pg.locator('#prio .tier').nth(3).locator('.gain').all_inner_texts()
    ok('P12 a past-year gate and a penalty show as lost points', pg.inner_text('#reach') == '91' and sorted(lost) == sorted(['−6', '−3']), (pg.inner_text('#reach'), lost))
    pg.screenshot(path='a-prio.png')
    pg.close()
    pg = page(b, {'nodb': True}); pg.click('#tab-prio'); pg.select_option('#cur-year', '2'); pg.screenshot(path='a-prio-blank.png'); pg.close()
    # H: phone, both views, both themes
    for scheme in ['light', 'dark']:
        pg = page(b, {'nodb': True}, 400, 800, scheme)
        w1 = pg.evaluate('document.documentElement.scrollWidth'); pg.click('#tab-docs'); pg.wait_for_timeout(100); w2 = pg.evaluate('document.documentElement.scrollWidth'); pg.click('#tab-prio'); w2 = max(w2, pg.evaluate('document.documentElement.scrollWidth'))
        ok('H phone %s: no sideways page scroll in any view' % scheme, w1 <= 400 and w2 <= 400, (w1, w2))
        if scheme == 'dark': pg.click('#tab-score'); pg.screenshot(path='a-phone.png')
        pg.close()
    # I: page without window.claude at all
    pg = page(b, None)
    ok('I no viewer runtime: page still works locally', 'this browser only' in S(pg) and pg.inner_text('#total') == '4')
    pg.close()
    b.close()
print('console/page errors:', errs[:5])
print('SUMMARY', sum(1 for r in res if r[1]), 'passed of', len(res))
print('Screenshots in', WORK)
sys.exit(0 if all(r[1] for r in res) and not errs else 1)
