# 公共 UI 换皮技能包

三个项目级入口，覆盖设计 → 资源 → 离线网页原型，不包含原生接入。安装文件全部位于 `.agents/skills/`，没有对原项目、个人路径或外部规范文档的运行依赖。

| 入口 | 可以这样测试 |
|---|---|
| `$ui-skin-design` | 按我提供的页面截图设计新风格，先交一张母版与完整组件清单。 |
| `$ui-skin-assets` | 按选定设计准备独立切图，复用已有合格资源，给我逐件审核网页。 |
| `$ui-skin-prototype` | 使用这些切图组装离线交互原型，覆盖标准、长内容和空态。 |

从任何阶段开始都可以。已有授权允许连续推进；用户要求阶段评审时按指定阶段交付。技能不会自动接入业务、合并分支或上传到固定服务。

## 文件与迁移

```text
.agents/skills/
├── ui-skin-design/SKILL.md
├── ui-skin-assets/
│   ├── SKILL.md
│   └── scripts/{assets.py,requirements.txt}
└── ui-skin-prototype/
    ├── SKILL.md
    └── assets/preview-shell.html
```

每个目录另有轻量的 `agents/openai.yaml` 界面信息。复制到其他项目时将三个技能目录一起放入该项目的 `.agents/skills/`，不需要复制本 README、测试或开发依赖。资源检查工具只维护一份，位于资源 skill 内。

若当前会话尚未发现新技能，可在本项目新任务中测试，或直接要求读取对应 `SKILL.md` 使用；文件存在不等于当前会话已刷新技能列表。图像生成/编辑与浏览器依赖目标环境实际提供的能力，不随本包附送，也不绑定某个账号或服务。

## 工具检查

Python 3.10+；图片命令需要 Pillow，快照命令只用标准库。优先使用已有含 Pillow 的运行时，或创建项目虚拟环境：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python .agents/skills/ui-skin-assets/scripts/assets.py example
```

生成两张简单几何 PNG 及审核/原型测试页（输出目录必须不存在）：

```sh
.venv/bin/python tests/make_demo.py .ui-skin-check
```

有 Playwright 的环境可以运行 `node tests/browser_smoke.cjs .ui-skin-check`。可选环境变量 `UI_SKIN_PLAYWRIGHT_PATH` 指定 Playwright 模块位置，`UI_SKIN_CHROME_PATH` 指定浏览器可执行文件；默认使用已安装的 Playwright Chromium。本项是开发检查，不是技能运行依赖。

只有使用 skill 的资源工具时需要 `scripts/requirements.txt` 中的 Pillow；PyYAML 仅用于开发时校验技能元数据。自动测试在临时目录生成简单几何图片，不调用生图服务、不上传图片、不构建原生项目。

共用工具提供 `inspect`、`slice`、`check`、`preview`、`snapshot`、`verify-snapshot`，各命令支持 `--help`。资源清单格式和命令示例已包含在资源 skill 内，无需再阅读独立契约文档。

`preview-shell.html` 仅提供比例切换、设计单位容器和按压反馈；页面布局、状态与数据仍由 AI 按任务编写，避免以通用渲染器限制设计。它本身不是交付成品。

## 本版边界

- 文件校验不能识别审美、文字错误或所有边缘污染，仍需查看真实图片。
- 工具校验独立静态 PNG；图集、动画、多语言字体等按任务单独交接，不假装已经通用支持。
- 快照绑定完整文件集合和哈希，但不是签名、用户批准或离线运行证明；网页仍须实际体验。
- 这是从现有多页面流程提炼的首版；自动验证不等于已完成新项目的真实设计、切图和原型验收。

2026-09-17 本地验证：三个 skill 均通过 skill-creator 元数据校验；18 项 Python 测试通过，包含复制到另一个临时项目后的独立运行。Chrome 实际通过 file 协议打开测试页，检查像素放大、四底色、点击/键盘、按压恢复、四画幅、状态切换与重置，无页面脚本错误或 HTTP 请求。测试截图和浏览器报告保存在本地 `.ui-skin-check/`，不属于正式美术成果。
