"""Arayüz katmanı: Gradio. API'ye HTTP ile bağlanır; RAG'i, service'i ya da log dosyalarını bilmez.

İki şekilde çalışır:
  1) API ile aynı sunucuda (önerilen):  venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
     -> arayüz http://localhost:8000/ui , API dokümantasyonu http://localhost:8000/docs
  2) Ayrı süreç olarak (API başka yerde çalışıyorsa):  API_URL=http://... venv/Scripts/python.exe -m app.ui
"""
import os
import uuid

import gradio as gr
import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
# Tek bir client tüm istekler için yeniden kullanılır (bağlantı havuzu). Cevap üretimi (rewrite + retrieval +
# LLM) birkaç saniye sürebildiği için timeout geniş tutuldu.
client = httpx.Client(base_url=API_URL, timeout=120)


def _error_message(e):
    """API hatasını kullanıcıya gösterilecek metne çevirir."""
    if isinstance(e, httpx.HTTPStatusError):
        try:
            detail = e.response.json().get("detail")
        except ValueError:
            detail = e.response.text
        return f"⚠️ {detail} (HTTP {e.response.status_code})"
    return f"⚠️ API'ye ulaşılamadı: {type(e).__name__}. Sunucu çalışıyor mu? ({API_URL})"


def _format_answer(body):
    """Cevabın altına kaynakları ve (varsa) yeniden yazılan soruyu ekler."""
    lines = [body["answer"], "", "**Kaynaklar:**"]
    lines += [f"- {s['label']}" for s in body["sources"]]
    if body["rewritten_query"]:
        lines += ["", f"_Aranan soru: {body['rewritten_query']}_"]
    lines += ["", f"<sub>{body['latency_ms'] / 1000:.1f} sn</sub>"]
    return "\n".join(lines)


# --- Sohbet sekmesi ---
# Durum (state) her tarayıcı oturumunda ayrı tutulur (gr.State):
#   history:    API'ye gönderilen sade geçmiş (kaynak listesi olmadan, yalnız soru ve cevap metni)
#   answer_ids: sohbet ekranındaki mesaj sırası -> API'nin verdiği cevap kimliği (👍/👎 için)
#   session_id: bu sohbetin kayıtlarını log'da gruplamak için

def respond(question, chat, history, answer_ids, session_id):
    question = question.strip()
    if not question:
        return "", chat, history, answer_ids
    chat = chat + [{"role": "user", "content": question}]
    try:
        r = client.post("/ask", json={"question": question, "history": history, "session_id": session_id})
        r.raise_for_status()
    except httpx.HTTPError as e:
        # Hata mesajı ekranda görünür ama geçmişe eklenmez: sonraki soruların rewrite'ını bozmasın.
        return "", chat + [{"role": "assistant", "content": _error_message(e)}], history, answer_ids
    body = r.json()
    answer_ids = {**answer_ids, len(chat): body["id"]}  # cevap mesajının ekrandaki sırası
    chat = chat + [{"role": "assistant", "content": _format_answer(body)}]
    history = history + [{"role": "user", "content": question}, {"role": "assistant", "content": body["answer"]}]
    return "", chat, history, answer_ids


def on_feedback(data: gr.LikeData, answer_ids):
    """Chatbot'taki 👍/👎 tıklaması. Gradio tıklanan mesajın sırasını ve beğenilip beğenilmediğini verir."""
    index = data.index[0] if isinstance(data.index, (list, tuple)) else data.index
    answer_id = answer_ids.get(index)
    if answer_id is None or data.liked not in (True, False):  # hata mesajı ya da beğeninin geri alınması
        return
    try:
        client.post("/feedback", json={"id": answer_id, "rating": 1 if data.liked else -1}).raise_for_status()
        gr.Info("Geri bildirim kaydedildi, teşekkürler.")
    except httpx.HTTPError as e:
        gr.Warning(_error_message(e))


def new_chat():
    return [], [], {}, uuid.uuid4().hex


# --- Belgeler sekmesi ---

def load_documents():
    try:
        r = client.get("/documents")
        r.raise_for_status()
    except httpx.HTTPError as e:
        gr.Warning(_error_message(e))
        return [], [], gr.update(choices=[])
    docs = sorted(r.json(), key=lambda d: d["title"].casefold())
    rows = [[d["title"], d["kind"] or "", d["chunk_count"], d["source"]] for d in docs]
    choices = [(f"{d['title']} ({d['chunk_count']} chunk)", d["source"]) for d in docs]
    return rows, rows, gr.update(choices=choices)


def filter_documents(query, all_rows):
    q = query.strip().casefold()
    return [r for r in all_rows if q in r[0].casefold() or q in r[3].casefold()] if q else all_rows


def show_chunks(source):
    if not source:
        return ""
    try:
        r = client.get(f"/documents/{source}/chunks")
        r.raise_for_status()
    except httpx.HTTPError as e:
        return _error_message(e)
    return "\n\n---\n\n".join(f"**{c['label']}** · chunk {c['chunk_id']}\n\n{c['text']}" for c in r.json())


def load_status():
    try:
        h = client.get("/health").raise_for_status().json()
    except httpx.HTTPError as e:
        return _error_message(e)
    return f"Config: **{h['experiment']}** · commit `{h['commit']}` · {h['documents']} belge"


def build_ui():
    # analytics_enabled=False: Gradio varsayılan olarak kullanım istatistiklerini kendi sunucularına gönderir.
    with gr.Blocks(title="BAİBÜ Kampüs Asistanı", analytics_enabled=False) as demo:
        gr.Markdown("# BAİBÜ Kampüs Asistanı\nÜniversite yönetmelik ve yönergeleri hakkında soru sorun.")
        status = gr.Markdown()

        history = gr.State([])
        answer_ids = gr.State({})
        session_id = gr.State()

        with gr.Tab("Sohbet"):
            chatbot = gr.Chatbot(height=520, feedback_options=("Like", "Dislike"), show_label=False,
                                 placeholder="Örnek: Yatay geçiş başvurusu için not ortalaması şartı nedir?")
            with gr.Row():
                question = gr.Textbox(placeholder="Sorunuzu yazın ve Enter'a basın", show_label=False, scale=8)
                send = gr.Button("Gönder", variant="primary", scale=1)
            reset = gr.Button("Yeni sohbet", size="sm")

            io = dict(fn=respond, inputs=[question, chatbot, history, answer_ids, session_id],
                      outputs=[question, chatbot, history, answer_ids])
            question.submit(**io)
            send.click(**io)
            chatbot.like(on_feedback, inputs=[answer_ids], outputs=None)
            reset.click(new_chat, outputs=[chatbot, history, answer_ids, session_id])

        with gr.Tab("Belgeler"):
            all_rows = gr.State([])
            search = gr.Textbox(placeholder="Belge adında ara", show_label=False)
            table = gr.Dataframe(headers=["Başlık", "Tür", "Chunk", "Dosya"], interactive=False, max_height=320)
            picker = gr.Dropdown(label="Chunk'larını görmek için bir belge seçin", choices=[], filterable=True)
            chunks = gr.Markdown()

            search.change(filter_documents, inputs=[search, all_rows], outputs=table)
            picker.change(show_chunks, inputs=picker, outputs=chunks)

        # Sayfa her açıldığında: yeni oturum kimliği, sunucu durumu, belge listesi.
        demo.load(lambda: uuid.uuid4().hex, outputs=session_id)
        demo.load(load_status, outputs=status)
        demo.load(load_documents, outputs=[table, all_rows, picker])
    return demo


if __name__ == "__main__":
    build_ui().launch()
