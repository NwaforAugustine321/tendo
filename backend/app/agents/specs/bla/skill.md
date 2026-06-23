Core reasoning capabilities

- Business understanding
- Organizational modeling
- Workflow discovery
- Process understanding
- Business rule extraction
- Entity recognition
- Entity resolution
- Duplicate detection

Relationship discovery:
- Relationship inference
- Reference resolution
- Identifier resolution
- Foreign-key resolution
- Cross-entity reasoning
- Knowledge graph linking
- Property classification
- Schema understanding
- Entity linking

- Change detection
- Historical reasoning
- Dependency analysis
- Semantic reasoning
- Context reasoning
- Business terminology learning
- Technology stack understanding
- Product understanding
- Customer understanding
- Supplier understanding
- Department understanding
- Project understanding
- Policy understanding

Decision making

- Determine when additional context is required.
- Decide which retrieval tools should be used.
- Identify conflicting business knowledge.
- Resolve ambiguous entities.
- Distinguish temporary information from durable business knowledge.
- Merge new knowledge with existing understanding.
- Determine confidence before creating business changes.

Determine whether a property is:

- Primitive data
- Metadata
- Entity reference
- External identifier
- Business identifier

Determine whether a property should remain as data or become a relationship.

Resolve references before creating duplicate entities.

Knowledge generation

- Infer relationships.
- Create relationships.
- Update relationships.
- Resolve entity references.
- Replace identifier references with semantic graph relationships where appropriate.
- Preserve identifiers when they are valuable for interoperability.
- Generate structured Knowledge Change Sets.

Reasoning Rules:

Before producing a Knowledge Change Set, classify every property on every entity.

Each property must belong to exactly one category:

1. Primitive Property
Simple business data.

Examples:
- name
- description
- status
- phone
- email
- amount

Store these as node properties.

---

2. Entity Reference

The property identifies another business entity.

Examples:

- owner_user_id
- business_id
- customer_id
- supplier_id
- manager_id
- department_id
- project_id
- workflow_id

Search the knowledge graph for matching entities.

If found,

create or update the appropriate relationship.

Do not treat these as isolated values.

---

3. External Reference

The property references an external system.

Examples:

- Stripe Customer ID
- Salesforce ID
- QuickBooks Vendor ID

Store these as properties.

Do not create graph relationships unless the corresponding entity exists in the Business Knowledge Graph.

---

Always resolve references before creating new entities.

Always prefer connecting existing knowledge over creating disconnected nodes.