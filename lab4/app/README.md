# Ситуаційний навігатор — запуск на Windows

Навчальний застосунок; не офіційний регламент поштової компанії. Не вводьте справжні номери накладних та персональні дані. Потрібні Python 3.10+, Ollama, пакет `openai` для бенчмарка. Команди виконуються у PowerShell з каталогу `lab4`.

## 1. Підготовка (один раз)

Якщо `.venv` уже створено — не створюйте повторно.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install openai
ollama pull qwen3:1.7b-q8_0
ollama pull qwen3:1.7b-q4_K_M
ollama create postal-q8 -f app/Modelfile.q8
ollama create postal-q4 -f app/Modelfile.q4
ollama list
```

Якщо політика дозволів заважає активувати `.venv`, використовуйте `.\.venv\Scripts\python.exe` замість `python`.

Для контрольованого порівняння рекомендовано 1 внутрішній паралельний слот; вийдіть із Ollama через значок у системному треї (не просто закрийте вікно), потім у **окремому** PowerShell:

```powershell
$env:OLLAMA_NUM_PARALLEL = "1"
ollama serve
```

Залиште цей термінал відкритим. Якщо не змінюєте налаштування рантайму, не вигадуйте значення `OLLAMA_NUM_PARALLEL`. Перевірте `Invoke-RestMethod http://localhost:11434/api/version`. Перед тестами закрийте зайві програми, підключіть зарядку; бажано не менше 6 GiB доступної RAM. Не змінюйте бекенд/режим живлення між моделями.

## 2. Запуск UI і функціональні тести

```powershell
python app/checks.py
$env:POSTAL_MODEL = "postal-q4"
python app/main.py
```

Відкрийте http://127.0.0.1:8765, введіть «Клієнт відмовляється від отримання посилки, оскільки упаковка має видимі пошкодження». Пояснення Ollama ввімкнено за замовчуванням. Переконайтеся, що під чеклістом є фактичний текст моделі. Якщо ні, надішліть JSON відповіді тестового запиту та повідомлення застосунку. Зупиніть застосунок `Ctrl+C` перед бенчмарком.

`workflow.py` обирає навчальну процедуру зі структурованого `procedures.json`. `llm.py` надсилає короткий опис і картку через локальний OpenAI-сумісний API; інструкції відокремлено від пояснення моделі. `temperature=0`, `seed=1`, `max_tokens=260`, `reasoning_effort=none`, контекст 4096 задано у Modelfile. Індикатор очікування і розділені повідомлення про помилки. Вибір процедури за правилами не гарантує розпізнавання всіх природномовних формулювань.

## 3. BEFORE та AFTER

У CSV вже є заголовок. Якщо замір повторний, збережіть попередній CSV окремо (не змішуйте дублікати); для чистого запуску залиште тільки заголовок. На кожному рівні навантаження 10 промптів, 10 запитів, 1/2/4 клієнти, ліміт 200 токенів.

```powershell
ollama stop postal-q4
python app/bench.py --base-url http://localhost:11434/v1 --model postal-q8 --label before --reasoning-effort none --requests 10 --concurrency 1 2 4 --max-tokens 200 --timeout 180 --prompts app/bench_prompts.txt
ollama ps | Tee-Object -FilePath demo/runtime_before.txt
Invoke-RestMethod http://localhost:11434/api/ps | ConvertTo-Json -Depth 10 | Add-Content demo/runtime_before.txt
python app/quality_eval.py --model postal-q8 --label before
ollama stop postal-q8
python app/bench.py --base-url http://localhost:11434/v1 --model postal-q4 --label after --reasoning-effort none --requests 10 --concurrency 1 2 4 --max-tokens 200 --timeout 180 --prompts app/bench_prompts.txt
ollama ps | Tee-Object -FilePath demo/runtime_after.txt
Invoke-RestMethod http://localhost:11434/api/ps | ConvertTo-Json -Depth 10 | Add-Content demo/runtime_after.txt
python app/quality_eval.py --model postal-q4 --label after
```

Якщо є помилки/Thinking, не вважати вимірювання успішним. `ollama ps` описує завантажену модель, а не пікову RAM. Не запускати тести якості паралельно з бенчмарком. `bench.py` (демо викладача) тестує швидкість на окремому наборі 10 промптів; `quality_eval.py` відтворює фактичний системний промпт і параметри застосунку на 10 однакових сценаріях для обох моделей.

## 4. Ручне оцінювання

```powershell
python app/review_quality.py --label before
python app/review_quality.py --label after
python app/summary.py
```

Оцінка 1 — правильний маршрут, змістовне пояснення в межах навчальної картки, без вигаданих правил, сум/строків; 0 — помилка, порожній/обірваний текст чи неправильна процедура. Додайте причину. Enter пропускає оцінку; перед здачею не повинно залишатися null. Не запускайте `quality_eval.py` повторно без резервної копії: він перезаписує відповідний JSON. Якщо виправили промпт після реальної помилки, збережіть старі файли та за потреби повторіть тест з `--label revised` для обраної моделі; опишіть факт у звіті.

15 автоматичних тестів `checks.py` (10 основних, 5 крайових) перевіряють тільки маршрутизацію, не LLM. Власні оцінки необхідні окремо. Виберіть фінальну модель за швидкістю та якістю й встановіть перед запуском `$env:POSTAL_MODEL = "postal-q4"` або `"postal-q8"`. Запишіть демонстрацію у `demo/demo.mp4`.

## 5. Ноутбук та здача

Відкрийте `local_models_demo.ipynb` у Colab з T4. Виконайте демо, внесіть `VOTES`, потім відповіді з позначкою РУЧНИЙ КРОК. У секції 1.8 імпортуйте `bench_results.csv`, `demo/quality_before.json`, `demo/quality_after.json`, `demo/routing_results.json`, `demo/runtime_before.txt`, `demo/runtime_after.txt` (і `quality_revised.json` за наявності). Збережіть ноутбук з виводами як `lab4/local_models_demo.ipynb`. Не публікуйте `.venv`, ваги та персональні дані.
