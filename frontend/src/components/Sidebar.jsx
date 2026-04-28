import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'

export default function Sidebar({ collection, setCollection, userId }) {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    getHealth()
      .then(r => setHealth(r.data))
      .catch(() => setHealth(null))
  }, [])

  const svc = health?.services || {}
  const dot = (ok) => <span className={`status-dot ${ok ? 'ok' : 'err'}`} />

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">✦</div>
          <div>
            <div className="logo-text">DocuMind AI</div>
          </div>
        </div>
        <div className="logo-sub">Agentic Document Intelligence</div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Active Collection</p>
        <select
          className="select"
          value={collection}
          onChange={e => setCollection(e.target.value)}
        >
          <option value="documind">documind (default)</option>
          <option value="research">research</option>
          <option value="reports">reports</option>
          <option value="legal">legal</option>
        </select>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">User Session</p>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {userId}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
          Memory is persisted across sessions
        </div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Infrastructure</p>
        <div className="status-grid">
          <div className="status-item">{dot(!!health)}  <span>API Backend</span></div>
          <div className="status-item">{dot(!!svc.qdrant)} <span>Qdrant (Vector DB)</span></div>
          <div className="status-item">{dot(!!svc.mongodb)} <span>MongoDB (Memory)</span></div>
          <div className="status-item">{dot(!!svc.redis)}  <span>Redis (Job Queue)</span></div>
          <div className="status-item">
            {dot(svc.voice?.stt)} <span>Voice STT</span>
          </div>
          <div className="status-item">
            {dot(svc.voice?.tts)} <span>Voice TTS</span>
          </div>
        </div>
      </div>

      <div className="sidebar-section" style={{ marginTop: 'auto' }}>
        <p className="sidebar-label">Tech Stack</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {['FastAPI', 'LangGraph', 'Qdrant', 'mem0', 'ReAct', 'Redis RQ', 'Gemini'].map(t => (
            <span key={t} style={{
              background: 'var(--bg-glass)',
              border: '1px solid var(--border)',
              borderRadius: '99px',
              padding: '2px 8px',
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
            }}>{t}</span>
          ))}
        </div>
      </div>
    </aside>
  )
}
