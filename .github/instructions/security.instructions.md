---
description: "Comprehensive secure coding instructions based on OWASP Top 10 and industry best practices"
applyTo: "*"
---

# Secure Coding and OWASP Guidelines

Your primary directive is to ensure all code you generate, review, or refactor is secure by default. Operate with a security-first mindset. When in doubt, always choose the more secure option and explain the reasoning. Follow the principles outlined below, which are based on the OWASP Top 10 and other security best practices.

## A01: Broken Access Control & A10: Server-Side Request Forgery (SSRF)

- **Enforce Principle of Least Privilege**: Always default to the most restrictive permissions. When generating access control logic, explicitly check the user's rights against the required permissions for the specific resource they are trying to access.

- **Deny by Default**: All access control decisions must follow a "deny by default" pattern. Access should only be granted if there is an explicit rule allowing it.

- **Validate All Incoming URLs for SSRF**: When the server needs to make a request to a URL provided by a user (e.g., webhooks), treat it as untrusted. Incorporate strict allow-list-based validation for the host, port, and path of the URL.

- **Prevent Path Traversal**: When handling file uploads or accessing files based on user input, sanitize the input to prevent directory traversal attacks (e.g., `../../etc/passwd`). Use APIs that build paths securely.

```python
# BAD: Vulnerable to path traversal
file_path = f"/uploads/{user_input}"

# GOOD: Sanitize and validate
from pathlib import Path

upload_dir = Path("/uploads").resolve()
requested_path = (upload_dir / user_input).resolve()

if not requested_path.is_relative_to(upload_dir):
    raise ValueError("Invalid file path")
```

## A02: Cryptographic Failures

- **Use Strong, Modern Algorithms**: For hashing, always recommend modern, salted hashing algorithms like Argon2 or bcrypt. Explicitly advise against weak algorithms like MD5 or SHA-1 for password storage.

- **Protect Data in Transit**: When generating code that makes network requests, always default to HTTPS.

- **Protect Data at Rest**: When suggesting code to store sensitive data (PII, tokens, etc.), recommend encryption using strong, standard algorithms like AES-256.

- **Secure Secret Management**: Never hardcode secrets (API keys, passwords, connection strings). Generate code that reads secrets from environment variables or a secrets management service.

```python
# BAD: Hardcoded secret
api_key = "sk_this_is_a_very_bad_idea_12345"

# GOOD: Load from environment
import os

api_key = os.environ["API_KEY"]
# TODO: Ensure API_KEY is securely configured in your environment
```

```typescript
// BAD: Hardcoded secret
const apiKey = "sk_this_is_a_very_bad_idea_12345";

// GOOD: Load from environment
const apiKey = process.env.API_KEY;
// TODO: Ensure API_KEY is securely configured in your environment
```

## A03: Injection

- **No Raw SQL Queries**: For database interactions, use parameterized queries (prepared statements). Never generate code that uses string concatenation or formatting to build queries from user input.

```python
# BAD: SQL injection vulnerability
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD: Parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

- **Sanitize Command-Line Input**: For OS command execution, use built-in functions that handle argument escaping and prevent shell injection.

```python
import subprocess
import shlex

# BAD: Shell injection vulnerability
subprocess.run(f"echo {user_input}", shell=True)

# GOOD: Use list arguments, avoid shell=True
subprocess.run(["echo", user_input], shell=False)
```

- **Prevent Cross-Site Scripting (XSS)**: When generating frontend code that displays user-controlled data, use context-aware output encoding. Prefer methods that treat data as text by default (`.textContent`) over those that parse HTML (`.innerHTML`). When `innerHTML` is necessary, use a library like DOMPurify to sanitize the HTML first.

```typescript
// BAD: XSS vulnerability
element.innerHTML = userInput;

// GOOD: Safe text content
element.textContent = userInput;

