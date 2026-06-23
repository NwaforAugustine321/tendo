import { useState } from 'react'
import { ArrowRight, Circle, CheckCircle2 } from 'lucide-react'

type Field = {
  id?: string
  name: string
  label?: string
  placeholder?: string
  description?: string
}

type Props = {
  fields: Field[]
  onSubmit: (value: string) => void
  disabled?: boolean
}

export function InputCard({ fields, onSubmit, disabled = false }: Props) {
  const [selectedRadio, setSelectedRadio] = useState<Record<string, string>>({})
  const [textValues, setTextValues] = useState<Record<string, string>>({})
  const [otherValues, setOtherValues] = useState<Record<string, string>>({})

  if (!fields || fields.length === 0) return null

  // Determine field type by structure:
  // Has id + label + shared name → radio/choice group
  // Has placeholder → text input
  const isChoice = (f: Field) => !!f.id && !!f.label
  const isText = (f: Field) => !!f.placeholder && !f.id

  // Group choice fields by name
  const choiceGroups: Record<string, Field[]> = {}
  const textFields: Field[] = []

  for (const field of fields) {
    if (isChoice(field)) {
      const groupName = field.name || '_choice'
      if (!choiceGroups[groupName]) choiceGroups[groupName] = []
      choiceGroups[groupName].push(field)
    } else if (isText(field)) {
      textFields.push(field)
    } else {
      // Fallback: treat as text
      textFields.push(field)
    }
  }

  const handleContinue = () => {
    if (disabled) return

    const responses: Array<{name: string; label?: string; description?: string; answer: string}> = []

    // Collect radio selections
    for (const [groupName, selected] of Object.entries(selectedRadio)) {
      if (selected === '__other__') {
        const otherText = otherValues[groupName]?.trim()
        if (otherText) {
          responses.push({ name: groupName, answer: otherText })
        }
      } else if (selected) {
        // Find the matching option to get its label/description
        const group = choiceGroups[groupName] || []
        const option = group.find((f) => f.id === selected)
        responses.push({
          name: groupName,
          label: option?.label || selected,
          description: option?.description,
          answer: option?.label || selected,
        })
      }
    }

    // Collect text values — send plain text only
    for (const field of textFields) {
      const val = textValues[field.name]?.trim()
      if (val) {
        responses.push({
          name: field.name,
          answer: val,
        })
      }
    }

    if (responses.length > 0) {
      // If only one plain text response, send just the text (cleaner display)
      if (responses.length === 1 && !responses[0].label) {
        onSubmit(responses[0].answer)
      } else {
        // Multiple fields or option selections — send as JSON for backend formatting
        onSubmit(JSON.stringify(responses))
      }
      setTextValues({})
      setSelectedRadio({})
      setOtherValues({})
    }
  }

  const hasValue = Object.values(selectedRadio).some((v) => {
    if (v === '__other__') return !!Object.values(otherValues).some((o) => o.trim())
    return !!v
  }) || Object.values(textValues).some((v) => v.trim())

  return (
    <div className="max-w-xs space-y-2">
      {/* Choice groups */}
      {Object.entries(choiceGroups).map(([groupName, options]) => {
        const currentSelected = selectedRadio[groupName] || ''

        return (
          <div key={groupName} className="space-y-1">
            {options.map((opt) => (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => setSelectedRadio((prev) => ({ ...prev, [groupName]: opt.id! }))}
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
            {/* Other option */}
            {!disabled && (
              <div className="space-y-1">
                <button
                  type="button"
                  onClick={() => setSelectedRadio((prev) => ({ ...prev, [groupName]: '__other__' }))}
                  className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all ${
                    currentSelected === '__other__' ? 'bg-orange-900/30' : 'hover:bg-zinc-800/30'
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
                {currentSelected === '__other__' && (
                  <textarea
                    value={otherValues[groupName] || ''}
                    onChange={(e) => {
                      setOtherValues((prev) => ({ ...prev, [groupName]: e.target.value }))
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleContinue())}
                    placeholder="Type your answer..."
                    rows={2}
                    className="ml-7 w-[calc(100%-1.75rem)] resize-none rounded-lg border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-500"
                  />
                )}
              </div>
            )}
          </div>
        )
      })}

      {/* Text fields */}
      {textFields.map((field, idx) => (
        <div key={`${field.name}-${idx}`}>
          {field.description && (
            <p className="mb-1.5 text-sm text-zinc-200">{field.description}</p>
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
              value={textValues[field.name] || ''}
              onChange={(e) => setTextValues((prev) => ({ ...prev, [field.name]: e.target.value }))}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleContinue())}
              placeholder={field.placeholder || 'Type here...'}
              rows={2}
              className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-500"
            />
          )}
        </div>
      ))}

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
