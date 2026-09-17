"""Read-only PNG inspection and HTML review; does not modify image pixels."""
from pathlib import Path
import importlib.util, json, base64, html

base = Path(__file__).resolve().parent
root = base.parents[3]
spec = importlib.util.spec_from_file_location('assets', root / '.agents/skills/ui-skin-assets/scripts/assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)
files = ['panel-generated.png', 'panel-refined.png', 'card-base-transparent-r01.png', 'buy-base-transparent-r01.png', 'vip-band-transparent-r01.png', 'buy-base-neutral-transparent.png']
items = []
sections = []
for name in files:
    data = (base / name).read_bytes()
    stats = assets.inspect_bytes(data)
    items.append(dict(file=name, visualStatus='rejected-colored-edge-fringe', **stats))
    url = 'data:image/png;base64,' + base64.b64encode(data).decode()
    cells = ''.join(f'<div class="sample" style="background:{color}"><img src="{url}" alt="{name}"></div>' for color in ['#ffffff','#152025','#808080','repeating-conic-gradient(#ddd 0% 25%,#fff 0% 50%) 0/16px 16px'])
    sections.append(f'<section><h2>{html.escape(name)}</h2><p>过程稿 · 未通过视觉检查 · {stats["pixelSize"]} · SHA256 {stats["sha256"]}</p><div class="grid">{cells}</div><details><summary>展开原始像素检查（暗底，可横向滚动）</summary><div class="original"><img src="{url}" alt="原始像素"></div></details></section>')
(base / 'diagnostics.json').write_text(json.dumps({'status':'blocked-output-quality','approvedAssets':0,'items':items}, ensure_ascii=False, indent=2))
(base.parent / 'diagnostic-preview.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>商城切图 — 过程稿诊断</title><style>body{font:15px system-ui;margin:28px;background:#e8eced;color:#20343a}h1{font-size:25px}h2{font-size:18px}p{overflow-wrap:anywhere}section{background:white;margin:20px 0;padding:20px;border-radius:12px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.sample{height:250px;display:flex;align-items:center;justify-content:center;border:1px solid #aaa;overflow:hidden}.sample img{max-width:95%;max-height:95%;object-fit:contain}.original{overflow:auto;background:#152025;max-height:800px}.original img{max-width:none}summary{cursor:pointer;padding:16px 0}</style><h1>商城切图 r01：过程稿诊断，尚未完成</h1><p>以下为内置 image_gen 的原始透明输出，仅在浏览器合成到不同底色上查看。未进行本地去底或像素清理。真实 Alpha 不代表视觉质量合格；红、绿、黄色残边导致这些候选未通过检查。页面不代表切图审核提交。</p>''' + ''.join(sections) + '</html>', encoding='utf-8')
print(json.dumps({'files':len(items),'preview':str(base.parent / 'diagnostic-preview.html')},ensure_ascii=False))
