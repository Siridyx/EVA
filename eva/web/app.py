"""
EVA Web — Interface browser légère (R-032).

Scope Phase 3 :
    GET / — page HTML complète (chat + status)

Phase 4(C) :
    - Injection clé API dans la page (GET / à chaque requête)
    - EventSource pour /chat/stream (streaming SSE token par token)
    - Correction auth /status dans le polling (Bearer header)

Architecture :
    Module-plugin : l'import de ce module enregistre GET /
    sur l'app FastAPI existante (R-031).
    eva/api/app.py n'est PAS modifié.

HTML/CSS/JS entièrement embarqués — zéro dépendance supplémentaire,
zéro framework, zéro build tool, zéro CDN.

Lancement :
    eva --web               # http://127.0.0.1:8000

Standards :
- Python 3.9 strict
- PEP8 strict
- host=127.0.0.1 strict (hérité de main() de l'API)
"""

from __future__ import annotations

from eva import __version__
from eva.api.app import _state  # noqa: F401  — accès au key_manager pour injection clé
from eva.api.app import app  # réutilise l'app FastAPI R-031 (+ lifespan + _state)
from fastapi.responses import HTMLResponse


# ---------------------------------------------------------------------------
# HTML embarqué (CSS + JS inline)
# ---------------------------------------------------------------------------


def _build_html() -> str:
    """Construit la page HTML complète avec CSS et JS embarqués.

    La clé API (__API_KEY__) est injectée dynamiquement à chaque requête GET /
    via _HTML.replace("__API_KEY__", key, 1) dans web_index().
    """
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EVA {__version__}</title>
  <style>
    /* ── Reset ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    /* ── Thème : dark cyan/bleu (cohérent avec TUI) ── */
    :root {{
      --bg:      #0a0a1a;
      --bg2:     #0f0f2a;
      --bg3:     #14143a;
      --cyan:    #00d4ff;
      --cyan2:   #00a8cc;
      --white:   #e0e0e0;
      --grey:    #8888aa;
      --red:     #ff4444;
      --border:  #1e1e4a;
      --radius:  6px;
    }}

    body {{
      background: var(--bg);
      color: var(--white);
      font-family: "Consolas", "Monaco", "Courier New", monospace;
      font-size: 14px;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* ── Header ── */
    header {{
      background: var(--bg2);
      border-bottom: 1px solid var(--border);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }}

    .logo {{
      color: var(--cyan);
      font-weight: bold;
      font-size: 16px;
      letter-spacing: 2px;
    }}

    .logo span {{
      color: var(--grey);
      font-size: 12px;
      font-weight: normal;
      letter-spacing: 0;
      margin-left: 8px;
    }}

    .status-badge {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--grey);
    }}

    .status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--grey);
      transition: background 0.3s;
    }}

    .status-dot.running  {{ background: var(--cyan); box-shadow: 0 0 6px var(--cyan); }}
    .status-dot.stopped  {{ background: var(--grey); }}
    .status-dot.error    {{ background: var(--red); }}

    /* ── Zone chat ── */
    #chat-history {{
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 900px;
      width: 100%;
      margin: 0 auto;
      align-self: stretch;
    }}

    /* Scrollbar discrète */
    #chat-history::-webkit-scrollbar {{ width: 4px; }}
    #chat-history::-webkit-scrollbar-track {{ background: var(--bg); }}
    #chat-history::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

    /* ── Messages ── */
    .msg {{
      display: flex;
      flex-direction: column;
      gap: 2px;
      animation: fadeIn 0.2s ease-in;
    }}

    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; }} }}

    .msg-sender {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      opacity: 0.7;
    }}

    .msg-text {{
      padding: 8px 12px;
      border-radius: var(--radius);
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
      max-width: 85%;
    }}

    .msg-eva .msg-sender  {{ color: var(--cyan); }}
    .msg-eva .msg-text    {{ background: var(--bg3); border-left: 3px solid var(--cyan); color: var(--white); }}

    .msg-user .msg-sender {{ color: var(--white); text-align: right; align-self: flex-end; }}
    .msg-user .msg-text   {{ background: var(--bg2); border-right: 3px solid var(--white); align-self: flex-end; color: var(--white); }}

    .msg-sys .msg-text    {{ color: var(--grey); font-style: italic; font-size: 12px; }}
    .msg-err .msg-text    {{ color: var(--red); border-left: 3px solid var(--red); background: #1a0a0a; }}

    /* ── Zone saisie ── */
    #input-area {{
      background: var(--bg2);
      border-top: 1px solid var(--border);
      padding: 12px 20px;
      flex-shrink: 0;
    }}

    #chat-form {{
      display: flex;
      gap: 8px;
      max-width: 900px;
      margin: 0 auto;
    }}

    #msg-input {{
      flex: 1;
      background: var(--bg3);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      color: var(--white);
      font-family: inherit;
      font-size: 14px;
      padding: 8px 12px;
      outline: none;
      transition: border-color 0.2s;
    }}

    #msg-input:focus {{ border-color: var(--cyan); }}
    #msg-input::placeholder {{ color: var(--grey); }}
    #msg-input:disabled {{ opacity: 0.5; cursor: not-allowed; }}

    #send-btn {{
      background: var(--cyan);
      color: var(--bg);
      border: none;
      border-radius: var(--radius);
      font-family: inherit;
      font-size: 13px;
      font-weight: bold;
      padding: 8px 16px;
      cursor: pointer;
      letter-spacing: 1px;
      transition: background 0.2s, opacity 0.2s;
    }}

    #send-btn:hover   {{ background: var(--cyan2); }}
    #send-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}

    /* ── Footer ── */
    footer {{
      background: var(--bg);
      border-top: 1px solid var(--border);
      padding: 4px 20px;
      text-align: center;
      font-size: 11px;
      color: var(--grey);
      flex-shrink: 0;
    }}

    /* ── Perf badge (header) -- Phase 5(D) ── */
    .perf-badge {{
      border-left: 1px solid var(--border);
      padding-left: 10px;
      margin-left: 4px;
      font-size: 11px;
      color: var(--grey);
    }}

    /* ── Metadonnees message (event:done) -- Phase 5(D) ── */
    .msg-meta {{
      font-size: 11px;
      color: var(--grey);
      padding: 2px 12px 0;
      font-style: italic;
    }}
  </style>
