"""Rebuild index.html (standalone page) from artifact.html (the published artifact source).

The artifact host wraps the page in its own document skeleton; this script adds an
equivalent skeleton so the page also opens directly in a browser.
Run: python3 scripts/make_standalone.py
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / 'artifact.html').read_text(encoding='utf-8')
i = src.index('<div class="page">')
head, body = src[:i], src[i:]
reset = ':root{color-scheme:light}body{margin:0;font:14px system-ui;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}'
out = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       '<style>' + reset + '</style>\n' + head.strip() + '\n</head>\n<body>\n' + body.strip() + '\n</body>\n</html>\n')
(ROOT / 'index.html').write_text(out, encoding='utf-8')
print('wrote index.html')
