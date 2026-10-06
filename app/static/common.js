// Ortak yardımcılar: API çağrıları, güvenli markdown, atıf eşleştirme, kaynak paneli.
// Framework yok; tarayıcının kendi API'leri (fetch, DOM) kullanılıyor.

// --- API ---

// fetch'i saran yardımcı: JSON gönderir/alır, HTTP hatasında API'nin "detail" mesajıyla hata fırlatır.
async function api(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Sunucuya ulaşılamadı. Sunucu çalışıyor mu?");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    let detail = data && data.detail;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; "); // 422 doğrulama hataları liste döner
    throw new Error(`${detail || res.statusText} (HTTP ${res.status})`);
  }
  return data;
}

// --- Metin yardımcıları ---

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// Türkçe'ye uygun küçük harf + noktalama temizliği; atıf ve belge adı karşılaştırması için.
function norm(s) {
  return String(s)
    .toLocaleLowerCase("tr")
    .replace(/baibü|baibu/g, " ")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// --- Atıf eşleştirme ---
// LLM cevapta "[Yatay Geçiş Yönergesi, Madde 8]" gibi atıflar yazıyor (prompt'ta istendiği için). Bunu, LLM'e
// gönderilen kaynaklardan biriyle eşleştirip tıklanabilir yapıyoruz. LLM'in yazdığı metin serbest olduğu için
// eşleşme "en iyi çaba"dır: madde numarası yazılmışsa birebir aynı olmalı, belge adının kelimelerinin çoğu
// kaynağın başlığında geçmeli. Eşleşmeyen atıf düz metin kalır.

function matchSource(part, sources) {
  const m = part.match(/madde\s*(\d+)/i);
  const madde = m ? m[1] : null;
  const titleWords = norm(part.split(/,|madde/i)[0]).split(" ").filter((w) => w.length > 2);
  const partWords = norm(part).split(" ").filter((w) => w.length > 2);
  if (!titleWords.length) return null;

  let best = null;
  let bestScore = 0;
  for (const s of sources) {
    if (!s.title) continue;
    if (madde && String(s.madde) !== madde) continue; // yanlış maddeye link vermektense hiç verme
    const title = norm(s.title);
    const titleHit = titleWords.filter((w) => title.includes(w)).length / titleWords.length;
    if (titleHit < 0.6) continue;
    const label = norm(s.label);
    const labelHit = partWords.filter((w) => label.includes(w)).length / partWords.length; // ör. takvimde bölüm adı
    const score = titleHit + labelHit;
    if (score > bestScore) { best = s; bestScore = score; }
  }
  return best;
}

// Cevap metnindeki [ ... ] atıflarını link'e çevirir. Markdown link'lerine ([metin](url)) dokunmaz.
// Bir köşeli parantezde ";" ile ayrılmış birden fazla atıf olabilir.
function linkCitations(text, sources) {
  return text.replace(/\[([^\]\n]{3,300})\](?!\()/g, (whole, inner) => {
    const parts = inner.split(";").map((part) => {
      const s = matchSource(part, sources);
      return s ? `<a href="#" class="cite" data-chunk="${s.chunk_id}">${escapeHtml(part.trim())}</a>` : escapeHtml(part);
    });
    return `[${parts.join("; ")}]`;
  });
}

// Markdown → güvenli HTML. LLM'in ürettiği metin HTML içerebilir; DOMPurify, sayfaya eklenmeden önce
// <script>, onclick=... gibi çalıştırılabilir her şeyi temizler (XSS koruması).
function renderAnswer(text, sources = []) {
  const html = marked.parse(linkCitations(text, sources), { breaks: true });
  return DOMPurify.sanitize(html);
}

// --- Kaynak paneli ---

const panel = {
  el: null,
  init() {
    this.el = document.createElement("aside");
    this.el.className = "panel";
    this.el.setAttribute("aria-hidden", "true");
    this.el.innerHTML = `
      <div class="panel-head">
        <div><h2></h2><div class="sub"></div></div>
        <button class="panel-close" aria-label="Kapat">×</button>
      </div>
      <div class="panel-body"></div>
      <div class="panel-foot" hidden></div>`;
    document.body.appendChild(this.el);
    this.el.querySelector(".panel-close").addEventListener("click", () => this.close());
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") this.close(); });
  },
  show({ title, sub = "", html, pdf }) {
    this.el.querySelector("h2").textContent = title;
    this.el.querySelector(".sub").textContent = sub;
    const body = this.el.querySelector(".panel-body");
    body.innerHTML = html;
    body.scrollTop = 0;
    const foot = this.el.querySelector(".panel-foot");
    foot.hidden = !pdf;
    if (pdf) foot.innerHTML = `<a href="${pdf.url}" target="_blank" rel="noopener">PDF'te aç${pdf.page ? ` (s. ${pdf.page})` : ""} ↗</a>`;
    this.el.classList.add("open");
    this.el.setAttribute("aria-hidden", "false");
  },
  close() {
    this.el.classList.remove("open");
    this.el.setAttribute("aria-hidden", "true");
    document.querySelectorAll(".source-chip.active").forEach((b) => b.classList.remove("active"));
  },
};

// PDF'ten okunan metinde satırlar sayfa genişliğinde kırılmış ("...bitirmiş olduğu dönemlere ait\ngenel not...").
// Okurken bu kırılmaları birleştirir; fıkra "(3)", bent "a)", "MADDE" ve boş satır başlangıçlarını korur.
// Yalnız gösterim için: chunk'ın kendisi (retrieval'da kullanılan metin) değişmez.
function reflow(text) {
  return text.replace(/([^\n])\n(?!\n|\s*(\(\d+\)|[a-zçğıöşü]\)|[A-ZÇĞİÖŞÜ]{3,}|MADDE|\[|-|•))/g, "$1 ");
}

function pdfUrl(source, page) {
  // encodeURIComponent: dosya adlarında boşluk ve Türkçe karakter var ("Engelli Öğrenciler ... .pdf").
  // #page=N tarayıcının PDF görüntüleyicisine hangi sayfayı açacağını söyler.
  return `/files/${encodeURIComponent(source)}${page ? `#page=${page}` : ""}`;
}

async function openChunk(chunkId) {
  panel.show({ title: "Yükleniyor…", html: "" });
  try {
    const c = await api(`/chunks/${chunkId}`);
    panel.show({
      title: c.title,
      sub: c.label.slice(c.title.length).replace(/^,\s*/, ""),
      html: `<p class="chunk-text">${escapeHtml(reflow(c.text))}</p>`,
      pdf: { url: pdfUrl(c.source, c.page), page: c.page },
    });
  } catch (e) {
    panel.show({ title: "Kaynak açılamadı", html: `<p>${escapeHtml(e.message)}</p>` });
  }
}

async function openDocument(source, title) {
  panel.show({ title, sub: "Yükleniyor…", html: "" });
  try {
    const chunks = await api(`/documents/${encodeURIComponent(source)}/chunks`);
    panel.show({
      title,
      sub: `${chunks.length} chunk`,
      html: chunks.map((c) => `
        <div class="chunk-block">
          <h3>${escapeHtml(c.label.slice(title.length).replace(/^,\s*/, "") || c.label)} · chunk ${c.chunk_id}</h3>
          <p class="chunk-text">${escapeHtml(reflow(c.text))}</p>
        </div>`).join(""),
      pdf: { url: pdfUrl(source) },
    });
  } catch (e) {
    panel.show({ title, html: `<p>${escapeHtml(e.message)}</p>` });
  }
}

// Sayfadaki her atıf linki ve kaynak düğmesi için tek bir dinleyici (event delegation): elemanlar sonradan
// eklense bile çalışır, her elemana ayrı dinleyici eklemek gerekmez.
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-chunk]");
  if (!el) return;
  e.preventDefault();
  document.querySelectorAll(".source-chip.active").forEach((b) => b.classList.remove("active"));
  if (el.classList.contains("source-chip")) el.classList.add("active");
  openChunk(Number(el.dataset.chunk));
});

// --- Üst bar durumu ---

async function loadStatus() {
  const el = document.querySelector(".status");
  if (!el) return;
  try {
    const h = await api("/health");
    el.textContent = `${h.experiment} · ${h.commit} · ${h.documents} belge`;
  } catch {
    el.textContent = "sunucuya ulaşılamıyor";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  panel.init();
  loadStatus();
});