</head>
<body>

  <header>
    <div class="logo">EVA <span>v{__version__}</span></div>
    <div class="status-badge">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text">Connexion…</span>
      <div class="perf-badge" id="perf-badge" style="display:none"><span id="perf-text"></span></div>
    </div>
  </header>

  <div id="chat-history"></div>

  <div id="input-area">
    <form id="chat-form">
      <input
        id="msg-input"
        type="text"
        placeholder="Écrire un message… (Entrée pour envoyer)"
        autocomplete="off"
        autofocus
      >
      <button id="send-btn" type="submit">Envoyer</button>
    </form>
  </div>

  <footer>EVA {__version__} — interface web (R-032) — <a href="/docs" style="color:#00d4ff">API docs</a></footer>

  <script>
    "use strict";

    // ── DOM ──────────────────────────────────────────────────────────────────
    const history  = document.getElementById("chat-history");
    const form     = document.getElementById("chat-form");
    const input    = document.getElementById("msg-input");
    const sendBtn  = document.getElementById("send-btn");
    const statusDot  = document.getElementById("status-dot");
    const statusText = document.getElementById("status-text");
    const perfBadge  = document.getElementById("perf-badge");
    const perfText   = document.getElementById("perf-text");

    // ── État ─────────────────────────────────────────────────────────────────
    let conversationId  = null;   // maintenu côté client
    let engineRunning   = false;
    let _evaStreamAccum = "";     // accumule les tokens SSE en cours

    // Clé API injectée par le serveur à la génération de la page
    const API_KEY = "__API_KEY__";

    // ── Utilitaires ──────────────────────────────────────────────────────────
    function addMessage(sender, text, cls) {{
      const div = document.createElement("div");
      div.className = "msg " + cls;

      const senderEl = document.createElement("div");
      senderEl.className = "msg-sender";
      senderEl.textContent = sender;

      const textEl = document.createElement("div");
      textEl.className = "msg-text";
      textEl.textContent = text;

      div.appendChild(senderEl);
      div.appendChild(textEl);
      history.appendChild(div);
      history.scrollTop = history.scrollHeight;
      return textEl;  // retourné pour mise à jour progressive (SSE)
    }}

    function addEva(text)    {{ addMessage("EVA", text, "msg-eva"); }}
    function addUser(text)   {{ addMessage("Toi", text, "msg-user"); }}
    function addSys(text)    {{ addMessage("Système", text, "msg-sys"); }}
    function addError(text)  {{ addMessage("Erreur", text, "msg-err"); }}

    // ── Indicateur "EVA réfléchit…" ──────────────────────────────────────────
    // thinkingEl : référence au .msg-text de l'indicateur EVA.
    // Réutilisé pendant le SSE pour afficher les tokens progressivement
    // (évite de créer un nouvel élément DOM au premier token).
    let thinkingEl = null;

    function showThinking() {{
      thinkingEl = addMessage("EVA", "Réfléchit…", "msg-eva");
    }}

    function hideThinking(responseText) {{
      if (thinkingEl) {{
        if (responseText !== null && responseText !== undefined) {{
          thinkingEl.textContent = responseText;
        }} else {{
          // Erreur : supprimer l'indicateur du DOM
          const parentMsg = thinkingEl.closest(".msg");
          if (parentMsg) parentMsg.remove();
        }}
        thinkingEl = null;
      }}
    }}

    // ── Polling statut ───────────────────────────────────────────────────────
    async function pollStatus() {{
      try {{
        // /status requiert auth depuis Phase 4(B)
        const headers = API_KEY ? {{ "Authorization": "Bearer " + API_KEY }} : {{}};
        const res = await fetch("/status", {{ headers }});
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        engineRunning = data.engine === "RUNNING";

        statusDot.className = "status-dot " + (engineRunning ? "running" : "stopped");
        statusText.textContent = data.engine + (data.provider ? " · " + data.provider : "");

        if (!engineRunning) {{
          input.disabled = true;
          sendBtn.disabled = true;
          input.placeholder = "Moteur EVA non démarré…";
        }} else {{
          input.disabled = false;
          sendBtn.disabled = false;
          input.placeholder = "Écrire un message… (Entrée pour envoyer)";
        }}
      }} catch (e) {{
        statusDot.className = "status-dot error";
        statusText.textContent = "Connexion perdue";
      }}
    }}

    // Polling metriques (/metrics) -- Phase 5(D)
    async function pollMetrics() {{
      if (!API_KEY) return;
      try {{
        const res = await fetch("/metrics", {{
          headers: {{ "Authorization": "Bearer " + API_KEY }},
        }});
        if (!res.ok) return;  // 503 (pas init) ou 401 : silent
        const data = await res.json();
        const stream = data.endpoints && data.endpoints.chat_stream;
        if (stream && stream.p50_ttft_ms > 0) {{
          const parts = ["TTFT p50 " + stream.p50_ttft_ms + "ms"];
          const chat = data.endpoints.chat;
          if (chat && chat.p50_ms > 0) parts.push("chat p50 " + chat.p50_ms + "ms");
          perfText.textContent = parts.join(" \u00b7 ");
          perfBadge.style.display = "";
        }}
      }} catch (_) {{}}
    }}

    // Demarrer le polling : immediat + toutes les 5s
    pollStatus();
    setInterval(pollStatus, 5000);
    // Metriques : appel initial a t+2s puis toutes les 30s
    setTimeout(function() {{ pollMetrics(); setInterval(pollMetrics, 30000); }}, 2000);

    // ── Envoi message (SSE / EventSource) ────────────────────────────────────
    // Phase 4(C) : remplace fetch POST /chat par EventSource GET /chat/stream
    // EventSource ne supporte pas les headers customs → clé passée en query param.
    function sendMessage(text) {{
      if (!text.trim()) return;

      addUser(text);
      input.value = "";
      input.disabled = true;
      sendBtn.disabled = true;
      showThinking();  // affiche "Réfléchit…" — thinkingEl = .msg-text

      // Construire l'URL SSE avec les paramètres
      const params = new URLSearchParams({{ message: text }});
      if (conversationId) params.set("conversation_id", conversationId);
      if (API_KEY) params.set("api_key", API_KEY);

      _evaStreamAccum = "";
      const es = new EventSource("/chat/stream?" + params.toString());

      // event: meta — reçoit conversation_id et provider
      es.addEventListener("meta", (e) => {{
        const d = JSON.parse(e.data);
        conversationId = d.conversation_id;
      }});

      // event: token — accumule et affiche progressivement dans thinkingEl
      es.addEventListener("token", (e) => {{
        const d = JSON.parse(e.data);
        _evaStreamAccum += d.text;
        if (thinkingEl) {{
          // Premier token : remplace "Réfléchit…" par le texte en cours
          thinkingEl.textContent = _evaStreamAccum;
          history.scrollTop = history.scrollHeight;
        }}
      }});

      // event: done — fin normale du stream
      es.addEventListener("done", (e) => {{
        es.close();
        if (!_evaStreamAccum && thinkingEl) {{
          thinkingEl.textContent = "…";  // fallback si aucun token recu
        }}
        // Metadonnees TTFT/tokens depuis event:done -- Phase 5(D)
        try {{
          const d = JSON.parse(e.data);
          const parentMsg = thinkingEl && thinkingEl.closest(".msg");
          if (parentMsg && (d.ttft_ms !== undefined || d.tokens_per_sec !== undefined)) {{
            const parts = [];
            if (d.ttft_ms !== undefined) parts.push("TTFT " + d.ttft_ms + "ms");
            if (d.tokens !== undefined) parts.push(d.tokens + " tok");
            if (d.tokens_per_sec !== undefined) parts.push(d.tokens_per_sec + " t/s");
            if (parts.length > 0) {{
              const metaEl = document.createElement("div");
              metaEl.className = "msg-meta";
              metaEl.textContent = parts.join(" \u00b7 ");
              parentMsg.appendChild(metaEl);
            }}
          }}
        }} catch (_) {{}}
        thinkingEl = null;
        if (engineRunning) {{ input.disabled = false; sendBtn.disabled = false; }}
        input.focus();
      }});

      // event: error (custom du serveur) OU erreur réseau/HTTP
      // - e.data présent  → événement "error" envoyé par le serveur
      // - e.data absent   → erreur de connexion (401, réseau, etc.)
      es.addEventListener("error", (e) => {{
        es.close();
        hideThinking(null);  // supprime l'indicateur "Réfléchit…"
        if (e.data) {{
          try {{
            addError(JSON.parse(e.data).message || "Erreur serveur");
          }} catch (_) {{
            addError("Erreur serveur");
          }}
        }} else {{
          addError("Connexion perdue ou erreur serveur (vérifiez la clé API)");
        }}
        if (engineRunning) {{ input.disabled = false; sendBtn.disabled = false; }}
        input.focus();
      }});
    }}

    // ── Événements formulaire ─────────────────────────────────────────────────
    form.addEventListener("submit", (e) => {{
      e.preventDefault();
      sendMessage(input.value.trim());
    }});

    // ── Message de bienvenue ─────────────────────────────────────────────────
    addSys("Interface web EVA v{__version__} — connecté à http://127.0.0.1:8000");
  </script>

