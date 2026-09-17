"""Generate local geometry-only review fixtures; never generates or uploads AI art."""
import argparse
import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assets', ROOT / '.agents/skills/ui-skin-assets/scripts/assets.py')
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = tool.example(); manifest['id'] = 'portable-tool-demo'; manifest['assets'] = []
    for key, color in [('primary', '#317db7'), ('secondary', '#c07531')]:
        image = Image.new('RGBA', (240, 80))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 234, 74), radius=18, fill=color)
        image.save(output / (key + '.png'))
        info = tool.inspect(output / (key + '.png'))
        manifest['assets'].append(dict(key=key, file=key+'.png', sha256=info['sha256'],
            pixelSize=info['pixelSize'], displaySize=[240, 80], transparency='required'))
    tool.write_new(output / 'assets.json', tool.dumps(manifest))
    tool.preview(output / 'assets.json', output / 'asset-preview.html')
    shell = (ROOT / '.agents/skills/ui-skin-prototype/assets/preview-shell.html').read_text()
    shell = shell.replace('<div class="placeholder">添加独立图片、动态文字和控件<br>不要用整页母版叠热点替代组件</div>', '''
<div class="demo-panel"><h2 id="demo-title">独立组件测试</h2><p id="demo-body">测试数据，不执行实际业务</p>
<button id="demo-action" data-press><span class="visual"><img src="primary.png" alt=""><span>操作</span></span></button>
<button id="demo-toggle" data-press><span class="visual"><img src="secondary.png" alt=""><span>开关</span></span></button>
<p id="demo-result" role="status">计数 0 · 关闭</p></div>''')
    shell = shell.replace('</style>', '''
.demo-panel{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);text-align:center;width:480px;max-width:100%;padding:20px;background:#fff;color:#234;border-radius:20px}
.demo-panel button{border:0;padding:0;background:none;width:240px;height:80px;display:block;margin:14px auto}.demo-panel .visual{position:relative;width:100%;height:100%}.demo-panel img{width:100%;height:100%}.demo-panel .visual span{position:absolute;inset:0;display:grid;place-items:center;color:white;font-weight:700}
</style>''')
    shell += '''<script>
let count=0,enabled=false;const result=document.getElementById('demo-result');
function renderResult(){result.textContent=`计数 ${count} · ${enabled?'开启':'关闭'}`}
document.getElementById('demo-action').onclick=()=>{count++;renderResult()};
document.getElementById('demo-toggle').onclick=()=>{enabled=!enabled;renderResult()};
scene.addEventListener('ui-state',e=>{document.getElementById('demo-body').textContent=e.detail.state==='empty'?'暂无内容':e.detail.state==='long'?'这是一段用于检查换行与布局空间的较长示例说明，不连接任何业务服务。':'测试数据，不执行实际业务'});
scene.addEventListener('ui-layout',e=>{document.querySelector('.demo-panel').style.width=Math.min(480,e.detail.width-40)+'px'});resize();
</script>'''
    tool.write_new(output / 'prototype.html', shell)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output', type=Path)
    print(build(parser.parse_args().output))
