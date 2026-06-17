import clsx from 'clsx'

type Props = {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes = {
  sm: 'h-4 w-4 border-[2px]',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
}

export function Spinner({ size = 'md', className }: Props) {
  return (
    <div className={clsx('animate-spin rounded-full border-zinc-700 border-t-[#3ecf8e]', sizes[size], className)} />
  )
}