</body>
</html>"""


# Construire le HTML une seule fois au chargement du module
# La clé API (__API_KEY__) sera remplacée dynamiquement dans web_index()
_HTML: str = _build_html()


# ---------------------------------------------------------------------------
# Route web (enregistrée sur l'app FastAPI existante R-031)
# ---------------------------------------------------------------------------


@app.get("/", tags=["Web"], include_in_schema=False)
async def web_index() -> HTMLResponse:
    """
    Interface browser EVA.

    Consomme GET /chat/stream (SSE, Phase 4(C)) et GET /status (R-031).
    HTML/CSS/JS entièrement embarqués.

    Injection de la clé API dans la page à chaque requête (Phase 4(C)) :
    le placeholder __API_KEY__ est remplacé par la vraie clé pour que
    le JS puisse appeler /chat/stream?api_key=<key> via EventSource.
    """
    api_key = _state.key_manager.key if _state.key_manager else ""
    return HTMLResponse(content=_HTML.replace("__API_KEY__", api_key, 1))


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main(host: str = "127.0.0.1", port: int = 8000) -> int:
    """
    Lance le serveur EVA Web.

    Args:
        host: Adresse d'écoute.
              Phase 3 security rule: API bound to 127.0.0.1 only.
        port: Port d'écoute (défaut : 8000)

    Returns:
        Code de sortie (0 = normal, 1 = erreur)
    """
    try:
        import uvicorn

        print(f"EVA Web v{__version__} — http://{host}:{port}")
        print(f"  API docs : http://{host}:{port}/docs")
        uvicorn.run(app, host=host, port=port)
        return 0
    except ImportError:
        print(
            "uvicorn non installé. "
            "Installez-le : pip install 'fastapi[standard]'"
        )
        return 1
    except Exception as exc:
        print(f"Erreur Web : {exc}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
