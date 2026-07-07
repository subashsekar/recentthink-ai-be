# LeetCode Coder Module

The Coder module formats solution code from structured JSON. It **never** calls OpenRouter.

## Responsibilities

- Format brute-force, better, and optimal solutions
- Normalize supported languages (python, java, cpp, javascript, go, rust)
- Persist code blocks to `ai_messages`
- Expose structured solutions for API responses

## Expected JSON Fields

- `brute_force`, `better_solution`, `optimal_solution`
- Each solution: `language`, `code`, `explanation`, `complexity`
