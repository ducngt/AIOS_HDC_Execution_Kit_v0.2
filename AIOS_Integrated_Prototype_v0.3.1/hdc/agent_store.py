"""AI Agent Registry and multi-provider runtime for the AIOS prototype.

Secrets are never stored in SQLite. Provider records only store the name of the
environment variable that contains the API key.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

from hdc.people_store import connect


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def ensure_agent_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS ai_providers(
          provider_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          adapter_type TEXT NOT NULL,
          base_url TEXT,
          api_key_env TEXT,
          default_model TEXT,
          models_json TEXT NOT NULL DEFAULT '[]',
          enabled INTEGER NOT NULL DEFAULT 1,
          config_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ai_agents(
          agent_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          category TEXT NOT NULL,
          purpose TEXT NOT NULL,
          owner TEXT,
          beneficiary TEXT,
          domain TEXT,
          role_scope TEXT,
          data_scope TEXT,
          knowledge_scope TEXT,
          capabilities_json TEXT NOT NULL DEFAULT '[]',
          tools_json TEXT NOT NULL DEFAULT '[]',
          allowed_actions_json TEXT NOT NULL DEFAULT '[]',
          forbidden_actions_json TEXT NOT NULL DEFAULT '[]',
          authority TEXT,
          autonomy TEXT NOT NULL DEFAULT 'assistive',
          risk TEXT NOT NULL DEFAULT 'medium',
          human_supervisor TEXT,
          escalation TEXT,
          provider_id TEXT,
          model TEXT,
          system_prompt TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          version TEXT NOT NULL DEFAULT '0.1.0',
          lifecycle TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(provider_id) REFERENCES ai_providers(provider_id)
        );
        CREATE TABLE IF NOT EXISTS ai_runs(
          run_id TEXT PRIMARY KEY,
          agent_id TEXT NOT NULL,
          provider_id TEXT,
          model TEXT,
          identity TEXT,
          role_context TEXT,
          authority_context TEXT,
          prompt_excerpt TEXT,
          status TEXT NOT NULL,
          error TEXT,
          created_at TEXT NOT NULL
        );
        """
    )
    con.commit()


def _provider_seed() -> list[dict[str, Any]]:
    return [
        {
            "provider_id": "openai",
            "name": "OpenAI",
            "adapter_type": "openai_responses",
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "api_key_env": "OPENAI_API_KEY",
            "default_model": os.getenv("AIOS_OPENAI_MODEL", "gpt-5.6-luna"),
            "models": ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"],
        },
        {
            "provider_id": "anthropic",
            "name": "Anthropic",
            "adapter_type": "anthropic_messages",
            "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            "api_key_env": "ANTHROPIC_API_KEY",
            "default_model": os.getenv("AIOS_ANTHROPIC_MODEL", "claude-sonnet-5"),
            "models": ["claude-sonnet-5", "claude-opus-5", "claude-fable-5"],
        },
        {
            "provider_id": "gemini",
            "name": "Google Gemini",
            "adapter_type": "gemini_generate_content",
            "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            "api_key_env": "GEMINI_API_KEY",
            "default_model": os.getenv("AIOS_GEMINI_MODEL", "gemini-3.8-flash"),
            "models": ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-pro"],
        },
        {
            "provider_id": "compatible",
            "name": "OpenAI-compatible",
            "adapter_type": "openai_chat",
            "base_url": os.getenv("AIOS_COMPATIBLE_BASE_URL", ""),
            "api_key_env": "AIOS_COMPATIBLE_API_KEY",
            "default_model": os.getenv("AIOS_COMPATIBLE_MODEL", ""),
            "models": [],
        },
    ]


