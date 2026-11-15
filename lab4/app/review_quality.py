"""Ручне оцінювання відповідей, без автоматичного вигадування оцінок."""
import argparse
import json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("--label", choices=["before", "after", "revised"], required=True)
args = p.parse_args()
path = Path(__file__).resolve().parent.parent / "demo" / f"quality_{args.label}.json"
data = json.loads(path.read_text(encoding="utf-8"))
for r in data["results"]:
    print("\n", r["id"], r["situation"], "\nОчікувані кроки:", *r["expected_steps"], sep="\n")
    print("Відповідь:", r["answer"], "\nПомилка API:", r["error"], "\nМаршрут:", r["procedure"], "очікуваний:", r["expected_procedure"])
    if r["correct"] is not None:
        print("Попередня оцінка:", r["correct"], r["remarks"])
    while True:
        v = input("1 = правильно, 0 = неправильно, Enter = залишити без змін: ").strip()
        if v in ("1", "0", ""): break
    if not v: continue
    if v == "1" and (r["error"] or not r["answer"].strip() or r["procedure"] != r["expected_procedure"]):
        print("Не можна зарахувати порожню відповідь, помилку API або неправильний маршрут.")
        continue
    r["correct"] = v == "1"
    r["remarks"] = input("Коротке обґрунтування: ").strip()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Збережено:", path)
