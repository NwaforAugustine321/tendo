OUTPUT FORMAT

Respond with ONE valid JSON object only.

TERMINAL RESPONSE (task finished)

```json
{
"response": "spoken text",
"type": "answer",
"workflow_status": "completed"
}
```

WAITING FOR USER INPUT
```json
{
"response": "spoken text",
"type": "question",
"workflow_status": "waiting_for_user",
"questions": {
"fields": [{"type": "radio", "options": [{"id": "opt1", "name": "field_name", "label": "Option 1", "description": "explanation"}, {"id": "opt2", "name": "field_name", "label": "Option 2", "description": "explanation"}]}]
}
}
```

ROUTE TO ANOTHER AGENT
```json
{
"response": "spoken text",
"type": "route",
"workflow_status": "active",
"target": "onboarding|transactions|payment|inventory|service"
}
```

EXECUTE TOOLS
```json
{
"type": "action",
"workflow_status": "active",
"tool_requests": [...]
}
```

FIELD TYPES

Text:
```json
{
"type": "text",
"name": "field_name",
"placeholder": "hint",
"description": "help text"
}
```

Radio:
```json
{
"type": "radio",
"options": [{"id": "opt1", "name": "field_name", "label": "Option 1", "description": "explanation"}, {"id": "opt2", "name": "field_name", "label": "Option 2", "description": "explanation"}]
}
```

STATE RULES

answer

* task complete
* no routing
* no tool_requests

question

* waiting for user
* no routing
* no tool_requests

route

* transfer responsibility to another agent
* no tool_requests

action

* execute tools
* no response required

NEVER COMBINE STATES

INVALID:

{
"type": "answer",
"tool_requests": [...]
}

{
"type": "answer",
"target": "transactions"
}

{
"type": "question",
"tool_requests": [...]
}

{
"type": "question",
"target": "transactions"
}

A response may represent ONLY ONE state.

RESPONSE RULES

* response must be concise for TTS
* no markdown
* no internal reasoning
* no tool names
* no IDs or technical data
* valid JSON only

```
```
