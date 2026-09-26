# AIOS Integrated Prototype v0.3

Runnable AIOS prototype for Human review.

## Included

- Login, Identity/Role/Context/Authority workspace
- Foundation People/Student/Organization Excel import persisted in SQLite
- Admin account/role management
- Data records persisted in SQLite
- AI Agent Registry with Personal, Domain, Admin, Verification, Data/Semantic and Institutional Intelligence agents
- Multi-provider adapters: OpenAI, Anthropic, Gemini and OpenAI-compatible endpoints
- Provider/model registry with server-side environment secrets only
- AI run audit trail
- Static GitHub review mode plus full Codespaces/server runtime

## Full runtime

```bash
python -m pip install -e .
python -m hdc.prototype_server --host 0.0.0.0 --port 8000
```

Open the Codespaces forwarded port 8000.

Provider secrets are optional and are never placed in browser code:

```bash
export OPENAI_API_KEY='...'
export ANTHROPIC_API_KEY='...'
export GEMINI_API_KEY='...'
```

Provider/model bindings are managed in **Administration → Provider Registry** and **AI Agent Registry**.

## GitHub review page

The repository root contains `index.html`, which redirects to `ui/`. GitHub Pages can therefore publish the branch from **/(root)**. In this mode AIOS displays the complete interface, Agent Registry and Provider Registry with demo/synthetic responses; backend-only functions are clearly marked as requiring runtime.

## Runtime data

Default SQLite database: `runtime/aios-prototype.sqlite3`.
Set `AIOS_DB_PATH` to a persistent server/Codespaces path when desired. Source `.xlsx` uploads are parsed in memory and are not retained by the app.


## Live AI providers

Copy `.env.example` to `.env` and place provider keys only in `.env` (never in the browser or Git). The server automatically loads `.env` on startup. Supported adapters are OpenAI Responses, Anthropic Messages, Gemini generateContent, and OpenAI-compatible chat completions. Admin > AI Providers exposes whether a server secret is configured and can run a minimal connectivity test without revealing the key.

## v0.3.2 review/runtime bridge

- GitHub Pages can serve the root UI for Human review.
- In Administration > Provider Registry, set the public runtime backend URL and click **Kết nối backend**.
- OpenAI / Anthropic / Gemini API keys can then be entered directly in the Provider drawer and saved with **Lưu & kiểm tra**.
- API keys are sent to the runtime backend and persisted only under `runtime/provider-secrets.json` (gitignored, mode 0600 where supported). They are never returned by provider APIs and are never stored in browser localStorage.
- Foundation Data imports, accounts, SQLite persistence, AI chat and provider tests use that same backend.
