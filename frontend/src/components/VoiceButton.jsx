import { useState, useRef } from 'react'
import { speechToText } from '../api/client'

export default function VoiceButton({ onTranscript, addToast }) {
  const [recording, setRecording] = useState(false)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  const toggleRecording = async () => {
    if (recording) {
      mediaRef.current?.stop()
      setRecording(false)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Use webm for better browser support; backend now converts it
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunksRef.current = []
      
      recorder.ondataavailable = e => chunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        try {
          const { data } = await speechToText(blob)
          if (data.transcript) {
            onTranscript(data.transcript)
          } else {
            addToast('No speech detected.', 'info')
          }
        } catch (e) {
          addToast('Voice error: ' + (e.response?.data?.detail || 'Could not understand audio'), 'error')
        }
      }
      
      recorder.start()
      mediaRef.current = recorder
      setRecording(true)
    } catch (e) {
      console.error(e)
      addToast('Microphone access denied or not supported.', 'error')
    }
  }

  return (
    <button
      className={`btn-icon btn-voice ${recording ? 'recording' : ''}`}
      onClick={toggleRecording}
      title={recording ? 'Click to stop' : 'Click to speak'}
    >
      {recording ? (
        <span className="rec-pulse">⏹</span>
      ) : (
        '🎙'
      )}
    </button>
  )
}
