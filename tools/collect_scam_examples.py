"""
Сборщик примеров мошеннических сообщений из открытых источников.

Источники:
1. Reddit r/Scams — реальные примеры с разметкой
2. Ручной ввод через интерактивный режим
3. Импорт из текстового файла

Использование:
    python tools/collect_scam_examples.py --mode manual
    python tools/collect_scam_examples.py --mode reddit
    python tools/collect_scam_examples.py --mode import --file examples.txt
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

DATASET_PATH = Path(__file__).parent.parent / "data" / "scam_dataset.jsonl"

SCAM_TYPES = {
    "1": "bank_phishing",
    "2": "loan_scam",
    "3": "fake_prize",
    "4": "job_scam",
    "5": "investment_scam",
    "6": "romance_scam",
    "7": "family_scam",
    "8": "rental_scam",
    "9": "other_scam",
    "0": "legitimate",
}


def save_example(text: str, label: int, scam_type: str, lang: str, source: str):
    """Сохраняет пример в датасет."""
    DATASET_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "text": text.strip(),
        "label": label,
        "type": scam_type,
        "lang": lang,
        "source": source,
        "added_at": datetime.now().isoformat(),
    }
    with open(DATASET_PATH, "a", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False)
        f.write("\n")
    return entry


def manual_mode():
    """Интерактивный режим: вводишь сообщения вручную."""
    print("📝 Режим ручного ввода примеров")
    print("   Введи 'q' чтобы выйти, 'END' для завершения сообщения\n")

    added = 0
    while True:
        print("-" * 50)
        print("Вставь текст сообщения (END для завершения, q для выхода):")

        lines = []
        while True:
            line = input()
            if line.strip().lower() == 'q':
                print(f"\n✅ Добавлено {added} примеров в {DATASET_PATH}")
                return
            if line.strip() == 'END':
                break
            lines.append(line)

        text = "\n".join(lines).strip()
        if not text:
            continue

        print("\nТип мошенничества (или 0 = легитимное):")
        for k, v in SCAM_TYPES.items():
            print(f"  {k}. {v}")

        scam_type_key = input("Выбор [1-9, 0]: ").strip()
        scam_type = SCAM_TYPES.get(scam_type_key, "other_scam")
        label = 0 if scam_type == "legitimate" else 1

        lang = input("Язык [ru/uz/en, по умолчанию ru]: ").strip() or "ru"

        entry = save_example(text, label, scam_type, lang, "manual")
        print(f"✅ Сохранено: label={label}, type={scam_type}, lang={lang}")
        added += 1


def import_mode(filepath: str):
    """
    Импорт из текстового файла.

    Формат файла — блоки разделённые '---':
        Текст сообщения 1
        ---
        bank_phishing
        ---
        Текст сообщения 2
        ...

    Или просто один абзац на строку (будет помечено как other_scam).
    """
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Файл не найден: {filepath}")
        return

    content = path.read_text(encoding="utf-8")

    # Попробуем формат с разделителями
    if "---" in content:
        blocks = content.split("---")
        added = 0
        for i in range(0, len(blocks) - 1, 2):
            text = blocks[i].strip()
            scam_type = blocks[i+1].strip() if i+1 < len(blocks) else "other_scam"
            if scam_type not in SCAM_TYPES.values():
                scam_type = "other_scam"
            label = 0 if scam_type == "legitimate" else 1
            save_example(text, label, scam_type, "ru", f"import:{path.name}")
            added += 1
        print(f"✅ Импортировано {added} примеров")
    else:
        # Каждая непустая строка — отдельное сообщение
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        for line in lines:
            save_example(line, 1, "other_scam", "ru", f"import:{path.name}")
        print(f"✅ Импортировано {len(lines)} примеров")


def reddit_mode():
    """Загружает примеры с Reddit r/Scams через публичный API."""
    try:
        import httpx
    except ImportError:
        print("❌ Установи httpx: pip install httpx")
        return

    import asyncio

    async def fetch():
        url = "https://www.reddit.com/r/Scams/search.json"
        params = {
            "q": "loan scam OR bank phishing OR fake prize",
            "sort": "new",
            "limit": 25,
            "t": "month",
        }
        headers = {"User-Agent": "ScamGuard/1.0 dataset-collector"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=headers)
            data = resp.json()

        posts = data.get("data", {}).get("children", [])
        added = 0
        for post in posts:
            pd = post["data"]
            selftext = pd.get("selftext", "").strip()
            title = pd.get("title", "").strip()

            if not selftext or selftext == "[removed]" or selftext == "[deleted]":
                continue
            if len(selftext) < 50:
                continue

            text = f"{title}\n\n{selftext}"
            save_example(text, 1, "other_scam", "en", "reddit_r/Scams")
            added += 1
            print(f"  + {title[:60]}...")

        print(f"\n✅ Загружено {added} примеров с Reddit")

    asyncio.run(fetch())


def show_stats():
    """Показывает статистику датасета."""
    if not DATASET_PATH.exists():
        print("📁 Датасет пуст")
        return

    entries = []
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    total = len(entries)
    scam_count = sum(1 for e in entries if e.get("label") == 1)
    legit_count = total - scam_count

    types: dict = {}
    for e in entries:
        t = e.get("type", "unknown")
        types[t] = types.get(t, 0) + 1

    print(f"\n📊 Датасет: {DATASET_PATH}")
    print(f"   Всего примеров: {total}")
    print(f"   Мошеннических:  {scam_count}")
    print(f"   Легитимных:     {legit_count}")
    print(f"\n   По типам:")
    for t, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"   {t}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Сборщик датасета ScamGuard")
    parser.add_argument("--mode", choices=["manual", "reddit", "import", "stats"],
                        default="stats")
    parser.add_argument("--file", help="Путь к файлу для импорта")
    args = parser.parse_args()

    if args.mode == "stats":
        show_stats()
    elif args.mode == "manual":
        manual_mode()
    elif args.mode == "reddit":
        reddit_mode()
    elif args.mode == "import":
        if not args.file:
            print("❌ Укажи --file путь_к_файлу")
            sys.exit(1)
        import_mode(args.file)


if __name__ == "__main__":
    main()