def _agent_seed() -> list[dict[str, Any]]:
    common = (
        "You operate inside AIOS. Human retains institutional meaning, authority, responsibility and final consequential decisions. "
        "Never present recommendation, inference or generated content as an approved institutional decision. "
        "Respect the supplied role, context, authority and data scope."
    )
    return [
        {"agent_id":"personal-ai","name":"Personal AI","category":"personal","purpose":"Contextual assistant for the current Human, role and work.","domain":"ALL","role_scope":"authenticated user","data_scope":"user-authorized context","knowledge_scope":"current workspace","capabilities":["summarize","plan","draft","explain"],"authority":"none; advisory only","autonomy":"assistive","risk":"low","human_supervisor":"current user","escalation":"ask Human before consequential action","provider_id":"openai","system_prompt":common+" Focus on the user's current workspace and work queue."},
        {"agent_id":"ris-ai","name":"RIS AI","category":"domain","purpose":"Research intelligence for projects, publications, evidence and research work.","domain":"RIS","role_scope":"research roles","data_scope":"RIS-authorized data","knowledge_scope":"research domain","capabilities":["research-analysis","evidence-synthesis","risk-analysis","draft"],"authority":"none; cannot approve research decisions","autonomy":"assistive","risk":"medium","human_supervisor":"research authority","escalation":"escalate approvals and policy conflicts","provider_id":"openai","system_prompt":common+" You are the RIS domain agent. Keep evidence separate from decisions."},
        {"agent_id":"lis-ai","name":"LIS AI","category":"domain","purpose":"Learning intelligence for curriculum, teaching, assessment and learner support.","domain":"LIS","role_scope":"teaching/learning roles","data_scope":"LIS-authorized data","knowledge_scope":"learning domain","capabilities":["curriculum-analysis","assessment-support","learner-support","draft"],"authority":"none; cannot issue official academic decisions","autonomy":"assistive","risk":"medium","human_supervisor":"academic authority","escalation":"escalate official assessment/approval","provider_id":"gemini","system_prompt":common+" You are the LIS domain agent. Preserve academic authority boundaries."},
        {"agent_id":"sis-ai","name":"SIS AI","category":"domain","purpose":"Student intelligence for student journey, status and service coordination.","domain":"SIS","role_scope":"student-service roles","data_scope":"SIS-authorized data","knowledge_scope":"student domain","capabilities":["student-support","case-summary","risk-signal"],"authority":"none; no disciplinary or official decision","autonomy":"assistive","risk":"high","human_supervisor":"student affairs authority","escalation":"escalate high-impact student matters","provider_id":"openai","system_prompt":common+" You are the SIS domain agent. Treat personal/student data as sensitive and minimize disclosure."},
        {"agent_id":"admin-ai","name":"AI Admin Copilot","category":"admin","purpose":"Assist authorized administrators with configuration, dependency analysis, changes and operations.","domain":"PLATFORM","role_scope":"admin roles","data_scope":"platform operational metadata","knowledge_scope":"AIOS configuration and operations","capabilities":["configuration-analysis","change-planning","dependency-check","rollback-planning"],"authority":"technical advice only; no institutional authority","autonomy":"supervised","risk":"high","human_supervisor":"Platform Admin","escalation":"require Human approval for consequential change","provider_id":"openai","system_prompt":common+" You are AI Admin Copilot. Technical administration is not institutional authority."},
        {"agent_id":"verification-ai","name":"Verification AI","category":"verification","purpose":"Verify evidence, consistency, contract conformance and policy conditions.","domain":"ALL","role_scope":"verification/audit roles","data_scope":"evidence and audit scope","knowledge_scope":"contracts, evidence, provenance","capabilities":["consistency-check","evidence-check","contract-review","policy-check"],"authority":"verification finding only","autonomy":"assistive","risk":"medium","human_supervisor":"Audit/Quality authority","escalation":"surface unresolved conflict to Human","provider_id":"anthropic","system_prompt":common+" You are Verification AI. Findings are evidence, not approval."},
        {"agent_id":"data-semantic-ai","name":"Data & Semantic AI","category":"data","purpose":"Map, clean and reconcile Foundation/Living Data and semantic conflicts.","domain":"DATA","role_scope":"data/semantic steward roles","data_scope":"authorized data governance scope","knowledge_scope":"canonical identity, semantics and mappings","capabilities":["mapping","deduplication","semantic-alignment","conflict-detection"],"authority":"candidate mapping only until approved","autonomy":"assistive","risk":"high","human_supervisor":"Data/Semantic Steward","escalation":"escalate ambiguous authority or semantic conflicts","provider_id":"gemini","system_prompt":common+" You are Data & Semantic AI. Candidate mappings are not authoritative until governed approval."},
        {"agent_id":"institutional-intelligence","name":"Institutional Intelligence","category":"institutional","purpose":"Cross-domain synthesis of outcomes, risk, dependencies and decision options.","domain":"CROSS-DOMAIN","role_scope":"leadership roles","data_scope":"authority-filtered institutional scope","knowledge_scope":"cross-domain institutional intelligence","capabilities":["cross-domain-synthesis","forecast","scenario-analysis","decision-options"],"authority":"advisory only; Human leadership decides","autonomy":"assistive","risk":"high","human_supervisor":"institutional leadership","escalation":"always preserve Human decision boundary","provider_id":"anthropic","system_prompt":common+" You are Institutional Intelligence. Present options, consequences, evidence and uncertainty; never decide for leadership."},
    ]


