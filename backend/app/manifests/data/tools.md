# Tool Manifest

## fetch_business_profile
- **Capability**: Fetch the current business profile information
- **Domain**: onboarding, transactions, inventory

## get_business_profile
- **Capability**: Fetch the profile information about the business
- **Domain**: knowledge, transactions, inventory, record

## update_profile
- **Capability**: Update the business profile with provided fields (name, category, description, phone, location, logo)
- **Domain**: onboarding

## fetch_transactions
- **Capability**: Fetch recent transactions for a business, filter by type or status
- **Domain**: transactions

## fetch_transactions_summary
- **Capability**: Get a summary of transactions (total revenue, count, completed)
- **Domain**: transactions

## fetch_customers
- **Capability**: Search customers by name, phone, or email
- **Domain**: transactions

## fetch_products
- **Capability**: Search products by name or category
- **Domain**: transactions, inventory

## fetch_inventory
- **Capability**: Fetch inventory items, optionally filtered by product
- **Domain**: inventory

## add_inventory_item
- **Capability**: Add a new inventory entry for a product
- **Domain**: inventory

## record_movement
- **Capability**: Record an inventory movement (in/out/adjustment)
- **Domain**: inventory

## create_product
- **Capability**: Create a new product with name, price, unit, and category
- **Domain**: inventory

## search_knowledge
- **Capability**: Search knowledge for context and understanding
- **Domain**: knowledge, onboarding, transactions, inventory, record

## save_knowledge
- **Capability**: Store important facts, decisions, observations, or lessons in memory
- **Domain**: knowledge, onboarding, record

## count_knowledge
- **Capability**: Get the total count of knowledge entries
- **Domain**: knowledge, record

## fetch_knowledge
- **Capability**: Fetch multiple pages of knowledge entries
- **Domain**: knowledge, record