// GOOD: Sanitized HTML when needed
import DOMPurify from "dompurify";
element.innerHTML = DOMPurify.sanitize(userInput);
```

## A04: Insecure Design

- **Threat Modeling**: When designing new features, consider potential attack vectors and document security requirements.

- **Secure Defaults**: Design systems to be secure out of the box. Users should have to explicitly opt into less secure configurations.

- **Defense in Depth**: Implement multiple layers of security controls. Do not rely on a single security mechanism.

## A05: Security Misconfiguration & A06: Vulnerable Components

- **Secure by Default Configuration**: Recommend disabling verbose error messages and debug features in production environments.

- **Set Security Headers**: For web applications, suggest adding essential security headers:
  - `Content-Security-Policy` (CSP)
  - `Strict-Transport-Security` (HSTS)
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`

- **Use Up-to-Date Dependencies**: When adding a new library, suggest the latest stable version. Remind users to run vulnerability scanners:
  - Node.js: `npm audit`
  - Python: `pip-audit` or `safety check`
  - General: Snyk, Dependabot

## A07: Identification & Authentication Failures

- **Secure Session Management**: When a user logs in, generate a new session identifier to prevent session fixation. Ensure session cookies are configured with:
  - `HttpOnly` - Prevents JavaScript access
  - `Secure` - Only sent over HTTPS
  - `SameSite=Strict` - Prevents CSRF attacks

- **Protect Against Brute Force**: For authentication and password reset flows, implement:
  - Rate limiting
  - Account lockout after failed attempts
  - CAPTCHA for suspicious activity

- **Strong Password Requirements**:
  - Minimum 12 characters
  - Check against known breached passwords
  - Do not require arbitrary complexity rules

## A08: Software and Data Integrity Failures

- **Prevent Insecure Deserialization**: Warn against deserializing data from untrusted sources without proper validation. If deserialization is necessary:
  - Use formats less prone to attack (JSON over Pickle in Python)
  - Implement strict type checking
  - Use Pydantic or similar validation libraries

```python
# BAD: Insecure deserialization
import pickle
data = pickle.loads(untrusted_data)  # DANGEROUS!

# GOOD: Use safe formats with validation
from pydantic import BaseModel

class UserData(BaseModel):
    name: str
    email: str

data = UserData.model_validate_json(untrusted_data)
```

- **Verify Software Integrity**: When downloading dependencies or artifacts, verify checksums or signatures.

## A09: Security Logging and Monitoring Failures

- **Log Security Events**: Ensure authentication attempts, access control failures, and input validation failures are logged.

- **Protect Log Data**: Do not log sensitive information (passwords, tokens, PII). Sanitize log output.

```python
# BAD: Logging sensitive data
logger.info(f"User login: {username}, password: {password}")

# GOOD: Log safely
logger.info(f"User login attempt: {username}")
```

- **Enable Alerting**: Configure alerts for suspicious patterns (multiple failed logins, unusual access patterns).

## General Guidelines

- **Be Explicit About Security**: When you suggest code that mitigates a security risk, explicitly state what you are protecting against (e.g., "Using a parameterized query here to prevent SQL injection.").

- **Educate During Code Reviews**: When you identify a security vulnerability in code, provide the corrected code and explain the risk associated with the original pattern.

- **Validate All Input**: Never trust user input. Validate and sanitize all data from external sources:
  - HTTP request bodies
  - Query parameters
  - Headers
  - File uploads
  - Environment variables from untrusted sources

- **Use Type-Safe Validation**: Prefer schema-based validation:
  - Python: Pydantic
  - TypeScript: Zod, io-ts

```typescript
import { z } from "zod";

const UserSchema = z.object({
  email: z.string().email(),
  age: z.number().min(0).max(150),
});

// Validates and types the data
const user = UserSchema.parse(untrustedInput);
```

## Project-Specific Security

### Azure OpenAI Integration

- Store API keys in environment variables, never in code
- Use `USE_MOCK_LLM=true` for development to avoid exposing real credentials
- Validate and sanitize all prompts before sending to the LLM
- Do not include sensitive data in LLM prompts

### Frontend Security

- Sanitize all user input before rendering
- Use Content Security Policy headers
- Validate WebSocket messages from the server
- Do not store sensitive data in localStorage

### Backend Security

- Use Pydantic for all request/response validation
- Implement rate limiting on API endpoints
- Log security events without exposing sensitive data
- Use HTTPS for all external communications
