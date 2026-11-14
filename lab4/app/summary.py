"""Друкує лише наявні результати. Не вигадує якість моделі та не оцінює відповіді."""
import csv
import json
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent

def show_bench():
    path = LAB / "bench_results.csv"
    if not path.exists():
        print("Бенчмарк: CSV ще немає")
        return
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        print("Бенчмарк: вимірювання ще не проведені")
        return
    print("Бенчмарк (реальні результати):")
    for row in rows:
        print(f"  {row['label']} {row['model']} | клієнтів {row['concurrency']} | "
              f"TTFT p50 {row['ttft_p50_s']} с | tok/s {row['tokens_per_s_per_user_p50']}")

def show_quality():
    for label in ("before", "after", "revised"):
        path = LAB / "demo" / f"quality_{label}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        results = data.get("results", [])
        completed = [r for r in results if r.get("correct") is True or r.get("correct") is False]
        good = sum(r.get("correct") is True for r in completed)
        print(f"{label}: відповідей {len(results)}/10; оцінено {len(completed)}/10; "
              + (f"правильних {good}/{len(completed)}" if completed else "потрібна ручна оцінка"))

def main():
    show_bench()
    check_file = LAB / "demo" / "routing_results.json"
    if check_file.exists():
        data = json.loads(check_file.read_text(encoding="utf-8"))
        results = data["results"]
        print(f"Алгоритмічна маршрутизація: {sum(x['passed'] for x in results)}/{len(results)} тестів")
    show_quality()

if __name__ == "__main__":
    main()
