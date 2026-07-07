# LeetCode Deterministic Planner

The planner module does **not** invoke OpenRouter. It classifies problems and prepares execution metadata from fetched problem context.

## Responsibilities

- Problem classification from title, description, and topics
- Difficulty normalization from LeetCode metadata
- Pattern detection (Array, Hash Map, DP, Graph, etc.)
- Learning objectives generation
- Module selection (Teacher, Coder, Evaluator)
- Execution plan for the single-LLM workflow

## Input

Problem context JSON from `LeetCodeProblemFetcher`:

- `title`, `slug`, `url`, `description`
- `difficulty`, `topics`, `examples`, `constraints`

## Output

Planner metadata stored in session and passed to the OpenRouter user prompt.
