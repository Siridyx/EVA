"""
EVA Web — Interface browser légère (R-032).

Scope Phase 3 :
    GET / — page HTML complète (chat + status)

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
from eva.api.app import app  # réutilise l'app FastAPI R-031 (+ lifespan + _state)
from fastapi.responses import HTMLResponse


# ---------------------------------------------------------------------------
# HTML embarqué (CSS + JS inline)
# ---------------------------------------------------------------------------


def _build_html() -> str:
    """Construit la page HTML complète avec CSS et JS embarqués."""
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
  </style>
</head>
<body>

  <header>
    <div class="logo">EVA <span>v{__version__}</span></div>
    <div class="status-badge">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text">Connexion…</span>
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

    // ── État ─────────────────────────────────────────────────────────────────
    let conversationId = null;  // maintenu côté client
    let engineRunning  = false;

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
      return textEl;  // retourné pour replace_thinking
    }}

    function addEva(text)    {{ addMessage("EVA", text, "msg-eva"); }}
    function addUser(text)   {{ addMessage("Toi", text, "msg-user"); }}
    function addSys(text)    {{ addMessage("Système", text, "msg-sys"); }}
    function addError(text)  {{ addMessage("Erreur", text, "msg-err"); }}

    // ── Indicateur "EVA réfléchit…" ──────────────────────────────────────────
    let thinkingEl = null;

    function showThinking() {{
      thinkingEl = addMessage("EVA", "Réfléchit…", "msg-eva");
    }}

    function hideThinking(responseText) {{
      if (thinkingEl) {{
        if (responseText !== null && responseText !== undefined) {{
          // Remplace le texte "Réfléchit…" par la vraie réponse
          thinkingEl.textContent = responseText;
        }} else {{
          // Erreur : supprimer l'indicateur du DOM plutôt qu'afficher "null"
          const parentMsg = thinkingEl.closest(".msg");
          if (parentMsg) parentMsg.remove();
        }}
        thinkingEl = null;
      }}
    }}

    // ── Polling statut ───────────────────────────────────────────────────────
    async function pollStatus() {{
      try {{
        const res = await fetch("/status");
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

    // Démarrer le polling : immédiat + toutes les 5s
    pollStatus();
    setInterval(pollStatus, 5000);

    // ── Envoi message ────────────────────────────────────────────────────────
    async function sendMessage(text) {{
      if (!text.trim()) return;

      addUser(text);
      input.value = "";
      input.disabled = true;
      sendBtn.disabled = true;
      showThinking();

      try {{
        const payload = {{ message: text }};
        if (conversationId) payload.conversation_id = conversationId;

        const res = await fetch("/chat", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});

        if (!res.ok) {{
          const err = await res.json().catch(() => ({{}}));
          hideThinking(null);  // supprime l'indicateur du DOM
          addError(err.detail || "Erreur HTTP " + res.status);
        }} else {{
          const data = await res.json();
          conversationId = data.conversation_id;
          hideThinking(data.response);
        }}
      }} catch (e) {{
        hideThinking(null);
        addError("Impossible de contacter le serveur : " + e.message);
      }} finally {{
        if (engineRunning) {{
          input.disabled = false;
          sendBtn.disabled = false;
        }}
        input.focus();
      }}
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
_HTML: str = _build_html()


# ---------------------------------------------------------------------------
# Route web (enregistrée sur l'app FastAPI existante R-031)
# ---------------------------------------------------------------------------


@app.get("/", tags=["Web"], include_in_schema=False)
async def web_index() -> HTMLResponse:
    """
    Interface browser EVA.

    Consomme POST /chat et GET /status (R-031).
    HTML/CSS/JS entièrement embarqués.
    """
    return HTMLResponse(content=_HTML)


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
