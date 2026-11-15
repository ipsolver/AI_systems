"""Локальні вимірювання лабораторної №4. Запуск з Windows: python app/run_lab4.py."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

LAB = Path(__file__).resolve().parent.parent
APP = LAB / 'app'
DEMO = LAB / 'demo'
CSV = LAB / 'bench_results.csv'
MODELS = {'before': 'postal-q8', 'after': 'postal-q4'}
FIELDS = ['label','model','concurrency','requests','errors','ttft_p50_s','ttft_p95_s','tokens_per_s_per_user_p50','throughput_tokens_per_s','reasoning']


def run(*args):
    print('\n>', ' '.join(map(str,args)), flush=True)
    subprocess.run([str(a) for a in args], cwd=LAB, check=True)


def py(name, *args):
    run(sys.executable, APP / name, *args)


def current_rows():
    if not CSV.exists():
        return []
    with CSV.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def complete(rows, label):
    group = [r for r in rows if r['label'] == label]
    return (len(group)==3 and {r['concurrency'] for r in group}=={'1','2','4'}
            and all(r['model'] in (MODELS[label], MODELS[label]+':latest') for r in group))


def measure(label, requests, redo):
    model = MODELS[label]
    rows = current_rows()
    if complete(rows, label) and not redo:
        print(f'{label}: CSV вже містить 3 вимірювання; пропускаю. Для повтору: --redo.')
    else:
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td) / 'bench.csv'
            py('bench.py', '--base-url','http://localhost:11434/v1','--model',model,
               '--label',label,'--reasoning-effort','none','--requests',requests,
               '--concurrency',1,2,4,'--max-tokens',200,'--timeout',180,
               '--prompts',APP/'bench_prompts.txt','--output',temp)
            with temp.open(encoding='utf-8',newline='') as f:
                new = list(csv.DictReader(f))
            if not complete(new,label):
                raise RuntimeError('Бенчмарк не створив усі 3 рядки.')
            # Заміна тільки після успішного нового запуску, без накопичення дублікатів
            rows = [r for r in rows if r['label']!=label]+new
            with CSV.open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    group = [r for r in current_rows() if r['label']==label]
    if any(r['errors']!='0' or r['reasoning'].lower() in ('true','1') for r in group):
        print('УВАГА: у вимірюваннях є помилки або Thinking. Не приховуйте їх у звіті.')
    quality = DEMO / f'quality_{label}.json'
    runtime = DEMO / f'runtime_{label}.txt'
    if redo or not quality.exists():
        py('quality_eval.py','--model',model,'--label',label)
    else:
        print(f'{quality.name} вже існує; пропускаю генерацію.')
    if redo or not runtime.exists():
        result = subprocess.check_output(['ollama','ps'],cwd=LAB)
        with urllib.request.urlopen('http://localhost:11434/api/ps',timeout=5) as f:
            ps=json.load(f)
        runtime.write_text(result.decode('utf-8',errors='replace')+'\n'+json.dumps(ps,ensure_ascii=False,indent=2),encoding='utf-8')
        if not any(m.get('name','').split(':')[0]==model for m in ps.get('models',[])):
            print('УВАГА: модель не відображається у /api/ps. Перевірте runtime-файл.')


def pack():
    paths=[CSV]+[DEMO / name for name in ('quality_before.json','quality_after.json','routing_results.json','runtime_before.txt','runtime_after.txt','quality_revised.json')]
    missing=[p.name for p in paths[:-1] if not p.exists()]
    if missing:
        raise RuntimeError('Бракує файлів: '+', '.join(missing))
    with zipfile.ZipFile(LAB/'local_results.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            if p.exists(): z.write(p,p.name)
    print('\nГотово: ', LAB/'local_results.zip', '\nЦей ZIP завантажте в клітинку D5 у Colab')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--requests',type=int,default=4,help='запитів на кожен рівень паралельності (мінімум 4)')
    parser.add_argument('--redo',action='store_true',help='повторити вимірювання та якість (замінити відповідні результати)')
    parser.add_argument('--pack-only',action='store_true',help='лише запакувати наявні результати для Colab')
    args=parser.parse_args()
    if args.pack_only:
        pack();return
    if args.requests<4: parser.error('--requests має бути не менше 4')
    DEMO.mkdir(exist_ok=True)
    with urllib.request.urlopen('http://localhost:11434/api/version',timeout=5) as f:
        print('Ollama:',json.load(f))
    run('ollama','list')
    rows=current_rows()
    for label in MODELS:
        if complete(rows,label) and not args.redo:
            counts={int(r['requests']) for r in rows if r['label']==label}
            if counts!={args.requests}:
                raise RuntimeError(f'{label}: наявні вимірювання мають --requests {counts}. Запустіть із тією самою кількістю, або --redo.')
    for label,model in MODELS.items():
        other=next(m for m in MODELS.values() if m!=model)
        subprocess.run(['ollama','stop',other],cwd=LAB,check=False)
        measure(label,args.requests,args.redo)
    py('checks.py')
    for label in MODELS:
        quality=json.loads((DEMO/f'quality_{label}.json').read_text(encoding='utf-8'))
        if any(r.get('correct') is None for r in quality['results']):
            print('\nОЦІНКА',label,'— 1 правильно, 0 неправильно, потім коротка причина.')
            py('review_quality.py','--label',label)
    py('summary.py')
    pack()

if __name__=='__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('\nПомилка:',exc,file=sys.stderr)
        print('Виправте проблему та запустіть команду ще раз. Успішні результати збережено.',file=sys.stderr)
        sys.exit(1)
