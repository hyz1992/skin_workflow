#!/usr/bin/env python3
"""Portable PNG review and byte-bound UI handoffs. No project or engine imports."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

MAX_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 32_000_000


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def write_new(path, data):
    # Exclusive create also refuses dangling symlinks; never overwrite a reviewed file.
    with Path(path).open('xb') as stream:
        stream.write(data.encode('utf-8') if isinstance(data, str) else data)


def read_json(path):
    require(path.stat().st_size <= 2 * 1024 * 1024, 'JSON exceeds 2 MiB')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)


def safe_file(root, name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name
            and '\x00' not in name, 'invalid relative path')
    require(all(part not in ('', '.', '..') for part in name.split('/')), 'unsafe relative path')
    require(not PurePosixPath(name).is_absolute(), 'absolute path refused')
    current = root.resolve()
    for part in name.split('/'):
        current = current / part
        require(not current.is_symlink(), f'symlink refused: {name}')
    require(current.is_file() and current.resolve().is_relative_to(root.resolve()), f'missing file: {name}')
    return current


def vector(value, count, label, positive=False, integer=False):
    require(isinstance(value, list) and len(value) == count, f'invalid {label}')
    require(all(type(v) in (int, float) and math.isfinite(v) for v in value), f'invalid {label}')
    if positive:
        require(all(v > 0 for v in value), f'nonpositive {label}')
    if integer:
        require(all(type(v) is int for v in value), f'noninteger {label}')


def pillow():
    try:
        from PIL import Image
    except ImportError as exc:
        raise Invalid('PNG commands need Pillow; install scripts/requirements.txt in a task virtual environment') from exc
    return Image


def decode(data):
    Image = pillow()
    require(len(data) <= MAX_BYTES, 'PNG exceeds 32 MiB')
    try:
        with Image.open(io.BytesIO(data)) as image:
            require(image.format == 'PNG', 'expected PNG')
            require(image.width * image.height <= MAX_PIXELS, 'PNG exceeds 32 million pixels')
            require(getattr(image, 'n_frames', 1) == 1, 'animated PNG requires separate frame handling')
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            return image.convert('RGBA')
    except Invalid:
        raise
    except Exception as exc:
        raise Invalid(f'PNG decode failed: {exc}') from exc


def inspect_bytes(data):
    image = decode(data)
    alpha = image.getchannel('A')
    histogram = alpha.histogram()
    count = image.width * image.height
    return dict(sha256=sha(data), pixelSize=list(image.size), byteCount=len(data),
                alpha=dict(range=list(alpha.getextrema()), transparent=histogram[0],
                           semitransparent=count-histogram[0]-histogram[255], opaque=histogram[255]),
                visibleBounds=list(alpha.getbbox()) if alpha.getbbox() else None)


def inspect(path):
    require(path.stat().st_size <= MAX_BYTES, 'PNG exceeds 32 MiB')
    return inspect_bytes(path.read_bytes())


def example():
    return dict(format='ui-skin-assets-v1', id='sample-r01', designSize=[800, 600],
                coordinates='top-left-y-down', assets=[dict(key='primary-button', file='button.png',
                sha256='REPLACE_WITH_ACTUAL_SHA256', pixelSize=[200, 80], displaySize=[200, 80],
                transparency='required', position=[400, 480], anchor=[0.5, 0.5], z=10,
                states=['normal'], provenance={}, notes='Display units belong to designSize; source image pixels are independent.')])


def check(manifest_path):
    manifest = read_json(manifest_path)
    require(isinstance(manifest, dict) and manifest.get('format') == 'ui-skin-assets-v1', 'unsupported asset format')
    require(isinstance(manifest.get('id'), str) and manifest['id'].strip(), 'missing revision id')
    vector(manifest.get('designSize'), 2, 'designSize', positive=True)
    require(manifest.get('coordinates') == 'top-left-y-down', 'coordinates must be top-left-y-down')
    assets = manifest.get('assets')
    require(isinstance(assets, list) and 0 < len(assets) <= 512, 'expected 1–512 assets')
    keys, files, items = set(), set(), []
    for asset in assets:
        require(isinstance(asset, dict), 'asset must be an object')
        key = asset.get('key')
        require(isinstance(key, str) and key.strip() and key not in keys, 'missing or duplicate asset key')
        keys.add(key)
        path = safe_file(manifest_path.parent, asset.get('file'))
        require(path not in files, 'final independent PNG manifest requires one file per role')
        files.add(path)
        info = inspect(path)
        require(asset.get('sha256') == info['sha256'], f'{key}: SHA-256 mismatch')
        vector(asset.get('pixelSize'), 2, f'{key}: pixelSize', positive=True, integer=True)
        require(asset['pixelSize'] == info['pixelSize'], f'{key}: pixel size mismatch')
        vector(asset.get('displaySize'), 2, f'{key}: displaySize', positive=True)
        mode = asset.get('resizeMode', 'uniform')
        require(mode in ('uniform', 'stretch'), f'{key}: unsupported resize mode')
        if mode == 'uniform':
            w, h = asset['pixelSize']; dw, dh = asset['displaySize']
            require(math.isclose(dw / w, dh / h, rel_tol=1e-5, abs_tol=1e-9), f'{key}: nonuniform display scale')
        else:
            require(isinstance(asset.get('notes'), str) and asset['notes'].strip(), f'{key}: explain intentional stretch in notes')
        transparency = asset.get('transparency')
        require(transparency in ('required', 'opaque', 'any'), f'{key}: declare transparency')
        require(info['visibleBounds'] is not None, f'{key}: image is completely invisible')
        if transparency == 'required':
            require(info['alpha']['transparent'] > 0, f'{key}: no fully transparent pixels')
        if transparency == 'opaque':
            require(info['alpha']['range'] == [255, 255], f'{key}: expected opaque background')
        if 'position' in asset:
            vector(asset['position'], 2, f'{key}: position')
        if 'anchor' in asset:
            vector(asset['anchor'], 2, f'{key}: anchor')
            require(all(0 <= v <= 1 for v in asset['anchor']), f'{key}: anchor outside 0–1')
        if 'z' in asset:
            vector([asset['z']], 1, f'{key}: z')
        if 'states' in asset:
            require(isinstance(asset['states'], list) and all(isinstance(s, str) for s in asset['states']), f'{key}: invalid states')
        if 'provenance' in asset:
            require(isinstance(asset['provenance'], dict), f'{key}: provenance must be an object')
        items.append(dict(key=key, **info))
    return manifest, dict(technicalStatus='passed', visualApproval='not-assessed', assets=items,
                          limitations=['No semantic, edge-quality, provenance-authenticity or layout approval inferred.'])


def preview(manifest_path, output):
    manifest, report = check(manifest_path)
    cards = []
    for asset in manifest['assets']:
        data = safe_file(manifest_path.parent, asset['file']).read_bytes()
        require(sha(data) == asset['sha256'], 'asset changed while building preview')
        uri = 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
        label = html.escape(asset.get('label', asset['key']))
        meta = html.escape(dumps(asset))
        dw, dh = asset['displaySize']
        cards.append(f'<article><h2>{label}</h2><button class="tile" aria-label="放大 {label}"><img alt="{label}" src="{uri}" data-w="{dw}" data-h="{dh}"></button><p>PNG {asset["pixelSize"][0]} × {asset["pixelSize"][1]} · 设计 {dw} × {dh}</p><details><summary>文件身份与用途</summary><pre>{meta}</pre></details></article>')
    title = html.escape(manifest['id'])
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>资源审核</title><style>
*{box-sizing:border-box}body{margin:0;padding:24px;background:#f3f4f5;color:#20282d;font:16px/1.5 system-ui;--surface:repeating-conic-gradient(#ddd 0% 25%,#fff 0% 50%)}
header{max-width:1200px;margin:auto}nav{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}button,select,input{font:inherit}button,select{padding:8px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;max-width:1200px;margin:auto}
article{background:white;padding:16px;border-radius:12px;min-width:0}h2{font-size:18px;overflow-wrap:anywhere}.tile,.large{background:var(--surface);background-size:24px 24px}.tile{width:100%;height:220px;display:flex;align-items:center;justify-content:center;border:0;cursor:zoom-in}.tile img{max-width:100%;max-height:100%;object-fit:contain}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}dialog{width:94vw;max-height:94vh;border:1px solid #bbb;border-radius:12px}dialog::backdrop{background:#0009}.large{height:70vh;overflow:auto;display:flex;align-items:center;justify-content:center}.large img{max-width:100%;max-height:100%;object-fit:contain}.large.exact{display:block}.large.exact img{max-width:none;max-height:none;object-fit:fill}
</style><header><h1>__TITLE__ · 逐件资源审核</h1><p>实际 PNG 原字节。技术校验通过不代表审美批准；棋盘格来自网页背景。设计尺寸预览按 1 设计单位 = 1 CSS px 展示，不代表目标设备上的最终大小。</p>
<nav><label>底色 <select id="bg"><option value="checker">棋盘</option><option value="#ffffff">白</option><option value="#152025">暗</option><option value="#808080">灰</option><option value="custom">页面底色</option></select></label><input id="color" aria-label="页面底色" type="color" value="#e5d9bb"></nav></header><main>__CARDS__</main>
<dialog id="viewer"><nav><strong id="name"></strong><select id="mode" aria-label="查看尺寸"><option value="fit">适应窗口</option><option value="pixels">原始像素</option><option value="design">设计尺寸</option></select><button id="close">关闭</button></nav><div class="large" id="large"></div></dialog>
<script>
const bg=document.getElementById('bg'),color=document.getElementById('color'),viewer=document.getElementById('viewer'),large=document.getElementById('large'),mode=document.getElementById('mode');let current;
function surface(){document.body.style.setProperty('--surface',bg.value==='checker'?'repeating-conic-gradient(#ddd 0% 25%,#fff 0% 50%)':bg.value==='custom'?color.value:bg.value)}bg.onchange=surface;color.oninput=surface;
function sizing(){if(!current)return;large.classList.toggle('exact',mode.value!=='fit');current.style.width=mode.value==='design'?current.dataset.w+'px':mode.value==='pixels'?current.naturalWidth+'px':'';current.style.height=mode.value==='design'?current.dataset.h+'px':mode.value==='pixels'?current.naturalHeight+'px':''}mode.onchange=sizing;
document.querySelectorAll('.tile').forEach(b=>b.onclick=()=>{current=b.querySelector('img').cloneNode();large.replaceChildren(current);document.getElementById('name').textContent=current.alt;mode.value='fit';sizing();viewer.showModal()});document.getElementById('close').onclick=()=>viewer.close();
</script></html>'''.replace('__TITLE__', title).replace('__CARDS__', ''.join(cards))
    write_new(output, page)
    return dict(output=str(output), **report)


def slice_png(source, rect, output):
    vector(rect, 4, 'source rect', integer=True)
    x, y, w, h = rect
    require(source.stat().st_size <= MAX_BYTES, 'PNG exceeds 32 MiB')
    data = source.read_bytes()
    image = decode(data)
    require(x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= image.width and y+h <= image.height, 'crop outside source')
    cropped = image.crop((x, y, x+w, y+h))
    buffer = io.BytesIO(); cropped.save(buffer, format='PNG')
    result = buffer.getvalue()
    require(decode(result).tobytes() == cropped.tobytes(), 'decoded crop pixels differ')
    write_new(output, result)
    return dict(file=str(output), **inspect_bytes(result), provenance=dict(sourceName=source.name,
                sourceSHA256=sha(data), sourcePixelSize=list(image.size), sourceRect=rect,
                operation='RGBA pixel crop; no background removal', decodedPixelsEqual=True))


def file_inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), f'symlink refused: {path.relative_to(root)}')
        if path.is_dir():
            continue
        require(path.is_file(), 'nonregular file refused')
        name = path.relative_to(root).as_posix()
        safe_file(root, name)
        result[name] = path
    return result


def snapshot(root, entry, output):
    root = root.resolve()
    require(root.is_dir(), 'missing delivery directory')
    require(not output.exists() and not output.is_symlink(), 'output already exists')
    require(not output.resolve().is_relative_to(root), 'snapshot output cannot be inside its source')
    safe_file(root, entry)
    files = file_inventory(root)
    require('snapshot.json' not in files, 'source already contains snapshot.json; use a new working version')
    before = {name: sha(path.read_bytes()) for name, path in files.items()}
    output.mkdir(parents=True, exist_ok=False)
    for name, path in files.items():
        data = path.read_bytes()
        require(sha(data) == before[name], 'source changed while freezing')
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        write_new(target, data)
    require({name: sha(path.read_bytes()) for name, path in file_inventory(root).items()} == before, 'source changed while freezing')
    record = dict(format='ui-skin-snapshot-v1', entry=entry, files=before,
                  scope='Byte integrity only; not visual approval or proof of offline execution.')
    write_new(output / 'snapshot.json', dumps(record))
    return verify_snapshot(output)


def verify_snapshot(root):
    record = read_json(safe_file(root, 'snapshot.json'))
    require(record.get('format') == 'ui-skin-snapshot-v1', 'unsupported snapshot')
    files = record.get('files')
    require(isinstance(files, dict) and files and 'snapshot.json' not in files, 'invalid snapshot files')
    require(isinstance(record.get('entry'), str) and record['entry'] in files, 'entry not bound to snapshot')
    require(set(file_inventory(root)) == set(files) | {'snapshot.json'}, 'snapshot files missing or added')
    for name, digest in files.items():
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'invalid SHA-256')
        require(sha(safe_file(root, name).read_bytes()) == digest, f'snapshot mismatch: {name}')
    return dict(technicalStatus='passed', files=len(files), entry=record['entry'],
                visualApproval='not-assessed', offlineExecution='not-assessed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('example', help='print the minimal resource manifest')
    for command in ('inspect', 'check', 'preview', 'slice', 'snapshot', 'verify-snapshot'):
        child = sub.add_parser(command)
        child.add_argument('path', type=Path)
        if command in ('preview', 'slice', 'snapshot'):
            child.add_argument('--output', type=Path, required=True)
        if command == 'slice':
            child.add_argument('--rect', type=int, nargs=4, required=True, metavar=('X', 'Y', 'W', 'H'))
        if command == 'snapshot':
            child.add_argument('--entry', default='prototype.html')
    args = parser.parse_args()
    try:
        if args.command == 'example': result = example()
        elif args.command == 'inspect': result = inspect(args.path)
        elif args.command == 'check': result = check(args.path)[1]
        elif args.command == 'preview': result = preview(args.path, args.output)
        elif args.command == 'slice': result = slice_png(args.path, args.rect, args.output)
        elif args.command == 'snapshot': result = snapshot(args.path, args.entry, args.output)
        else: result = verify_snapshot(args.path)
        print(dumps(result), end='')
    except (Invalid, OSError, ValueError, TypeError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
