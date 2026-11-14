"""Збирає 10 реальних відповідей LLM. Не виставляє автоматично оцінки correctness."""
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from workflow import build_guide

HERE = Path(__file__).resolve().parent

def call_model(base_url, model, case, guide):
    request = {
        "model": model, "stream": False, "temperature": 0, "max_tokens": 300, "seed": 1,
        "messages": [
            {"role": "system", "content": "Ти пояснюєш працівнику НАВЧАЛЬНУ процедуру поштового відділення. Користуйся тільки наданим списком дій. Не вигадуй внутрішніх кнопок чи офіційних наказів. Відповідай українською."},
            {"role": "user", "content": "Ситуація: " + case["description"] + "\nДозволені кроки: " + json.dumps(guide["steps"], ensure_ascii=False) + "\nКоротко розкажи порядок дій."}
        ]
    }
    url = base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(request, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)["choices"][0]["message"]["content"]


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
            answer = call_model(args.base_url, args.model, case, guide)
            error = None
        except (OSError, ValueError, KeyError, IndexError) as ex:
            answer, error = "", str(ex)
        rows.append({"id": case["id"], "situation": case["description"],
                     "expected_procedure": case["expected_id"], "procedure": guide["id"],
                     "expected_steps": guide["steps"], "answer": answer,
                     "error": error, "correct": None, "remarks": "Перевірити вручну за expected_steps"})
        print(f"{case['id']}/10: {'відповідь отримано' if answer else 'помилка'}")
    output = HERE.parent / "demo" / f"quality_{args.label}.json"
    output.write_text(json.dumps({"model": args.model, "label": args.label,
                                  "recorded_utc": datetime.now(timezone.utc).isoformat(),
                                  "note": "correct=null, доки не виконане ручне оцінювання", "results": rows},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print("Результат:", output)

if __name__ == "__main__":
    main()
