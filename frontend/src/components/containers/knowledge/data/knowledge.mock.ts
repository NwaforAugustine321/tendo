import type { KnowledgeRecord } from "../knowledge.types";

export const INITIAL_RECORDS: KnowledgeRecord[] = [
  // ---------------------------------------------------------------------------
  // Customers
  // ---------------------------------------------------------------------------
  {
    id: "customer-musa-ibrahim",
    definitionId: "customers",
    values: {
      "customer-name": "Musa Ibrahim",
      "customer-description": "Regular wholesale buyer",
    },
    understanding: [
      "Frequently buys rice",
      "Usually orders in bulk",
      "Last purchase was 5 bags",
      "Preferred payment method is transfer",
    ],
    activity: [
      {
        id: "musa-activity-1",
        label: "Purchased 5 bags of rice",
        timestamp: "Sep 2",
      },
      {
        id: "musa-activity-2",
        label: "Payment received",
        timestamp: "Aug 29",
      },
      {
        id: "musa-activity-3",
        label: "Purchased 10 bags of rice",
        timestamp: "Aug 21",
      },
    ],
    related: [
      {
        id: "rice-product",
        name: "Rice",
        type: "Product",
      },
      {
        id: "order-musa-001",
        name: "Order #1042",
        type: "Order",
        description: "5 bags of rice",
      },
    ],
    updatedAt: "2 min ago",
  },

  {
    id: "customer-john-trading",
    definitionId: "customers",
    values: {
      "customer-name": "John Trading Ltd.",
      "customer-description": "Retail customer",
    },
    understanding: [
      "Usually purchases products for retail",
      "Places smaller orders than wholesale customers",
    ],
    activity: [
      {
        id: "john-activity-1",
        label: "Purchased assorted products",
        timestamp: "Sep 1",
      },
      {
        id: "john-activity-2",
        label: "Order received",
        timestamp: "Aug 27",
      },
    ],
    updatedAt: "Yesterday",
  },

  {
    id: "customer-amina-stores",
    definitionId: "customers",
    values: {
      "customer-name": "Amina Stores",
      "customer-description": "Grocery retailer",
    },
    understanding: [
      "Frequently purchases grocery products",
      "Often orders at the beginning of the week",
    ],
    activity: [
      {
        id: "amina-activity-1",
        label: "Purchased grocery products",
        timestamp: "Aug 30",
      },
    ],
    updatedAt: "3 days ago",
  },

  // ---------------------------------------------------------------------------
  // Products
  // ---------------------------------------------------------------------------
  {
    id: "product-rice",
    definitionId: "products",
    values: {
      "product-name": "Rice",
      "product-description": "25kg bag of rice",
    },
    understanding: [
      "One of the most frequently ordered products",
      "Commonly purchased by wholesale customers",
    ],
    activity: [
      {
        id: "rice-activity-1",
        label: "5 bags sold",
        timestamp: "Sep 2",
      },
      {
        id: "rice-activity-2",
        label: "10 bags sold",
        timestamp: "Aug 21",
      },
    ],
    related: [
      {
        id: "supplier-rice",
        name: "Northern Foods Ltd.",
        type: "Supplier",
      },
      {
        id: "warehouse-main",
        name: "Main Warehouse",
        type: "Warehouse",
      },
    ],
    updatedAt: "Today",
  },

  // ---------------------------------------------------------------------------
  // Orders
  // ---------------------------------------------------------------------------
  {
    id: "order-1042",
    definitionId: "orders",
    values: {
      "order-name": "Order #1042",
      "order-description": "5 bags of rice for Musa Ibrahim",
    },
    understanding: [
      "Customer usually pays by transfer",
      "Order was part of a wholesale purchase",
    ],
    activity: [
      {
        id: "order-1042-activity-1",
        label: "Order completed",
        timestamp: "Sep 2",
      },
      {
        id: "order-1042-activity-2",
        label: "Payment received",
        timestamp: "Sep 2",
      },
    ],
    related: [
      {
        id: "customer-musa-ibrahim",
        name: "Musa Ibrahim",
        type: "Customer",
      },
      {
        id: "product-rice",
        name: "Rice",
        type: "Product",
      },
    ],
    updatedAt: "Today",
  },

  // ---------------------------------------------------------------------------
  // Suppliers
  // ---------------------------------------------------------------------------
  {
    id: "supplier-northern-foods",
    definitionId: "suppliers",
    values: {
      "supplier-name": "Northern Foods Ltd.",
      "supplier-description": "Primary supplier for rice products",
    },
    understanding: [
      "Supplies one of the business's highest-volume products",
      "Frequently delivers to the main warehouse",
    ],
    activity: [
      {
        id: "supplier-activity-1",
        label: "Delivery received",
        timestamp: "Aug 30",
      },
    ],
    related: [
      {
        id: "product-rice",
        name: "Rice",
        type: "Product",
      },
      {
        id: "warehouse-main",
        name: "Main Warehouse",
        type: "Warehouse",
      },
    ],
    updatedAt: "3 days ago",
  },

  // ---------------------------------------------------------------------------
  // Employees
  // ---------------------------------------------------------------------------
  {
    id: "employee-emeka",
    definitionId: "employees",
    values: {
      "employee-name": "Emeka Okafor",
      "employee-description": "Sales representative",
    },
    understanding: [
      "Handles several wholesale customer relationships",
      "Frequently follows up on customer orders",
    ],
    activity: [
      {
        id: "employee-activity-1",
        label: "Followed up with Musa Ibrahim",
        timestamp: "Sep 1",
      },
    ],
    updatedAt: "Yesterday",
  },

  // ---------------------------------------------------------------------------
  // Locations
  // ---------------------------------------------------------------------------
  {
    id: "location-main-office",
    definitionId: "locations",
    values: {
      "location-name": "Main Office",
      "location-description": "Primary business office",
    },
    activity: [
      {
        id: "location-activity-1",
        label: "Business activity recorded",
        timestamp: "Sep 2",
      },
    ],
    updatedAt: "Today",
  },

  // ---------------------------------------------------------------------------
  // Distributors
  // ---------------------------------------------------------------------------
  {
    id: "distributor-city-distribution",
    definitionId: "distributors",
    values: {
      "distributor-name": "City Distribution",
      "distributor-description": "Local distribution partner",
    },
    understanding: [
      "Handles deliveries to several retail customers",
      "Usually operates within the local area",
    ],
    activity: [
      {
        id: "distributor-activity-1",
        label: "Delivery completed",
        timestamp: "Sep 1",
      },
    ],
    related: [
      {
        id: "customer-amina-stores",
        name: "Amina Stores",
        type: "Customer",
      },
    ],
    updatedAt: "Yesterday",
  },

  // ---------------------------------------------------------------------------
  // Warehouses
  // ---------------------------------------------------------------------------
  {
    id: "warehouse-main",
    definitionId: "warehouses",
    values: {
      "warehouse-name": "Main Warehouse",
      "warehouse-description": "Central storage location",
    },
    understanding: [
      "Stores the majority of the business's rice inventory",
      "Receives regular deliveries from suppliers",
    ],
    activity: [
      {
        id: "warehouse-activity-1",
        label: "5 bags of rice added",
        timestamp: "Sep 2",
      },
      {
        id: "warehouse-activity-2",
        label: "Delivery received",
        timestamp: "Aug 30",
      },
    ],
    related: [
      {
        id: "supplier-northern-foods",
        name: "Northern Foods Ltd.",
        type: "Supplier",
      },
      {
        id: "product-rice",
        name: "Rice",
        type: "Product",
      },
    ],
    updatedAt: "Today",
  },
];
