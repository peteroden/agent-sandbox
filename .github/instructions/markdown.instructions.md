---
description: "Required instructions for creating or editing any Markdown (.md) files"
applyTo: "**/*.md"
---

# Markdown Instructions

These instructions define the Markdown style guide enforced in this codebase. Follow them when creating or updating any `.md` file.

## Scope

- Applies to all Markdown files in this codebase excluding files with `<!-- markdownlint-disable-file -->`.
- When in doubt, prefer clarity and consistency. Automated fixes are acceptable if they preserve intent.

## General conventions

- Use UTF-8 and plain ASCII punctuation unless content requires otherwise.
- Prefer descriptive headings and concise paragraphs; avoid trailing or leading extra spaces.
- Keep lines reasonably short for readability; wrap where sensible without breaking URLs or code.

## Headings

- Start documents with a single level-1 heading that acts as the title when appropriate.
- Increase heading levels by one at a time; do not skip levels.
- Use a consistent heading style per file. Prefer ATX style (`#`, `##`, `###`, ...) for new content.
- Do not indent headings; they must start at column 1.
- Surround each heading with a blank line above and below (except at file start/end).
- Do not end headings with punctuation such as `. , ; : !` or their full-width variants.
- Avoid duplicate headings under the same parent section; make them unique.
- Do NOT use an H1 heading when YAML frontmatter contains a `title:` field.
- Use exactly one space after the `#` characters in headings.
- Use only one top-level heading per document; subsequent sections must use lower levels.

```markdown
# Title

## Section

### Subsection
```

## YAML Frontmatter

- All markdown files SHOULD include YAML frontmatter at the beginning of the file for instructions, agents, and prompts.
- Frontmatter MUST be the first content in the file (before H1 heading).
- Use triple-dash delimiters (---) on separate lines to wrap frontmatter YAML.
- Do NOT use an H1 heading when frontmatter includes a `title:` field.
- Start document content with H2 or below when frontmatter contains a `title:` field.

### Required Fields by File Type

| File Type                               | Required Fields          |
| --------------------------------------- | ------------------------ |
| Instruction files (`*.instructions.md`) | `description`, `applyTo` |
| Agent files (`*.agent.md`)              | `description`            |
| Prompt files (`*.prompt.md`)            | `description`            |

### Recommended Fields

- `maturity`: Lifecycle stage: `experimental`, `preview`, `stable`, or `deprecated`

## Lists

- Use unordered list markers consistently across a file; for the same level, do not mix `*`, `+`, `-`.
  - Try to always use `*` for unordered lists.
- Indent unordered sublist content by 2 spaces per level.
- Keep indentation consistent for items at the same nesting level.
- Use one space between any list marker and the list text for both ordered and unordered lists.
- Surround lists with a blank line before and after (unless at file start/end).
- For ordered lists, either use `1.` for all items or increment numerically; do not mix styles within a list.

```markdown
- Item 1
- Item 2
  - Nested item

1. Step
2. Step
3. Step
```

### Bullet point punctuation

Follow professional editorial standards for bullet point punctuation consistency:

- **Fragment bullet points** (short phrases, technical terms, simple commands): Do NOT end with periods.
- **Complete sentence bullet points** (subject + verb constructions): End with periods.

```markdown
- Configuration file
- API endpoint
- User authentication

- This function validates the input parameters.
- The system processes requests asynchronously.
```

## Code blocks and code spans

- Use fenced code blocks consistently (prefer triple backticks) and surround them with a blank line before and after.
- Always specify a language for fenced code blocks; use `text` if no highlighting is desired.
- Avoid tabs; use spaces everywhere.
- Do not add spaces just inside backticks of code spans; write `` `code` `` not `` ` code ` ``.
- For shell examples, do not prefix commands with `$` unless you also show the command output.
- Use backticks for code fences consistently; do not use tildes.

````markdown
```bash
echo "Hello"
```

Some inline `code` here.
````

## Links and images

- Do not reverse link syntax; write `[text](url)`.
- Do not use empty links like `[]()` or `(#)`; always provide a valid destination.
- Avoid bare URLs; wrap them in angle brackets like `<https://example.com>` or make them proper links with text.
- Ensure link fragments match generated heading IDs (kebab-case, lower-case).
- Provide alternate text for all images.
- Keep spaces out of link text brackets: `[text]`, not `[ text ]`.

```markdown
See <https://example.com> and [Docs](https://example.com/docs).

![Diagram](./diagram.png)
```

## Spacing and blank lines

- Limit paragraph and prose lines to approximately 500 characters; keep headings under 80 characters.
- Do not add trailing spaces at the end of lines except when intentionally forcing a hard line break.
- Do not use multiple consecutive blank lines; keep at most one in a row.
- Surround fenced code blocks, headings, lists, and tables with a blank line before and after.
- Files must end with a single newline; no extra blank lines at EOF.

## Blockquotes

- Use a single space after the `>` marker; avoid multiple spaces.
- Inside blockquotes, apply the same list and code rules.

```markdown
> Quoted text continues
>
> Same quote after a blank line.
```

## Horizontal rules

- Use one horizontal rule style consistently within a document. Prefer `---`.

## Emphasis

- Use a consistent style for emphasis and strong emphasis throughout a document. Prefer `*italic*` and `**bold**` for new content.
- Do not put spaces inside emphasis markers: `**bold**`, not `** bold **`.
- Do not use emphasis-only lines as section separators; use proper headings instead.

## Tables

- Surround tables with a blank line before and after.
- Use a consistent pipe style; prefer leading and trailing pipes on all rows.
- Ensure every row has the same number of cells as the header.
- Keep header and delimiter rows aligned in column count.

```markdown
| Column A | Column B | Column C |
| -------- | -------- | -------- |
| Short    | Medium   | Longer   |
| A        | BB       | CCC      |
```

## Callouts and Alerts

Use GitHub-flavored markdown alerts for important callouts:

| Alert Type   | Purpose                                                     |
| ------------ | ----------------------------------------------------------- |
| [!NOTE]      | Useful information users should know when skimming          |
| [!TIP]       | Helpful advice for doing things better or more easily       |
| [!IMPORTANT] | Key information users need to achieve their goal            |
| [!WARNING]   | Urgent info needing immediate attention to avoid problems   |
| [!CAUTION]   | Advises about risks or negative outcomes of certain actions |

```markdown
> [!NOTE]
> Useful information that users should know, even when skimming content.

> [!TIP]
> Helpful advice for doing things better or more easily.
```

## Miscellaneous

- Do not include inline HTML unless necessary; if used, limit to explicitly allowed elements like `<details>` and `<summary>`.
- Follow proper capitalization for product and technology names (e.g., "GitHub", "JavaScript", "TypeScript").
- Ensure files end with exactly one trailing newline character.
