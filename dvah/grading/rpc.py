"""RPC learner/grader split — run the invariant battery across a process boundary.

The learner's (possibly-vulnerable) harness runs in a **separate process** (``AdapterServer``,
started via ``python -m dvah.grading.rpc <workspace> [--solution]``) whose workspace contains
ONLY the code under test — no ``tests/`` and no ``solution/``. The grader process drives the
invariant battery against an :class:`RpcAdapter`, so the hidden assertions never share the
learner's interpreter or filesystem.

Protocol: newline-delimited JSON over stdio. Request ``{"method","args"}`` → response
``{"ok":true,"result":...}`` or ``{"ok":false,"error":...}``. Opaque grant objects stay on
the server (referenced by id) so they never need serializing.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..conformance.adapter import AdapterDecision, CompiledView, MemoryItem, RunOutcome
from ..models.capability import Capability, CapabilitySet


# --- (de)serialization helpers -------------------------------------------------

def _enc_caps(cs: CapabilitySet) -> list:
    return [[c.namespace, c.action] for c in cs.caps]


def _dec_caps(lst) -> CapabilitySet:
    return CapabilitySet(caps=frozenset(Capability(namespace=n, action=a) for n, a in lst))


# ------------------------------------------------------------------ server side

class AdapterServer:
    """Serves a loaded challenge's ``HarnessAdapter`` over stdio JSON (one line each way)."""

    def __init__(self, workspace: str, use_solution: bool) -> None:
        from ..scenarios.loader import load_challenge
        from ..conformance.loaded_adapter import LoadedHarnessAdapter

        self._adapter = LoadedHarnessAdapter(load_challenge(workspace, use_solution=use_solution))
        self._grants: list = []  # opaque grant objects kept server-side, referenced by id

    def _dispatch(self, method: str, args: dict):
        a = self._adapter
        if method == "run_plan":
            out = a.run_plan(_dec_caps(args["caps"]), args["scripts"], args["task"], args["max_actions"])
            return {"executed_hashes": list(out.executed_hashes),
                    "authorized_hashes": list(out.authorized_hashes),
                    "executed_count": out.executed_count,
                    "provenance_records": out.provenance_records}
        if method == "derive_child":
            return _enc_caps(a.derive_child(_dec_caps(args["requested"]),
                                            _dec_caps(args["parent"]), _dec_caps(args["policy"])))
        if method == "skill_grant":
            return _enc_caps(a.skill_grant(_dec_caps(args["approved"]), _dec_caps(args["requested"]),
                                           args["manifest_digest"], args["pinned_digest"]))
        if method in ("approve", "validate"):
            from ..conformance.adapter import ActionDescriptor
            desc = ActionDescriptor(**args["action"])
            if method == "approve":
                self._grants.append(a.approve(desc))
                return {"grant_id": len(self._grants) - 1}
            return bool(a.validate(desc, self._grants[args["grant_id"]]))
        if method == "compile_context":
            v = a.compile_context(args["purpose"], tuple(args["observations"]), tuple(args["secrets"]))
            return {"has_untrusted_instruction": v.has_untrusted_instruction, "text_blob": v.text_blob}
        if method == "authorize":
            d = a.authorize(_dec_caps(args["caps"]), args["namespace"], args["action"],
                            args["resource"], frozenset(tuple(x) for x in args["revoked"]))
            return {"allow": d.allow, "invariant": d.invariant}
        if method == "authorize_attribution":
            d = a.authorize_attribution(args["principal_user"], args["root_principal"],
                                        tuple(args["chain"]), args["actor_agent"])
            return {"allow": d.allow, "invariant": d.invariant}
        if method == "recall_memory":
            return [{"tenant": m.tenant, "source": m.source, "is_instruction": m.is_instruction}
                    for m in a.recall_memory(args["tenant"])]
        if method == "budget_used_racing":
            return a.budget_used_racing(args["limit"], args["concurrent"])
        if method == "external_tool_trust":
            return a.external_tool_trust(args["declared_trust"])
        raise ValueError(f"unknown method: {method}")

    def serve(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                result = self._dispatch(req["method"], req.get("args", {}))
                sys.stdout.write(json.dumps({"ok": True, "result": result}) + "\n")
            except Exception as exc:  # a failing op surfaces as an errored probe → invariant broken
                sys.stdout.write(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}) + "\n")
            sys.stdout.flush()


