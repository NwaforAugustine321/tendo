import { Link } from 'react-router-dom'

function IconVoice() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0 text-[#3ecf8e]">
      <path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4Z" stroke="currentColor" strokeWidth="1" />
      <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 19v4M8 23h8" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  )
}

function IconBrain() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0 text-[#3ecf8e]">
      <path d="M12 2a7 7 0 0 0-7 7c0 3 1.5 5 4 6.5V20h6v-4.5c2.5-1.5 4-3.5 4-6.5a7 7 0 0 0-7-7Z" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
      <path d="M9 20v2h6v-2" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  )
}

function IconShield() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0 text-[#3ecf8e]">
      <path d="M12 2l8 4v6c0 5.5-3.8 9.7-8 11-4.2-1.3-8-5.5-8-11V6l8-4Z" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
      <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function Landing() {
  return (
    <div className="landing-atmosphere min-h-screen">
      <div className="landing-atmosphere__fixed" aria-hidden>
        <div className="landing-atmosphere__nebula" />
        <div className="landing-atmosphere__stars" />
        <div className="landing-atmosphere__grain" />
      </div>

      <div className="landing-atmosphere__content">
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-white/[0.06]">
          <div className="landing-grid-overlay opacity-[0.55]" aria-hidden />
          <div className="relative mx-auto max-w-5xl px-4 pb-20 pt-16 sm:pb-24 sm:pt-20">
            {/* Nav */}
            <nav className="mb-16 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
                  <span className="flex items-center gap-[2px]">
                    <span className="h-[5px] w-[5px] rounded-full bg-purple-600" />
                    <span className="h-[5px] w-[5px] rounded-full bg-purple-600" />
                  </span>
                </div>
                <span className="text-[15px] font-semibold text-zinc-200">Tendo</span>
              </div>
              <div className="flex items-center gap-2">
                <Link to="/onboarding" className="rounded-md border border-zinc-700/90 bg-zinc-900/60 px-3 py-1.5 text-[13px] font-medium text-zinc-200 transition-colors hover:border-zinc-600 hover:text-white">
                  Sign in
                </Link>
                <Link to="/onboarding" className="rounded-md bg-[#3ecf8e] px-3 py-1.5 text-[13px] font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0]">
                  Get Started
                </Link>
              </div>
            </nav>

            <div className="max-w-3xl">
              <p className="font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">
                AI Business Operating System
              </p>
              <h1 className="mt-4 font-sans text-[1.875rem] font-semibold leading-[1.12] tracking-[-0.02em] text-white sm:text-4xl lg:text-[2.625rem]">
                Talk to your business. Tendo handles the rest.
              </h1>
              <p className="mt-5 max-w-2xl text-[15px] font-normal leading-relaxed text-zinc-500 sm:text-base">
                An AI employee that learns how your business operates. Record sales, manage inventory, track payments — through natural voice and text conversations.
              </p>
            </div>

            <div className="mt-8 flex flex-wrap gap-2">
              {['Voice & Text', 'Web & WhatsApp', 'No Setup Forms', 'Learns Over Time'].map((chip) => (
                <span key={chip} className="landing-chip inline-flex items-center px-3 py-1 text-[11px] font-normal text-zinc-500">
                  {chip}
                </span>
              ))}
            </div>

            <div className="mt-8 flex flex-wrap gap-2 sm:items-center">
              <Link to="/onboarding" className="inline-flex items-center justify-center rounded-lg bg-[#3ecf8e] px-5 py-2.5 text-sm font-semibold text-[#0a0a0a] shadow-sm shadow-[#3ecf8e]/25 transition hover:bg-[#5ee9b0]">
                Start Free
              </Link>
              <a href="#how-it-works" className="rounded-md border border-zinc-700/90 bg-zinc-900/60 px-4 py-2 text-sm font-medium text-zinc-200 transition-colors hover:border-zinc-600 hover:text-white">
                How It Works
              </a>
            </div>

            {/* Pillar cards */}
            <div className="mt-12 grid min-w-0 gap-4 border-t border-white/[0.06] pt-8 sm:mt-14 sm:grid-cols-3 sm:gap-5 sm:pt-9">
              {[
                { Icon: IconVoice, title: 'Voice-first operations', body: 'Speak naturally. "I sold 5 bags of rice to Musa" — Tendo records it instantly.' },
                { Icon: IconBrain, title: 'Learns your business', body: 'No forms or setup wizards. Tendo observes your operations and builds understanding over time.' },
                { Icon: IconShield, title: 'Nothing without approval', body: 'Every financial action needs your confirmation. Review, approve, or reject before anything changes.' },
              ].map((p) => (
                <div
                  key={p.title}
                  className="landing-glass min-w-0 w-full px-3 py-4 transition-[border-color,background-color] duration-300 sm:px-4"
                >
                  <p.Icon />
                  <p className="mt-2 text-sm font-medium leading-snug tracking-tight text-zinc-200 sm:text-[15px]">
                    {p.title}
                  </p>
                  <p className="mt-1.5 text-[13px] font-normal leading-snug text-zinc-500">{p.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Workflow */}
        <section id="how-it-works" className="landing-tech-surface relative scroll-mt-14 border-t border-white/[0.07]">
          <div className="landing-grid-overlay opacity-[0.35]" aria-hidden />
          <div className="relative mx-auto max-w-5xl px-4 py-16 sm:py-20">
            <p className="font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">How it works</p>
            <h2 className="mt-2 font-sans text-2xl font-semibold tracking-tight text-white sm:text-[1.65rem]">
              From conversation to business intelligence
            </h2>

            <div className="relative mt-10">
              <div className="absolute bottom-3 left-[15px] top-10 w-px bg-white/[0.1] sm:left-[19px]" aria-hidden />
              <ol className="relative list-none space-y-12 sm:space-y-14">
                {[
                  { kicker: 'Onboard', title: 'Tell Tendo about your business', body: 'Describe what you do in your own words. Tendo creates an initial understanding — no forms required.' },
                  { kicker: 'Operate', title: 'Record daily activities naturally', body: 'Say or type your business operations. Sales, payments, inventory — Tendo handles the bookkeeping.' },
                  { kicker: 'Evolve', title: 'The AI gets smarter every day', body: 'With each confirmed operation, Tendo deepens its understanding of how your specific business works.' },
                ].map((s, idx) => (
                  <li key={s.kicker} className="grid grid-cols-[2.5rem_1fr] gap-4 sm:grid-cols-[2.75rem_1fr] sm:gap-6">
                    <div className="flex justify-center pt-0.5">
                      <span className="landing-step-ring relative z-[1] flex h-8 w-8 shrink-0 items-center justify-center font-mono text-xs font-medium tabular-nums text-[#3ecf8e] sm:h-9 sm:w-9 sm:text-sm">
                        {idx + 1}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[#3ecf8e]">{s.kicker}</p>
                      <p className="mt-1 text-lg font-medium tracking-tight text-zinc-100">{s.title}</p>
                      <p className="mt-2 max-w-2xl text-sm font-normal leading-relaxed text-zinc-500 sm:text-[15px]">{s.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 px-4 py-10">
          <div className="mx-auto flex max-w-5xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white border border-zinc-900">
                <span className="flex items-center gap-[1.5px]">
                  <span className="h-[4px] w-[4px] rounded-full bg-purple-600" />
                  <span className="h-[4px] w-[4px] rounded-full bg-purple-600" />
                </span>
              </div>
              <span className="text-sm font-semibold text-zinc-200">Tendo</span>
            </div>
            <p className="text-xs font-normal text-zinc-600">© 2026 Tendo. Built for business owners who want to operate, not configure.</p>
          </div>
        </footer>
      </div>
    </div>
  )
}
