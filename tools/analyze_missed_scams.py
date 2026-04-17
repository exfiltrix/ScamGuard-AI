"""
Анализ пропущенных мошеннических сообщений из БД.

Использование:
    python tools/analyze_missed_scams.py

Что делает:
1. Находит случаи где пользователь сказал "это мошенничество" (feedback),
   но бот дал низкий/средний риск (< 70)
2. Находит самые частые слова и фразы в этих сообщениях
3. Предлагает новые паттерны для rule_engine.py
"""

import sqlite3
import json
import re
from collections import Counter
from pathlib import Path

_base = Path(__file__).parent.parent
DB_PATH = next(
    (p for p in [_base / "data" / "scamguard.db", _base / "scamguard.db"] if p.exists()),
    _base / "data" / "scamguard.db",
)


def load_missed_scams():
    """Загружает сообщения, которые бот недооценил."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT message_text, risk_score, risk_level, is_scam, feedback, red_flags
        FROM message_analyses
        WHERE
            -- пользователь пометил как скам, но бот дал низкий риск
            (is_scam = 1 AND risk_score < 70)
            OR
            -- пользователь написал "мошенничество" в feedback
            (feedback IS NOT NULL AND feedback LIKE '%scam%' AND risk_score < 70)
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return rows


def load_all_scams():
    """Загружает все подтверждённые мошеннические сообщения."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT message_text, risk_score, risk_level
        FROM message_analyses
        WHERE is_scam = 1
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return rows


def extract_ngrams(texts, n=2):
    """Извлекает n-граммы из текстов."""
    all_ngrams = []
    for text in texts:
        words = re.findall(r'[а-яёa-z]+', text.lower())
        ngrams = [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]
        all_ngrams.extend(ngrams)
    return Counter(all_ngrams)


def suggest_patterns(texts):
    """Предлагает новые паттерны на основе текстов."""
    print("\n📊 Анализ пропущенных мошеннических сообщений:")
    print("=" * 60)

    # Частые слова
    unigrams = extract_ngrams(texts, 1)
    bigrams = extract_ngrams(texts, 2)
    trigrams = extract_ngrams(texts, 3)

    # Фильтруем стоп-слова
    stop_words = {'и', 'в', 'на', 'не', 'с', 'по', 'для', 'от', 'до', 'из',
                  'к', 'а', 'но', 'или', 'это', 'то', 'что', 'как', 'все',
                  'вы', 'ваш', 'ваша', 'вашего', 'вам', 'я', 'мы', 'он', 'она'}

    print("\n🔤 Топ-20 частых слов (unigrams):")
    for word, count in unigrams.most_common(30):
        if word not in stop_words and len(word) > 3:
            print(f"  '{word}': {count}x")

    print("\n🔤 Топ-20 частых биграм:")
    for phrase, count in bigrams.most_common(20):
        words = phrase.split()
        if not any(w in stop_words for w in words):
            print(f"  '{phrase}': {count}x")

    print("\n🔤 Топ-15 частых триграм (готовые паттерны):")
    for phrase, count in trigrams.most_common(15):
        words = phrase.split()
        if not any(w in stop_words for w in words):
            print(f"  '{phrase}': {count}x")
            if count >= 2:
                print(f"    → Добавить в rule_engine: '{phrase}': {{'severity': 8, 'category': 'scam', 'type': 'detected'}}")


def export_dataset(rows, output_path="data/missed_scams.jsonl"):
    """Экспортирует датасет в JSONL для последующего использования."""
    output = Path(__file__).parent.parent / output_path
    output.parent.mkdir(exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        for text, score, level, is_scam, feedback, flags in rows:
            json.dump({
                "text": text,
                "label": 1,
                "bot_score": score,
                "bot_level": level,
                "source": "user_feedback_missed",
            }, f, ensure_ascii=False)
            f.write("\n")

    print(f"\n✅ Экспортировано {len(rows)} примеров → {output}")


def main():
    if not DB_PATH.exists():
        print(f"❌ БД не найдена: {DB_PATH}")
        return

    missed = load_missed_scams()
    all_scams = load_all_scams()

    print(f"📁 БД: {DB_PATH}")
    print(f"📊 Всего подтверждённых скамов: {len(all_scams)}")
    print(f"⚠️  Пропущенных (скам, но риск < 70): {len(missed)}")

    if not missed:
        print("\n✅ Пропущенных скамов нет! Или пока мало feedback данных.")
        print("   Попросите пользователей нажимать '🚨 Это мошенничество' в боте.")
        return

    texts = [row[0] for row in missed]
    suggest_patterns(texts)
    export_dataset(missed)

    print("\n📝 Следующие шаги:")
    print("  1. Добавь частые фразы в backend/services/rule_engine.py → red_flag_keywords")
    print("  2. Если видишь паттерн-комбинацию — добавь в _check_phishing_combos()")
    print("  3. Перезапусти сервер: pkill -f test_server && ./start-simple.sh")


if __name__ == "__main__":
    main()
