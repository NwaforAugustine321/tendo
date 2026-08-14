import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { authInputClass } from "./AuthCard";
import { forgotPassword } from "../../lib/services/auth";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
      toast.success("Reset link sent! Check your inbox.");
    } catch {
      // error toast handled by http layer
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
            <span className="flex items-center gap-[3px]">
              <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
              <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
            </span>
          </div>
          <span className="text-[13px] font-semibold text-zinc-200">Tendo</span>
        </div>

        <p className="font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-400">
          Account
        </p>
        <h1 className="mt-3 font-sans text-2xl font-semibold tracking-tight text-white">
          Forgot password
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-zinc-400">
          Enter your email and we'll send you a link to reset your password.
        </p>

        <div className="mt-8">
          {sent ? (
            <div className="space-y-4">
              <p className="text-sm text-[#3ecf8e]">
                Reset link sent! Check your inbox.
              </p>
              <Link
                to="/login"
                className="inline-block text-sm font-medium text-zinc-400 transition-colors hover:text-zinc-200"
              >
                ← Back to login
              </Link>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSend}>
              <label className="block text-[11px] font-medium text-zinc-400">
                Email
                <input
                  className={authInputClass}
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </label>
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={!email || loading}
                  className="flex w-full items-center justify-center gap-2 rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0] disabled:opacity-50"
                >
                  {loading ? "Sending…" : "Send reset link"}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="mt-8 border-t border-zinc-800/60 pt-6 text-center text-sm text-zinc-400">
          <p>
            Remember your password?{" "}
            <Link to="/login" className="text-[#3ecf8e] hover:underline">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
