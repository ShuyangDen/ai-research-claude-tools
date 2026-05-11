# Development Workflow

> This file extends [common/git-workflow.md](./git-workflow.md) with the full feature development process that happens before git operations.

## Feature Implementation Workflow

1. **Plan First**
   - Use **planner** agent for complex analysis pipelines or multi-file scripts
   - Identify dependencies and data flow before coding
   - Break down into phases

2. **TDD Approach**
   - Write tests first (RED)
   - Implement to pass tests (GREEN)
   - Refactor (IMPROVE)

3. **Code Review**
   - Use **code-reviewer** or **python-reviewer** agent immediately after writing code
   - Address CRITICAL and HIGH issues before committing

4. **Commit & Push**
   - Detailed commit messages
   - Follow conventional commits format
   - See [git-workflow.md](./git-workflow.md) for commit message format and PR process