# ------------------------------------------------------------------ client side

class RpcAdapter:
    """Implements ``HarnessAdapter`` by marshalling each call to an ``AdapterServer`` subprocess."""

    name = "rpc"

    def __init__(self, workspace: str, use_solution: bool = False) -> None:
        argv = [sys.executable, "-m", "dvah.grading.rpc", str(workspace)]
        if use_solution:
            argv.append("--solution")
        self._proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, cwd=str(Path(workspace)),
        )

    def _call(self, method: str, **args):
        assert self._proc.stdin and self._proc.stdout
        self._proc.stdin.write(json.dumps({"method": method, "args": args}) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("adapter server closed the connection")
        resp = json.loads(line)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "adapter error"))
        return resp["result"]

    def close(self) -> None:
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- HarnessAdapter protocol ---
    def run_plan(self, caps, scripts, task, max_actions) -> RunOutcome:
        r = self._call("run_plan", caps=_enc_caps(caps), scripts=scripts, task=task, max_actions=max_actions)
        return RunOutcome(executed_hashes=tuple(r["executed_hashes"]),
                          authorized_hashes=frozenset(r["authorized_hashes"]),
                          executed_count=r["executed_count"], provenance_records=r["provenance_records"])

    def derive_child(self, requested, parent, policy) -> CapabilitySet:
        return _dec_caps(self._call("derive_child", requested=_enc_caps(requested),
                                    parent=_enc_caps(parent), policy=_enc_caps(policy)))

    def skill_grant(self, approved, requested, manifest_digest, pinned_digest) -> CapabilitySet:
        return _dec_caps(self._call("skill_grant", approved=_enc_caps(approved),
                                    requested=_enc_caps(requested), manifest_digest=manifest_digest,
                                    pinned_digest=pinned_digest))

    def _desc(self, action):
        return {"actor": action.actor, "namespace": action.namespace, "action": action.action,
                "resource": action.resource, "parameters": action.parameters,
                "tenant": action.tenant, "tool_digest": action.tool_digest}

    def approve(self, action):
        return self._call("approve", action=self._desc(action))["grant_id"]

    def validate(self, action, grant) -> bool:
        return self._call("validate", action=self._desc(action), grant_id=grant)

    def compile_context(self, purpose, observations, secrets=()) -> CompiledView:
        r = self._call("compile_context", purpose=purpose, observations=list(observations),
                       secrets=list(secrets))
        return CompiledView(has_untrusted_instruction=r["has_untrusted_instruction"], text_blob=r["text_blob"])

    def authorize(self, caps, namespace, action, resource, revoked=frozenset()) -> AdapterDecision:
        r = self._call("authorize", caps=_enc_caps(caps), namespace=namespace, action=action,
                       resource=resource, revoked=[list(x) for x in revoked])
        return AdapterDecision(allow=r["allow"], invariant=r["invariant"])

    def authorize_attribution(self, principal_user, root_principal, chain, actor_agent) -> AdapterDecision:
        r = self._call("authorize_attribution", principal_user=principal_user,
                       root_principal=root_principal, chain=list(chain), actor_agent=actor_agent)
        return AdapterDecision(allow=r["allow"], invariant=r["invariant"])

    def recall_memory(self, tenant) -> tuple[MemoryItem, ...]:
        return tuple(MemoryItem(tenant=i["tenant"], source=i["source"], is_instruction=i["is_instruction"])
                     for i in self._call("recall_memory", tenant=tenant))

    def budget_used_racing(self, limit, concurrent) -> int:
        return self._call("budget_used_racing", limit=limit, concurrent=concurrent)

    def external_tool_trust(self, declared_trust) -> str:
        return self._call("external_tool_trust", declared_trust=declared_trust)


def _main(argv: list[str]) -> None:
    use_solution = "--solution" in argv
    positional = [a for a in argv if not a.startswith("--")]
    AdapterServer(positional[0], use_solution=use_solution).serve()


if __name__ == "__main__":
    _main(sys.argv[1:])
