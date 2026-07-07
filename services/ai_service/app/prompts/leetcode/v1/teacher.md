# LeetCode Teacher Module

The Teacher module formats structured JSON from the single OpenRouter response. It **never** calls OpenRouter.

## Responsibilities

- Format mentor-style explanations as markdown
- Generate frontend cards for concepts, hints, and next steps
- Persist assistant messages to `ai_messages`
- Support follow-up context via Conversation Memory

## Expected JSON Fields

- `problem_summary`, `thinking_process`, `concepts`
- `learning_objectives`, `approach`, `common_mistakes`
- `analogy`, `next_step`, `hints`
