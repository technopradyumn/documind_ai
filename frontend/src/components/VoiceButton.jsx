import { useState, useRef, useEffect } from 'react'
import { speechToText } from '../api/client'

// Check for browser-native speech recognition
const BrowserSpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition || null

export default function VoiceButton({ onTranscript, addToast }) {
  const [recording, setRecording] = useState(false)
  const [mode, setMode] = useState('idle') // 'idle' | 'listening' | 'processing'
  const recognizerRef = useRef(null)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      recognizerRef.current?.abort()
      mediaRef.current?.stop()
    }
  }, [])

  const stopAll = () => {
    recognizerRef.current?.abort()
    recognizerRef.current = null
    if (mediaRef.current?.state === 'recording') {
      mediaRef.current.stop()
    }
    mediaRef.current = null
    setRecording(false)
    setMode('idle')
  }

  // ── Path 1: Browser-native SpeechRecognition (Chrome, Edge, Safari) ──────
  const startBrowserSTT = () => {
    const recognition = new BrowserSpeechRecognition()
    recognizerRef.current = recognition
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.continuous = false

    recognition.onstart = () => {
      setRecording(true)
      setMode('listening')
    }

    recognition.onresult = (e) => {
      const transcript = e.results[0]?.[0]?.transcript?.trim()
      if (transcript) {
        onTranscript(transcript)
      } else {
        addToast('No speech detected. Please try again.', 'info')
      }
    }

    recognition.onerror = (e) => {
      if (e.error === 'no-speech') {
        addToast('No speech detected. Please speak clearly.', 'info')
      } else if (e.error === 'not-allowed') {
        addToast('Microphone access denied. Please allow microphone in browser settings.', 'error')
      } else if (e.error === 'network') {
        addToast('Network error during speech recognition. Check your connection.', 'error')
      } else {
        addToast(`Voice error: ${e.error}`, 'error')
      }
    }

    recognition.onend = () => {
      setRecording(false)
      setMode('idle')
      recognizerRef.current = null
    }

    try {
      recognition.start()
    } catch (err) {
      addToast('Could not start voice recognition: ' + err.message, 'error')
      setRecording(false)
      setMode('idle')
    }
  }

  // ── Path 2: MediaRecorder + backend STT (fallback) ────────────────────────
  const startBackendSTT = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Prefer webm for backend compatibility; fall back to default
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : ''

      const options = mimeType ? { mimeType } : {}
      const recorder = new MediaRecorder(stream, options)
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setMode('processing')
        const blob = new Blob(chunksRef.current, { type: mimeType || 'audio/webm' })
        try {
          const { data } = await speechToText(blob)
          if (data.transcript) {
            onTranscript(data.transcript)
          } else {
            addToast('No speech detected. Please speak more clearly.', 'info')
          }
        } catch (err) {
          const detail = err.response?.data?.detail || err.message || 'Unknown error'
          addToast('Voice error: ' + detail, 'error')
        } finally {
          setMode('idle')
          setRecording(false)
        }
      }

      recorder.start(100) // collect in 100ms chunks for smoother streaming
      mediaRef.current = recorder
      setRecording(true)
      setMode('listening')
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        addToast('Microphone access denied. Please allow microphone in browser settings.', 'error')
      } else {
        addToast('Could not access microphone: ' + err.message, 'error')
      }
      setMode('idle')
    }
  }

  const toggleRecording = async () => {
    if (recording) {
      stopAll()
      return
    }

    // Use browser-native STT if available (faster, no server round-trip)
    if (BrowserSpeechRecognition) {
      startBrowserSTT()
    } else {
      await startBackendSTT()
    }
  }

  const label = mode === 'listening'
    ? 'Listening…'
    : mode === 'processing'
      ? 'Processing…'
      : BrowserSpeechRecognition ? 'Click to speak' : 'Click to record'

  return (
    <button
      className={`btn-icon btn-voice ${recording ? 'recording' : ''}`}
      onClick={toggleRecording}
      title={label}
      aria-label={label}
      disabled={mode === 'processing'}
    >
      {mode === 'processing' ? (
        <span style={{ fontSize: '0.8rem' }}>⏳</span>
      ) : recording ? (
        <span className="rec-pulse">⏹</span>
      ) : (
        '🎙'
      )}
    </button>
  )
}
