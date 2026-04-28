import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import ThinkingSteps from './ThinkingSteps'
import VoiceButton from './VoiceButton'
import { sendChat } from '../api/client'

export default function ChatWindow({ collection, userId, addToast }) {
  const [messages, setMessages] = useState([])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const suggestions = [
    'Summarize the uploaded document',
    'What are the key findings?',
    'List all important dates mentioned',
    'Explain the main concepts in simple terms',
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
        session_id: 'session-1',
        collection,
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
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <h2>DocuMind AI is ready</h2>
            <p>Upload a PDF in the Documents tab, then ask anything about it. I'll reason step-by-step to find your answer.</p>
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
        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="input-field"
            placeholder="Ask anything about your documents… (Enter to send, Shift+Enter for newline)"
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
        <p className="input-hint">DocuMind AI uses RAG + ReAct reasoning + persistent memory</p>
      </div>
    </>
  )
}
