"""Package unmodified built-in outputs. This script never edits PNG pixels."""
from pathlib import Path
import importlib.util, json

prod=Path(__file__).resolve().parent
base=prod.parent
root=prod.parents[3]
spec=importlib.util.spec_from_file_location('assets',root/'.agents/skills/ui-skin-assets/scripts/assets.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
# Content rectangles were checked against the displayed subjects; they are placement
# guides, not crop instructions. Keep the full original canvas and all generated alpha.
rows=[
('panel','主面板','panel-refined.png',[22,30,1671,845],1500,True),
('title','充值标题','title-generated.png',[189,108,1424,673],196,False),
('service','客服按钮','service-generated.png',[224,146,869,863],88,False),
('close','关闭按钮','close-generated.png',[275,208,760,753],88,False),
('tab-selected','选中页签底','tab-selected-generated.png',[48,110,1991,485],274,True),
('tab-normal','未选中页签底','tab-normal-generated.png',[29,129,1989,495],274,True),
('icon-diamond','钻石图标','icon-diamond-generated.png',[101,143,1133,886],62,False),
('icon-coin','金币图标','icon-coin-generated.png',[211,178,865,844],50,False),
('icon-energy','体力图标','icon-energy-generated.png',[325,191,735,861],42,False),
('vip-band','VIP 横条','vip-band-transparent-r01.png',[25,270,2122,181],1317,True),
('vip-badge','VIP 徽章底','vip-badge-generated.png',[36,8,1337,1083],110,True),
('privilege','贵族特权按钮','privilege-generated.png',[359,137,1438,448],195,False),
('card-base','商品卡底','card-base-transparent-r01.png',[34,32,938,1500],246,True),
('buy-base','购买按钮底','buy-base-neutral-transparent.png',[140,101,1791,502],216,True),
('gems-small','10 钻商品插画','gems-small-generated.png',[108,125,1086,1015],139,False),
('gems-single','30 钻商品插画','gems-single-generated.png',[253,149,1040,765],136,False),
('gems-pair','60 钻商品插画','gems-pair-generated.png',[122,126,1193,856],169,False),
('gems-cluster','180 钻商品插画','gems-cluster-generated.png',[137,194,1098,817],179,False),
('gems-pouch','300 钻商品插画','gems-pouch-generated.png',[50,69,1250,1050],216,False),
]
manifest=dict(format='ui-skin-assets-v1',id='shop-xianxia-assets-r01',designSize=[1870,841],coordinates='top-left-y-down',reviewStatus='pending-user-review',assets=[])
master=base.parent/'design-r01/master.png'
mastersha=tool.sha(master.read_bytes())
for key,label,source,rect,width,repaint in rows:
    data=(prod/source).read_bytes();stats=tool.inspect_bytes(data)
    target=base/'png'/(key+'.png')
    tool.write_new(target,data)
    scale=width/rect[2]
    display=[round(v*scale,6) for v in stats['pixelSize']]
    prompts=[str(p.relative_to(base)) for p in prod.glob(key+'*prompt.txt')]
    if key=='panel':prompts=['production/generation-log.json']
    manifest['assets'].append(dict(key=key,label=label,file='png/'+key+'.png',sha256=stats['sha256'],pixelSize=stats['pixelSize'],displaySize=display,transparency='required',resizeMode='uniform',states=['selected'] if key=='tab-selected' else ['unselected'] if key=='tab-normal' else ['normal'],contentRect=rect,provenance=dict(method='builtin-imagegen-redraw-and-extraction' if repaint else 'builtin-imagegen-reference-extraction',master='../design-r01/master.png',masterSha256=mastersha,generatedSource='production/'+source,promptFiles=prompts,localPixelEdits=False,byteIdentity='PNG bytes identical to selected generated output'),notes='保留原始透明留白与 Alpha。displaySize 含留白；contentRect 是主体摆放参考，不是裁切范围。'+('底板有补绘重建，并非母版逐像素裁切。' if repaint else '依照母版局部由内置工具分离，细节可能有重绘差异。')))
tool.write_new(base/'assets.json',tool.dumps(manifest))
_,report=tool.check(base/'assets.json');tool.write_new(base/'technical-check.json',tool.dumps(report))
tool.preview(base/'assets.json',base/'asset-preview.html')
print(json.dumps(dict(assets=len(rows),technicalStatus=report['technicalStatus'],pixelEdits=False),ensure_ascii=False))
