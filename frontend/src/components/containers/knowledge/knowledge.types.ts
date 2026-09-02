import type { ElementType } from "react";

export type KnowledgeSource = "tendo" | "you" | "documents";

export type KnowledgeField = {
  id: string;
  name: string;
  description?: string;
};

export type KnowledgeDefinition = {
  id: string;
  name: string;
  description: string;
  fields: KnowledgeField[];
};

export type KnowledgeEntryValues = Record<string, string>;

export type KnowledgeItem = {
  id: string;
  name: string;
  records: number;
  properties: number;
  icon: ElementType;
  source: KnowledgeSource;
  updatedRecently?: boolean;
  addedRecently?: boolean;
};

/**
 * A single item inside a knowledge type.
 *
 * Example:
 * Customers → Musa Ibrahim
 * Products → 50kg Rice
 * Warehouses → Main Warehouse
 */
export type KnowledgeRecord = {
  id: string;
  definitionId: string;
  values: KnowledgeEntryValues;

  /**
   * Things Tendo has learned about this item
   * from conversations, documents, and activity.
   */
  understanding?: string[];

  /**
   * Recent activity involving this item.
   */
  activity?: KnowledgeActivity[];

  /**
   * Other things Tendo knows that are connected
   * to this item.
   */
  related?: KnowledgeRelatedItem[];

  createdAt?: string;
  updatedAt?: string;
};

export type KnowledgeActivity = {
  id: string;
  label: string;
  description?: string;
  timestamp: string;
};

export type KnowledgeRelatedItem = {
  id: string;
  name: string;
  type: string;
  description?: string;
};
