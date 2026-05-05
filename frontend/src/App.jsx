import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import DocumentPanel from './components/DocumentPanel'

const getUserId = () => {
  let id = localStorage.getItem('documind_user_id')
  if (!id) {
    id = `user_${Math.random().toString(36).slice(2, 9)}`
    localStorage.setItem('documind_user_id', id)
  }
  return id
}
const USER_ID = getUserId()

const genSessionId = () => `chat_${Math.random().toString(36).slice(2, 9)}`

function Toast({ msg, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [])
  return <div className={`toast ${type}`} onClick={onClose}>{msg}</div>
}

export default function App() {
  const [tab, setTab]             = useState('chat')
  const [collection, setCollection] = useState(genSessionId())
  const [toasts, setToasts]       = useState([])
  const [sessions, setSessions]   = useState([])

  const fetchSessions = async () => {
    try {
      const { getSessions } = await import('./api/client')
      const { data } = await getSessions(USER_ID)
      setSessions(data.sessions || [])
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    fetchSessions()
  }, [])

  const addToast = (msg, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, msg, type }])
  }
  const removeToast = (id) => setToasts(prev => prev.filter(t => t.id !== id))

  const handleNewChat = () => {
    setCollection(genSessionId())
    setTab('chat')
  }

  const handleSwitchSession = (sid) => {
    setCollection(sid)
    setTab('chat')
  }

  const handleClearChat = async () => {
    if (!window.confirm('Clear all messages and delete uploaded documents for this session?')) return
    try {
      const { clearCollection, deleteSession } = await import('./api/client')
      await clearCollection(collection)
      await deleteSession(collection)
      addToast('Session cleared and documents deleted.', 'success')
      fetchSessions()
      handleNewChat()
    } catch (e) {
      addToast('Failed to clear session.', 'error')
    }
  }

  return (
    <div className="app">
      <Sidebar 
        collection={collection} 
        userId={USER_ID} 
        sessions={sessions}
        onNewChat={handleNewChat}
        onSwitchSession={handleSwitchSession}
        onClearChat={handleClearChat}
      />

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
          <ChatWindow collection={collection} userId={USER_ID} addToast={addToast} onUploadClick={() => setTab('docs')} />
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
