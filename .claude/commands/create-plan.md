---
description: Convert a feature discussion into a structured implementation plan
argument-hint: [feature-description or leave blank if discussed in chat]
---

# Create Implementation Plan

## Feature

$ARGUMENTS

---

## Your Role

You are a senior engineer turning a feature discussion into a structured plan document.

**You have already been primed** — you have a high-level understanding of the codebase structure.
**The feature has already been discussed** — you know what we are building.

Your job is to **read the specific files that will be touched**, fill any gaps in your understanding, then crystallize everything into a plan file that a fresh AI agent with no memory of this conversation can execute end-to-end without making assumptions.

---

## Step 1 — Derive the Plan Name

From the feature description or conversation, create a concise kebab-case name.

**Plan will be saved to:** `plans/[feature-name].md`

---

## Step 2 — Read the Files That Will Be Modified

From the feature discussion, identify every file that will need a change or that a changed file directly depends on. **Read all of them now**, before writing a single task.

For each file, note:
- Exact function/class/component signatures
- Field names, prop names, type definitions
- Import structure and existing patterns to follow
- Current behavior that must be preserved

Do not author any task that references code you have not read.

---

## Step 3 — Write the Plan

Save as `plans/[feature-name].md`:

---

```markdown
# Plan: [Feature Name]

## Goal
[What exists today. What will exist after. Why it matters.]

## Success Criteria
- [ ] [Specific, observable outcome]
- [ ] [Fallback behavior if applicable]
- [ ] [Zero type/lint errors]

## Files to Read Before Implementing

| File | Why |
|---|---|
| `exact/path/to/file.tsx` | [what the executor needs from this file] |

## Known Gotchas
- [Non-obvious fact that will cause a mistake if unknown]
- [Another codebase quirk — e.g. "location.state is undefined on direct navigation"]

## Tasks

```yaml
- task: 1
  action: CREATE        # CREATE | MODIFY
  file: 'exact/path/to/file.ts'
  description: 'One-line summary'
  instructions:
    - 'Specific instruction referencing actual code found during Step 2'
    - 'Mirror the pattern from [exact file/function you read]'
    - 'Preserve all existing [fields/props] — do not remove anything'

- task: 2
  action: MODIFY
  file: 'exact/path/to/other.tsx'
  description: 'One-line summary'
  instructions:
    - 'Find the pattern: "[exact existing code string to locate]"'
    - 'Change [specific thing] to [specific other thing]'
    - 'No other changes to this file'
```

## Validation

### Syntax & Style
```bash
[exact lint command for this project]
```

### Type Safety
```bash
[exact typecheck command for this project]
```
```

---

## Step 4 — Self-Check Before Saving

Apply the **No Prior Knowledge test**: if an AI agent received only this plan and access to the codebase, could it implement the feature without asking a single question?

- [ ] Every file path exists — confirmed by reading it in Step 2
- [ ] Every function, field, and constant name is real — taken from the actual files
- [ ] Tasks are in dependency order — no task depends on work from a later task
- [ ] Instructions reference specific patterns found in the code, not generic guidance
- [ ] Validation commands are exact and runnable, not placeholders

If any box fails, fix the plan before saving.

---

**Next step:** Open a fresh context and run `/execute-plan plans/[feature-name].md`
