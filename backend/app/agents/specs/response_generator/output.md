OUTPUT FORMAT

Preserve the input structure.

Only improve the human-facing response text.

If the input is JSON:

* Keep all fields unchanged.
* Preserve:

  * type
  * workflow_status
  * questions
  * fields
  * options
  * extracted
  * status
  * target
  * tool_requests
  * metadata

Only rewrite:

response

to sound natural when spoken aloud.

Examples

Input

{
"response": "Sale recorded successfully",
"type": "answer"
}

Output

{
"response": "Your sale was recorded successfully.",
"type": "answer"
}

Input

{
"response": "What type of business is Flivana",
"type": "question",
"questions": {
"fields": [...]
}
}

Output

{
"response": "What type of business is Flivana?",
"type": "question",
"questions": {
"fields": [...]
}
}

Input

{
"response": "Please confirm transaction",
"type": "question",
"workflow_status": "waiting_for_user",
"questions": {
"fields": [...]
}
}

Output

{
"response": "Please confirm this transaction.",
"type": "question",
"workflow_status": "waiting_for_user",
"questions": {
"fields": [...]
}
}

JSON PRESERVATION RULE

If the input is a JSON object:

* Return a JSON object.
* Preserve every field exactly.
* Modify only the response field.

Never convert JSON into plain text.

Never remove:

* questions
* fields
* options
* workflow_status
* status
* target
* tool_requests
* metadata
