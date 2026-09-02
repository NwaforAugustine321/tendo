import { useMemo, useState } from "react";
import {
  MapPin,
  Package,
  ShoppingCart,
  Truck,
  UserRound,
  Users,
  Warehouse,
} from "lucide-react";

import KnowledgeContent from "./KnowledgeContent";
import KnowledgeDetail from "./KnowledgeDetail";
import AddToKnowledgeModal from "./AddToKnowledgeModal";

import { INITIAL_RECORDS } from "./data/knowledge.mock";

import type {
  KnowledgeDefinition,
  KnowledgeItem,
  KnowledgeSource,
  KnowledgeEntryValues,
  KnowledgeRecord,
} from "./knowledge.types";

const INITIAL_KNOWLEDGE: KnowledgeItem[] = [
  {
    id: "customers",
    name: "Customers",
    records: 1284,
    properties: 8,
    icon: Users,
    source: "tendo",
    updatedRecently: true,
  },
  {
    id: "products",
    name: "Products",
    records: 438,
    properties: 12,
    icon: Package,
    source: "tendo",
    addedRecently: true,
  },
  {
    id: "orders",
    name: "Orders",
    records: 3921,
    properties: 14,
    icon: ShoppingCart,
    source: "tendo",
    updatedRecently: true,
  },
  {
    id: "suppliers",
    name: "Suppliers",
    records: 86,
    properties: 7,
    icon: Truck,
    source: "documents",
    addedRecently: true,
  },
  {
    id: "employees",
    name: "Employees",
    records: 42,
    properties: 9,
    icon: UserRound,
    source: "tendo",
    updatedRecently: true,
  },
  {
    id: "locations",
    name: "Locations",
    records: 6,
    properties: 5,
    icon: MapPin,
    source: "documents",
  },
  {
    id: "distributors",
    name: "Distributors",
    records: 43,
    properties: 6,
    icon: Truck,
    source: "you",
    addedRecently: true,
  },
  {
    id: "warehouses",
    name: "Warehouses",
    records: 12,
    properties: 8,
    icon: Warehouse,
    source: "you",
    updatedRecently: true,
  },
];

/*
 * -----------------------------------------------------------------------
 * INITIAL TEMPLATE DEFINITIONS
 * -----------------------------------------------------------------------
 */

const INITIAL_DEFINITIONS: KnowledgeDefinition[] = [
  {
    id: "customers",
    name: "Customers",
    description: "People and organizations your business serves.",
    fields: [
      {
        id: "customer-name",
        name: "Name",
      },
      {
        id: "customer-description",
        name: "Description",
      },
    ],
  },
  {
    id: "products",
    name: "Products",
    description: "Products your business sells or manages.",
    fields: [
      {
        id: "product-name",
        name: "Name",
      },
      {
        id: "product-description",
        name: "Description",
      },
    ],
  },
  {
    id: "orders",
    name: "Orders",
    description: "Orders placed with your business.",
    fields: [
      {
        id: "order-name",
        name: "Name",
      },
      {
        id: "order-description",
        name: "Description",
      },
    ],
  },
  {
    id: "suppliers",
    name: "Suppliers",
    description:
      "Suppliers that provide products or services to your business.",
    fields: [
      {
        id: "supplier-name",
        name: "Name",
      },
      {
        id: "supplier-description",
        name: "Description",
      },
    ],
  },
  {
    id: "employees",
    name: "Employees",
    description: "People who work for your business.",
    fields: [
      {
        id: "employee-name",
        name: "Name",
      },
      {
        id: "employee-description",
        name: "Description",
      },
    ],
  },
  {
    id: "locations",
    name: "Locations",
    description: "Places connected to your business.",
    fields: [
      {
        id: "location-name",
        name: "Name",
      },
      {
        id: "location-description",
        name: "Description",
      },
    ],
  },
  {
    id: "distributors",
    name: "Distributors",
    description: "Distributors that help move your products.",
    fields: [
      {
        id: "distributor-name",
        name: "Name",
      },
      {
        id: "distributor-description",
        name: "Description",
      },
    ],
  },
  {
    id: "warehouses",
    name: "Warehouses",
    description: "Warehouses used to store your products.",
    fields: [
      {
        id: "warehouse-name",
        name: "Name",
      },
      {
        id: "warehouse-description",
        name: "Description",
      },
    ],
  },
];

