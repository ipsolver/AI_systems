"""Функціональні тести класифікатора; не оцінює якість мовної моделі."""
import json
from pathlib import Path
from workflow import build_guide

ROOT = Path(__file__).resolve().parent

def run():
    tests = json.loads((ROOT / "test_cases.json").read_text(encoding="utf-8"))
    results = []
    for case in tests:
        guide = build_guide(case)
        success = guide["id"] == case["expected_id"] and len(guide["steps"]) >= 3
        results.append({"id": case["id"], "expected": case["expected_id"],
                        "actual": guide["id"], "passed": success})
        print(f"{case['id']:2d}. {'OK' if success else 'FAIL'}: {case['expected_id']} → {guide['id']}")
    passed = sum(item["passed"] for item in results)
    print(f"Маршрутизація сценаріїв: {passed}/{len(results)}")
    out = ROOT.parent / "demo" / "routing_results.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"note": "Автоматичні тести маршрутизації, НЕ оцінка LLM", "results": results},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    if passed != len(results):
        raise SystemExit(1)

if __name__ == "__main__":
    run()
