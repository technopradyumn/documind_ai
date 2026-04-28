import { useState, useRef } from 'react'
import { speechToText } from '../api/client'

export default function VoiceButton({ onTranscript, addToast }) {
  const [recording, setRecording] = useState(false)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = e => chunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        try {
          const { data } = await speechToText(blob)
          onTranscript(data.transcript)
        } catch (e) {
          addToast('Voice error: ' + (e.response?.data?.detail || 'Could not understand audio'), 'error')
        }
      }
      recorder.start()
      mediaRef.current = recorder
      setRecording(true)
    } catch (e) {
      addToast('Microphone access denied.', 'error')
    }
  }

  const stopRecording = () => {
    mediaRef.current?.stop()
    setRecording(false)
  }

  return (
    <button
      className={`btn-icon btn-voice ${recording ? 'recording' : ''}`}
      onMouseDown={startRecording}
      onMouseUp={stopRecording}
      onTouchStart={startRecording}
      onTouchEnd={stopRecording}
      title={recording ? 'Release to send' : 'Hold to speak'}
    >
      {recording ? '⏹' : '🎙'}
    </button>
  )
}
