# Agent Orchestration

## Available Agents

Located in `~/.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex analysis pipelines, refactoring |
| code-reviewer | Code review | After writing or modifying code |
| python-reviewer | Python-specific review | Python scripts (PEP8, type hints, pandas) |
| build-error-resolver | Fix runtime/import errors | When script fails to run |

## Immediate Agent Usage

No user prompt needed:
1. Complex analysis pipeline or script — Use **planner** agent
2. Code just written/modified — Use **code-reviewer** agent
3. Python file changed — Use **python-reviewer** agent
4. Script crashes or import fails — Use **build-error-resolver** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch agents in parallel:
1. Agent 1: Review data cleaning script
2. Agent 2: Review regression analysis script

# BAD: Sequential when unnecessary
First agent 1, then agent 2
```
