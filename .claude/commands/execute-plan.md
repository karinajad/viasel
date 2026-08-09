---
description: Execute an implementation plan task by task
argument-hint: [path/to/plan.md]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(npm:*), Bash(npx:*), Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), TodoWrite
---

# Execute Plan

## Plan: $ARGUMENTS

---

## Step 1 — Read the Plan

Read the entire plan file. Understand every task, what files are touched, and what the success criteria are before writing a single line of code.

---

## Step 2 — Read the Files Listed in "Files to Read Before Implementing"

Open every file in that table. Know the current structure, signatures, and patterns before you touch anything.

---

## Step 3 — Load Tasks into Todo

Create a todo item for every task in the plan's task list. You will check each one off as it is completed.

---

## Step 4 — Execute Tasks in Order

Work through the tasks **sequentially**. For each task:

1. Identify the file and action (`CREATE` or `MODIFY`)
2. Follow the instructions exactly — reference the actual code you read in Step 2
3. Stay consistent with the existing patterns in that file
4. Mark the task complete in your todo list before moving to the next

Do not skip tasks. Do not reorder tasks. If a task is blocked, stop and surface the issue — do not work around it silently.

**Do not stop until every task in the plan is complete and all validation passes.** Partial implementation is not done.

---

## Step 5 — Run Validation

Run every command in the plan's **Validation** section in order.

**If a command fails:**
- Read the error
- Fix the issue in the relevant file
- Re-run the command
- Do not proceed until it passes

Both validation levels must pass before the work is considered done.

---

## Step 6 — Done

Confirm:
- [ ] Every task from the plan is complete
- [ ] All validation commands pass with zero errors
- [ ] No files were modified outside the plan's scope
