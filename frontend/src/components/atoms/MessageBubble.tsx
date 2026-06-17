import clsx from 'clsx'
import { BotAvatar } from './BotAvatar'
import { UserAvatar } from './UserAvatar'

type Props = {
  role: 'user' | 'assistant'
  content: string
}

export function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user'
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className={clsx('flex gap-2', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      {!isUser ? <BotAvatar size={28} /> : <UserAvatar size={28} />}

      {/* Bubble with tail */}
      <div className="relative max-w-[80%]">
        {/* Tail */}
        <div
          className={clsx(
            'absolute top-2 h-3 w-3 rotate-45',
            isUser
              ? '-right-1.5 bg-[#1a2e1a]'
              : '-left-1.5 border border-zinc-800/90 bg-[#141414]'
          )}
        />

        {/* Message body */}
        <div
          className={clsx(
            'relative rounded-lg px-3 py-2 text-sm leading-relaxed',
            isUser
              ? 'bg-[#1a2e1a] text-zinc-100'
              : 'border border-zinc-800/90 bg-[#141414] text-zinc-200'
          )}
        >
          {content.split('\n').map((line, i) => (
            <p key={i} className={i > 0 ? 'mt-1' : ''}>
              {line}
            </p>
          ))}

          {/* Timestamp */}
          <span className={clsx(
            'mt-1 block text-right text-[10px]',
            isUser ? 'text-zinc-500' : 'text-zinc-600'
          )}>
            {time}
          </span>
        </div>
      </div>
    </div>
  )
}
