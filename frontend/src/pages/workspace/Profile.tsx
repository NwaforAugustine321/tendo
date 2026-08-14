import { useState, useEffect } from "react";
import clsx from "clsx";
import { toast } from "sonner";
import { logout, forgotPassword } from "../../lib/services/auth";
import { useAuthStore } from "../../store/auth";
import { useNavigate } from "react-router-dom";

type Tab = "profile" | "settings";

export function Profile() {
  const { user, fetchProfile } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("profile");

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleLogout = async () => {
    await logout();
    useAuthStore.getState().clear();
    navigate("/login");
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "profile", label: "Profile" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <div className="flex h-full w-full items-start justify-center overflow-y-auto py-10 px-6">
      <div className="w-full max-w-[720px]">
        <div className="mb-10">
          <h1 className="text-xl font-semibold text-white">
            {user?.name || "User"}
          </h1>
          <p className="mt-0.5 text-sm text-zinc-500">{user?.email || ""}</p>
        </div>

        <div className="flex gap-12">
          <nav className="flex w-[120px] shrink-0 flex-col gap-3">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "text-left text-sm font-medium transition-colors",
                  activeTab === tab.id
                    ? "text-white"
                    : "text-zinc-500 hover:text-zinc-300",
                )}
              >
                {tab.label}
              </button>
            ))}
            <button
              type="button"
              onClick={handleLogout}
              className="mt-4 text-left text-sm font-medium text-red-400 transition-colors hover:text-red-300"
            >
              Log out
            </button>
          </nav>

          <div className="flex-1 min-w-0">
            {activeTab === "profile" && <ProfileContent user={user} />}
            {activeTab === "settings" && (
              <SettingsContent userEmail={user?.email || ""} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileContent({
  user,
}: {
  user: { user_id: string; email: string; name: string } | null;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">
          Profile
          <span className="ml-2 inline-block rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 text-xs font-medium text-zinc-400">
            Free
          </span>
        </h2>
        <p className="mt-2 text-sm text-zinc-500">
          Your account details and personal information.
        </p>
      </div>

      <div className="space-y-4 pt-2">
        <div>
          <label className="block text-xs font-medium text-zinc-500 mb-1">
            Name
          </label>
          <p className="text-sm text-zinc-200">{user?.name || "User"}</p>
        </div>
        <div className="border-t border-zinc-800/60 pt-4">
          <label className="block text-xs font-medium text-zinc-500 mb-1">
            Email
          </label>
          <p className="text-sm text-zinc-200">{user?.email || ""}</p>
        </div>
      </div>
    </div>
  );
}

function SettingsContent({ userEmail }: { userEmail: string }) {
  const [loading, setLoading] = useState(false);

  const handleSendReset = async () => {
    if (!userEmail) {
      toast.error("No email associated with this account.");
      return;
    }
    setLoading(true);
    try {
      await forgotPassword(userEmail);
      toast.success("Password reset link sent to your email.");
    } catch {
      // error toast handled by http layer
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Settings</h2>
        <p className="mt-2 text-sm text-zinc-500">
          Manage your account settings.
        </p>
      </div>

      <div className="pt-2">
        <label className="block text-xs font-medium text-zinc-500 mb-1.5">
          Reset password
        </label>
        <p className="text-sm text-zinc-500 mb-3">
          We'll send a password reset link to{" "}
          <span className="text-zinc-300">{userEmail}</span>.
        </p>
        <button
          type="button"
          onClick={handleSendReset}
          disabled={loading}
          className="av-btn-primary h-[28px] w-fit px-3 text-xs"
        >
          {loading ? "Sending…" : "Send reset link"}
        </button>
      </div>

      <div className="border-t border-zinc-800/60 pt-6 mt-8">
        <h3 className="text-sm font-medium text-red-400 mb-3">Danger zone</h3>
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-400">
            Permanently delete your account and all data
          </p>
          <button
            type="button"
            disabled
            className="rounded-md border border-red-800/70 bg-red-950/40 px-3 py-1.5 text-xs font-medium text-red-400 opacity-50 cursor-not-allowed"
          >
            Delete account
          </button>
        </div>
      </div>
    </div>
  );
}
