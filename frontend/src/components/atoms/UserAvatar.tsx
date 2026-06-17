/**
 * User profile avatar — simple circle with initials or generic user icon.
 */
export function UserAvatar({ size = 32 }: { size?: number }) {
  return (
    <div
      className="shrink-0 rounded-full border border-zinc-700 bg-zinc-800 flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24" fill="none">
        <path
          d="M12 12a3.5 3.5 0 1 0-3.5-3.5A3.5 3.5 0 0 0 12 12Z"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-zinc-400"
        />
        <path
          d="M5.5 20.5c.8-3.2 3.5-5.5 6.5-5.5s5.7 2.3 6.5 5.5"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          className="text-zinc-400"
        />
      </svg>
    </div>
  )
}
