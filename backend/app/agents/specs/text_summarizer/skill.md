Summarization Strategy

For every piece of text content:

1. Identify the content type:
   - Business note
   - Meeting note
   - Personal observation
   - Transaction description
   - Customer interaction
   - Task or reminder
   - General text

2. Extract key information:
   - Who is involved (names, roles, customers)
   - What happened or was described
   - When (dates, times, periods)
   - Where (locations, channels)
   - How much (amounts, quantities, prices)
   - Why it matters (decisions, outcomes, next steps)

3. Produce a summary that:
   - Reads as a single coherent paragraph or two
   - Captures all business-relevant facts
   - Omits filler words, greetings, and formatting artifacts
   - Preserves specific numbers, names, and dates exactly
   - Is useful without the original text

4. Handle edge cases:
   - Very short text (< 100 chars): return as-is
   - Empty or whitespace-only: return "Empty note with no content."
   - Garbled or meaningless: return "Content could not be meaningfully summarized."
