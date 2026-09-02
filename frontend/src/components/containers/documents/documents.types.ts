export type DocumentStatus = "uploading" | "processing" | "ready" | "failed";

export type DocumentSourceType = "upload" | "computer" | "folder" | "other";

export type DocumentSource = {
  id: string;
  name: string;
  type: DocumentSourceType;
  connected: boolean;
  createdAt: string;
  updatedAt?: string;
};

export type DocumentEntityReference = {
  id: string;
  definitionId: string;
  definitionName: string;
  entryId: string;
  entryName: string;
};

export type KnowledgeDocument = {
  id: string;
  name: string;
  type: string;
  size: number;
  status: DocumentStatus;
  source: DocumentSourceType;
  sourceId?: string;
  uploadedAt: string;
  updatedAt?: string;
  entities: DocumentEntityReference[];
};

export type DocumentFilter = "all" | DocumentStatus;

export type DocumentTab = "documents" | "sources" | "upload";

export type DocumentEntity = {
  id: string;
  definitionId: string;
  definitionName: string;
  name: string;
};

export type DocumentUpload = {
  files: File[];
  entities: DocumentEntity[];
};
