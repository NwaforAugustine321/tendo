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
  name?: string
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
  const [selectedRadio, setSelectedRadio] = useState<Record<string, string>>({})
  const [textValues, setTextValues] = useState<Record<string, string>>({})
  const [otherValues, setOtherValues] = useState<Record<string, string>>({})

  const isFlatOption = (f: any): boolean =>
    f && typeof f === 'object' && 'id' in f && 'label' in f && !('type' in f)

  const normalizedFields = (() => {
    const raw = fields || []
    // Check if all fields are flat options (id + label, no type)
    const allFlat = raw.length > 0 && raw.every((f: any) => isFlatOption(f))
    if (allFlat) {
      // Group them into a single radio field
      const name = (raw[0] as any).name || 'choice'
      return [{
        type: 'radio' as const,
        name,
        options: raw.map((f: any) => ({ id: f.id, name: f.name || name, label: f.label, description: f.description })),
      }]
    }
    return raw
  })()

  // Separate flat options from typed fields
  const flatOptions: RadioOption[] = []
  const typedFields: Field[] = []
  for (const field of normalizedFields) {
    if (field.type === 'radio' && 'options' in field) {
      typedFields.push(field as RadioField)
    } else if (field.type === 'text') {
      typedFields.push(field as TextField)
    }
  }

  const flatSelected = selectedRadio['_flat'] || ''

  const handleContinue = () => {
    if (disabled) return

    // Collect all values
    const parts: string[] = []

    for (const field of normalizedFields) {
      if (field.type === 'radio' && 'options' in field) {
        const fieldName = field.name || field.options?.[0]?.name || 'radio'
        const val = selectedRadio[fieldName]
        if (val === '__other__') {
          const otherText = otherValues[fieldName]?.trim()
          if (otherText) parts.push(otherText)
        } else if (val) {
          parts.push(val)
        }
      }
      if (field.type === 'text') {
        const val = textValues[field.name]?.trim()
        if (val) parts.push(val)
      }
    }

    if (parts.length > 0) {
      onSubmit(parts.join(', '))
      setTextValues({})
      setSelectedRadio({})
      setOtherValues({})
    }
  }

  const hasValue = Object.entries(selectedRadio).some(([key, val]) => {
    if (val === '__other__') return !!otherValues[key]?.trim()
    return !!val
  }) || Object.values(textValues).some((v) => v.trim())

  return (
    <div className="max-w-xs space-y-2">
      {/* Flat options (id + label format) */}
      {flatOptions.length > 0 && (
        <div className="space-y-1">
          {flatOptions.map((opt) => (
            <button
              key={opt.id}
              type="button"
              disabled={disabled}
              onClick={() => setSelectedRadio((prev) => ({ ...prev, ['_flat']: opt.id }))}
              className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all ${
                flatSelected === opt.id
                  ? 'bg-orange-900/30'
                  : 'hover:bg-zinc-800/30'
              } disabled:pointer-events-none`}
            >
              <span className="mt-0.5 flex-shrink-0">
                {flatSelected === opt.id ? (
                  <CheckCircle2 size={16} className="text-orange-500" />
                ) : (
                  <Circle size={16} className="text-zinc-400" />
                )}
              </span>
              <span className="flex flex-col">
                <span className={`text-sm ${flatSelected === opt.id ? 'text-orange-400' : 'text-zinc-300'}`}>
                  {opt.label}
                </span>
                {opt.description && (
                  <span className="text-xs text-zinc-400">{opt.description}</span>
                )}
              </span>
            </button>
          ))}
          {/* Other option */}
          {!disabled && (
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => setSelectedRadio((prev) => ({ ...prev, ['_flat']: '__other__' }))}
                className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all ${
                  flatSelected === '__other__' ? 'bg-orange-900/30' : 'hover:bg-zinc-800/30'
                }`}
              >
                <span className="mt-0.5 flex-shrink-0">
                  {flatSelected === '__other__' ? (
                    <CheckCircle2 size={16} className="text-orange-500" />
                  ) : (
                    <Circle size={16} className="text-zinc-400" />
                  )}
                </span>
                <span className={`text-sm ${flatSelected === '__other__' ? 'text-orange-400' : 'text-zinc-300'}`}>
                  Other
                </span>
              </button>
              <textarea
                value={otherValues['_flat'] || ''}
                onChange={(e) => {
                  setOtherValues((prev) => ({ ...prev, ['_flat']: e.target.value }))
                  setSelectedRadio((prev) => ({ ...prev, ['_flat']: '__other__' }))
                }}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleContinue())}
                placeholder="Type your answer..."
                rows={2}
                className="ml-7 w-[calc(100%-1.75rem)] resize-none rounded-lg border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-500"
              />
            </div>
          )}
        </div>
      )}

      {/* Typed fields (radio with options array, text) */}
      {typedFields.map((field, idx) => {
        if (field.type === 'radio' && 'options' in field && field.options) {
          const fieldName = field.name || field.options?.[0]?.name || `radio-${idx}`
          const currentSelected = selectedRadio[fieldName] || ''

          return (
            <div key={idx} className="space-y-1">
              {field.options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => setSelectedRadio((prev) => ({ ...prev, [fieldName]: opt.id }))}
                  className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all ${
                    currentSelected === opt.id
                      ? 'bg-orange-900/30'
                      : 'hover:bg-zinc-800/30'
                  } disabled:pointer-events-none`}
                >
                  <span className="mt-0.5 flex-shrink-0">
                    {currentSelected === opt.id ? (
                      <CheckCircle2 size={16} className="text-orange-500" />
                    ) : (
                      <Circle size={16} className="text-zinc-400" />
                    )}
                  </span>
                  <span className="flex flex-col">
                    <span className={`text-sm ${currentSelected === opt.id ? 'text-orange-400' : 'text-zinc-300'}`}>
                      {opt.label}
                    </span>
                    {opt.description && (
                      <span className="text-xs text-zinc-400">{opt.description}</span>
                    )}
                  </span>
                </button>
              ))}
              {/* Other option with text input — always visible */}
              {!disabled && (
                <div className="space-y-1">
                  <button
                    type="button"
                    onClick={() => setSelectedRadio((prev) => ({ ...prev, [fieldName]: '__other__' }))}
                    className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all ${
                      currentSelected === '__other__'
                        ? 'bg-orange-900/30'
                        : 'hover:bg-zinc-800/30'
                    }`}
                  >
                    <span className="mt-0.5 flex-shrink-0">
                      {currentSelected === '__other__' ? (
                        <CheckCircle2 size={16} className="text-orange-500" />
                      ) : (
                        <Circle size={16} className="text-zinc-400" />
                      )}
                    </span>
                    <span className={`text-sm ${currentSelected === '__other__' ? 'text-orange-400' : 'text-zinc-300'}`}>
                      Other
                    </span>
                  </button>
                  <textarea
                    value={otherValues[fieldName] || ''}
                    onChange={(e) => {
                      setOtherValues((prev) => ({ ...prev, [fieldName]: e.target.value }))
                      setSelectedRadio((prev) => ({ ...prev, [fieldName]: '__other__' }))
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleContinue())}
                    placeholder="Type your answer..."
                    rows={2}
                    className="ml-7 w-[calc(100%-1.75rem)] resize-none rounded-lg border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-500"
                  />
                </div>
              )}
            </div>
          )
        }

        if (field.type === 'text') {
          const currentValue = textValues[field.name] || ''

          return (
            <div key={idx}>
              {(field.description || field.label) && (
                <p className="mb-1.5 text-sm text-zinc-200">{field.description || field.label}</p>
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
                  value={currentValue}
                  onChange={(e) => setTextValues((prev) => ({ ...prev, [field.name]: e.target.value }))}
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
          disabled={!hasValue}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Continue
          <ArrowRight size={12} />
        </button>
      )}
    </div>
  )
}
