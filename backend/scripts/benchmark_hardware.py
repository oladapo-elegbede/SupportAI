import time
import json
import httpx

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:3b"

SAMPLE_CONTEXT = """
SupportAI is an AI-powered customer support SaaS platform.
It uses Retrieval-Augmented Generation (RAG) to ground customer support responses in verified documentation.
SupportAI stores vectors using PostgreSQL and pgvector.
"""

SAMPLE_QUERY = "What database does SupportAI use to store vectors?"


def benchmark_embeddings():
    print("\n" + "=" * 50)
    print("1. BENCHMARKING EMBEDDING GENERATION (nomic-embed-text)")
    print("=" * 50)

    payload = {
        "model": EMBEDDING_MODEL,
        "prompt": SAMPLE_CONTEXT,
    }

    start_time = time.perf_counter()
    response = httpx.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=30.0)
    elapsed = (time.perf_counter() - start_time) * 1000

    if response.status_code == 200:
        data = response.json()
        vector_dims = len(data.get("embedding", []))
        print(f"✅ Embedding successful!")
        print(f"   • Vector dimensions: {vector_dims}")
        print(f"   • Total embedding latency: {elapsed:.2f} ms")
        return elapsed
    else:
        print(f"❌ Embedding failed: {response.status_code} - {response.text}")
        return None


def benchmark_llm():
    print("\n" + "=" * 50)
    print(f"2. BENCHMARKING LLM INFERENCE ({LLM_MODEL})")
    print("=" * 50)

    prompt = f"""
INSTRUCTIONS: Answer the question based ONLY on the context below.

CONTEXT:
{SAMPLE_CONTEXT}

QUESTION:
{SAMPLE_QUERY}

ANSWER:
"""

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    print("• Sending query to local model... (Warm-up / load into RAM may take a few seconds)")
    start_time = time.perf_counter()
    response = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120.0)
    total_elapsed = time.perf_counter() - start_time

    if response.status_code == 200:
        data = response.json()
        ans = data.get("response", "").strip()
        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 1)
        load_duration_ns = data.get("load_duration", 0)

        eval_sec = eval_duration_ns / 1e9 if eval_duration_ns else 1
        load_sec = load_duration_ns / 1e9 if load_duration_ns else 0
        tokens_per_sec = eval_count / eval_sec if eval_sec > 0 else 0

        print(f"✅ LLM Generation successful!")
        print(f"\n--- GENERATED ANSWER ---")
        print(ans)
        print("------------------------\n")
        print(f"   • Total elapsed time: {total_elapsed:.2f} seconds")
        print(f"   • Model load time: {load_sec:.2f} seconds")
        print(f"   • Tokens generated: {eval_count}")
        print(f"   • Generation speed: {tokens_per_sec:.2f} tokens/sec")
        return {
            "total_sec": total_elapsed,
            "tokens_per_sec": tokens_per_sec,
        }
    else:
        print(f"❌ LLM generation failed: {response.status_code} - {response.text}")
        return None


if __name__ == "__main__":
    print("🚀 STARTING SUPPORTAI HARDWARE BENCHMARK")
    print(f"Targeting Ollama at {OLLAMA_URL}")

    emb_time = benchmark_embeddings()
    llm_stats = benchmark_llm()

    print("\n" + "=" * 50)
    print("HARDWARE BENCHMARK SUMMARY")
    print("=" * 50)
    if emb_time and llm_stats:
        print(f"• Embedding Speed: {emb_time:.2f} ms")
        print(f"• LLM Response Time: {llm_stats['total_sec']:.2f} seconds")
        print(f"• LLM Generation Rate: {llm_stats['tokens_per_sec']:.2f} tokens/sec")

        if llm_stats['total_sec'] <= 15:
            print("\n🟢 VERDICT: PERFORMS GREAT! qwen2.5:3b is highly responsive on your machine.")
        elif llm_stats['total_sec'] <= 35:
            print("\n🟡 VERDICT: ACCEPTABLE FOR LOCAL DEV! qwen2.5:3b is usable. Keep as primary.")
        else:
            print("\n🔴 VERDICT: SLOW. Consider pulling llama3.2:1b for faster local iteration.")
    print("=" * 50 + "\n")
