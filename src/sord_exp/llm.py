"""Chat backends: an OpenAI-compatible client (provider prefixes, e.g. "modal:gemma-4-31b-it") and a scripted test model.

API keys are read from the environment, or from an env file whose path is given by --env-file / SORD_ENV_FILE.
Key values are never logged or written anywhere.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from .scenarios import ORACLE

MODAL_APPS = {"gemma-4-31b-it": "revres-vllm", "qwen3.8-27b": "revres-vllm-qwen", "ministral-3-14b": "revres-vllm-ministral",
              "gpt-oss-120b": "revres-vllm-gptoss"}

PROVIDERS = {  # "provider:model"; no prefix means OpenRouter
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "modal": ("https://fatimahemad--{app}-serve.us-east.modal.run/v1", "REVRES_VLLM_KEY"),
    "ollama": ("http://localhost:11434/v1", "OLLAMA_API_KEY"),
}


def load_env_file(path: str | None) -> None:
    path = path or os.environ.get("SORD_ENV_FILE")
    for p in ([Path(path)] if path else []) + [Path.cwd() / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def strip_reasoning(text: str) -> str:
    text = re.sub(r"<(think|thought)>.*?</(think|thought)>", "", text, flags=re.S)
    return re.sub(r"^.*?</think>", "", text, flags=re.S).strip()


class OpenAIChat:
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 1500):
        from openai import OpenAI
        provider, _, name = model.partition(":") if ":" in model else ("openrouter", "", model)
        base, keyvar = PROVIDERS[provider]
        if provider == "modal":
            base = base.format(app=MODAL_APPS.get(name, name))
        key = os.environ.get(keyvar)
        if not key:
            raise RuntimeError(f"Set {keyvar} in the environment or the env file")
        self.client = OpenAI(base_url=base, api_key=key, timeout=600, max_retries=0)
        self.model, self.provider, self.temperature, self.max_tokens = name, provider, temperature, max_tokens
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    def __call__(self, messages: list[dict], seed: int | None = None) -> str:
        last, empties = None, 0
        for attempt in range(8):
            try:
                extra: dict = {"seed": None if seed is None else seed + 1000 * empties}
                if "gpt-oss" in self.model:
                    extra["reasoning_effort"] = "low"
                if "qwen" in self.model:
                    extra["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
                r = self.client.chat.completions.create(model=self.model, messages=messages, temperature=self.temperature,
                                                        max_tokens=self.max_tokens, **extra)
                if r.usage:
                    self.usage["prompt_tokens"] += r.usage.prompt_tokens or 0
                    self.usage["completion_tokens"] += r.usage.completion_tokens or 0
                self.usage["calls"] += 1
                text = strip_reasoning(r.choices[0].message.content or "")
                if not text.strip():
                    # gpt-oss on vLLM sometimes ends after its reasoning channel with no final message. Retry once
                    # with a shifted seed, then return "" so the env treats it as an invalid turn and re-prompts.
                    empties += 1
                    self.usage["empty"] = self.usage.get("empty", 0) + 1
                    if empties >= 2:
                        return ""
                    continue
                return text
            except Exception as e:  # transient provider errors, cold starts
                last = e
                time.sleep(min(60, 2 ** attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last!r}")


class ScriptedChat:
    """Deterministic test model: an ideal conformist.

    It lists the wiki, reads the index (or the first page), answers correctly, then writes its own page copying
    whatever page-name suffix and body tag it saw, and appends itself to Answers-Index if one exists.
    """
    def __init__(self, model: str = "scripted"):
        self.model = model
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    def __call__(self, messages: list[dict], seed: int | None = None) -> str:
        self.usage["calls"] += 1
        user0 = messages[1]["content"]
        aid = re.search(r"You are (A\d+)", user0).group(1)
        qid = re.search(r"\(id (Q-\d{4})\)", user0).group(1)
        question = user0.split("): ", 1)[1].split("\n\n", 1)[0]
        answer = ORACLE.get(question, "unknown")
        done = [json.loads(m["content"]) for m in messages[2:] if m["role"] == "assistant"]
        obs = [m["content"] for m in messages[2:] if m["role"] == "user"]
        listing = obs[0][len("Result: "):] if obs else ""
        pages = [] if "empty" in listing else [p for p in listing.splitlines() if p]
        plan = [{"tool": "list_pages", "args": {}}]
        if pages:
            plan.append({"tool": "read_page", "args": {"name": "Answers-Index" if "Answers-Index" in pages else pages[0]}})
            other = next((p for p in pages if p != "Answers-Index"), None)
            if other and "Answers-Index" in pages:
                plan.append({"tool": "read_page", "args": {"name": other}})
        seen = "\n".join(obs)
        suf = next((m.group(1) for p in pages if (m := re.search(r"-([A-Z0-9]{3})$", p))), None)
        tag = re.search(r"~[a-z0-9]+~", seen)
        plan.append({"tool": "submit_answer", "args": {"answer": answer}})
        name = f"answer-{qid}" + (f"-{suf}" if suf else "")
        body = (f"{tag.group(0)} " if tag else "") + f"{qid}: {question}\nAnswer: {answer}\n-- {aid}"
        plan.append({"tool": "write_page", "args": {"name": name, "body": body}})
        if "Answers-Index" in pages:
            prev = obs[1][len("Result: "):].strip() if len(obs) > 1 else ""
            plan.append({"tool": "write_page", "args": {"name": "Answers-Index", "body": f"{prev}\n[{qid}] {answer} (by {aid})".strip()}})
        plan.append({"tool": "finish", "args": {"note": "done"}})
        return json.dumps(plan[min(len(done), len(plan) - 1)])


def make_backend(kind: str, model: str):
    return ScriptedChat(model) if kind == "scripted" else OpenAIChat(model)
