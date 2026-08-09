---
description: Generate a feature reference file by researching the codebase
argument-hint: [feature-name]
allowed-tools: Read Write Glob Grep
---

# Create Feature Reference File

**Feature:** $ARGUMENTS

## Mission

Research the codebase and create a clean, scannable reference file listing all files related to the specified feature. The reference file will be used with `/prime-specific` for deep feature study.

**CRITICAL**: Follow the 80/20 principle - keep it simple, concise, and scannable. NO over-engineering.

## Scope Detection

Before researching, determine which layers this feature touches:

- **Frontend only** → output `## Frontend Files` section only
- **Backend only** → output `## Backend Files` section only
- **Frontend + Backend** → output `## Frontend Files` and `## Backend Files` sections
- **Full-stack** → output all three: `## Frontend Files`, `## Backend Files`, `## Database Files`

If the argument makes the scope obvious, infer it. If ambiguous, ask:
> "Is this frontend-only, backend-only, frontend + backend, or full-stack (includes database)?"

Only generate sections for the detected scope. Skip all others entirely.

---

## Research Process

1. **Search the codebase** for all files related to: `$ARGUMENTS`
   - Use `Glob`, `Grep`, and `Read` in parallel
   - Focus on: frontend/, backend/, and database-related files

2. **Organize findings** into categories:
   - **Frontend**: Components, Hooks, State Management, API Client, Types, Providers
   - **Backend**: Routers, Services, Schemas, AI Agents, Database operations
   - **Database**: Migrations, Tables with key features

3. **Keep only core files** - Remove duplicates, skip trivial files

## Output Format

Create file: `references/[feature_name]_reference.md` with this EXACT structure:

**CRITICAL**: All file paths in markdown links must use `../` prefix since reference files are stored in the `references/` folder. This ensures clickable links resolve correctly from the reference file location to the project root.

```markdown
# [Feature Name] - File Reference

## Frontend Files

### Core Components
- [frontend/src/path/to/component.tsx](../frontend/src/path/to/component.tsx) - Brief description (one line)

### Hooks
- [frontend/src/path/to/hook.ts](../frontend/src/path/to/hook.ts) - Brief description

### State Management
- [frontend/src/path/to/store.ts](../frontend/src/path/to/store.ts) - Brief description

### API Client
- [frontend/src/services/api.ts](../frontend/src/services/api.ts) - Brief description

### Types
- [frontend/src/path/to/types.ts](../frontend/src/path/to/types.ts) - Brief description

### Providers
- [frontend/src/path/to/provider.tsx](../frontend/src/path/to/provider.tsx) - Brief description

---

## Backend Files

### API Routers
- [backend/api/routers/path/to/router.py](../backend/api/routers/path/to/router.py) - Brief description

### Services
- [backend/services/path/to/service.py](../backend/services/path/to/service.py) - Brief description

### Schemas
- [backend/path/to/schemas.py](../backend/path/to/schemas.py) - Brief description

### AI Agent
- [backend/path/to/agent.py](../backend/path/to/agent.py) - Brief description

---

## Database Files

### Migrations
- [backend/database/path/to/migration.sql](../backend/database/path/to/migration.sql) - Brief description

### Tables
- `table_name` - Description (columns: id, key_field, **important_field**)

### Key Features
- ✅ **Feature 1**: Brief description
- ✅ **Feature 2**: Brief description
```

## Rules

1. **Keep descriptions to ONE LINE** per file
2. **NO code examples** or detailed explanations
3. **NO architecture deep-dives** or flowcharts
4. **Use markdown links with `../` prefix**: `[path/to/file](../path/to/file)` - this is required for links to work from the `references/` folder
5. **Bold important fields** in table descriptions using `**field_name**`
6. **Aim for 50-100 lines total** (not 300+)
7. **Skip sections** that don't apply (e.g., no Providers = skip that section)
8. **Always save to `references/` folder** - reference files must be in this directory

## Final Report

After creating the file, report:
```
✅ Reference file created: `[filename]`
📁 Frontend files: [count]
📁 Backend files: [count]
📁 Database files: [count]
🎯 Ready to use with: `/prime-specific [filename]`
```

**Remember**: Simple, scannable, essential files only. 80/20 rule!
