"use client";
import { useState, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useSportConfig } from "@/lib/useSportConfig";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sport = useSportConfig();
  const next = searchParams.get("next") || "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (res.ok) {
        router.push(next);
        router.refresh();
      } else {
        const data = await res.json();
        setError(data.error || "Login failed");
      }
    } catch {
      setError("Network error — please try again");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-brand-dark flex items-center justify-center p-4"
      style={{backgroundImage: "radial-gradient(ellipse 120% 60% at 50% 0%, rgba(13,74,37,0.25) 0%, transparent 70%)"}}>
      <div className="w-full max-w-sm">
        {/* Logo / brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-3">
            <span className="text-5xl drop-shadow-lg">{sport.emoji}</span>
            <div>
              <div className="font-display font-bold text-brand-gold text-3xl leading-none tracking-wide uppercase">
                Sports-IQ
              </div>
              <div className="text-[10px] text-white/40 uppercase tracking-widest mt-0.5">
                {sport.headerSubtitle}
              </div>
            </div>
          </div>
          <p className="text-white/40 text-sm mt-3">Sign in to access the demo</p>
        </div>

        {/* Card */}
        <div className="bg-brand-navy border border-brand-steel/50 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-1.5">
                Username
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={loading}
                className="w-full bg-brand-dark border border-brand-steel/60 rounded-lg px-4 py-2.5 text-white text-sm
                           placeholder:text-white/20 focus:outline-none focus:border-brand-gold/60 focus:ring-1
                           focus:ring-brand-gold/40 transition disabled:opacity-50"
                placeholder="admin"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-white/50 uppercase tracking-widest mb-1.5">
                Password
              </label>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="w-full bg-brand-dark border border-brand-steel/60 rounded-lg px-4 py-2.5 text-white text-sm
                           placeholder:text-white/20 focus:outline-none focus:border-brand-gold/60 focus:ring-1
                           focus:ring-brand-gold/40 transition disabled:opacity-50"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/40 rounded-lg px-3 py-2">
                <span className="text-red-400 text-sm">⚠</span>
                <span className="text-red-300 text-sm">{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full bg-brand-gold hover:bg-brand-gold/90 disabled:bg-brand-gold/30 disabled:cursor-not-allowed
                         text-brand-dark font-display font-bold uppercase tracking-widest text-sm
                         rounded-lg px-4 py-3 transition-all duration-150 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-brand-dark/30 border-t-brand-dark rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-white/20 text-xs mt-6 uppercase tracking-widest">
          Restricted access · Authorised personnel only
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
