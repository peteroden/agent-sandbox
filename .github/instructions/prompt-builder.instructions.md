---
description: "Authoring standards for prompt engineering artifacts including file types, protocol patterns, writing style, and quality criteria"
applyTo: "**/*.prompt.md, **/*.agent.md, **/*.instructions.md"
---

# Prompt Builder Instructions

These instructions define authoring standards for prompt engineering artifacts. Apply these standards when creating or modifying prompt, agent, instructions, or skill files.

## File Types

This section defines file type selection criteria, authoring patterns, and validation checks.

### Prompt Files

_Extension_: `.prompt.md`

Purpose: Single-session workflows where users invoke a prompt and Copilot executes to completion.

Characteristics:

- Single invocation completes the workflow.
- Frontmatter includes `agent: 'agent-name'` to delegate to an agent.
- Content ends with `---` followed by an activation instruction.
- Use `#file:` only when the prompt must pull in the full contents of another file.
- Input variables use `${input:variableName}` or `${input:variableName:defaultValue}` syntax.

### Agent Files

_Extension_: `.agent.md`

Purpose: Agent files support both conversational workflows (multi-turn interactions with a specialized assistant) and autonomous workflows (task execution with minimal user interaction).

#### Conversational Agents

Conversational agents guide users through multi-turn interactions:

- Users guide the conversation through different activities or stages.
- State persists across conversation turns via planning files when needed.
- Frontmatter defines available `tools` and optional `handoffs` to other agents.
- Typically represents a domain expert or specialized assistant role.

#### Autonomous Agents

Autonomous agents execute tasks with minimal user interaction:

- Executes autonomously after receiving initial instructions.
- Frontmatter defines available `tools` and optional `handoffs` to other agents.
- Typically completes a bounded task and reports results.
- May dispatch subagents for parallelizable work.

### Instructions Files

_Extension_: `.instructions.md`

Purpose: Auto-applied guidance based on file patterns. Instructions define conventions, standards, and patterns that Copilot follows when working with matching files.

Characteristics:

- Frontmatter includes `applyTo` with glob patterns (for example, `**/*.py`).
- Applied automatically when editing files matching the pattern.
- Define coding standards, naming conventions, and best practices.

Validation guidelines:

- Include `applyTo` frontmatter with valid glob patterns.
- Content defines standards and conventions.
- Wrap examples in fenced code blocks.

## Frontmatter Requirements

This section defines frontmatter field requirements for prompt engineering artifacts.

### Required Fields

All prompt engineering artifacts include these frontmatter fields:

- `description:` - Brief description of the artifact's purpose.

### Optional Fields

Optional fields vary by file type:

- `name:` - Identifier for agents and skills.
- `applyTo:` - Glob patterns (required for instructions files only).
- `tools:` - Tool restrictions for agents. When omitted, all tools are accessible.
- `handoffs:` - Agent handoff declarations for agents.
- `agent:` - Agent delegation for prompt files.
- `argument-hint:` - Hint text for prompt picker display.
- `model:` - Model specification.

## Protocol Patterns

Protocol patterns apply to prompt and agent files.

### Step-Based Protocols

Step-based protocols define groupings of sequential prompt instructions that execute in order.

Structure guidelines:

- A `## Required Steps` section contains all steps and provides an overview of how the protocol flows.
- Protocol steps contain groupings of prompt instructions that execute as a whole group, in order.

Step conventions:

- Format steps as `### Step N: Short Summary` within the Required Steps section.
- Give each step an accurate short summary that indicates the grouping of prompt instructions.
- Include prompt instructions to follow while implementing the step.
- Steps can repeat or move to a previous step based on instructions.

### Phase-Based Protocols

Phase-based protocols define groups of instructions for iterating on user requests through conversation.

Structure guidelines:

- A `## Required Phases` section contains all phases and provides an overview of how the protocol flows.
- Protocol phases contain groupings of prompt instructions that execute as a whole group.
- Conversation guidelines include instructions on interacting with the user through each of the phases.

Phase conventions:

- Format phases as `### Phase N: Short Summary` within the Required Phases section.
- Give each phase an accurate short summary that indicates the grouping of prompt instructions.
- Announce phase transitions and summarize outcomes when completing phases.

## Prompt Writing Style

Prompt instructions have the following characteristics:

- Guide the model on what to do, rather than command it.
- Written with proper grammar and formatting.

Additional characteristics:

- Use protocol-based structure with descriptive language when phases or ordered steps are needed.
- Use `*` bulleted lists for groupings and `1.` ordered lists for sequential instruction steps.
- Use **bold** only for human readability when drawing attention to a key concept.
- Use _italics_ only for human readability when introducing new concepts, file names, or technical terms.
- Follow standard markdown conventions and instructions for the codebase.

### User-Facing Responses

When instructions describe how to respond to users in conversation:

- Format file references as markdown links: `[filename](path/to/file)`.
- Format URLs as markdown links: `[display text](https://example.com)`.
- Use workspace-relative paths for file links.
- Do not wrap file paths or links in backticks.

Prefer guidance style over command style:

```markdown
<!-- Avoid command style -->

You must search the folder and you will collect all conventions.

<!-- Use guidance style -->

Search the folder and collect conventions into the research document.
```

### Patterns to Avoid

The following patterns provide limited value as prompt instructions:

- ALL CAPS directives and emphasis markers.
- Second-person commands with modal verbs (will, must, shall).
- Condition-heavy and overly branching instructions.
- List items where each item has a bolded title line.
- XML-style groupings of prompt instructions. Use markdown sections instead.

## Prompt Key Criteria

Successful prompts demonstrate these qualities:

- Clarity: Each prompt instruction can be followed without guessing intent.
- Consistency: Prompt instructions produce similar results with similar inputs.
- Alignment: Prompt instructions match the conventions or standards provided by the user.
- Coherence: Prompt instructions avoid conflicting with other prompt instructions in the same or related prompt files.
- Calibration: Prompts provide just enough instruction to complete the user requests, avoiding overt specificity without being too vague.
- Correctness: Prompts provide instruction on asking the user whenever unclear about progression, avoiding guessing.

## Prompt Quality Criteria

Every item applies to the entire file. Validation fails if any item is not satisfied.

- [ ] File structure follows the File Types guidelines for the artifact type.
- [ ] Frontmatter includes required fields and follows Frontmatter Requirements.
- [ ] Protocols follow Protocol Patterns when step-based or phase-based structure is used.
- [ ] Instructions match the Prompt Writing Style.
- [ ] Instructions follow all Prompt Key Criteria.
- [ ] Few-shot examples are in correctly fenced code blocks and match the instructions exactly.
- [ ] The user's request and requirements are implemented completely.
