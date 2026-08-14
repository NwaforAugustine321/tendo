import { useState, useMemo } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { AuthCard, authInputClass } from "./AuthCard";
import { resetPassword } from "../../lib/services/auth";

export function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const accessToken = useMemo(() => {
    const fromQuery = searchParams.get("access_token");
    if (fromQuery) return fromQuery;
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    return params.get("access_token") || "";
  }, [searchParams]);

  const handleSave = async () => {
    if (!password || !confirmPassword) {
      toast.error("Both fields are required.");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (!accessToken) {
      toast.error("Invalid or missing reset token.");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(accessToken, password);
      toast.success("Password updated successfully.");
      navigate("/login");
    } catch {
      // error toast handled by http layer
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthCard
      title="Reset password"
      subtitle="Enter your new password below."
      footer={
        <p>
          Remember your password?{" "}
          <Link to="/login" className="text-[#3ecf8e] hover:underline">
            Log in
          </Link>
        </p>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          handleSave();
        }}
      >
        <label className="block text-[11px] font-medium text-zinc-400">
          New password
          <input
            className={authInputClass}
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>
        <label className="block text-[11px] font-medium text-zinc-400">
          Confirm password
          <input
            className={authInputClass}
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        <div className="pt-2">
          <button
            type="submit"
            disabled={!password || !confirmPassword || loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0] disabled:opacity-50"
          >
            {loading ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </AuthCard>
  );
}
