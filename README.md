# imgread — 零配置本地识图（给纯文本模型一双眼睛）

一条命令读图，输出结构化文字证据。纯 CPU 经典 CV + RapidOCR，不联网、不占显卡、永不崩。专为小模型 agent 设计的视觉外挂。

```bash
imgread 截图.png              # auto：结构 + 形状 + OCR + 结论，一次全出
imgread 截图.png shapes       # 形状识别：圆形/三角/正方形/横竖矩形 + 坐标 + 颜色 + 填充率
imgread 截图.png ocr          # 文字识别：按行合并，带 y 坐标
imgread 截图.png scan         # 色块结构：主色/暗色占比/对称性/内容区域
imgread 截图.png sample x y w h   # 区域像素采样（0..1 小数或像素）
imgvlm 图片.png "这是什么？"    # 双层：imgread 证据层 + 本地 VLM 语义层
```

实测输出（一张俄罗斯方块截图）：

```
■ _test_grid.png | 400x500 | 模式=auto
[结构] 暗色 78% | 左右对称 是 | 主色: #000000 76% ...
[形状] 检出 6 个图形（按颜色分割）
  正方形 x184 y132 71x71 填充97% #a020e0
  横矩形 x148 y276 143x35 填充96% #2060e0
  竖矩形 x40 y204 35x71 填充96% #20c040   ...
[文字] 1 行
  y17: TETRIS分数4800
[结论] 含 1 行文字的界面/游戏画面
```

## 安装（Windows，双击即装）

1. 装 Python 3.10+（勾选 Add to PATH）
2. 下载 Release 的 zip，解压到任意目录
3. 双击 `install.bat`
4. **开个新终端**，`imgread 你的图.png` 即用

安装器自动完成：venv + 依赖（~200MB，含 RapidOCR 的 onnx 模型）+ `imgread`/`imgvlm` 命令 + 用户 PATH。

## 设计原则（为什么这么造）

- **小模型友好**：一次调用出全部结论，不用来回追问；输出全中文带坐标、长度有界（不撑爆上下文）；永不抛栈（内部错误降级成一行提示）
- **确定性优先**：形状用按颜色分割的连通域（Canny 边缘检测在游戏网格上会粘连相邻方块——踩过的坑）；OCR 用 RapidOCR（Windows 自带 OCR 常缺语言包——踩过的坑）
- **零决策接口**：给小模型的接口不许有"发现/连接/配置"环节。这也是它取代 MCP 形态的原因：实测模型面对未暴露的 MCP 工具会浪费七八个回合手写 JSON-RPC
- **双层架构**：imgread 是证据层（永不出错），imgvlm 挂一个本地 VLM（默认 8087 端口的 Qwen3-VL-4B）做语义层（"这是香蕉"）；VLM 不在线自动降级纯证据层
- 有趣对照：经典 CV 在游戏截图这类任务上**完胜** 0.1B 级 VLM（后者看图说话"五个黄色圆圈"，图里只有三个图形）——看图要么用确定性算法、要么用足够大的模型

## 给 agent 挂技能（可选）

`skill/SKILL.md` 是 ZCode（或同类 harness）的技能说明书，铁律："用户提到图片 → 立即执行 imgread，禁止说看不了图，禁止找 MCP"。复制到技能目录即可。

## 相关项目

- [picturereader](https://github.com/jing-hy/picturereader)（jing-hy）—— 本工具链哲学的源头（"图 → 序列化证据 → 进上下文"）
- [llama-monitor](https://github.com/denjhang/llama-monitor) —— 配套的多模型监控

## License

MIT
