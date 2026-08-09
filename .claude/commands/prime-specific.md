---
description: Context-efficient priming - parse reference file and spawn parallel sub-agents to study content across any defined sections
argument-hint: [reference-file.md]
allowed-tools: Read Task Glob
---

# Prime Specific Context (Sub-Agent Coordination)

**Reference File:** @$ARGUMENTS

## Mission: Focused Context Loading Without Bloat

This command delivers fast, focused understanding by:
1. ✅ Parsing the reference file to extract all `## [X] Files` sections
2. ✅ Spawning **parallel sub-agents** (each reads only its assigned files)
3. ✅ Collecting concise, structured summaries from each section
4. ✅ Synthesizing into clear understanding without noise

**Key Benefit**: Sub-agents read files independently, report back summaries only — zero context pollution from unrelated parts of the codebase.

---

## Prerequisites: Reference File Format

Your reference file MUST have this structure:

```markdown
# [Feature/Topic Name] - File Reference

## Summary
[One sentence description]

## [Section Name] Files
- path/to/file1.md
- path/to/file2.ts

## [Another Section] Files
- path/to/file3.py
```

Section headers MUST end in `Files` (e.g. `## Context Files`, `## Agent Files`, `## Backend Files`). Any section name works.

**If your reference file doesn't follow this format**, stop and ask the user to provide it.

---

## Process

### Step 1: VALIDATE Reference File

Read `@$ARGUMENTS` and verify:
- ✅ File exists and is readable
- ✅ Has at least one `## [X] Files` section (any name ending in `Files`)
- ✅ Files listed are specific paths (not generic descriptions)
- ℹ️ `## Summary` section is optional — use it as the overview if present, skip if absent

If validation fails, stop with a clear error message.

### Step 2: Extract Metadata

From the reference file, extract:
- **Topic Name** (from the top-level heading)
- **Topic Summary** (from `## Summary` section if present, otherwise use the topic name alone)
- **All sections** that match the `## [X] Files` pattern, each with its complete file list including any `###` subsection groupings

### Step 3: Spawn Parallel Sub-Agents (One Per Section)

For EACH `## [X] Files` section discovered, spawn one sub-agent using this prompt template (fill in brackets with actual values):

---

```
You are a specialist analyst studying [TOPIC_NAME] — specifically the [SECTION_NAME] layer.

**Files to read (strict scope — only these):**
[LIST OF FILES FROM THIS SECTION, preserving any ### subsection groupings as labels]

**Your task:**
1. Read ONLY the files listed above. Do not explore related files.
2. Use the `###` subsection names (e.g. Core Components, Hooks, Services) as organizational labels — they tell you what role each file plays.
3. Understand what these files contain and how they relate to [TOPIC_NAME].
4. Report concisely (2-3 paragraphs max):
   - What each file does and what it defines
   - Key patterns, rules, or structures present
   - How these files relate to each other
   - Any critical gotchas or constraints

**Format your response as:**
## [SECTION_NAME] Analysis: [TOPIC_NAME]

[Your 2-3 paragraph analysis]

**Key Files**: [comma-separated list]
**Key Concepts**: [comma-separated list]
**Critical Gotchas**: [bullet points or "None"]

If you cannot understand something without files outside this list, note it:
"⚠️ Needs [filename] to understand [aspect]"
```

---

### Step 4: Collect and Synthesize Reports

After all sub-agents complete, compile their reports into:

```markdown
# Context Understanding: [TOPIC_NAME]

## Overview
[Summary from reference file]

## [Section 1 Name]
[Sub-agent report]

## [Section 2 Name]
[Sub-agent report]

## [Section N Name]
[Sub-agent report]

## How It All Connects
[Describe relationships between sections: what depends on what, how the pieces fit together]

## Critical Gotchas (Consolidated)
[Unique gotchas from all sub-agents, deduplicated]

## Information Gaps
[Any "⚠️ Needs [file]" items from sub-agents]

---

## Confirmation
Context is loaded. If anything above looks wrong or incomplete, correct it now — otherwise we are ready to proceed.
```

---

## Rules

### ✅ DO:
- Accept any `## [X] Files` section name — not just frontend/backend/database
- Dynamically discover sections from the reference file at runtime
- Stop and ask if reference file format is wrong
- Use the exact file lists from the reference (no assumptions, no extras)
- Keep sub-agent reports short (2-3 paragraphs max)
- Ask for confirmation before proceeding

### ❌ DON'T:
- Hard-code assumptions about which sections should exist
- Explore files not listed in the reference
- Make assumptions about missing sections
- Over-explain or pad the analysis
- Proceed without user confirmation

---

## Success Criteria

- ✅ Reference file validated
- ✅ One sub-agent spawned per section, all completed
- ✅ Reports synthesized into a clear, connected picture
- ✅ User confirms understanding is accurate
- ✅ Total context used is minimal (efficient)