export default function Knowledge() {
  /*
   * -----------------------------------------------------------------------
   * KNOWLEDGE ITEMS
   * -----------------------------------------------------------------------
   */

  const [knowledgeItems, setKnowledgeItems] =
    useState<KnowledgeItem[]>(INITIAL_KNOWLEDGE);

  /*
   * -----------------------------------------------------------------------
   * KNOWLEDGE DEFINITIONS / TEMPLATES
   * -----------------------------------------------------------------------
   */

  const [definitions, setDefinitions] =
    useState<KnowledgeDefinition[]>(INITIAL_DEFINITIONS);

  /*
   * -----------------------------------------------------------------------
   * KNOWLEDGE RECORDS
   * -----------------------------------------------------------------------
   */

  const [records, setRecords] = useState<KnowledgeRecord[]>(INITIAL_RECORDS);

  /*
   * -----------------------------------------------------------------------
   * SELECTED KNOWLEDGE RECORD
   * -----------------------------------------------------------------------
   */

  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);

  /*
   * -----------------------------------------------------------------------
   * SEARCH / MODAL
   * -----------------------------------------------------------------------
   */

  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  /*
   * -----------------------------------------------------------------------
   * PENDING ENTITY FOR DOCUMENT UPLOAD
   * -----------------------------------------------------------------------
   *
   * After the entity is saved, we keep the newly-created record here while
   * the user moves through the document upload step.
   *
   * This gives the document flow a concrete entity/record to attach the
   * uploaded files to.
   */

  const [pendingDocumentRecord, setPendingDocumentRecord] =
    useState<KnowledgeRecord | null>(null);

  /*
   * -----------------------------------------------------------------------
   * DOCUMENTS
   * -----------------------------------------------------------------------
   *
   * Temporary frontend storage for the selected files.
   *
   * This is intentionally kept separate from the knowledge record itself.
   * The actual upload, document extraction, processing and persistence
   * should be connected here when the document service/API is ready.
   */

  const [entityDocuments, setEntityDocuments] = useState<
    Record<string, File[]>
  >({});

  /*
   * -----------------------------------------------------------------------
   * FILTER STATE
   * -----------------------------------------------------------------------
   */

  const [selectedKnowledge, setSelectedKnowledge] = useState<string[]>([]);

  const [selectedSource, setSelectedSource] = useState<KnowledgeSource[]>([]);

  const [selectedRecent, setSelectedRecent] = useState<string[]>([]);

  const [appliedKnowledge, setAppliedKnowledge] = useState<string[]>([]);

  const [appliedSource, setAppliedSource] = useState<KnowledgeSource[]>([]);

  const [appliedRecent, setAppliedRecent] = useState<string[]>([]);

  /*
   * -----------------------------------------------------------------------
   * FILTER SECTIONS
   * -----------------------------------------------------------------------
   */

  const [expandedKnowledge, setExpandedKnowledge] = useState(true);
  const [expandedSource, setExpandedSource] = useState(true);
  const [expandedRecent, setExpandedRecent] = useState(true);

  /*
   * -----------------------------------------------------------------------
   * SOURCE GROUPS
   * -----------------------------------------------------------------------
   */

  const yourBusiness = useMemo(
    () => knowledgeItems.filter((item) => item.source !== "you"),
    [knowledgeItems],
  );

  const addedByYou = useMemo(
    () => knowledgeItems.filter((item) => item.source === "you"),
    [knowledgeItems],
  );

  /*
   * -----------------------------------------------------------------------
   * FILTERING
   * -----------------------------------------------------------------------
   */

  const filterItems = (items: KnowledgeItem[]) => {
    const query = search.trim().toLowerCase();

    return items.filter((item) => {
      const matchesSearch = !query || item.name.toLowerCase().includes(query);

      const matchesKnowledge =
        appliedKnowledge.length === 0 || appliedKnowledge.includes(item.id);

      const matchesSource =
        appliedSource.length === 0 || appliedSource.includes(item.source);

      const matchesRecent =
        appliedRecent.length === 0 ||
        (appliedRecent.includes("added") && item.addedRecently) ||
        (appliedRecent.includes("updated") && item.updatedRecently);

      return (
        matchesSearch && matchesKnowledge && matchesSource && matchesRecent
      );
    });
  };

  const filteredYourBusiness = useMemo(
    () => filterItems(yourBusiness),
    [search, appliedKnowledge, appliedSource, appliedRecent, yourBusiness],
  );

  const filteredAddedByYou = useMemo(
    () => filterItems(addedByYou),
    [search, appliedKnowledge, appliedSource, appliedRecent, addedByYou],
  );

  /*
   * -----------------------------------------------------------------------
   * FILTER DATA
   * -----------------------------------------------------------------------
   */

  const knowledgeFilterItems = knowledgeItems.map((item) => ({
    id: item.id,
    name: item.name,
    count: item.records,
  }));

  const sourceFilters = [
    {
      id: "tendo" as KnowledgeSource,
      label: "Tendo already knows",
      count: knowledgeItems.filter((item) => item.source === "tendo").length,
    },
    {
      id: "you" as KnowledgeSource,
      label: "Added by you",
      count: knowledgeItems.filter((item) => item.source === "you").length,
    },
    {
      id: "documents" as KnowledgeSource,
      label: "Learned from documents",
      count: knowledgeItems.filter((item) => item.source === "documents")
        .length,
    },
  ];

  const recentFilters = [
    {
      id: "added",
      label: "Added recently",
      count: knowledgeItems.filter((item) => item.addedRecently).length,
    },
    {
      id: "updated",
      label: "Updated recently",
      count: knowledgeItems.filter((item) => item.updatedRecently).length,
    },
  ];

  /*
   * -----------------------------------------------------------------------
   * FILTER ACTIONS
   * -----------------------------------------------------------------------
   */

  const toggleKnowledge = (id: string) => {
    setSelectedKnowledge((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  };

  const toggleSource = (source: KnowledgeSource) => {
    setSelectedSource((current) =>
      current.includes(source)
        ? current.filter((value) => value !== source)
        : [...current, source],
    );
  };

  const toggleRecent = (id: string) => {
    setSelectedRecent((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  };

  const resetFilters = () => {
    setSelectedKnowledge([]);
    setSelectedSource([]);
    setSelectedRecent([]);

    setAppliedKnowledge([]);
    setAppliedSource([]);
    setAppliedRecent([]);
  };

  const applyFilters = () => {
    setAppliedKnowledge(selectedKnowledge);
    setAppliedSource(selectedSource);
    setAppliedRecent(selectedRecent);
  };

  /*
   * -----------------------------------------------------------------------
   * DETAIL VIEW
   * -----------------------------------------------------------------------
   */

  const selectedRecord = useMemo(() => {
    if (!selectedRecordId) {
      return null;
    }

    return records.find((record) => record.id === selectedRecordId) ?? null;
  }, [records, selectedRecordId]);

  const selectedDefinition = useMemo(() => {
    if (!selectedRecord) {
      return null;
    }

    return (
      definitions.find(
        (definition) => definition.id === selectedRecord.definitionId,
      ) ?? null
    );
  }, [definitions, selectedRecord]);

  const handleKnowledgeItemClick = (item: KnowledgeItem) => {
    const record = records.find((value) => value.definitionId === item.id);

    if (!record) {
      return;
    }

    setSelectedRecordId(record.id);
  };

  const handleBackFromDetail = () => {
    setSelectedRecordId(null);
  };

  /*
   * -----------------------------------------------------------------------
   * ADD FLOW
   * -----------------------------------------------------------------------
   */

  const closeAddModal = () => {
    setShowAdd(false);
    setPendingDocumentRecord(null);
  };

  /**
   * Create or update a template.
   */
  const handleDefinitionSaved = (definition: KnowledgeDefinition) => {
    setDefinitions((current) => {
      const exists = current.some((item) => item.id === definition.id);

      if (exists) {
        return current.map((item) =>
          item.id === definition.id ? definition : item,
        );
      }

      return [...current, definition];
    });

    setKnowledgeItems((current) => {
      const existing = current.find((item) => item.id === definition.id);

      if (existing) {
        return current.map((item) =>
          item.id === definition.id
            ? {
                ...item,
                name: definition.name,
                properties: definition.fields.length,
              }
            : item,
        );
      }

      return [
        ...current,
        {
          id: definition.id,
          name: definition.name,
          records: 0,
          properties: definition.fields.length,
          icon: Package,
          source: "you",
          addedRecently: true,
        },
      ];
    });
  };

  /**
   * Save a new knowledge entry.
   *
   * IMPORTANT:
   * We do not close the modal here.
   *
   * The AddToKnowledgeModal owns the next step and will move the user to
   * document selection after this save completes.
   */
  const handleSaveEntry = (
    definition: KnowledgeDefinition,
    values: KnowledgeEntryValues,
  ) => {
    const newRecord: KnowledgeRecord = {
      id: `${definition.id}-${Date.now()}`,
      definitionId: definition.id,
      values,
      createdAt: "Just now",
      updatedAt: "Just now",
    };

    setRecords((current) => [...current, newRecord]);

    setKnowledgeItems((current) =>
      current.map((item) =>
        item.id === definition.id
          ? {
              ...item,
              records: item.records + 1,
              addedRecently: true,
            }
          : item,
      ),
    );

    /*
     * Keep this record alive for the following document step.
     */
    setPendingDocumentRecord(newRecord);
  };

  /**
   * Handle documents selected for the newly-created entity.
   *
   * The modal supplies the definition and selected files. The actual entity
   * is resolved from pendingDocumentRecord, which was created immediately
   * before the document step.
   *
   * This currently stores the files in local frontend state only.
   * Replace the body with the real document upload/processing API when that
   * service is connected.
   */
  const handleUploadDocuments = async (
    definition: KnowledgeDefinition,
    files: File[],
  ) => {
    if (!pendingDocumentRecord) {
      console.error(
        "Cannot upload documents because no entity record is pending.",
      );
      return;
    }

    if (pendingDocumentRecord.definitionId !== definition.id) {
      console.error(
        "Cannot upload documents because the pending entity does not match the selected definition.",
      );
      return;
    }

    setEntityDocuments((current) => ({
      ...current,
      [pendingDocumentRecord.id]: [
        ...(current[pendingDocumentRecord.id] ?? []),
        ...files,
      ],
    }));

    /*
     * ---------------------------------------------------------------------
     * DOCUMENT SERVICE INTEGRATION POINT
     * ---------------------------------------------------------------------
     *
     * This is where the real upload/processing call should eventually go.
     *
     * Example future flow:
     *
     * await uploadDocuments({
     *   entityId: pendingDocumentRecord.id,
     *   definitionId: definition.id,
     *   files,
     * });
     *
     * The document service can then:
     *
     * 1. Upload the files.
     * 2. Create document records.
     * 3. Process/extract their contents.
     * 4. Associate the documents with this entity.
     * 5. Trigger the knowledge/document processing pipeline.
     *
     * We intentionally do not invent that API here.
     */

    closeAddModal();
  };

  /*
   * -----------------------------------------------------------------------
   * RENDER
   * -----------------------------------------------------------------------
   */

  return (
    <div className="h-screen overflow-hidden bg-[#0f0f0f] text-zinc-100">
      <div className="mx-auto flex h-full w-full max-w-[1400px] gap-8 px-6">
        {selectedRecord && selectedDefinition ? (
          <main className="min-w-0 flex-1">
            <KnowledgeDetail
              definition={selectedDefinition}
              record={selectedRecord}
              onBack={handleBackFromDetail}
            />
          </main>
        ) : (
          <KnowledgeContent
            search={search}
            onSearchChange={setSearch}
            knowledgeItems={knowledgeItems}
            filteredYourBusiness={filteredYourBusiness}
            filteredAddedByYou={filteredAddedByYou}
            selectedKnowledge={selectedKnowledge}
            selectedSource={selectedSource}
            selectedRecent={selectedRecent}
            appliedKnowledge={appliedKnowledge}
            appliedSource={appliedSource}
            appliedRecent={appliedRecent}
            expandedKnowledge={expandedKnowledge}
            expandedSource={expandedSource}
            expandedRecent={expandedRecent}
            knowledgeFilterItems={knowledgeFilterItems}
            sourceFilters={sourceFilters}
            recentFilters={recentFilters}
            onToggleKnowledge={toggleKnowledge}
            onToggleSource={toggleSource}
            onToggleRecent={toggleRecent}
            onToggleKnowledgeSection={() =>
              setExpandedKnowledge((value) => !value)
            }
            onToggleSourceSection={() => setExpandedSource((value) => !value)}
            onToggleRecentSection={() => setExpandedRecent((value) => !value)}
            onResetFilters={resetFilters}
            onApplyFilters={applyFilters}
            onAdd={() => setShowAdd(true)}
            onItemClick={handleKnowledgeItemClick}
          />
        )}
      </div>

      {showAdd && (
        <AddToKnowledgeModal
          definitions={definitions}
          onClose={closeAddModal}
          onDefinitionSaved={handleDefinitionSaved}
          onSaveEntry={handleSaveEntry}
          onUploadDocuments={handleUploadDocuments}
        />
      )}
    </div>
  );
}
