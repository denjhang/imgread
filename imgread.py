# -*- coding: utf-8 -*-
"""imgread v2 —— 本地识图全家桶（零配置一条命令；纯 CPU 经典技术：OpenCV + RapidOCR）

用法:
  imgread <图片路径> [模式]
模式:
  auto(默认)  智能全套：类型判定 → 结构+形状+OCR 自适应组合 + 一句话结论
  ocr         只文字（按行合并，带坐标）
  shapes      只形状（圆/三角/正方/矩形/多边形，坐标+颜色+填充率）
  scan        只色块结构（主色/暗色占比/对称性/内容区域）
  sample x y w h   区域采样（0..1 小数或像素）
  批量: 多个路径一次丢进来也行

设计原则（小模型友好）:
  - 一次调用出全部结论，不用再来回追问
  - 永不抛栈：任何内部错误都降级成提示行
  - 输出全中文、坐标明确、长度有界（防撑爆上下文）
"""
import sys, os, glob

def analyze(path, mode, extra):
    from PIL import Image
    import numpy as np
    out = []
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        return [f"无法打开 {path}: {e}"]
    W, H = img.size
    kb = os.path.getsize(path) // 1024
    out.append(f"■ {os.path.basename(path)} | {W}x{H} | {kb}KB | 模式={mode}")
    a = np.asarray(img)

    # ---------- 结构 ----------
    def scan():
        small = np.asarray(img.resize((32, 18))).astype(int)
        flat = small.reshape(-1, 3)
        dark = (flat.sum(1) < 90).mean()
        q = (small // 32) * 32
        colors, counts = np.unique(q.reshape(-1, 3), axis=0, return_counts=True)
        order = counts.argsort()[::-1][:5]
        total = counts.sum()
        parts = [f"#{'%02x%02x%02x' % tuple(colors[i])} {counts[i]*100//total}%" for i in order]
        sym = (abs(small - small[:, ::-1]).mean() < 24)
        bg = colors[order[0]]
        mask = (np.abs(q - bg).sum(2) > 96)
        ys, xs = np.where(mask)
        out.append(f"[结构] 暗色 {dark*100:.0f}% | 左右对称 {'是' if sym else '否'} | 主色: " + " ".join(parts))
        if len(xs) > 4:
            gx = (xs / 32 * W).astype(int); gy = (ys / 18 * H).astype(int)
            out.append(f"[结构] 内容区 约x{gx.min()}-{gx.max()} y{gy.min()}-{gy.max()} (占{mask.mean()*100:.0f}%)")

    # ---------- 形状（经典 CV：按颜色分割连通域，游戏网格友好） ----------
    def shapes():
        import cv2
        q = (a.astype(int) // 32) * 32
        flat = q.reshape(-1, 3)
        colors, counts = np.unique(flat, axis=0, return_counts=True)
        order = counts.argsort()[::-1]
        bg = colors[order[0]]
        found = []
        min_area = max(150, W * H // 3000)
        for ci in order[:14]:
            col = colors[ci]
            if counts[ci] * 9 < min_area:   # 占比太小的色块跳过
                continue
            if abs(col - bg).sum() < 60:    # 接近背景色跳过
                continue
            mask = np.all(q == col, axis=2).astype(np.uint8) * 255
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                area = cv2.contourArea(c)
                if area < min_area:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                if w < 8 or h < 8:
                    continue
                peri = cv2.arcLength(c, True)
                n = len(cv2.approxPolyDP(c, 0.04 * peri, True))
                (_, _), r = cv2.minEnclosingCircle(c)
                circ = area / (3.14159 * r * r) if r > 0 else 0
                fill = area / (w * h)
                if circ > 0.82 and n >= 6: sh = "圆形"
                elif n == 3: sh = "三角形"
                elif n == 4:
                    ar = w / float(h)
                    sh = "正方形" if 0.85 <= ar <= 1.18 else ("横矩形" if ar > 1.18 else "竖矩形")
                elif n == 5: sh = "五边形"
                else: sh = "多边形" if n <= 8 else "不规则形"
                found.append((area, f"  {sh} x{x} y{y} {w}x{h} 填充{fill*100:.0f}% #{'%02x%02x%02x' % tuple(col)}"))
        found.sort(reverse=True)
        out.append(f"[形状] 检出 {len(found)} 个图形（按颜色分割）")
        out.extend(s for _, s in found[:20])

    # ---------- OCR（按行合并） ----------
    def ocr():
        try:
            from rapidocr_onnxruntime import RapidOCR
            big = max(W, H)
            target = img if big <= 2000 else img.resize((int(W * 2000 / big), int(H * 2000 / big)))
            tmp = target.save(os.environ.get("TEMP", ".").replace("\\", "/") + "/_imgread_tmp.png")
            path2 = os.environ.get("TEMP", ".") + "/_imgread_tmp.png"
            res, _ = RapidOCR()(path2)
            if not res:
                out.append("[文字] 未检测到文字")
                return 0
            scale = W / target.size[0]
            lines = []
            for box, text, conf in res:
                if conf < 0.5: continue
                x, y = int(box[0][0] * scale), int(box[0][1] * scale)
                lines.append((y, x, text, conf))
            lines.sort()
            # y 相近合并成行
            merged = []
            for y, x, t, c in lines:
                if merged and abs(merged[-1][0] - y) < 14:
                    merged[-1][1] += "  |  " + t
                else:
                    merged.append([y, t])
            out.append(f"[文字] {len(merged)} 行")
            for y, t in merged[:30]:
                out.append(f"  y{y}: {t}")
            return len(merged)
        except Exception as e:
            out.append(f"[文字] OCR 降级失败: {e}")
            return 0

    # ---------- 类型判定 + 自适应 ----------
    n_text = 0
    if mode == "auto":
        scan(); shapes(); n_text = ocr()
        # 一句话结论（确定性规则，不猜语义）
        gray_std = float(a.std())
        hints = []
        if n_text >= 5: hints.append("文字为主的界面/文档，重点看[文字]区")
        elif n_text > 0: hints.append(f"含 {n_text} 行文字的界面/游戏画面")
        else: hints.append("无文字的图形/照片，重点看[形状]和[结构]")
        out.append(f"[结论] {hints[0]} | 画面复杂度(灰度σ)={gray_std:.0f}")
    elif mode == "scan": scan()
    elif mode == "shapes": shapes()
    elif mode == "ocr": ocr()
    elif mode == "sample":
        if len(extra) < 4:
            out.append("sample 需要 x y w h")
        else:
            x, y, w, h = (float(v) for v in extra[:4])
            if x <= 1 and y <= 1 and w <= 1 and h <= 1:
                x, y, w, h = x * W, y * H, w * W, h * H
            x, y = max(0, int(x)), max(0, int(y))
            w, h = min(W - x, int(w)), min(H - y, int(h))
            crop = np.asarray(img.crop((x, y, x + w, y + h))).reshape(-1, 3)
            out.append(f"[采样] x{x} y{y} {w}x{h}: 均值#{'%02x%02x%02x' % tuple(crop.mean(0).astype(int))} "
                       f"中位#{'%02x%02x%02x' % tuple(np.median(crop,0).astype(int))} 色彩数~{len(np.unique(crop//32, axis=0))}")
    return out

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 1
    paths, mode, extra = [], "auto", []
    if args and args[-1] in ("auto", "ocr", "shapes", "scan"):
        mode = args[-1]; args = args[:-1]
    elif "sample" in args:
        i = args.index("sample")
        mode = "sample"
        extra = args[i + 1:i + 5]           # x y w h
        args = args[:i] + args[i + 5:]
    for a in args:
        if os.path.isdir(a):
            paths.extend(glob.glob(os.path.join(a, "*.png")) + glob.glob(os.path.join(a, "*.jpg")))
        elif a.startswith("-"):
            continue
        else:
            paths.append(a)
    rc = 0
    for p in paths:
        try:
            print("\n".join(analyze(p, mode, extra)))
        except Exception as e:
            print(f"■ {p} 分析失败(降级): {e}")
            rc = 1
    return rc

if __name__ == "__main__":
    sys.exit(main())
