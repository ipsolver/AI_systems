"""Навчальний алгоритм підбору процедури. Не використовує зовнішні API."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load_knowledge():
    return json.loads((BASE / "procedures.json").read_text(encoding="utf-8"))


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def choose_procedure(payload, knowledge=None):
    """Пріоритет пошкоджень над звичайною відмовою; безпечний fallback."""
    k = knowledge or load_knowledge()
    by_id = {p["id"]: p for p in k["procedures"]}
    selected = normalize(payload.get("case_id"))
    description = normalize(payload.get("description"))
    damaged = bool(payload.get("damaged")) or any(w in description for w in (
        "пошкодж", "розбит", "розірван", "зім'ят", "зім’ят", "тріщин"
    ))
    refused = bool(payload.get("refused")) or any(w in description for w in (
        "відмов", "не забира", "не прийма", "відміна отриман"
    ))
    # Не дозволяємо помилково використовувати безпечніший сценарій, коли є пошкодження.
    if damaged and (refused or selected == "recipient_refusal"):
        chosen = "recipient_refusal_damage"
    elif damaged:
        chosen = "damage_without_refusal"
    elif selected in by_id and selected != "unknown_case":
        chosen = selected
    else:
        rules = (
            ("missing_contents", ("нестач", "не вистачає", "бракує", "порожня посил")),
            ("sender_return", ("повернути відправник", "назад відправник", "повернення відправник")),
            ("cancel_label", ("скасувати накладну", "видалити накладну", "скасування накладної", "чернетк")),
            ("recipient_refusal", ("відмов", "не забира", "не прийма")),
            ("recipient_data_error", ("помилка у прізвищ", "неправильн номер", "помилка в даних", "змінити телефон")),
            ("delivery_delay", ("затрим", "запіз", "не приїхала", "довго їде")),
            ("wrong_branch", ("інше відділення", "не те відділення", "помилкове відділення")),
        )
        chosen = next((key for key, words in rules if any(w in description for w in words)), "unknown_case")
    return by_id[chosen]


def build_guide(payload):
    k = load_knowledge()
    p = choose_procedure(payload, k)
    return {"id": p["id"], "title": p["title"], "category": p["category"],
            "priority": p["priority"], "steps": p["steps"], "ask": p["ask"],
            "do_not": p["do_not"], "source_type": p["source_type"],
            "source": p["source"], "disclaimer": k["disclaimer"]}
