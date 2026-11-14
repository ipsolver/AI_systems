"""Ситуаційний навігатор для відділення: стандартна бібліотека Python, локальна LLM через /v1."""
import argparse
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from workflow import build_guide, load_knowledge

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
MODEL = os.environ.get("POSTAL_MODEL", "qwen3:1.7b-q4_K_M")
LLM_URL = os.environ.get("POSTAL_LLM_URL", "http://127.0.0.1:11434/v1/chat/completions")


def llm_explain(guide, description):
    """LLM формулює пояснення, а перевірені кроки завжди показуються окремо."""
    allowed = {"title": guide["title"], "steps": guide["steps"], "ask": guide["ask"],
               "restrictions": guide["do_not"]}
    messages = [
        {"role": "system", "content": (
            "Ти пояснюєш НАВЧАЛЬНУ процедуру працівникові поштового відділення. "
            "Пиши українською коротко, просто. Використовуй ВИКЛЮЧНО наведені дозволені кроки. "
            "Не вигадуй команди внутрішньої системи, строки, суми, компенсації чи обов'язкові документи. "
            "Якщо даних бракує, назви уточнювальне питання. Текст не є офіційним регламентом."
        )},
        {"role": "user", "content": (
            "Ситуація: " + description[:350] + "\nНавчальна картка: "
            + json.dumps(allowed, ensure_ascii=False) + "\nНадай пояснення до 120 слів."
        )}
    ]
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0,
                       "max_tokens": 260, "seed": 1, "stream": False}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(LLM_URL, body, {"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            answer = json.load(res)["choices"][0]["message"]["content"].strip()
            return {"ok": bool(answer), "text": answer or "Модель не повернула текст."}
    except (OSError, KeyError, IndexError, ValueError) as exc:
        return {"ok": False, "text": "Модель недоступна. Контрольний список залишається доступним.",
                "detail": type(exc).__name__}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        b = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            b = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif self.path == "/api/procedures":
            db = load_knowledge()
            self.send_json(200, {"cases": [{"id": p["id"], "title": p["title"], "category": p["category"]}
                                           for p in db["procedures"]], "model": MODEL})
        elif self.path == "/api/health":
            self.send_json(200, {"server": "ok", "model": MODEL})
        else:
            self.send_json(404, {"error": "Сторінку не знайдено"})

    def do_POST(self):
        if self.path != "/api/guide":
            return self.send_json(404, {"error": "Невідомий маршрут"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 20000:
                return self.send_json(413, {"error": "Невірний розмір запиту"})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Очікується об'єкт JSON")
            description = str(data.get("description", ""))
            if len(description) > 1500:
                return self.send_json(400, {"error": "Опис занадто довгий"})
            guide = build_guide(data)
            guide["llm"] = llm_explain(guide, description) if data.get("use_llm", False) else None
            return self.send_json(200, guide)
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Некоректний запит. Спробуйте ще раз."})


def main():
    p = argparse.ArgumentParser(description="Навчальний помічник працівника відділення")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    server = ThreadingHTTPServer((HOST, args.port), Handler)
    print(f"Відкрийте http://{HOST}:{args.port} | модель: {MODEL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер зупинено")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