def ensure_seeded() -> None:
    with connect() as con:
        ensure_agent_schema(con)
        ts = now()
        for p in _provider_seed():
            con.execute(
                """INSERT INTO ai_providers(provider_id,name,adapter_type,base_url,api_key_env,default_model,models_json,enabled,config_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(provider_id) DO NOTHING""",
                (p["provider_id"],p["name"],p["adapter_type"],p["base_url"],p["api_key_env"],p["default_model"],_j(p["models"]),1,"{}",ts,ts),
            )
        for a in _agent_seed():
            con.execute(
                """INSERT INTO ai_agents(agent_id,name,category,purpose,owner,beneficiary,domain,role_scope,data_scope,knowledge_scope,capabilities_json,tools_json,allowed_actions_json,forbidden_actions_json,authority,autonomy,risk,human_supervisor,escalation,provider_id,model,system_prompt,status,version,lifecycle,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(agent_id) DO NOTHING""",
                (a["agent_id"],a["name"],a["category"],a["purpose"],"AIOS",None,a["domain"],a["role_scope"],a["data_scope"],a["knowledge_scope"],_j(a["capabilities"]),"[]","[]","[]",a["authority"],a["autonomy"],a["risk"],a["human_supervisor"],a["escalation"],a["provider_id"],None,a["system_prompt"],"active","0.1.0","active",ts,ts),
            )
        con.commit()


def _provider_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["models"] = _loads(d.pop("models_json", None), [])
    d["config"] = _loads(d.pop("config_json", None), {})
    env_name = d.get("api_key_env") or ""
    d["configured"] = bool(env_name and os.getenv(env_name))
    d["secret_value"] = None
    return d


def _agent_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for key, target in [
        ("capabilities_json","capabilities"),("tools_json","tools"),
        ("allowed_actions_json","allowed_actions"),("forbidden_actions_json","forbidden_actions")
    ]:
        d[target] = _loads(d.pop(key, None), [])
    return d


def list_providers() -> list[dict[str, Any]]:
    ensure_seeded()
    with connect() as con:
        ensure_agent_schema(con)
        return [_provider_dict(r) for r in con.execute("SELECT * FROM ai_providers ORDER BY name").fetchall()]


