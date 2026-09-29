"""Markdown dosyalarını Notion sayfalarına senkronlar (learning_log ve experiment log).

  python tools/notion_sync.py                    # varsayılan dosyaların hepsi
  python tools/notion_sync.py learning_log/2026-09-29.md

Gerekenler (.env ya da GitHub Secrets):
  NOTION_TOKEN           Notion integration token'ı (secret_... / ntn_...)
  NOTION_PARENT_PAGE_ID  Sayfaların altında oluşturulacağı Notion sayfasının id'si

Nasıl çalışır:
- Markdown satır satır okunup Notion'un kendi block'larına çevrilir (heading, paragraph, bullet, numbered,
  table, code, quote, divider). Notion'un Markdown import'u tabloları ve iç içe listeleri kaydırdığı için
  import yerine block'lar doğrudan oluşturulur.
- Her dosya, parent sayfanın altında dosya adıyla bir alt sayfadır. Sayfa yoksa oluşturulur; varsa içeriği
  silinip yeniden yazılır (sayfanın linki değişmez).
- Sayfanın ilk block'unda içeriğin hash'i durur; dosya değişmediyse hiçbir şey yapılmaz.
"""
import hashlib
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILES = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "learning_log").glob("20*.md")) + [
    "experiments/experiment_log.md"]
API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_TEXT = 2000       # bir rich_text parçasının en fazla uzunluğu
MAX_CHILDREN = 100    # tek istekte eklenebilecek en fazla block
CODE_LANGUAGES = {"python", "bash", "json", "markdown", "mermaid", "shell", "yaml", "sql"}


# --- Markdown -> Notion block'ları ---

INLINE_RE = re.compile(r"(\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|(?<![\w*])\*([^*\n]+)\*(?![\w*]))")


def rich_text(text):
    """Satır içi biçimleri (**kalın**, `kod`, *italik*, [link](url)) Notion rich_text listesine çevirir."""
    parts, pos = [], 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            parts.append((text[pos:m.start()], {}, None))
        if m.group(2) is not None:
            parts.append((m.group(2), {"bold": True}, None))
        elif m.group(3) is not None:
            parts.append((m.group(3), {"code": True}, None))
        elif m.group(4) is not None:
            url = m.group(5)
            parts.append((m.group(4), {}, url if url.startswith("http") else None))
        else:
            parts.append((m.group(6), {"italic": True}, None))
        pos = m.end()
    if pos < len(text):
        parts.append((text[pos:], {}, None))
    out = []
    for content, annotations, url in parts:
        for i in range(0, len(content), MAX_TEXT):
            item = {"type": "text", "text": {"content": content[i:i + MAX_TEXT]}}
            if url:
                item["text"]["link"] = {"url": url}
            if annotations:
                item["annotations"] = annotations
            out.append(item)
    return out


def block(kind, text="", **extra):
    body = {"rich_text": rich_text(text)} if kind not in ("divider", "table", "table_row") else {}
    body.update(extra)
    return {"object": "block", "type": kind, kind: body}


def table_block(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]  # ayraç satırı
    width = max(len(r) for r in cells)
    children = [{"object": "block", "type": "table_row",
                 "table_row": {"cells": [rich_text(c) for c in r + [""] * (width - len(r))]}} for r in cells]
    return {"object": "block", "type": "table",
            "table": {"table_width": width, "has_column_header": True, "has_row_header": False,
                      "children": children}}


LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def markdown_to_blocks(markdown):
    lines = markdown.splitlines()
    blocks, i = [], 0
    list_stack = []  # (girinti, block) — iç içe listeler için
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            lang = stripped[3:].strip().lower()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            text = "\n".join(code)
            blocks.append({"object": "block", "type": "code", "code": {
                "rich_text": [{"type": "text", "text": {"content": text[j:j + MAX_TEXT]}}
                              for j in range(0, max(len(text), 1), MAX_TEXT)],
                "language": lang if lang in CODE_LANGUAGES else "plain text"}})
            list_stack = []
            i += 1
            continue

        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            blocks.append(table_block(rows))
            list_stack = []
            continue

        m = LIST_RE.match(line)
        if m:
            indent, marker, text = len(m.group(1)), m.group(2), m.group(3)
            # Liste maddesinin devam satırlarını (daha fazla girintili düz satırlar) birleştir.
            while i + 1 < len(lines) and lines[i + 1].startswith(" " * (indent + 2)) \
                    and lines[i + 1].strip() and not LIST_RE.match(lines[i + 1]) \
                    and not lines[i + 1].strip().startswith(("|", "```")):
                i += 1
                text += " " + lines[i].strip()
            kind = "numbered_list_item" if marker[0].isdigit() else "bulleted_list_item"
            item = block(kind, text)
            while list_stack and list_stack[-1][0] >= indent:
                list_stack.pop()
            if list_stack and len(list_stack) < 2:  # Notion tek istekte en fazla 2 seviye iç içe kabul eder
                list_stack[-1][1][list_stack[-1][1]["type"]].setdefault("children", []).append(item)
            else:
                blocks.append(item)
            list_stack.append((indent, item))
            i += 1
            continue

        list_stack = []
        if not stripped:
            i += 1
            continue
        if stripped in ("---", "***"):
            blocks.append(block("divider"))
        elif stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            blocks.append(block(f"heading_{level}", stripped.lstrip("#").strip()))
        elif stripped.startswith(">"):
            quote = [stripped.lstrip(">").strip()]
            while i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                i += 1
                quote.append(lines[i].strip().lstrip(">").strip())
            blocks.append(block("callout", " ".join(quote), icon={"type": "emoji", "emoji": "💡"}))
        else:
            para = [stripped]
            # Satır sonunda iki boşluk Markdown'da "satır kır" demek; orada ayrı paragraf başlatılır.
            while not lines[i].endswith("  ") and i + 1 < len(lines) and lines[i + 1].strip() and not re.match(
                    r"^\s*(#|>|\||```|---|[-*]\s|\d+\.\s)", lines[i + 1]):
                i += 1
                para.append(lines[i].strip())
            blocks.append(block("paragraph", " ".join(para)))
        i += 1
    return blocks


# --- Notion API ---

class Notion:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION,
                                     "Content-Type": "application/json"})

    def call(self, method, path, **kwargs):
        for attempt in range(5):
            r = self.session.request(method, f"{API}{path}", timeout=30, **kwargs)
            if r.status_code == 429:  # rate limit: saniyede ~3 istek
                time.sleep(float(r.headers.get("Retry-After", 1)))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Notion API {r.status_code}: {r.text[:500]}")
            return r.json()
        raise RuntimeError("Notion API: çok fazla 429")

    def children(self, block_id):
        out, cursor = [], None
        while True:
            params = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
            data = self.call("GET", f"/blocks/{block_id}/children", params=params)
            out += data["results"]
            if not data.get("has_more"):
                return out
            cursor = data["next_cursor"]

    def append(self, block_id, blocks):
        for i in range(0, len(blocks), MAX_CHILDREN):
            self.call("PATCH", f"/blocks/{block_id}/children", json={"children": blocks[i:i + MAX_CHILDREN]})

    def find_or_create_page(self, parent_id, title):
        for child in self.children(parent_id):
            if child["type"] == "child_page" and child["child_page"]["title"] == title:
                return child["id"], False
        page = self.call("POST", "/pages", json={
            "parent": {"page_id": parent_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}}})
        return page["id"], True


def sync_file(notion, parent_id, rel_path):
    path = ROOT / rel_path
    markdown = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(markdown.encode()).hexdigest()[:12]
    marker = f"GitHub'dan otomatik senkronlanır: {rel_path} · hash {digest}"
    title = path.stem if path.parent.name == "learning_log" else "Experiment Log"

    page_id, created = notion.find_or_create_page(parent_id, title)
    existing = [] if created else notion.children(page_id)
    if existing and existing[0]["type"] == "callout":
        first = "".join(t["plain_text"] for t in existing[0]["callout"]["rich_text"])
        if digest in first:
            print(f"  {rel_path}: değişmemiş, atlandı")
            return
    for b in existing:  # sayfa linki değişmesin diye sayfa değil içerik silinir
        notion.call("DELETE", f"/blocks/{b['id']}")
    header = block("callout", marker, icon={"type": "emoji", "emoji": "🔄"}, color="gray_background")
    notion.append(page_id, [header] + markdown_to_blocks(markdown))
    print(f"  {rel_path}: {'oluşturuldu' if created else 'güncellendi'}")


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    token, parent = os.getenv("NOTION_TOKEN"), os.getenv("NOTION_PARENT_PAGE_ID")
    if not token or not parent:
        print("NOTION_TOKEN / NOTION_PARENT_PAGE_ID tanımlı değil; Notion senkronu atlandı.")
        return 0
    parent = parent.replace("-", "")[-32:]  # sayfa linki yapıştırılmışsa id kısmını al
    files = sys.argv[1:] or DEFAULT_FILES
    notion = Notion(token)
    print(f"Notion senkronu ({len(files)} dosya):")
    for rel_path in files:
        if (ROOT / rel_path).exists():
            sync_file(notion, parent, rel_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
