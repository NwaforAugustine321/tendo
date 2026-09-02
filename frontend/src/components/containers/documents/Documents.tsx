import { useState } from "react";
import { FileText, Folder, Upload } from "lucide-react";

import DocumentsList from "./components/DocumentsList";
import DocumentsSources from "./components/DocumentsSources";
import DocumentsUpload from "./components/DocumentsUpload";

import {
  INITIAL_DOCUMENTS,
  INITIAL_DOCUMENT_ENTITIES,
  INITIAL_DOCUMENT_SOURCES,
} from "./documents.mock";

import type {
  DocumentTab,
  DocumentUpload,
  DocumentSource,
  KnowledgeDocument,
} from "./documents.types";

const TABS: {
  id: DocumentTab;
  label: string;
  icon: typeof FileText;
}[] = [
  {
    id: "documents",
    label: "Memory",
    icon: FileText,
  },
  {
    id: "sources",
    label: "Sources",
    icon: Folder,
  },
  {
    id: "upload",
    label: "Upload",
    icon: Upload,
  },
];

export default function Documents() {
  const [activeTab, setActiveTab] = useState<DocumentTab>("documents");

  const [documents, setDocuments] =
    useState<KnowledgeDocument[]>(INITIAL_DOCUMENTS);

  const [sources, setSources] = useState<DocumentSource[]>(
    INITIAL_DOCUMENT_SOURCES,
  );

  const handleUpload = async ({ files, entities }: DocumentUpload) => {
    /*
     * This is the integration point for the real document service.
     *
     * For now we create local document records so the UI behaves
     * like an actual upload flow.
     */
    const uploadedAt = "Just now";

    const newDocuments: KnowledgeDocument[] = files.map((file) => ({
      id: `doc-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: file.name,
      type: file.name.split(".").pop()?.toUpperCase() || "FILE",
      size: file.size,
      status: "processing",
      source: "upload",
      uploadedAt,
      entities: entities.map((entity) => ({
        id: entity.id,
        definitionId: entity.definitionId,
        definitionName: entity.definitionName,
        entryId: entity.id,
        entryName: entity.name,
      })),
    }));

    setDocuments((current) => [...newDocuments, ...current]);

    setActiveTab("documents");
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#0d0d0d]">
      {/* PAGE HEADER */}
      <div className="shrink-0 border-b border-zinc-800/70">
        <div className="px-6 pt-6">
          <h1 className="text-[17px] font-medium text-zinc-100">Memory</h1>

          <p className="mt-1 text-[11px] text-zinc-500">
            Manage the documents Tendo uses to build knowledge.
          </p>
        </div>

        {/* TABS */}
        <div className="mt-5 flex items-center gap-1 px-6">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-1.5 px-3 pb-3 text-[11px] font-medium transition-colors ${
                  active ? "text-zinc-200" : "text-zinc-600 hover:text-zinc-400"
                }`}
              >
                <Icon size={13} strokeWidth={1.7} />

                {tab.label}

                {active && (
                  <span className="absolute bottom-0 left-2 right-2 h-px bg-zinc-300" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* TAB CONTENT */}
      <div className="min-h-0 flex-1">
        {activeTab === "documents" && <DocumentsList documents={documents} />}

        {activeTab === "sources" && (
          <DocumentsSources sources={sources} onSourcesChange={setSources} />
        )}

        {activeTab === "upload" && (
          <DocumentsUpload
            entities={INITIAL_DOCUMENT_ENTITIES}
            onUpload={handleUpload}
          />
        )}
      </div>
    </div>
  );
}