def save_provider(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_seeded()
    provider_id = str(payload.get("provider_id") or "").strip().lower()
    if not provider_id:
        raise ValueError("provider_id is required")
    name = str(payload.get("name") or provider_id).strip()
    adapter_type = str(payload.get("adapter_type") or "openai_chat").strip()
    if adapter_type not in {"openai_responses","openai_chat","anthropic_messages","gemini_generate_content"}:
        raise ValueError("unsupported adapter_type")
    ts = now()
    with connect() as con:
        ensure_agent_schema(con)
        con.execute(
            """INSERT INTO ai_providers(provider_id,name,adapter_type,base_url,api_key_env,default_model,models_json,enabled,config_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(provider_id) DO UPDATE SET name=excluded.name,adapter_type=excluded.adapter_type,base_url=excluded.base_url,api_key_env=excluded.api_key_env,default_model=excluded.default_model,models_json=excluded.models_json,enabled=excluded.enabled,config_json=excluded.config_json,updated_at=excluded.updated_at""",
            (provider_id,name,adapter_type,payload.get("base_url"),payload.get("api_key_env"),payload.get("default_model"),_j(payload.get("models") or []),1 if payload.get("enabled",True) else 0,_j(payload.get("config") or {}),ts,ts),
        )
        con.commit()
    return {"provider_id": provider_id, "saved": True}


def list_agents(category: str | None = None, domain: str | None = None) -> list[dict[str, Any]]:
    ensure_seeded()
    sql = "SELECT * FROM ai_agents WHERE 1=1"; args: list[Any] = []
    if category:
        sql += " AND category=?"; args.append(category)
    if domain:
        sql += " AND (domain=? OR domain='ALL')"; args.append(domain)
    sql += " ORDER BY category,name"
    with connect() as con:
        ensure_agent_schema(con)
        return [_agent_dict(r) for r in con.execute(sql,args).fetchall()]


def get_agent(agent_id: str) -> dict[str, Any] | None:
    ensure_seeded()
    with connect() as con:
        ensure_agent_schema(con)
        row = con.execute("SELECT * FROM ai_agents WHERE agent_id=?",(agent_id,)).fetchone()
        return _agent_dict(row) if row else None


def save_agent(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_seeded()
    agent_id = str(payload.get("agent_id") or "").strip().lower()
    if not agent_id:
        raise ValueError("agent_id is required")
    name = str(payload.get("name") or "").strip()
    purpose = str(payload.get("purpose") or "").strip()
    system_prompt = str(payload.get("system_prompt") or "").strip()
    if not name or not purpose or not system_prompt:
        raise ValueError("name, purpose and system_prompt are required")
    ts = now()
    with connect() as con:
        ensure_agent_schema(con)
        con.execute(
            """INSERT INTO ai_agents(agent_id,name,category,purpose,owner,beneficiary,domain,role_scope,data_scope,knowledge_scope,capabilities_json,tools_json,allowed_actions_json,forbidden_actions_json,authority,autonomy,risk,human_supervisor,escalation,provider_id,model,system_prompt,status,version,lifecycle,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(agent_id) DO UPDATE SET name=excluded.name,category=excluded.category,purpose=excluded.purpose,owner=excluded.owner,beneficiary=excluded.beneficiary,domain=excluded.domain,role_scope=excluded.role_scope,data_scope=excluded.data_scope,knowledge_scope=excluded.knowledge_scope,capabilities_json=excluded.capabilities_json,tools_json=excluded.tools_json,allowed_actions_json=excluded.allowed_actions_json,forbidden_actions_json=excluded.forbidden_actions_json,authority=excluded.authority,autonomy=excluded.autonomy,risk=excluded.risk,human_supervisor=excluded.human_supervisor,escalation=excluded.escalation,provider_id=excluded.provider_id,model=excluded.model,system_prompt=excluded.system_prompt,status=excluded.status,version=excluded.version,lifecycle=excluded.lifecycle,updated_at=excluded.updated_at""",
            (agent_id,name,payload.get("category","personal"),purpose,payload.get("owner"),payload.get("beneficiary"),payload.get("domain"),payload.get("role_scope"),payload.get("data_scope"),payload.get("knowledge_scope"),_j(payload.get("capabilities") or []),_j(payload.get("tools") or []),_j(payload.get("allowed_actions") or []),_j(payload.get("forbidden_actions") or []),payload.get("authority"),payload.get("autonomy","assistive"),payload.get("risk","medium"),payload.get("human_supervisor"),payload.get("escalation"),payload.get("provider_id"),payload.get("model"),system_prompt,payload.get("status","active"),payload.get("version","0.1.0"),payload.get("lifecycle","active"),ts,ts),
        )
        con.commit()
    return {"agent_id": agent_id, "saved": True}


def _request_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 90) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"provider HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"provider network error: {exc}") from exc


def _call_provider(provider: dict[str, Any], model: str, system: str, prompt: str) -> str:
    env_name = str(provider.get("api_key_env") or "")
    key = os.getenv(env_name) if env_name else None
    if not key:
        raise RuntimeError(f"provider_not_configured:{env_name or provider['provider_id']}")
    base = str(provider.get("base_url") or "").rstrip("/")
    adapter = provider["adapter_type"]
    if not model:
        raise RuntimeError("model_not_configured")

    if adapter == "openai_responses":
        data = _request_json(base + "/responses", {"model":model,"instructions":system,"input":prompt}, {"Authorization":"Bearer "+key})
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        texts = []
        for item in data.get("output", []):
            for part in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(part, dict) and isinstance(part.get("text"), str): texts.append(part["text"])
        if texts: return "\n".join(texts)
        raise RuntimeError("provider_response_missing_text")

    if adapter == "openai_chat":
        data = _request_json(base + "/chat/completions", {"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}]}, {"Authorization":"Bearer "+key})
        return str(data["choices"][0]["message"]["content"])

    if adapter == "anthropic_messages":
        data = _request_json(base + "/v1/messages", {"model":model,"max_tokens":4096,"system":system,"messages":[{"role":"user","content":prompt}]}, {"x-api-key":key,"anthropic-version":"2023-06-01"})
        texts = [str(x.get("text")) for x in data.get("content",[]) if isinstance(x,dict) and x.get("type")=="text" and x.get("text")]
        if texts: return "\n".join(texts)
        raise RuntimeError("provider_response_missing_text")

    if adapter == "gemini_generate_content":
        url = base + "/models/" + urllib.parse.quote(model, safe="-_.") + ":generateContent"
        data = _request_json(url, {"systemInstruction":{"parts":[{"text":system}]},"contents":[{"role":"user","parts":[{"text":prompt}]}]}, {"x-goog-api-key":key})
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        texts = [str(x.get("text")) for x in parts if isinstance(x,dict) and x.get("text")]
        if texts: return "\n".join(texts)
        raise RuntimeError("provider_response_missing_text")

    raise RuntimeError("unsupported_adapter")



def provider_diagnostic(provider_id: str, prompt: str = "Reply only with OK") -> dict[str, Any]:
    """Perform a minimal live provider call without exposing the secret."""
    ensure_seeded()
    providers = {p["provider_id"]: p for p in list_providers()}
    provider = providers.get(provider_id)
    if not provider:
        raise ValueError("provider_not_found")
    if not provider.get("enabled"):
        raise ValueError("provider_disabled")
    model = str(provider.get("default_model") or "")
    if not provider.get("configured"):
        return {
            "provider_id": provider_id,
            "configured": False,
            "ok": False,
            "detail": f"Missing server secret: {provider.get('api_key_env') or provider_id}",
            "model": model,
        }
    try:
        text = _call_provider(
            provider,
            model,
            "You are an AIOS provider connectivity diagnostic. Return a concise response.",
            prompt[:1000],
        )
        return {
            "provider_id": provider_id,
            "configured": True,
            "ok": True,
            "model": model,
            "preview": text[:500],
        }
    except Exception as exc:
        return {
            "provider_id": provider_id,
            "configured": True,
            "ok": False,
            "model": model,
            "detail": str(exc),
        }

def chat(agent_id: str, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_seeded()
    agent = get_agent(agent_id)
    if not agent or agent.get("status") != "active":
        raise ValueError("agent_not_available")
    providers = {p["provider_id"]: p for p in list_providers()}
    provider = providers.get(agent.get("provider_id") or "")
    if not provider or not provider.get("enabled"):
        raise ValueError("provider_not_available")
    model = str(agent.get("model") or provider.get("default_model") or "")
    ctx = context or {}
    system = agent["system_prompt"] + "\nRuntime context: " + json.dumps(ctx, ensure_ascii=False)[:8000]
    run_id = "AIR-" + uuid.uuid4().hex[:16].upper()
    status = "completed"; error = None
    try:
        text = _call_provider(provider, model, system, prompt[:16000])
    except Exception as exc:
        status = "failed"; error = str(exc)
        text = ""
    with connect() as con:
        ensure_agent_schema(con)
        con.execute("INSERT INTO ai_runs(run_id,agent_id,provider_id,model,identity,role_context,authority_context,prompt_excerpt,status,error,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id,agent_id,provider["provider_id"],model,str(ctx.get("identity") or ""),str(ctx.get("role") or ""),str(ctx.get("authority") or ""),prompt[:500],status,error,now()))
        con.commit()
    if status != "completed":
        raise RuntimeError(error or "provider_error")
    return {"text":text,"run_id":run_id,"agent":agent,"provider":{"provider_id":provider["provider_id"],"name":provider["name"],"model":model}}


def recent_runs(limit: int = 100) -> list[dict[str, Any]]:
    ensure_seeded()
    with connect() as con:
        ensure_agent_schema(con)
        return [dict(r) for r in con.execute("SELECT * FROM ai_runs ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall()]
