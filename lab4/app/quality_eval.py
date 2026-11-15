"""Збирає 10 реальних відповідей LLM. Не виставляє автоматично оцінки correctness."""
import argparse
import json
from llm import explain
from datetime import datetime, timezone
from pathlib import Path
from workflow import build_guide

HERE = Path(__file__).resolve().parent

def call_model(base_url, model, case, guide):
    return explain(base_url.rstrip("/") + "/chat/completions", model, guide, case["description"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--label", choices=["before", "after", "revised"], required=True)
    p.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    args = p.parse_args()
    tests = json.loads((HERE / "test_cases.json").read_text(encoding="utf-8"))
    rows = []
    for case in tests:
        guide = build_guide(case)
        try:
            result = call_model(args.base_url, args.model, case, guide)
            answer = result["text"] if result["ok"] else result.get("answer", "")
            error = None if result["ok"] else result["text"] + " | " + str(result.get("detail", ""))
        except (OSError, ValueError, KeyError, IndexError) as ex:
            answer, error = "", str(ex)
        rows.append({"id": case["id"], "situation": case["description"],
                     "expected_procedure": case["expected_id"], "procedure": guide["id"],
                     "expected_steps": build_guide({"case_id": case["expected_id"]})["steps"],
                     "provided_steps": guide["steps"], "answer": answer,
                     "error": error, "correct": None, "remarks": "Перевірити вручну за expected_steps"})
        print(f"{case['id']}/10: {'відповідь отримано' if answer and not error else 'помилка'}")
    output = HERE.parent / "demo" / f"quality_{args.label}.json"
    output.write_text(json.dumps({"model": args.model, "label": args.label,
                                  "recorded_utc": datetime.now(timezone.utc).isoformat(),
                                  "note": "correct=null, доки не виконане ручне оцінювання", "results": rows},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print("Результат:", output)

if __name__ == "__main__":
    main()
