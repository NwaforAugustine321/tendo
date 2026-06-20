import { useState } from 'react'
import { ArrowRight, Circle, CheckCircle2 } from 'lucide-react'

type RadioOption = {
  id: string
  name: string
  label: string
  description?: string
}

type RadioField = {
  type: 'radio'
  options: RadioOption[]
}

type TextField = {
  type: 'text'
  name: string
  placeholder?: string
  description?: string
  label?: string
}

type Field = RadioField | TextField

type Props = {
  fields: Field[]
  onSubmit: (value: string) => void
  disabled?: boolean
}

export function InputCard({ fields, onSubmit, disabled = false }: Props) {
  const [selected, setSelected] = useState<string>('')
  const [textValue, setTextValue] = useState('')

  const normalizedFields = fields || []

  const handleContinue = () => {
    if (disabled) return
    // For radio: submit selected option
    if (selected) {
      onSubmit(selected)
      return
    }
    // For text: submit text value
    const trimmed = textValue.trim()
    if (trimmed) {
      onSubmit(trimmed)
      setTextValue('')
    }
  }

  const hasSelection = selected || textValue.trim()

  return (
    <div className="max-w-xs space-y-2">
      {normalizedFields.map((field, idx) => {
        if (field.type === 'radio' && 'options' in field && field.options) {
          return (
            <div key={idx} className="space-y-1">
              {field.options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => setSelected(opt.id)}
                  className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all ${
                    selected === opt.id
                      ? 'bg-orange-900/30'
                      : 'hover:bg-zinc-800/30'
                  } disabled:pointer-events-none`}
                >
                  <span className="mt-0.5 flex-shrink-0">
                    {selected === opt.id ? (
                      <CheckCircle2 size={16} className="text-orange-500" />
                    ) : (
                      <Circle size={16} className="text-zinc-400" />
                    )}
                  </span>
                  <span className="flex flex-col">
                    <span className={`text-sm ${selected === opt.id ? 'text-orange-400' : 'text-zinc-300'}`}>
                      {opt.label}
                    </span>
                    {opt.description && (
                      <span className="text-xs text-zinc-400">{opt.description}</span>
                    )}
                  </span>
                </button>
              ))}
            </div>
          )
        }

        if (field.type === 'text') {
          return (
            <div key={idx}>
              {(field.description || (field as any).label) && (
                <p className="mb-1.5 text-sm text-zinc-200">{field.description || (field as any).label}</p>
              )}
              {disabled ? (
                <input
                  type="text"
                  disabled
                  placeholder="••••••"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none pointer-events-none"
                />
              ) : (
                <textarea
                  value={textValue}
                  onChange={(e) => setTextValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleContinue())}
                  placeholder={field.placeholder || 'Type here...'}
                  rows={3}
                  className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-500"
                />
              )}
            </div>
          )
        }

        return null
      })}

      {!disabled && (
        <button
          type="button"
          onClick={handleContinue}
          disabled={!hasSelection}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Continue
          <ArrowRight size={12} />
        </button>
      )}
    </div>
  )
}
