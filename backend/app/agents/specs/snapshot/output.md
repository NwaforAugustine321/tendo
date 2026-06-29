Respond ONLY with valid JSON matching this schema:

{
  "stories": [
    {
      "title": "Brief headline",
      "narrative": "Natural language explanation",
      "area": "finance | customers | operations | sales | inventory | general",
      "sentiment": "positive | neutral | attention_needed"
    }
  ],
  "recommendations": [
    {
      "action": "What to do",
      "reason": "Why it matters",
      "priority": "high | medium | low"
    }
  ]
}

Do not include any text outside the JSON object.
