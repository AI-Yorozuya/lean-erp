#!/usr/bin/env python3
"""驗收跑者——跑後端測試、把逐條結果寫進 assets/驗收結果.json。

gen-系統總覽.py 讀這份 JSON 幫驗收條上色（🟢 通過／🔴 未過）；
沒跑過（檔案不存在）時，總覽只標「測試已寫，未跑」，不假裝有結果。

跑法：python3 intents/run-驗收.py
前置：本機資料庫要活著（infra/docker-compose.local.yml 的 db）。
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
BACKEND = HERE.parent / 'apps' / 'lean-backend'
OUT = HERE / 'assets' / '驗收結果.json'

r = subprocess.run(
    ['uv', 'run', 'python', 'manage.py', 'test', '-v', '2', '--noinput'],
    cwd=BACKEND, capture_output=True, text=True)
log = r.stdout + r.stderr

# django -v2 逐條格式：test_xxx (apps...) ... ok / FAIL / ERROR（hypothesis 案例行不吃）
results = {}
for m in re.finditer(r'^(test_\w+) \([\w.]+\)\n?.*?\.\.\. (ok|FAIL|ERROR|skipped)', log, re.M):
    results[m.group(1)] = 'pass' if m.group(2) == 'ok' else 'fail'

if not results:
    sys.exit(f'一條測試結果都沒撈到——測試根本沒跑起來？\n{log[-800:]}')

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps({
    'ran_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
    'results': results,
}, ensure_ascii=False, indent=1), encoding='utf-8')

n_pass = sum(1 for v in results.values() if v == 'pass')
print(f'✅ 驗收結果.json：{n_pass}/{len(results)} 通過（{OUT}）')
if n_pass < len(results):
    for k, v in results.items():
        if v != 'pass':
            print(f'  🔴 {k}')
    sys.exit(1)
