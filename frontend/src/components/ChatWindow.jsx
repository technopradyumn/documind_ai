import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import ThinkingSteps from './ThinkingSteps'
import VoiceButton from './VoiceButton'
import { sendChat, uploadDocument, getJobStatus } from '../api/client'

export default function ChatWindow({ collection, userId, addToast, onUploadClick }) {
  const [messages, setMessages] = useState([])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const [model, setModel]     = useState('gemini') // Default model
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const models = [
    { id: 'gemini',   name: 'Gemini 3.1 Flash Lite', icon: '✦' },
    { id: 'openai',   name: 'GPT-4o',              icon: '🤖' },
    { id: 'deepseek', name: 'DeepSeek Chat',        icon: '🐋' },
  ]

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const suggestions = [
    'Summarize the uploaded document',
    'What are the key findings?',
    'Explain the main concepts',
  ]

  const send = async (msg) => {
    const text = (msg || input).trim()
    if (!text || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text, ts: new Date() }])
    setLoading(true)
    try {
      const { data } = await sendChat({
        message: text,
        user_id: userId,
        session_id: collection,
        collection,
        model, // Send the selected model
      })
      setMessages(prev => [...prev, {
        role: 'ai',
        content: data.message,
        steps: data.steps,
        ts: new Date(),
      }])
    } catch (e) {
      addToast('Chat error: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setLoading(false)
    }
  }

  const inputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  const [sessionDocs, setSessionDocs] = useState([])

  const fetchSessionDocs = async () => {
    try {
      const { listDocuments } = await import('../api/client')
      const { data } = await listDocuments(collection)
      setSessionDocs(data.documents || [])
    } catch (e) { /* silent */ }
  }

  useEffect(() => {
    fetchSessionDocs()
  }, [collection])

  const handleDeleteDoc = async (filename) => {
    if (!window.confirm(`Remove "${filename}" from this session?`)) return
    try {
      const { deleteDocument } = await import('../api/client')
      await deleteDocument(filename, collection)
      setSessionDocs(prev => prev.filter(d => d !== filename))
      addToast(`🗑️ "${filename}" removed.`, 'success')
    } catch (e) {
      addToast('Failed to remove document.', 'error')
    }
  }

  const pollJob = (jobId, name) => {
    let attempts = 0
    const iv = setInterval(async () => {
      attempts++
      if (attempts > 120) {
        clearInterval(iv)
        addToast(`⚠️ Indexing "${name}" is taking too long.`, 'info')
        return
      }
      try {
        const { data } = await getJobStatus(jobId)
        if (data.status === 'finished') {
          clearInterval(iv)
          addToast(`✅ "${name}" indexed successfully!`, 'success')
          fetchSessionDocs() // Refresh list
        } else if (data.status === 'failed') {
          clearInterval(iv)
          addToast(`❌ Indexing failed for "${name}": ${data.error || 'Unknown error'}`, 'error')
        }
      } catch (e) { /* silent */ }
    }, 2500)
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      addToast('Only PDF files are supported.', 'error')
      return
    }

    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    form.append('collection', collection)
    form.append('user_id', userId)

    try {
      const { data } = await uploadDocument(form)
      if (data.job_id === 'sync-done') {
        addToast(`✅ "${file.name}" indexed!`, 'success')
        fetchSessionDocs()
      } else {
        addToast(`📄 "${file.name}" uploaded. Indexing…`, 'success')
        pollJob(data.job_id, file.name)
      }
    } catch (err) {
      addToast(`Upload failed: ${err.response?.data?.detail || err.message}`, 'error')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const handleVoiceTranscript = (transcript) => {
    setInput(transcript)
    send(transcript)
  }

  const fmt = (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <>
      <div className="chat-area">
        {/* Session Document Header */}
        {sessionDocs.length > 0 && (
          <div className="session-docs-bar">
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>SESSION CONTENT:</span>
            {sessionDocs.map(doc => (
              <div key={doc} className="session-doc-tag">
                <span>{doc.split('_').slice(1).join('_') || doc}</span>
                <button onClick={() => handleDeleteDoc(doc)}>✕</button>
              </div>
            ))}
          </div>
        )}

        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <h2>DocuMind AI is ready</h2>
            <p>Select a model and start chatting. If you have documents, upload them to chat about their content.</p>
            <div className="suggestion-chips">
              {suggestions.map(s => (
                <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              <div className={`msg-avatar ${m.role}`}>
                {m.role === 'ai' ? '✦' : '👤'}
              </div>
              <div className="msg-body">
                <div className="msg-bubble">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
                {m.steps && <ThinkingSteps steps={m.steps} />}
                <span className="msg-time">{fmt(m.ts)}</span>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="message ai">
            <div className="msg-avatar ai">✦</div>
            <div className="typing-indicator">
              <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-bar">
        <div className="model-selector-row">
          <select 
            className="model-select" 
            value={model} 
            onChange={(e) => setModel(e.target.value)}
          >
            {models.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
        
        <div className="input-row">
          <input 
            type="file" 
            ref={inputRef} 
            style={{ display: 'none' }} 
            accept=".pdf" 
            onChange={handleFileUpload} 
          />
          <button 
            className={`btn-icon btn-upload-quick ${uploading ? 'uploading' : ''}`} 
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            title="Upload Document"
          >
            {uploading ? '⏳' : '📂'}
          </button>
          <textarea
            ref={textareaRef}
            className="input-field"
            placeholder="Ask anything..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            rows={1}
          />
          <VoiceButton onTranscript={handleVoiceTranscript} addToast={addToast} />
          <button
            className="btn-icon btn-send"
            onClick={() => send()}
            disabled={!input.trim() || loading}
            title="Send message"
          >
            ➤
          </button>
        </div>
      </div>
    </>
  )
}
