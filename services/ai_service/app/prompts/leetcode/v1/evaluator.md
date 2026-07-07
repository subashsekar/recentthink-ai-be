# LeetCode Evaluator Module

The Evaluator module formats complexity analysis and interview feedback. It **never** calls OpenRouter.

## Responsibilities

- Format time and space complexity
- Surface optimizations, mistakes, and edge cases
- Extract interview follow-up questions
- Persist evaluation messages and analytics metadata

## Expected JSON Fields

- `time_complexity`, `space_complexity`
- `optimizations`, `mistakes`, `edge_cases`
- `follow_up_questions`, `interview_questions`, `feedback`, `analytics`
