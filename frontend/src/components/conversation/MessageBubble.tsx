import clsx from 'clsx'
import { BotAvatar } from './BotAvatar'
import { UserAvatar } from './UserAvatar'

type Props = {
  role: 'user' | 'assistant'
  content: string
}

export function MessageBubble({ role, content }: Props) {
  return (
    <div
      className={clsx('flex gap-2.5', role === 'user' ? 'flex-row-reverse' : 'flex-row')}
    >
      {/* Avatar */}
      {role === 'assistant' ? <BotAvatar size={28} /> : <UserAvatar size={28} />}

      {/* Bubble */}
      <div
        className={clsx(
          'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
          role === 'user'
            ? 'bg-zinc-800/60 text-zinc-100'
            : 'border border-zinc-800/90 bg-[#141414] text-zinc-200'
        )}
      >
        {content.split('\n').map((line, i) => (
          <p key={i} className={i > 0 ? 'mt-2' : ''}>
            {line}
          </p>
        ))}
      </div>
    </div>
  )
}
