import os, requests, chromadb
from pathlib import Path

OLLAMA = os.getenv("OLLAMA_BASE_URL")

client = chromadb.HttpClient(host="localhost", port=8000)
col = client.get_or_create_collection("docs")

def embed(t):
    r = requests.post(f"{OLLAMA}/api/embeddings",
        json={"model":"nomic-embed-text","prompt":t})
    return r.json()["embedding"]

def ingest(file):
    text = Path(file).read_text()
    chunks = [text[i:i+500] for i in range(0,len(text),400)]

    for i,c in enumerate(chunks):
        col.add(
            ids=[f"{file}-{i}"],
            documents=[c],
            embeddings=[embed(c)]
        )

if __name__=="__main__":
    import sys
    ingest(sys.argv[1])
