"""LLM gateway (agent layer). The single place the Claude API is called.

Agents send a job on greenhouse/llm/cmd and get the answer on greenhouse/llm/reply/<id>.
The gateway enforces a daily token budget and an hourly call limit, attaches images, and
answers "unavailable" instead of hanging when there is no key, no network or no budget.
Swapping to a local open model means replacing the transport function only."""
import base64
import json
import os
import time
import urllib.error
import urllib.request

from .. import topics as T
from ..module import Module

API_URL = "https://api.anthropic.com/v1/messages"


def anthropic_transport(body, api_key, timeout=90):
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
        "content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def reply_topic(job_id):
    return f"{T.ROOT}/llm/reply/{job_id}"


class LlmGateway(Module):
    transport = staticmethod(anthropic_transport)

    def setup(self):
        self.queue, self.day, self.tokens_today, self.calls = [], None, 0, []
        self.api_key = os.environ.get("GH_ANTHROPIC_API_KEY", "")
        self._status()

    def _status(self, error=""):
        if not self.api_key:
            return self.report("fault", "no API key configured")
        used = f"{self.tokens_today} of {self.config['daily_token_cap']} tokens used today"
        self.report("fault" if error else "running", f"{error}; {used}" if error else used)

    def on_cmd(self, data):
        if isinstance(data.get("id"), str):
            self.queue.append(data)

    def loop(self):
        while self.queue:
            job = self.queue.pop(0)
            self.bus.publish(reply_topic(job["id"]), self.answer(job))

    def answer(self, job):
        now = self.clock()
        day = time.strftime("%Y%m%d", time.localtime(now))
        if day != self.day:
            self.day, self.tokens_today = day, 0
        self.calls = [t for t in self.calls if now - t < 3600]
        if not self.api_key:
            return {"id": job["id"], "ok": False, "error": "no API key configured"}
        if self.tokens_today >= self.config["daily_token_cap"]:
            self._status("daily token budget reached")
            return {"id": job["id"], "ok": False, "error": "daily token budget reached"}
        if len(self.calls) >= self.config["calls_per_hour"]:
            return {"id": job["id"], "ok": False, "error": "hourly call limit reached"}
        content = []
        for path in job.get("images", []):
            try:
                with open(path, "rb") as fh:
                    content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                                "data": base64.b64encode(fh.read()).decode()}})
            except OSError as exc:
                return {"id": job["id"], "ok": False, "error": f"image unreadable: {exc}"}
        content.append({"type": "text", "text": str(job.get("user", ""))})
        body = {"model": self.config["model"], "max_tokens": int(job.get("max_tokens", self.config["max_tokens"])),
                "system": str(job.get("system", "")), "messages": [{"role": "user", "content": content}]}
        tool = job.get("tool")
        if tool:
            body["tools"] = [tool]
            body["tool_choice"] = {"type": "tool", "name": tool["name"]}
        self.calls.append(now)
        try:
            resp = self.transport(body, self.api_key)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            self._status(f"API call failed: {exc}")
            return {"id": job["id"], "ok": False, "error": f"API call failed: {exc}"}
        usage = resp.get("usage", {})
        self.tokens_today += int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        blocks = resp.get("content", [])
        out = {"id": job["id"], "ok": True, "usage": usage,
               "text": " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip(),
               "tool_input": next((b.get("input") for b in blocks if b.get("type") == "tool_use"), None)}
        if tool and not isinstance(out["tool_input"], dict):
            out.update(ok=False, error="model did not return the structured answer")
        self._status()
        return out
