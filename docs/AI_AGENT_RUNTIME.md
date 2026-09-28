# AIOS AI Agent Runtime v0.3

AIOS uses a registry-driven multi-Agent runtime rather than a single super-agent.

## Agent families

- Personal AI
- Domain Agents (RIS/LIS/SIS and future domains)
- Admin Agents
- Verification AI
- Data & Semantic AI
- Institutional Intelligence

Each Agent records purpose, domain/data scope, authority boundary, risk, Human supervisor, provider and model binding.

## Provider adapters

The prototype includes server-side adapters for:

- OpenAI Responses API (`OPENAI_API_KEY`)
- Anthropic Messages API (`ANTHROPIC_API_KEY`)
- Google Gemini `generateContent` (`GEMINI_API_KEY`)
- OpenAI-compatible Chat Completions (`AIOS_COMPATIBLE_API_KEY`)

Secrets are read only from environment variables. The Registry stores the secret variable name, never the secret value.

## Review vs runtime

GitHub Pages runs the UI in review mode with synthetic/demo responses and visible Agent/Provider registries. Full provider calls, Excel import and SQLite persistence require `python -m hdc.prototype_server`.
