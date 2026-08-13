import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { AuthCard, authInputClass } from "./AuthCard";

export function ResetPassword() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleSave = () => {
    setError("");
    if (!password || !confirmPassword) {
      setError("Both fields are required.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    // TODO: call reset password API with token from URL
    navigate("/login");
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

        {error && <p className="text-xs text-red-400">{error}</p>}

        <div className="pt-2">
          <button
            type="submit"
            disabled={!password || !confirmPassword}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0] disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </form>
    </AuthCard>
  );
}
