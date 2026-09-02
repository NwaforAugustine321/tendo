import type {
  DocumentEntity,
  DocumentSource,
  KnowledgeDocument,
} from "./documents.types";

export const INITIAL_DOCUMENTS: KnowledgeDocument[] = [
  {
    id: "doc-001",
    name: "Employee Handbook.pdf",
    type: "PDF",
    size: 2_450_000,
    status: "ready",
    source: "upload",
    uploadedAt: "Sep 2, 2026",
    entities: [
      {
        id: "employee-john-doe",
        definitionId: "employees",
        definitionName: "Employees",
        entryId: "employees-001",
        entryName: "John Doe",
      },
    ],
  },
  {
    id: "doc-002",
    name: "Product Catalog.pdf",
    type: "PDF",
    size: 4_820_000,
    status: "ready",
    source: "computer",
    uploadedAt: "Sep 1, 2026",
    entities: [
      {
        id: "product-001",
        definitionId: "products",
        definitionName: "Products",
        entryId: "products-001",
        entryName: "Product A",
      },
    ],
  },
  {
    id: "doc-003",
    name: "Supplier Agreement.docx",
    type: "DOCX",
    size: 1_180_000,
    status: "processing",
    source: "upload",
    uploadedAt: "Aug 31, 2026",
    entities: [],
  },
  {
    id: "doc-004",
    name: "Customer Records.xlsx",
    type: "XLSX",
    size: 3_640_000,
    status: "ready",
    source: "folder",
    sourceId: "source-001",
    uploadedAt: "Aug 29, 2026",
    entities: [
      {
        id: "customer-001",
        definitionId: "customers",
        definitionName: "Customers",
        entryId: "customers-001",
        entryName: "Acme Corporation",
      },
    ],
  },
  {
    id: "doc-005",
    name: "Annual Business Report.pdf",
    type: "PDF",
    size: 6_120_000,
    status: "failed",
    source: "upload",
    uploadedAt: "Aug 27, 2026",
    entities: [],
  },
];

export const INITIAL_DOCUMENT_SOURCES: DocumentSource[] = [
  {
    id: "source-001",
    name: "Business Documents",
    type: "folder",
    connected: true,
    createdAt: "Aug 20, 2026",
    updatedAt: "Sep 1, 2026",
  },
];

export const INITIAL_DOCUMENT_ENTITIES: DocumentEntity[] = [
  {
    id: "employees-001",
    definitionId: "employees",
    definitionName: "Employees",
    name: "John Doe",
  },
  {
    id: "employees-002",
    definitionId: "employees",
    definitionName: "Employees",
    name: "Jane Smith",
  },
  {
    id: "employees-003",
    definitionId: "employees",
    definitionName: "Employees",
    name: "Michael Brown",
  },
  {
    id: "customers-001",
    definitionId: "customers",
    definitionName: "Customers",
    name: "Acme Corporation",
  },
  {
    id: "customers-002",
    definitionId: "customers",
    definitionName: "Customers",
    name: "Globex Corporation",
  },
  {
    id: "products-001",
    definitionId: "products",
    definitionName: "Products",
    name: "Product A",
  },
  {
    id: "products-002",
    definitionId: "products",
    definitionName: "Products",
    name: "Product B",
  },
  {
    id: "orders-001",
    definitionId: "orders",
    definitionName: "Orders",
    name: "Order #1001",
  },
];
