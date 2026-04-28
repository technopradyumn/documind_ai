import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import DocumentPanel from './components/DocumentPanel'

const USER_ID = `user_${Math.random().toString(36).slice(2, 9)}`

function Toast({ msg, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [])
  return <div className={`toast ${type}`} onClick={onClose}>{msg}</div>
}

export default function App() {
  const [tab, setTab]             = useState('chat')
  const [collection, setCollection] = useState('documind')
  const [toasts, setToasts]       = useState([])

  const addToast = (msg, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, msg, type }])
  }
  const removeToast = (id) => setToasts(prev => prev.filter(t => t.id !== id))

  return (
    <div className="app">
      <Sidebar collection={collection} setCollection={setCollection} userId={USER_ID} />

      <main className="main">
        {/* Top bar */}
        <div className="topbar">
          <div>
            <div className="topbar-title">
              {tab === 'chat' ? '💬 Chat with Documents' : '📂 Document Manager'}
            </div>
            <div className="topbar-sub">Collection: <b>{collection}</b></div>
          </div>
          <div className="tab-group">
            <button className={`tab-btn ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
              💬 Chat
            </button>
            <button className={`tab-btn ${tab === 'docs' ? 'active' : ''}`} onClick={() => setTab('docs')}>
              📂 Documents
            </button>
          </div>
        </div>

        {tab === 'chat' ? (
          <ChatWindow collection={collection} userId={USER_ID} addToast={addToast} />
        ) : (
          <DocumentPanel collection={collection} addToast={addToast} />
        )}
      </main>

      {/* Toasts */}
      <div className="toast-container">
        {toasts.map(t => (
          <Toast key={t.id} msg={t.msg} type={t.type} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </div>
  )
}
