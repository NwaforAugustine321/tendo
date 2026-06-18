## Available Tools

### Business Profiles
- **create_business_profile**: Create a new business profile
  - Params: user_id (required), name (required), category?, description?, phone?, location?, logo_url?
- **get_business_profile**: Get a business profile by ID
  - Params: business_id (required)
- **update_business_profile**: Update a business profile
  - Params: business_id (required), name?, category?, description?, phone?, location?, logo_url?
- **upload_business_logo**: Upload a logo image to storage and save URL to profile
  - Params: business_id (required), logo_data_url (required, base64 data URL)

### Products
- **search_products**: Search products by name
  - Params: business_id (required), query?
- **create_product**: Create a new product
  - Params: business_id (required), name (required), unit_price?, unit?, category?
- **update_product**: Update a product
  - Params: business_id (required), product_id (required), name?, unit_price?, unit?, category?
- **delete_product**: Delete a product
  - Params: business_id (required), product_id (required)

### Services
- **search_services**: Search services by name
  - Params: business_id (required), query?
- **create_service**: Create a new service
  - Params: business_id (required), name (required), price?, category?
- **update_service**: Update a service
  - Params: business_id (required), service_id (required), name?, price?, category?
- **delete_service**: Delete a service
  - Params: business_id (required), service_id (required)

### Customers
- **search_customers**: Search customers by name, phone, or email
  - Params: business_id (required), query?
- **create_customer**: Create a new customer
  - Params: business_id (required), name (required), phone?, email?, customer_type?
- **get_customer**: Get a customer by ID
  - Params: business_id (required), customer_id (required)
- **update_customer**: Update a customer
  - Params: business_id (required), customer_id (required), name?, phone?, email?

### Inventory
- **get_inventory**: Get inventory items
  - Params: business_id (required), product_id?
- **update_inventory**: Update inventory quantity directly
  - Params: business_id (required), inventory_id (required), quantity (required)
- **add_inventory**: Add a new inventory entry for a product
  - Params: business_id (required), product_id (required), quantity?, reorder_level?
- **record_inventory_movement**: Record stock in/out/adjustment
  - Params: business_id (required), inventory_id (required), movement_type (in/out/adjustment), quantity (required), reference?

### Sales & Transactions
- **record_sale**: Record a sale transaction
  - Params: business_id (required), total (required), customer_id?, payment_type? (cash/transfer/card), items?
- **get_sales**: Get recent sales
  - Params: business_id (required), limit?, status?
- **get_sales_summary**: Get sales summary (total revenue, count)
  - Params: business_id (required)

### Payments
- **record_payment**: Record a payment received
  - Params: business_id (required), amount (required), customer_id?, invoice_id?, payment_method? (cash/transfer/card), reference?
- **get_payments**: Get recent payments
  - Params: business_id (required), customer_id?, limit?

### Invoices
- **create_invoice**: Create an invoice
  - Params: business_id (required), customer_id (required), total (required), due_date?, items? (array of {description, quantity, unit_price})
- **get_invoices**: Get invoices
  - Params: business_id (required), status? (pending/paid/overdue/cancelled), customer_id?, limit?
- **update_invoice_status**: Update invoice status
  - Params: business_id (required), invoice_id (required), status (required: pending/paid/overdue/cancelled)
