import os, requests
from pathlib import Path

OLLAMA = os.getenv("OLLAMA_BASE_URL")
OUT = Path("/mnt/f/ObsidianVault/AI-Inbox")

def run(file):
    text = Path(file).read_text()

    r = requests.post(f"{OLLAMA}/api/generate",
        json={
            "model":"qwen2.5:7b",
            "prompt":f"整理成Obsidian笔记:\n{text}",
            "stream":False
        })

    out = OUT/(Path(file).stem+".md")
    out.write_text(r.json()["response"])

if __name__=="__main__":
    import sys
    run(sys.argv[1])
