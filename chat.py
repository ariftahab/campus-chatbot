"""Terminalde sohbet arayüzü. Kullanım: python chat.py"""
import os
import sys

from rag import RagBot, source_label, tr_lower

EXIT_COMMANDS = {"çık", "çik", "cık", "cik", "exit", "quit", "q"}
RESET_COMMANDS = {"yeni", "/yeni", "sıfırla"}


def main():
    # Anahtar yoksa modelleri yüklemeye hiç başlama.
    if not os.getenv("GOOGLE_API_KEY"):
        print("Hata: GOOGLE_API_KEY .env dosyasında bulunamadı.")
        return 1

    print("Asistan hazırlanıyor (modeller yükleniyor)...")
    bot = RagBot.from_index()
    print("Hazır. Çıkmak için 'çık', yeni konuya geçmek için 'yeni' yazın.")

    while True:
        try:
            question = input("\nSoru: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        command = tr_lower(question)
        if command in EXIT_COMMANDS:
            break
        if command in RESET_COMMANDS:
            bot.reset()
            print("Sohbet geçmişi temizlendi.")
            continue

        print("Cevap düşünülüyor...")
        try:
            result = bot.ask(question)
        except Exception as e:  # kota, ağ, API hataları döngüyü öldürmesin
            print(f"Hata: cevap alınamadı ({type(e).__name__}: {e})")
            continue

        print(f"\n{result['answer']}")
        if result["query"] != question:
            print(f"\n(Aranan soru: {result['query']})")
        print("\nKaynaklar:")
        for doc in result["docs"]:
            print(f"  - {source_label(doc)}")

    print("Görüşmek üzere!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
