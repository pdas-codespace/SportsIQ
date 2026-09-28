"use client";
import { useEffect, useRef, useState } from "react";

const STORAGE_KEY = "sportsiq_demo_email";

interface Props {
  email: string;
  onChange: (email: string) => void;
}

export function DemoSettings({ email, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(email);
  const [panelPos, setPanelPos] = useState<{ top: number; right: number }>({ top: 0, right: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { setDraft(email); }, [email]);

  useEffect(() => {
    if (open) {
      // Calculate fixed position from the button rect to escape overflow:hidden parents
      if (btnRef.current) {
        const r = btnRef.current.getBoundingClientRect();
        setPanelPos({
          top: r.bottom + 8,
          right: window.innerWidth - r.right,
        });
      }
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  function handleSave() {
    const trimmed = draft.trim();
    onChange(trimmed);
    if (trimmed) localStorage.setItem(STORAGE_KEY, trimmed);
    else localStorage.removeItem(STORAGE_KEY);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") { setDraft(email); setOpen(false); }
  }

  return (
    <div className="relative">
      {/* Gear button */}
      <button
        ref={btnRef}
        onClick={() => setOpen((v) => !v)}
        title="Demo settings"
        className={`flex items-center gap-1.5 px-2 py-1 rounded border text-xs transition-all ${
          open
            ? "border-brand-gold/50 text-brand-gold bg-brand-gold/10"
            : "border-white/10 text-brand-chalk/40 hover:border-white/30 hover:text-brand-chalk/70"
        }`}
      >
        <span className="text-sm leading-none">⚙</span>
        <span className="uppercase tracking-widest font-display hidden sm:inline">Demo</span>
      </button>

      {/* Fixed-position panel — escapes overflow:hidden on the header */}
      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => { setDraft(email); setOpen(false); }}
          />

          <div
            className="fixed z-50 w-80 rounded-xl border border-white/15 shadow-2xl overflow-hidden"
            style={{
              top: panelPos.top,
              right: panelPos.right,
              background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)",
            }}
          >
            <div className="h-0.5 bg-gradient-to-r from-brand-field via-brand-gold to-brand-field" />

            <div className="px-4 pt-4 pb-5">
              <div className="text-[9px] font-display font-semibold tracking-widest text-brand-gold/60 uppercase mb-3">
                ⚙ Demo Settings
              </div>

              <label className="block mb-1 text-[10px] text-brand-chalk/50 font-display uppercase tracking-widest">
                Offer delivery email
              </label>
              <input
                ref={inputRef}
                type="email"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="your@email.com"
                className="w-full rounded-lg px-3 py-2 text-sm text-brand-chalk placeholder-brand-chalk/25
                           focus:outline-none focus:ring-1 focus:ring-brand-gold/50 transition-all"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)" }}
              />
              <p className="mt-1.5 text-[10px] text-brand-chalk/30 leading-relaxed">
                Approved offers will be sent to this address. Overrides the server default for this session.
              </p>

              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleSave}
                  className="flex-1 py-2 rounded-lg bg-brand-gold/15 border border-brand-gold/50 text-brand-gold
                             text-xs font-display font-semibold uppercase tracking-wider
                             hover:bg-brand-gold/25 transition-all active:scale-[0.98]"
                >
                  Save
                </button>
                <button
                  onClick={() => { setDraft(email); setOpen(false); }}
                  className="flex-1 py-2 rounded-lg bg-white/3 border border-white/10 text-brand-chalk/40
                             text-xs font-display font-semibold uppercase tracking-wider
                             hover:text-brand-chalk/70 transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/** Read the persisted demo email from localStorage (call on client only). */
export function getStoredDemoEmail(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEY) ?? "";
}
