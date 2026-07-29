# Tool Manifest

## fetch_business_profile
- **Capability**: Fetch business identity and configuration data for context
- **Domain**: knowledge, transactions, inventory

## get_business_profile
- **Capability**: Fetch business identity and configuration data for context
- **Domain**: knowledge, transactions, inventory

## fetch_transactions
- **Capability**: Fetch any customer entries from database
- **Domain**: knowledge, transactions, inventory

## fetch_customers
- **Capability**: Fetch any customer entries from database
- **Domain**: knowledge, transactions, inventory

## fetch_products
- **Capability**: Fetch any product entries from database
- **Domain**: knowledge, transactions, inventory

## fetch_inventory
- **Capability**: Fetch any inventory entries from database
- **Domain**: knowledge, transactions, inventory

## save_knowledge
- **Capability**: Persist information and data to short term memory
- **Domain**: transactions, inventory

## count_knowledge
- **Capability**: Get the total number of information entries to plan retrieval before calling fetch_knowledge to calculate page offsets.
- **Domain**: knowledge, transactions, inventory

## fetch_knowledge
- **Capability**: Retrieve all any type of information entries in batches using limit/offset pagination to answer any quesitons.
- **Domain**: knowledge, transactions, inventory
