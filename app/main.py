"""API ve arayüzü tek sunucuda birleştirir.

Çalıştırma:  venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
  http://localhost:8000/          sohbet (app/static/index.html)
  http://localhost:8000/belgeler  corpus'taki belgeler
  http://localhost:8000/admin     elle değerlendirme
  http://localhost:8000/docs      API dokümantasyonu (Swagger)
  http://localhost:8000/ui        eski Gradio arayüzü (yeni arayüz oturunca kaldırılacak)

Sayfalar statik dosyalardır (HTML/CSS/JS); veriyi tarayıcıdan API'ye fetch ile istek atarak alırlar.
Sunucu sayfa üretmez, yalnız dosyaları ve API'yi servis eder.
"""
from pathlib import Path

import gradio as gr
from fastapi import Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import app, require_admin
from app.ui import build_ui

STATIC = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _page(name):
    def handler():
        return FileResponse(STATIC / name)
    return handler


for route, page in [("/", "index.html"), ("/belgeler", "belgeler.html")]:
    app.add_api_route(route, _page(page), include_in_schema=False)
# Panel sayfası da korunur: tarayıcı şifreyi burada bir kez sorar, sonra /admin/* fetch isteklerine kendisi ekler.
app.add_api_route("/admin", _page("admin.html"), include_in_schema=False, dependencies=[Depends(require_admin)])

app = gr.mount_gradio_app(app, build_ui(), path="/ui")
