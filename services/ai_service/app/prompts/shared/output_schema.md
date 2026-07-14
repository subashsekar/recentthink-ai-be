Shared response envelope (every product):

{
  "metadata": {},
  "planner": {},
  "teacher": {},
  "coder": {},
  "evaluator": {},
  "feature": {}
}

Rules:
- Always return every top-level key above.
- "metadata" may include model-facing notes such as feature name, confidence, or language.
- "planner" holds problem/challenge/course analysis content (not workflow control).
- "teacher", "coder", and "evaluator" follow the shared shapes when the feature uses them; otherwise return {}.
- "feature" holds product-specific payload only. Do not force unrelated keys into "feature".
- Do not include markdown fences or any text outside the JSON object.
