import asyncio
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from CORE.engines.explainer import ExplanationEngine

# Define the models to benchmark
MODELS = [
    {"id": "llama-3.3-70b", "name": "Llama 3.3-70b (AgentRouter)", "cost_per_m": 0.60},
    {"id": "gpt-4o", "name": "GPT-4o (AgentRouter)", "cost_per_m": 5.00},
    {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet (AgentRouter)", "cost_per_m": 3.00},
    {"id": "deepseek-chat", "name": "DeepSeek V3 (AgentRouter)", "cost_per_m": 1.00},
]

# Test findings to evaluate
TEST_FINDINGS = [
    {
        "finding": {
            "canonical_rule_id": "SEC-001",
            "rule_id": "B105",
            "severity": "high",
            "category": "security",
            "file": "auth.py",
            "line": 42,
            "message": "Hardcoded password detected",
        },
        "snippet": "def connect_db():\n    db_password = 'super_secret_password'\n    db.connect('user', db_password)",
    },
    {
        "finding": {
            "canonical_rule_id": "SOLID-001",
            "rule_id": "PLR0913",
            "severity": "medium",
            "category": "design",
            "file": "utils.py",
            "line": 15,
            "message": "Too many arguments to function call (6 > 5)",
        },
        "snippet": "def process_data(user, data, options, cache, db_conn, logger):\n    pass",
    },
    {
        "finding": {
            "canonical_rule_id": "SEC-005",
            "rule_id": "B311",
            "severity": "medium",
            "category": "security",
            "file": "crypto.py",
            "line": 10,
            "message": "Standard pseudo-random generators are not suitable for security/cryptographic purposes.",
        },
        "snippet": "import random\n\ndef generate_token():\n    return str(random.random())",
    },
]


async def evaluate_model(
    client: httpx.AsyncClient, engine: ExplanationEngine, model_info: dict, base_url: str, api_key: str
):
    print(f"Evaluating {model_info['name']}...")
    model_id = model_info["id"]

    total_latency = 0
    total_cost = 0
    cites_rule_count = 0
    total_self_eval = 0

    for item in TEST_FINDINGS:
        finding = item["finding"]
        snippet = item["snippet"]

        prompt = engine._build_evidence_grounded_prompt(finding, snippet)

        start_time = time.time()

        payload = {
            "model": model_id,
            "max_tokens": 300,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await client.post(
                base_url, json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            latency = int((time.time() - start_time) * 1000)
            response_text = data["choices"][0]["message"]["content"].strip()
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            # Check cites rule
            canonical_id = finding.get("canonical_rule_id", "")
            cites_rule = canonical_id in response_text
            if cites_rule:
                cites_rule_count += 1

            # Self eval
            eval_payload = {
                "model": model_id,
                "max_tokens": 50,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Rate this code review explanation on a scale of 1-5 for each criterion.\n\n**Explanation to evaluate:**\n{response_text}\n\n**Original issue:** {canonical_id} - {finding.get('message', '')}\n\nRate each criterion (1=poor, 5=excellent):\n1. Relevance: Does this explanation directly address the code issue?\n2. Accuracy: Is the technical information correct?\n3. Clarity: Is the explanation clear and easy to understand?\n\nRespond ONLY in this exact format:\nRelevance: X\nAccuracy: X\nClarity: X",
                    }
                ],
            }
            eval_response = await client.post(
                base_url, json=eval_payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=15.0
            )
            eval_data = eval_response.json()
            eval_text = eval_data["choices"][0]["message"]["content"].strip()

            scores = []
            for line in eval_text.split("\n"):
                for key in ["Relevance", "Accuracy", "Clarity"]:
                    if key.lower() in line.lower():
                        try:
                            val = int("".join(c for c in line.split(":")[-1] if c.isdigit())[:1])
                            scores.append(min(max(val, 1), 5))
                        except Exception:
                            pass

            avg_score = sum(scores) / len(scores) if scores else 3.0
            total_self_eval += avg_score

            total_latency += latency
            # Cost per token
            cost = (tokens_used / 1_000_000) * model_info["cost_per_m"]
            total_cost += cost

        except Exception as e:
            print(f"Error with {model_id}: {e}")

    num_tests = len(TEST_FINDINGS)
    return {
        "model": model_info["name"],
        "cites_rule_pct": (cites_rule_count / num_tests) * 100 if num_tests else 0,
        "avg_latency": total_latency / num_tests if num_tests else 0,
        "self_eval_score": total_self_eval / num_tests if num_tests else 0,
        "cost_per_finding": total_cost / num_tests if num_tests else 0,
    }


async def main():
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("AGENTROUTER_API_KEY")
    if not api_key:
        print("Error: AGENTROUTER_API_KEY environment variable is missing.")
        print("Please provide it to run the benchmarks.")
        sys.exit(1)

    base_url = "https://agentrouter.org/v1/chat/completions"
    engine = ExplanationEngine()

    results = []

    async with httpx.AsyncClient() as client:
        for model in MODELS:
            res = await evaluate_model(client, engine, model, base_url, api_key)
            results.append(res)

    # Output markdown table
    print("\n# A/B Model Comparison Results\n")
    print("| Metric | " + " | ".join([r["model"] for r in results]) + " |")
    print("|--------|" + "|".join(["---" for _ in results]) + "|")

    cites_row = "| Cites Rule % | " + " | ".join([f"{r['cites_rule_pct']:.1f}%" for r in results]) + " |"
    latency_row = "| Avg Latency | " + " | ".join([f"{r['avg_latency']:.0f}ms" for r in results]) + " |"
    eval_row = "| Self-Eval Score | " + " | ".join([f"{r['self_eval_score']:.1f}/5" for r in results]) + " |"
    cost_row = "| Cost / Finding | " + " | ".join([f"${r['cost_per_finding']:.5f}" for r in results]) + " |"

    print(cites_row)
    print(latency_row)
    print(eval_row)
    print(cost_row)


if __name__ == "__main__":
    asyncio.run(main())
