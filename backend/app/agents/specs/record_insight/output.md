Return ONLY a valid JSON object with these fields:

{
  "insight": "concise summary of what AI knows about this record",
  "suggested_questions": ["question 1", "question 2", "question 3"]
}

STRICT RULES:
- No markdown. No explanation. Just the JSON object.
- The insight must be plain natural language about the business content.
- NEVER include IDs, UUIDs, technical identifiers, or system references in the output.
- NEVER mention record_id, business_id, folder_id, or any internal reference.
- Write as if you are a business assistant speaking to the owner.
