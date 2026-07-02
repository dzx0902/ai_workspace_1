import os, requests, chromadb

OLLAMA = os.getenv("OLLAMA_BASE_URL")

client = chromadb.HttpClient(host="localhost", port=8000)
col = client.get_or_create_collection("docs")

def embed(q):
    return requests.post(f"{OLLAMA}/api/embeddings",
        json={"model":"nomic-embed-text","prompt":q}).json()["embedding"]

def ask(prompt):
    return requests.post(f"{OLLAMA}/api/generate",
        json={"model":"qwen2.5:7b","prompt":prompt,"stream":False}
    ).json()["response"]

def query(q):
    res = col.query(query_embeddings=[embed(q)], n_results=3)
    ctx = "\n".join(res["documents"][0])
    print(ask(f"根据以下内容回答:\n{ctx}\n问题:{q}"))

if __name__=="__main__":
    import sys
    query(sys.argv[1])
