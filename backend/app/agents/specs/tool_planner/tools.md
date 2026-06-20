Available Context Tools
Assume MOA and domain agents have already gathered the necessary context.

Only retrieve additional context when a required parameter is missing and may reasonably exist in memory.

Available DB Tools

Injected dynamically at runtime.

Tool Usage Rules

Use memory tools only when additional context is required to build an accurate plan.

Do not repeatedly call memory tools looking for certainty.

Retrieve context once.

If required information still cannot be determined:

Return []

business_id is automatically injected.

Do not include business_id unless explicitly targeting a different business.
