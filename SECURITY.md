# Security Policy 🫠

Yes. We know. It's called **Damn Vulnerable** Agent Harness. Reporting that DVAH is
vulnerable is like reporting that the ocean is wet, or that the "Do Not Push" button is,
in fact, extremely pushable.

So before you type "🚨 CRITICAL RCE 🚨", let's sort the *intentional* chaos from the
*actual* problems.

## 🟢 Please do NOT report these (they're the product)

Everything under `challenges/*/vulnerable/` is broken **on purpose**. It is a lovingly
curated museum of bad decisions:

- "I can make the agent delete a repo it was never authorized to touch." — Yes. That's
  DVAH-008. Gold star. ⭐
- "The subagent is more privileged than its parent!" — Correct. That's the lab. Please
  patch it, don't email it.
- "Untrusted data became an instruction!" — Chef's kiss. Now go fix the compiler.

If you exploit a lab, the right move is to **patch the harness and prove the invariant
holds** — not to file a CVE against a training exercise. 🏆

## 🔴 Please DO report these (they can actually hurt someone)

Bugs in the **harness, runtime, `webapi`, CLI, or web app itself** — the machinery
*around* the labs — that could harm a person running DVAH beyond the intended exercise:

- The sandbox runner lets lab code escape and read your real files / env / keys.
- A path-traversal, secret leak, or "the tutor spent my rent money" cost bug.
- Something that turns "I opened localhost" into "my laptop is now a crypto miner."

If in doubt: *"could this bite someone who just wanted to learn?"* → report it. *"Is this
just the lab doing its job?"* → screenshot it and feel smug instead.

## 🏠 A gentle, loud reminder

DVAH is a **local, single-user** tool that **runs untrusted code by design**. Treat it
like a chemistry set, not a public API.

- The default runner confines code to your local process/container. On macOS it's
  timeout-only (no hard resource limits). It is **not** a hardened multi-tenant sandbox.
- Two grader modes (`DVAH_GRADER`): **`inprocess`** (default, self-study) copies the
  whole challenge — including `tests/` and `solution/` — into your session for fast
  iteration; the solution is only hidden from the file API, so it's on disk and **not**
  isolation. **`isolated`** (assessment/CTF) keeps the learner session to `vulnerable/`
  only and grades out of band in a throwaway workspace where the reference solution never
  coexists with learner-controlled code — use it for anything competitive/graded, ideally
  with a private challenge source (the public repo ships the solutions).
- There is **no auth and no rate limiting** — it expects `localhost` and only `localhost`.
- Exposing this to the internet or untrusted users is the one exploit we can't patch for
  you. Don't. 🙅 (If you must host it: `DVAH_RUNNER=docker`, add authn/z + rate limits +
  per-user isolation first — see the roadmap.)

## 🔑 About secrets

API keys entered in the UI live in server **memory only** — never written to disk, never
handed back in plaintext (you get a masked `…1234` hint and nothing more). For anything
past local tinkering, use environment variables or a real secrets manager.

## 📮 How to report (the real ones)

Open a private [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories),
or reach the maintainer at **[avishay.co.il](https://avishay.co.il)**. Include repro steps
and impact. We'll acknowledge within a few days — faster if it's genuinely spicy. 🌶️

Thanks for keeping the *harness* safe so everyone else can keep breaking the *labs*. 🛡️
