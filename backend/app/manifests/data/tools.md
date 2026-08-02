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
Return the total number of records available in the master repository. 

Use this function before executing sequential or paginated browse actions 
---

## browse_information_in_pages
Browse the master information repository sequentially in pages when targeted semantic search is insufficient.

Use this function when the request requires a broad sweep, overview, sequential audit, or complete contextual understanding of the available information corpus.

---

## search_information_with_semantic_search
Search the master information repository for any entity, topic, data point, keyword, or asset.

Use this function whenever the request references a specific concept, item, category, procedure, scenario, query, or any identifiable information point.

CRITICAL: All records, items, domain details, and contextual data are structurally stored inside this master repository. You MUST execute this search to see if data exists. Do not assume or guess content availability.