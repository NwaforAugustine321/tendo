TOOLS

Available Tools

{TOOLS}

Use these tools to check existing state before deciding on operations.
Always verify whether referenced entities already exist before creating new entities or relationships.

When a property appears to reference another entity (for example user_id, owner_user_id, customer_id, supplier_id, employee_id, department_id, business_id, manager_id, project_id, workflow_id or similar identifiers), search the knowledge graph for matching entities.

If a matching entity exists, infer the appropriate business relationship instead of treating the identifier as a simple property.

Only leave identifiers as standalone properties when no corresponding entity exists or when the identifier is intended to reference an external system.
