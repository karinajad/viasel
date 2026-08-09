---
description: Brownfield primer — understand any existing codebase before touching it. Maps structure with Glob, spawns one sub-agent per layer in parallel, synthesizes a clear compressed understanding into the main context.
allowed-tools: Glob, Read, Task
---

## Process

### Step 1 — Map the Structure

Run Glob on the working directory. Ignore: `node_modules`, `.git`, `__pycache__`, `dist`, `build`, `venv`, `.venv`, `.next`, `coverage`, `*.lock`.

From the paths alone, identify the project type and each layer with its root path.

| Project Type | What the paths show |
|---|---|
| **Script** | Single entry file, flat structure, no layer separation |
| **Backend-only** | Server-side files (`*.py`, `*.go`, `*.rs`, `*.java`, `*.rb`) — no frontend assets |
| **Frontend-only** | `*.tsx`, `*.jsx`, `*.vue`, `*.svelte` — no server-side layer |
| **Full-stack** | Both a frontend layer and a backend layer present |

If the project type cannot be determined from paths alone, read **one root-level config file only** (`package.json`, `pyproject.toml`, `go.mod`, or `Cargo.toml`) to resolve it. One file. No source code files.

If no meaningful code exists anywhere: stop. Tell the user — "This looks empty or skeleton-only. `/primer` works on existing codebases."

---

### Step 2 — Spawn Layer Sub-Agents

Call all Task invocations in a **single response**. All sub-agents run in parallel. Do not wait for one before spawning the next.

Spawn one sub-agent per layer:

| Project Type | Sub-Agents to Spawn |
|---|---|
| Script | 1 — the whole project |
| Backend-only | 1 — backend layer |
| Frontend-only | 1 — frontend layer |
| Full-stack | 2 or 3 — frontend + backend + database (only if a dedicated migrations or schema folder exists) |

Use this prompt for every sub-agent. Fill in the bracketed values with the actual layer name and path from Step 1.

---

**SUB-AGENT PROMPT**

You are a [LAYER NAME] analyst. Your job is to deeply understand the [LAYER NAME] layer of this project at `[LAYER PATH]`.

Use the `Glob` and `Read` tools only. Use Glob to find the most important files in this directory, then Read the ones that reveal what this layer does, how it is organized internally, and how it connects to the rest of the system. Do not use any other tools.

Return exactly this — no other text, no preamble, no explanation of what you are doing:

**What This Layer Does**
2–3 sentences. What is the purpose of this layer? What does it own and handle?

**Key Files**
The 6–8 most important files. One line each: `path` — what this file does.

**How It Connects**
How this layer communicates with other layers or the outside world. Name the actual mechanisms you found: specific route paths, the database client or ORM used, the HTTP client library, shared type imports, external service SDKs. 4–6 bullets. Specific — no generalities like "it calls the API."

Your entire response must be under 400 tokens. If you are over, cut the lowest-signal items first.

---

### Step 3 — Synthesize

Once all sub-agent reports are returned, produce the output below. Use only what the sub-agents reported and the Glob path map from Step 1. Do not read any additional files.

---

## Output

```
# Project Understanding

## What This Is
3–4 sentences. What does this project do? What problem does it solve?
Plain English — no jargon, no buzzwords.

## Stack
One line per layer: Layer name — language, framework, key libraries.

## Structure
The real folder layout with a one-line explanation per meaningful folder.
Mirror the actual paths from Glob. Skip generated folders (node_modules, dist, .venv, etc.).

## Key Files
The 10 most important files across the entire project.
`path` — what it does. One line each.

## How It Connects
How the layers communicate with each other and the outside world.
Name the actual mechanisms found: specific API routes, database driver,
HTTP client, shared type files, auth layer, external SDKs.
4–6 bullets. Specific — no generalities.
```