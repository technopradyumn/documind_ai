import { useState } from 'react'

export default function ThinkingSteps({ steps }) {
  const [open, setOpen] = useState(false)
  if (!steps || steps.length === 0) return null

  const toolSteps = steps.filter(s => s.step === 'TOOL')

  return (
    <div className="thinking-steps">
      <div className="thinking-header" onClick={() => setOpen(!open)}>
        <span>{open ? '▾' : '▸'}</span>
        <span>🧠 Reasoning steps ({steps.length})</span>
        {toolSteps.length > 0 && (
          <span style={{ marginLeft: 'auto', opacity: 0.7 }}>
            {toolSteps.map(s => s.tool).join(', ')}
          </span>
        )}
      </div>
      {open && (
        <div className="thinking-body">
          {steps.map((s, i) => (
            <div key={i} className="step-item">
              <span className={`step-badge ${s.step}`}>{s.step}</span>
              <div className="step-content">
                {s.tool && <div className="step-tool">🔧 {s.tool}({(s.input || '').slice(0, 80)})</div>}
                {s.content && <div>{s.content}</div>}
                {s.result && (
                  <div style={{ marginTop: 4, opacity: 0.7, fontSize: '0.73rem' }}>
                    ↳ {s.result.slice(0, 200)}{s.result.length > 200 ? '…' : ''}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
