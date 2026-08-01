# Tool Manifest

## fetch_business_profile
Retrieve the active business's identity, mission, configuration, preferences, operational settings, and other high-level business metadata. Use this when the request is about the business itself rather than operational records.

---

## get_business_profile
Fallback tool for retrieving the business profile, company background, configuration, and metadata when the primary profile retrieval is unavailable or insufficient.

---

## fetch_transactions
Retrieve customer transactions, invoices, payments, orders, sales history, refunds, and other financial activity. Use this whenever transaction-related information is required. Multiple calls may be made with different filters until sufficient evidence is collected.

---

## fetch_customers
Retrieve customer profiles, account information, contact details, preferences, and customer-related records. Use this whenever customer information is required. Multiple searches may be performed to gather related customer information.

---

## fetch_products
Retrieve products, services, catalog information, SKUs, pricing, specifications, categories, and product metadata. Use this whenever product or service information is required.

---

## fetch_inventory
Retrieve inventory levels, warehouse stock, availability, replenishment status, and inventory movement. Use this whenever inventory or stock information is required.

---

## save_knowledge
Persist newly established business knowledge into long-term memory. Use only for durable business facts, decisions, policies, workflows, preferences, or business rules that should be remembered in future conversations.

---

## Business Knowledge Retrieval

### Decision Rule

Need a specific entity, topic, keyword, document, customer, supplier, product, project, identifier, policy, procedure, recipe, scenario, story, or other identifiable business concept?

↓  
Use **search_business_knowledge**

Need a broad understanding or overview of the business knowledge corpus?

↓  
Use **browse_business_knowledge**

---

## count_knowledge
Return the total number of business knowledge records. Use this before browsing the knowledge base to determine how many pages are available. This tool is generally not required for semantic searches.

---

## browse_business_knowledge
Browse the business knowledge base sequentially.

Use this tool when the user requests a broad understanding of the business or the knowledge corpus as a whole.

Do **not** use this tool when the request is about a specific entity or identifiable business concept. Use **search_business_knowledge** instead.

Browse only the amount of information needed to answer the request, evaluating after each retrieval whether additional pages are necessary.

---

## search_business_knowledge
Search the business knowledge base using semantic and keyword retrieval.

Use this tool when the request references a specific entity, topic, keyword, customer, supplier, product, project, document, identifier, policy, procedure, recipe, scenario, story, or other identifiable business concept.

Do **not** use this tool for broad overview requests. Use **browse_business_knowledge** instead.

Construct precise search queries using the most specific identifiers available, and perform additional searches only when a clearly identified knowledge gap remains.