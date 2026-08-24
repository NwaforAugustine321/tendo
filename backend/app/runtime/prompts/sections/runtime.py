from __future__ import annotations

from app.runtime.agents.run_context import (
    RunContext,
)

runtime_reasoning_instructions = """
<runtime_reasoning>

For EVERY user turn, complete the reasoning cycle before producing a
user-facing response.

<response_contract>

Return exactly ONE <reasoning_state> block:

<reasoning_state>
{
  "phase": "reasoning|action|verification|final",
  "action": "none|tool|answer|retry",
  "ready": true|false,
  "response": null
}
</reasoning_state>

Rules:

- reasoning = determine what is required.
- action = a tool/action is required; the runtime handles execution.
- verification = evaluate the latest result.
- final = the user-facing answer is ready.
- response = complete user-facing answer only when action="answer".
- ready=false = NEVER finalize.
- ready=true = finalize ONLY when:
  phase="final", action="answer", and response is non-empty.

The reasoning_state is runtime control data.
NEVER show it to the user.
NEVER put private reasoning inside it.
Do not omit, duplicate, or modify its fields.
Do not return malformed JSON.

</response_contract>


<reasoning_cycle>

1. UNDERSTAND
Identify the user's actual objective.

2. SEPARATE
Distinguish the current request from system instructions, conversation
history, assistant history, memory, knowledge, and tool results.

3. REASON
Determine what information, tool, or action is required.

4. ACT
If a tool/action is required, return:

phase="action"
action="tool"
ready=false
response=null

The runtime handles the tool execution.

5. OBSERVE
After the runtime provides the result, evaluate it.

6. VERIFY
Determine whether the result is sufficient and whether another action
or reasoning cycle is required.

7. FINALIZE
When the task is resolved, place the complete user-facing answer in
"response" and return:

phase="final"
action="answer"
ready=true

Never expose private reasoning.

</reasoning_cycle>


<self_consistency>

Before finalization, independently check:

1. Did I understand the current request correctly?
2. Did I use the correct available information and source?
3. Is the proposed response sufficient and appropriate?

If any check fails or the decisions disagree, do NOT finalize.

Return:

{
  "phase": "reasoning",
  "action": "retry",
  "ready": false,
  "response": null
}

Only finalize when the checks are consistent.

</self_consistency>


<react>

For tasks requiring tools, follow:

THINK → ACTION → OBSERVE → VERIFY.

When a tool is required:

{
  "phase": "action",
  "action": "tool",
  "ready": false,
  "response": null
}

The runtime detects this state and executes the appropriate tool.

After the tool result:

- If another action is required, return action="tool".
- If the result needs further reasoning, return action="retry".
- If the result is sufficient, perform verification and finalize.

Never treat tool discovery/search as the final answer when the actual
task requires executing the discovered tool.

Never skip verification after a tool result.

</react>


<finalization>

The ONLY state that permits the runtime to return content to the user is:

<reasoning_state>
{
  "phase": "final",
  "action": "answer",
  "ready": true,
  "response": "COMPLETE USER-FACING ANSWER"
}
</reasoning_state>

The runtime MUST return ONLY the value of "response" to the user.

The runtime MUST NEVER expose:

- reasoning_state
- phase
- action
- ready
- runtime control data
- tool execution state

Any final state with an empty or missing response is INVALID and must
continue the reasoning loop.

Any non-final state MUST continue the runtime loop.

Apply this process independently on EVERY user turn.

</finalization>


<parse_failure>

If reasoning_state is missing, duplicated, malformed, or cannot be parsed,
the response is NOT final.

The runtime provides:

"Invalid reasoning state. Return exactly one valid <reasoning_state>
block using the required JSON schema."

Then perform the reasoning cycle again.

Never expose the parse error or runtime control state to the user.

</parse_failure>

</runtime_reasoning>
"""


class RuntimePromptBuilder:
    """
    Builds the prompt section describing the runtime 
    environment for the agent.
    """

    HEADER = (
        "\n[runtime_configurations]\n"
        "This is the runtime configuration throughout the task.\n"
        "Max Interaction Steps: {{max_iterations}}\n"
        "Do not exceed the maximum steps. If the task is incomplete when the limit is reached, "
        "provide the best final response and exit.\n"
        "[runtime_configurations]\n\n"
        # f"{runtime_reasoning_instructions}"


    )

    def build(
        self,
        runtime_inject_payload: list[dict[str, str]],
    ) -> str:

        prompt = self.HEADER

        for item in runtime_inject_payload:
            placeholder = f"{{{{{item['key']}}}}}"
            prompt = prompt.replace(
                placeholder,
                str(item["value"]),
            )

        return prompt
