You are assessing a product idea for completeness before a PRD is drafted.

Compare the idea against these six required inputs. For each one that the idea does NOT already cover, produce exactly one clarifying question.

Required inputs: problem, persona, metric, dependencies, scope, release.

Output ONLY a single fenced ```json block, no prose before or after:

```json
{"questions": [
  {"id": "q1", "checklist_item": "metric", "text": "..."}
]}
```

`checklist_item` must be one of the six ids. Ask at most one question per id. If the idea already covers an input, omit it. If it covers all six, return `{"questions": []}`.
