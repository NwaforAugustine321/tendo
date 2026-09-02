import { ChangeEvent, useMemo, useRef, useState } from "react";
import { Check, FileText, Search, Upload, X } from "lucide-react";

import type { DocumentEntity, DocumentUpload } from "../documents.types";

type Props = {
  entities: DocumentEntity[];
  onUpload?: (upload: DocumentUpload) => void | Promise<void>;
};

const formatFileSize = (size: number) => {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  if (size < 1024 * 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(2)} MB`;
  }

  return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

const getFileType = (file: File) => {
  const extension = file.name.split(".").pop();

  return extension ? extension.toUpperCase() : file.type || "FILE";
};

export default function DocumentsUpload({ entities, onUpload }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState("");

  const [selectedEntity, setSelectedEntity] = useState<DocumentEntity | null>(
    null,
  );

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const [isUploading, setIsUploading] = useState(false);

  const filteredEntities = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return entities;
    }

    return entities.filter(
      (entity) =>
        entity.name.toLowerCase().includes(query) ||
        entity.definitionName.toLowerCase().includes(query),
    );
  }, [entities, search]);

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);

    if (files.length === 0) {
      return;
    }

    setSelectedFiles((current) => {
      const existing = new Set(
        current.map((file) => `${file.name}-${file.size}-${file.lastModified}`),
      );

      const newFiles = files.filter(
        (file) =>
          !existing.has(`${file.name}-${file.size}-${file.lastModified}`),
      );

      return [...current, ...newFiles];
    });

    event.target.value = "";
  };

  const removeFile = (index: number) => {
    setSelectedFiles((current) =>
      current.filter((_, fileIndex) => fileIndex !== index),
    );
  };

  const clearFiles = () => {
    setSelectedFiles([]);
  };

  const handleUpload = async () => {
    if (!selectedEntity || selectedFiles.length === 0) {
      return;
    }

    setIsUploading(true);

    try {
      await onUpload?.({
        files: selectedFiles,
        entities: [selectedEntity],
      });

      setSelectedFiles([]);
    } finally {
      setIsUploading(false);
    }
  };

  const canUpload =
    Boolean(selectedEntity) && selectedFiles.length > 0 && !isUploading;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* HEADER */}
      <div className="shrink-0 border-b border-zinc-800/70">
        <div className="px-6 py-5">
          <h2 className="text-[15px] font-medium text-zinc-100">
            Upload documents
          </h2>

          <p className="mt-1 text-[11px] text-zinc-500">
            Select an entity and upload documents associated with it.
          </p>
        </div>
      </div>

      {/* WORKSPACE */}
      <div className="min-h-0 flex-1">
        <div className="flex h-full min-h-0">
          {/* ENTITY SIDEBAR */}
          <aside className="flex w-[250px] shrink-0 flex-col border-r border-zinc-800/70 bg-[#0f0f0f]">
            {/* SIDEBAR HEADER */}
            <div className="shrink-0 border-b border-zinc-800/60 px-4 py-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
                Entity
              </div>

              <div className="mt-1 text-[10px] text-zinc-700">
                Choose where the documents belong.
              </div>

              {/* SEARCH */}
              <div className="relative mt-3">
                <Search
                  size={12}
                  className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-600"
                />

                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search entities..."
                  className="h-8 w-full rounded-md border border-zinc-800 bg-[#141414] pl-8 pr-2.5 text-[10px] text-zinc-200 outline-none placeholder:text-zinc-700 focus:border-zinc-700"
                />

                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch("")}
                    className="absolute right-1.5 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-zinc-600 hover:bg-white/5 hover:text-zinc-300"
                  >
                    <X size={10} />
                  </button>
                )}
              </div>
            </div>

            {/* ENTITY LIST */}
            <div className="min-h-0 flex-1 overflow-y-auto p-2">
              {filteredEntities.length > 0 ? (
                <div className="space-y-0.5">
                  {filteredEntities.map((entity) => {
                    const selected = selectedEntity?.id === entity.id;

                    return (
                      <button
                        key={entity.id}
                        type="button"
                        onClick={() => setSelectedEntity(entity)}
                        className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-left transition-colors ${
                          selected
                            ? "bg-emerald-500/10 text-zinc-200"
                            : "text-zinc-400 hover:bg-white/[0.035] hover:text-zinc-200"
                        }`}
                      >
                        {/* ENTITY ICON */}
                        <div
                          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[9px] font-medium ${
                            selected
                              ? "bg-emerald-500/15 text-emerald-400"
                              : "bg-white/[0.035] text-zinc-600"
                          }`}
                        >
                          {entity.definitionName.slice(0, 1).toUpperCase()}
                        </div>

                        {/* ENTITY INFO */}
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[10px] font-medium">
                            {entity.name}
                          </div>

                          <div
                            className={`mt-0.5 truncate text-[9px] ${
                              selected ? "text-emerald-400/60" : "text-zinc-700"
                            }`}
                          >
                            {entity.definitionName}
                          </div>
                        </div>

                        {/* SELECTED */}
                        {selected && (
                          <Check
                            size={12}
                            className="shrink-0 text-emerald-400"
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="flex h-full items-center justify-center px-4 text-center">
                  <div>
                    <div className="text-[10px] text-zinc-500">
                      No entities found
                    </div>

                    <div className="mt-1 text-[9px] text-zinc-700">
                      Try a different search.
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* SELECTED ENTITY */}
            {selectedEntity && (
              <div className="shrink-0 border-t border-zinc-800/60 p-3">
                <div className="text-[9px] uppercase tracking-[0.08em] text-zinc-700">
                  Uploading to
                </div>

                <div className="mt-1 truncate text-[10px] font-medium text-emerald-400">
                  {selectedEntity.name}
                </div>

                <div className="mt-0.5 truncate text-[9px] text-zinc-700">
                  {selectedEntity.definitionName}
                </div>
              </div>
            )}
          </aside>

          {/* UPLOAD WORKSPACE */}
          <main className="min-w-0 flex-1 overflow-y-auto">
            <div className="mx-auto flex w-full max-w-[820px] flex-col px-8 py-7">
              {/* WORKSPACE HEADER */}
              <div>
                <div className="text-[13px] font-medium text-zinc-200">
                  Documents
                </div>

                <div className="mt-1 text-[10px] text-zinc-600">
                  Select the files you want Tendo to learn from.
                </div>
              </div>

              {/* UPLOAD AREA */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFiles}
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="group mt-5 flex min-h-[210px] w-full flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-[#111111] px-6 py-8 transition-colors hover:border-zinc-700 hover:bg-[#131313] disabled:cursor-not-allowed disabled:opacity-50"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white/[0.035] text-zinc-500 transition-colors group-hover:bg-white/[0.05] group-hover:text-zinc-400">
                  <Upload size={18} strokeWidth={1.7} />
                </div>

                <div className="mt-4 text-[11px] font-medium text-zinc-300">
                  Select files from your computer
                </div>

                <div className="mt-1.5 text-[10px] text-zinc-700">
                  Select one or multiple documents
                </div>

                <div className="mt-4 rounded-md border border-zinc-800 bg-[#151515] px-3 py-1.5 text-[9px] text-zinc-600">
                  Browse files
                </div>
              </button>

              {/* SELECTED FILES */}
              {selectedFiles.length > 0 && (
                <div className="mt-6">
                  <div className="mb-2 flex items-center justify-between">
                    <div>
                      <div className="text-[11px] font-medium text-zinc-300">
                        Selected files
                      </div>

                      <div className="mt-0.5 text-[9px] text-zinc-700">
                        {selectedFiles.length}{" "}
                        {selectedFiles.length === 1 ? "file" : "files"} ready to
                        upload
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={clearFiles}
                      disabled={isUploading}
                      className="text-[9px] text-zinc-600 transition-colors hover:text-zinc-300 disabled:opacity-40"
                    >
                      Clear all
                    </button>
                  </div>

                  <div className="overflow-hidden rounded-xl border border-zinc-800/70 bg-[#111111]">
                    {selectedFiles.map((file, index) => (
                      <div
                        key={`${file.name}-${file.size}-${file.lastModified}`}
                        className={`flex items-center gap-3 px-3.5 py-2.5 ${
                          index > 0 ? "border-t border-zinc-800/50" : ""
                        }`}
                      >
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white/[0.035] text-zinc-600">
                          <FileText size={13} />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[10px] font-medium text-zinc-300">
                            {file.name}
                          </div>

                          <div className="mt-0.5 flex items-center gap-1.5 text-[9px] text-zinc-700">
                            <span>{getFileType(file)}</span>

                            <span>·</span>

                            <span>{formatFileSize(file.size)}</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          disabled={isUploading}
                          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-zinc-700 transition-colors hover:bg-white/5 hover:text-zinc-300 disabled:opacity-40"
                          title="Remove file"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SELECTED ENTITY INFO */}
              <div className="mt-5 flex items-center justify-between rounded-lg border border-zinc-800/60 bg-[#111111] px-3.5 py-3">
                <div className="flex min-w-0 items-center gap-2.5">
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${
                      selectedEntity
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-white/[0.035] text-zinc-700"
                    }`}
                  >
                    {selectedEntity ? (
                      <Check size={13} />
                    ) : (
                      <FileText size={13} />
                    )}
                  </div>

                  <div className="min-w-0">
                    <div className="text-[9px] text-zinc-700">Destination</div>

                    <div
                      className={`truncate text-[10px] font-medium ${
                        selectedEntity ? "text-zinc-300" : "text-zinc-700"
                      }`}
                    >
                      {selectedEntity
                        ? `${selectedEntity.definitionName} · ${selectedEntity.name}`
                        : "Select an entity from the left"}
                    </div>
                  </div>
                </div>

                {selectedEntity && (
                  <button
                    type="button"
                    onClick={() => setSelectedEntity(null)}
                    className="shrink-0 text-[9px] text-zinc-600 hover:text-zinc-300"
                  >
                    Change
                  </button>
                )}
              </div>

              {/* UPLOAD ACTION */}
              <div className="mt-4 flex items-center justify-between">
                <div className="text-[9px] text-zinc-700">
                  {selectedEntity && selectedFiles.length > 0
                    ? `${selectedFiles.length} ${
                        selectedFiles.length === 1 ? "document" : "documents"
                      } will be uploaded to ${selectedEntity.name}.`
                    : !selectedEntity
                      ? "Select an entity to continue."
                      : "Select at least one document."}
                </div>

                <button
                  type="button"
                  onClick={handleUpload}
                  disabled={!canUpload}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-emerald-500 px-4 py-2 text-[10px] font-medium text-black transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
                >
                  <Upload
                    size={12}
                    className={isUploading ? "animate-pulse" : ""}
                  />

                  {isUploading
                    ? "Uploading..."
                    : selectedFiles.length > 0
                      ? `Upload ${selectedFiles.length} ${
                          selectedFiles.length === 1 ? "file" : "files"
                        }`
                      : "Upload documents"}
                </button>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
