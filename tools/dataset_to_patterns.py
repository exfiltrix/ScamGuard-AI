"""
Конвертирует накопленный датасет в паттерны для rule_engine.py.

Использование:
    python tools/dataset_to_patterns.py

Что делает:
1. Читает data/scam_dataset.jsonl
2. Находит фразы встречающиеся только в скамах (не в легитимных)
3. Генерирует готовый Python-код для вставки в rule_engine.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DATASET_PATH = Path(__file__).parent.parent / "data" / "scam_dataset.jsonl"

STOP_WORDS = {
    'и', 'в', 'на', 'не', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'а', 'но',
    'или', 'это', 'то', 'что', 'как', 'все', 'вы', 'ваш', 'ваша', 'вашего',
    'вам', 'я', 'мы', 'он', 'она', 'они', 'мне', 'ты', 'тебе', 'его', 'её',
    'нас', 'вас', 'их', 'со', 'за', 'при', 'уже', 'был', 'есть', 'будет',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'i', 'you', 'he', 'she',
}

SEVERITY_BY_TYPE = {
    "bank_phishing": 10,
    "loan_scam": 9,
    "fake_prize": 9,
    "job_scam": 7,
    "investment_scam": 9,
    "romance_scam": 8,
    "family_scam": 8,
    "rental_scam": 8,
    "other_scam": 7,
}


def load_dataset():
    if not DATASET_PATH.exists():
        print(f"❌ Датасет не найден: {DATASET_PATH}")
        print("   Запусти: python tools/collect_scam_examples.py --mode manual")
        return [], []

    scam_texts, legit_texts = [], []
    scam_types = defaultdict(list)

    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                text = e.get("text", "").lower()
                if e.get("label") == 1:
                    scam_texts.append((text, e.get("type", "other_scam")))
                    scam_types[e.get("type", "other_scam")].append(text)
                else:
                    legit_texts.append(text)
            except Exception:
                pass

    return scam_texts, legit_texts, scam_types


def get_ngrams(text, n):
    words = re.findall(r'[а-яёa-z]+', text)
    return [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]


def find_discriminative_phrases(scam_texts, legit_texts, min_count=2, max_legit_ratio=0.1):
    """
    Находит фразы которые часто встречаются в скамах,
    но редко или никогда — в легитимных сообщениях.
    """
    scam_ngrams: Counter = Counter()
    legit_ngrams: Counter = Counter()

    for text, _ in scam_texts:
        for n in (2, 3):
            scam_ngrams.update(get_ngrams(text, n))

    for text in legit_texts:
        for n in (2, 3):
            legit_ngrams.update(get_ngrams(text, n))

    total_scam = max(len(scam_texts), 1)
    total_legit = max(len(legit_texts), 1)

    discriminative = []
    for phrase, count in scam_ngrams.items():
        words = phrase.split()
        # Фильтрация стоп-слов
        if any(w in STOP_WORDS for w in words):
            continue
        if any(len(w) < 3 for w in words):
            continue

        scam_freq = count / total_scam
        legit_count = legit_ngrams.get(phrase, 0)
        legit_freq = legit_count / total_legit

        # Фраза дискриминативна если в скамах часто, в легитимных редко
        if count >= min_count and (legit_count == 0 or scam_freq / (legit_freq + 0.001) > 5):
            discriminative.append((phrase, count, scam_freq, legit_count))

    return sorted(discriminative, key=lambda x: -x[1])


def generate_code(discriminative_phrases, scam_types):
    """Генерирует готовый Python-код для rule_engine.py."""
    print("\n" + "=" * 60)
    print("# 🤖 АВТОГЕНЕРИРОВАННЫЕ ПАТТЕРНЫ (dataset_to_patterns.py)")
    print("# Вставь в red_flag_keywords в rule_engine.py")
    print("=" * 60)

    print("\n# Фразы из датасета (по частоте в мошеннических сообщениях):")
    for phrase, count, freq, legit_count in discriminative_phrases[:30]:
        severity = 8 if count >= 5 else 7
        print(f"            '{phrase}': {{'severity': {severity}, 'category': 'scam', 'type': 'detected'}},  # встречается {count}x")

    # По типам
    print("\n\n# По типам мошенничества:")
    for scam_type, texts in scam_types.items():
        if len(texts) < 2:
            continue

        type_ngrams: Counter = Counter()
        for text in texts:
            for n in (2, 3):
                type_ngrams.update(get_ngrams(text, n))

        severity = SEVERITY_BY_TYPE.get(scam_type, 7)
        top = [(p, c) for p, c in type_ngrams.most_common(10)
               if not any(w in STOP_WORDS for w in p.split())
               and all(len(w) >= 3 for w in p.split())][:5]

        if top:
            print(f"\n            # {scam_type}:")
            for phrase, count in top:
                print(f"            '{phrase}': {{'severity': {severity}, 'category': '{scam_type}', 'type': '{scam_type}'}},  # {count}x")


def main():
    result = load_dataset()
    if len(result) == 2:
        return

    scam_texts, legit_texts, scam_types = result

    print(f"📊 Загружено: {len(scam_texts)} скамов, {len(legit_texts)} легитимных")

    if len(scam_texts) < 5:
        print("\n⚠️  Слишком мало данных для анализа (нужно минимум 5 скамов).")
        print("   Добавь примеры через: python tools/collect_scam_examples.py --mode manual")
        return

    discriminative = find_discriminative_phrases(scam_texts, legit_texts)
    print(f"🔍 Найдено {len(discriminative)} дискриминативных фраз")

    generate_code(discriminative, scam_types)

    print("\n\n📝 Инструкция:")
    print("  1. Скопируй паттерны выше")
    print("  2. Вставь в backend/services/rule_engine.py → red_flag_keywords")
    print("  3. Перезапусти: pkill -f test_server && python test_server.py")


if __name__ == "__main__":
    main()
