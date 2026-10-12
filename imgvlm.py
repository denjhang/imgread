# -*- coding: utf-8 -*-
"""imgvlm —— 迷你视觉外援（本地 Qwen3-VL-4B @ 8087，GPU1）
用法:
  imgvlm <图片路径> [问题]        # 默认问题="这张图片里有什么？简要描述"
底层: imgread 先出确定性证据(结构/文字)，VLM 补语义理解，两层合并输出。
未启动/失败时自动降级为纯 imgread 结果，永不空手而归。
"""
import sys, os, json, base64, subprocess

VLM = "http://127.0.0.1:8087"

def imgread_text(path):
    r = subprocess.run([r"E:\tools\rapid_venv\Scripts\python.exe", r"D:\tools\imgread\imgread.py", path],
                       capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    return r.stdout or ""

def vlm_ask(path, question):
    import urllib.request
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    body = {
        "model": "qwen3-vl-4b",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": question + "\n（中文简要回答，50-150字，只说图里确定有的东西）"},
        ]}],
        "max_tokens": 500, "temperature": 0.2,
    }
    req = urllib.request.Request(VLM + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=180))
    return r["choices"][0]["message"].get("content") or ""

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 1
    path = args[0]
    question = " ".join(args[1:]) or "这张图片里有什么？简要描述"
    if not os.path.exists(path):
        print(f"错误: 文件不存在 {path}"); return 1
    print(f"■ {os.path.basename(path)} | 问题: {question}")
    # 第一层：确定性证据
    try:
        print(imgread_text(path))
    except Exception as e:
        print(f"[imgread 降级] {e}")
    # 第二层：语义外援
    try:
        print("[语义外援 Qwen3-VL-4B]")
        print("  " + vlm_ask(path, question))
    except Exception as e:
        print(f"[语义外援不可用，仅证据层] {type(e).__name__}: 启动命令: start-qwen3vl-4b.bat")
    return 0

if __name__ == "__main__":
    sys.exit(main())
