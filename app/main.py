"""API ve arayüzü tek sunucuda birleştirir.

Çalıştırma:  venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
  http://localhost:8000/ui    Gradio arayüzü
  http://localhost:8000/docs  API dokümantasyonu (Swagger)

Arayüz aynı süreçte olsa da service'i doğrudan çağırmaz, API'ye HTTP ile istek atar (app/ui.py);
böylece okul sistemi gibi dış istemcilerle aynı yolu kullanır.
"""
import gradio as gr
from fastapi.responses import RedirectResponse

from app.api import app
from app.ui import build_ui


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui")


app = gr.mount_gradio_app(app, build_ui(), path="/ui")
