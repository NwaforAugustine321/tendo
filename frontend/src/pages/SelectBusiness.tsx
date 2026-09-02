import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getProfiles,
  createEmptyBusiness,
  resumeSession,
  deleteBusinessProfile,
  type BusinessProfile,
} from "../lib/services/business";
import { Spinner } from "../components/atoms/Spinner";
import { TalkingCharacter } from "../components/containers/TalkingCharacter";
import { TopBar } from "../components/containers";
import { useBusinessStore } from "../store/business";
import { ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 3;

export function SelectBusiness() {
  const [profiles, setProfiles] = useState<BusinessProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [resumingId, setResumingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<BusinessProfile | null>(
    null,
  );
  const [page, setPage] = useState(0);
  const { setCurrentProfile } = useBusinessStore();
  const navigate = useNavigate();

  const totalPages = Math.max(1, Math.ceil(profiles.length / PAGE_SIZE));
  const paginatedProfiles = profiles.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE,
  );

  useEffect(() => {
    getProfiles()
      .then((p) => {
        setProfiles(p);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleCreateNew = async () => {
    setCreating(true);
    try {
      const { business_id, session_id } = await createEmptyBusiness();
      navigate(
        `/onboarding?session_id=${session_id}&business_id=${business_id}`,
      );
    } catch (err) {
      console.error("Failed to create business:", err);
      setCreating(false);
    }
  };

  const handleSelectBusiness = async (profile: BusinessProfile) => {
    setResumingId(profile.id);
    setCurrentProfile(profile);
    if (profile.onboarding_completed) {
      navigate("/me");
    } else {
      try {
        const { session_id, business_id } = await resumeSession(profile.id);
        navigate(
          `/onboarding?session_id=${session_id}&business_id=${business_id}`,
        );
      } catch (err) {
        console.error("Failed to resume session:", err);
        setResumingId(null);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#0a0a0a]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[#0a0a0a]">
      <TopBar onMenuClick={() => {}} />
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="mb-8 flex justify-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
              <span className="flex items-center gap-[3px]">
                <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
                <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
              </span>
            </div>
          </div>

          <h1 className="text-center text-2xl font-semibold tracking-tight text-white">
            Welcome!, Choose your business Profile
          </h1>
          <p className="mt-2 text-center text-sm text-zinc-400">
            Choose an existing business or create a new one.
          </p>

          {/* Paginated profiles */}
          {profiles.length > 0 && (
            <div className="mt-8 space-y-3">
              {paginatedProfiles.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSelectBusiness(p)}
                  disabled={resumingId === p.id}
                  className="flex w-full items-center gap-3 rounded-xl border border-zinc-800/90 bg-[#141414] p-4 text-left transition-colors hover:border-zinc-700/90 hover:bg-[#1a1a1a] cursor-pointer disabled:opacity-60"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3ecf8e]/10 text-[#3ecf8e]">
                    {resumingId === p.id ? (
                      <Spinner size="sm" />
                    ) : (
                      <span className="text-lg font-bold">
                        {(p.name || "B")[0].toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">
                      {p.name || "Untitled business"}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {p.onboarding_completed
                        ? "Continue with this business"
                        : "Onboarding in progress..."}
                    </p>
                  </div>
                  {!p.onboarding_completed && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(p);
                      }}
                      className="rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-medium text-red-400 hover:bg-red-500/20"
                    >
                      Delete
                    </button>
                  )}
                </button>
              ))}

              {/* Pagination controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft size={14} /> Prev
                  </button>
                  <span className="text-xs text-zinc-500">
                    {page + 1} / {totalPages}
                  </span>
                  <button
                    onClick={() =>
                      setPage((p) => Math.min(totalPages - 1, p + 1))
                    }
                    disabled={page >= totalPages - 1}
                    className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Create new business */}
          <button
            onClick={handleCreateNew}
            disabled={creating}
            className="mt-6 flex w-full items-center gap-3 rounded-xl border border-dashed border-[#3ecf8e]/40 bg-[#0a0a0a] p-4 transition-colors hover:border-[#3ecf8e]/70 hover:bg-[#141414] disabled:opacity-50"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#3ecf8e]/30 text-[#3ecf8e]">
              {creating ? (
                <Spinner size="sm" />
              ) : (
                <span className="text-xl">+</span>
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-[#3ecf8e]">
                {creating
                  ? "Setting up new profile..."
                  : "Create new business profile"}
              </p>
              <p className="text-xs text-zinc-400">
                Let Tendo learn about a new business
              </p>
            </div>
          </button>

          {profiles.length === 0 && (
            <p className="mt-6 text-center text-xs text-zinc-400">
              You don't have any business profiles yet. Create one to get
              started.
            </p>
          )}
        </div>
      </div>

      <TalkingCharacter isSpeaking={false} />

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75">
          <div className="w-full max-w-lg rounded-xl border border-zinc-800/40 bg-[#141414] p-6">
            <h3 className="text-base font-semibold text-white">
              Delete business profile?
            </h3>
            <p className="mt-2 text-sm text-zinc-400">
              This will permanently delete this incomplete profile. You can
              always create a new one.
            </p>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg px-4 py-2 text-sm text-zinc-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setResumingId(deleteTarget.id);
                  deleteBusinessProfile(deleteTarget.id)
                    .then(() => {
                      setProfiles((prev) => {
                        const updated = prev.filter(
                          (x) => x.id !== deleteTarget.id,
                        );
                        // Adjust page if current page would be empty
                        const newTotalPages = Math.max(
                          1,
                          Math.ceil(updated.length / PAGE_SIZE),
                        );
                        if (page >= newTotalPages) setPage(newTotalPages - 1);
                        return updated;
                      });
                      setDeleteTarget(null);
                      setResumingId(null);
                    })
                    .catch(() => setResumingId(null));
                }}
                disabled={resumingId === deleteTarget.id}
                className="flex items-center gap-2 rounded-lg bg-red-500/20 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/30 disabled:opacity-60"
              >
                {resumingId === deleteTarget.id ? <Spinner size="sm" /> : null}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
