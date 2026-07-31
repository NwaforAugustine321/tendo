# Tool Manifest

## fetch_business_profile
Primary tool to retrieve the active business's core identity, mission statement, configuration parameters, and company settings.

## get_business_profile
Secondary fallback tool to read active company background profiles, operational settings, and metadata configurations.

## fetch_transactions
Look up and retrieve customer transaction histories, sales records, invoices, orders, and payment database logs. You can execute this tool multiple times with different parameters or date ranges to compile a complete history.

## fetch_customers
Look up and retrieve customer profiles, account details, contact records, and registration histories from the database. You may invoke this repeatedly with varied search queries to pinpoint specific or related user records.

## fetch_products
Look up and retrieve specific product information, catalog details, names, SKU configurations, and product menu records. Call this multiple times using alternative keywords or categories to explore different matching products.

## fetch_inventory
Look up and check real-time stock levels, warehouse inventory details, availability counts, and supply metrics. If needed, make repeated calls across different SKUs or warehouses to cross-reference total stock.

## save_knowledge
Persist and store newly established business facts, customer preferences, case studies, updates, and rules into long-term memory for future retrieval.

## count_knowledge
Mandatory prerequisite lookup tool. Execute this first whenever you need to fetch information entries to retrieve the total row count. You must use this result to determine how many pages exist and plan your batch retrieval before calling fetch_knowledge.

## fetch_knowledge
Your primary all-purpose search tool to look up factual business information, answers, documents, procedures, recipes, scenarios, or stories. Pass your calculated page offsets and limits here in batches based on the results from count_knowledge to extract the actual database rows. You can call this tool multiple times with different limit, offset, questions or search phrasings to gather deeper information or explore alternative retrieval paths.
