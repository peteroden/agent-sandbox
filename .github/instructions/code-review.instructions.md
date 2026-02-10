---
description: "Mandatory code review guidelines for all code changes"
applyTo: "**"
---

# Code Review Instructions

All code changes require a code review before work is considered complete. This applies to both human-written and AI-generated code.

## Mandatory Workflow

**No coding work is finished until:**

1. Code review has been conducted
2. All 🔴 CRITICAL issues are resolved
3. All 🟡 IMPORTANT issues are resolved or explicitly deferred by the user
4. 🟢 SUGGESTION items are applied or acknowledged

When working on any task:

1. Complete the implementation
2. Run unit tests to verify functionality
3. Run E2E tests to verify no regressions (`cd e2e && pnpm test`)
4. **Perform self-review using this checklist**
5. Address all findings
6. Only then mark work as complete

## Review Priorities

### 🔴 CRITICAL (Must fix before completion)

- **Security**: Vulnerabilities, exposed secrets, authentication/authorization issues
- **Correctness**: Logic errors, data corruption risks, race conditions
- **Breaking Changes**: API contract changes without versioning
- **Data Loss**: Risk of data loss or corruption

### 🟡 IMPORTANT (Requires resolution or explicit deferral)

- **Code Quality**: Violations of SOLID principles, excessive duplication
- **Test Coverage**: Missing tests for critical paths or new functionality
- **Performance**: Obvious performance bottlenecks (N+1 queries, memory leaks)
- **Architecture**: Deviations from established patterns

### 🟢 SUGGESTION (Non-blocking improvements)

- **Readability**: Naming improvements, logic simplification
- **Optimization**: Performance improvements without functional impact
- **Best Practices**: Minor deviations from conventions
- **Documentation**: Missing or incomplete comments/documentation

## Review Checklist

### Code Quality

- [ ] Code follows consistent style and conventions
- [ ] Names are descriptive and follow naming conventions
- [ ] Functions/methods are small and focused (< 20-30 lines preferred)
- [ ] No code duplication (DRY principle)
- [ ] Complex logic is broken into simpler parts
- [ ] Error handling is appropriate
- [ ] No magic strings or numbers (use constants)
- [ ] No commented-out code or TODO without tickets

### Security

See [security.instructions.md](security.instructions.md) for comprehensive OWASP guidelines.

- [ ] No sensitive data in code or logs
- [ ] Input validation on all user inputs
- [ ] No SQL/command injection vulnerabilities
- [ ] Authentication and authorization properly implemented
- [ ] Dependencies are up-to-date and secure

### Testing

- [ ] New code has appropriate test coverage
- [ ] Tests focus on our code, not third-party libraries
- [ ] Tests use constants, not magic strings
- [ ] Parameterized tests used where applicable
- [ ] Tests cover edge cases and error scenarios
- [ ] Tests are independent and deterministic
- [ ] E2E tests pass (`cd e2e && pnpm test`)

### Performance

- [ ] No obvious performance issues (N+1, memory leaks)
- [ ] Appropriate use of caching
- [ ] Efficient algorithms and data structures
- [ ] Proper resource cleanup

### Architecture

- [ ] Follows established patterns and conventions
- [ ] Proper separation of concerns
- [ ] Dependencies flow in correct direction
- [ ] SOLID principles applied

### Documentation

- [ ] Public APIs are documented
- [ ] Complex logic has explanatory comments
- [ ] README is updated if needed
- [ ] Breaking changes are documented

## Comment Format

When reporting review findings, use this format:

```markdown
**[🔴/🟡/🟢] Category: Brief title**

Description of the issue.

**Why this matters:**
Impact explanation.

**Suggested fix:**
[code example if applicable]
```

### Example

````markdown
**🔴 Security: Hardcoded API key**

The API key is hardcoded on line 15 of `config.ts`.

**Why this matters:**
Exposed secrets can be extracted from source control history,
leading to unauthorized access.

**Suggested fix:**

```typescript
// Instead of:
const API_KEY = "sk_live_abc123";

// Use environment variable:
const API_KEY = process.env.API_KEY;
```
````

```

## Project-Specific Standards

### Python (Backend)

- Type hints on all function signatures
- Pydantic models for data validation
- pytest fixtures for test dependencies
- `@pytest.mark.parametrize` for multiple test cases

### TypeScript (Frontend)

- Strict TypeScript (no `any`)
- Preact functional components with typed props
- Vitest with `it.each` for parameterized tests
- Tailwind utility classes (extract when repeated 3+ times)

## Review Principles

1. **Be specific**: Reference exact lines and files
2. **Provide context**: Explain WHY something is an issue
3. **Suggest solutions**: Show corrected code, not just problems
4. **Be constructive**: Focus on improving code, not criticizing
5. **Recognize good practices**: Acknowledge well-written code
6. **Be pragmatic**: Not every suggestion needs immediate implementation
```
