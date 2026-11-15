"""Спільний OpenAI-сумісний клієнт для застосунку та оцінювання якості."""
import json
import socket
import urllib.error
import urllib.request

TEMPERATURE = 0
MAX_TOKENS = 260
SEED = 1
TIMEOUT = 180

def explain(url, model, guide, description):
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
            + json.dumps(allowed, ensure_ascii=False) + "\nНадай пояснення до 120 слів"
        )}
    ]
    payload = {"model": model, "messages": messages, "temperature": TEMPERATURE,
               "max_tokens": MAX_TOKENS, "seed": SEED, "stream": False,
               "reasoning_effort": "none"}
    req = urllib.request.Request(url, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 {"Content-Type": "application/json"}, method="POST")
    def fail(text, detail):
        return {"ok": False, "text": text, "detail": detail}
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            data = json.load(res)
        choice = data["choices"][0]
        msg = choice["message"]
        answer = msg.get("content")
        finish = choice.get("finish_reason")
        if msg.get("reasoning") or msg.get("reasoning_content"):
            return fail("Модель міркує попри вимкнений Thinking. Перевірте версію Ollama.", str(finish))
        if not isinstance(answer, str) or not answer.strip():
            return fail("Модель не повернула текст. Перевірте Thinking і ліміт токенів.", str(finish))
        if finish == "length":
            return {"ok": False, "text": "Відповідь обірвана через ліміт токенів: " + answer.strip(),
                    "detail": "length", "answer": answer.strip()}
        return {"ok": True, "text": answer.strip(), "finish_reason": finish, "usage": data.get("usage")}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 404:
            return fail("Модель або маршрут API не знайдено. Перевірте ollama list та адресу API.", detail)
        return fail(f"Ollama повернула HTTP {exc.code}. Перевірте модель та параметри.", detail)
    except (TimeoutError, socket.timeout):
        return fail("Час очікування відповіді вичерпано.", "timeout")
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            return fail("Час очікування відповіді вичерпано.", str(exc.reason))
        return fail("Не вдалося підключитися до Ollama. Перевірте, чи працює сервер.", str(exc.reason))
    except (OSError, KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
        return fail("Некоректна відповідь або збій з'єднання з моделлю.", str(exc))
