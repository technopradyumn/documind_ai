import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Global response error handler — logs details to console for debugging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || ''
    const status = error.response?.status
    const detail = error.response?.data?.detail || error.message
    console.error(`[DocuMind API] ${status || 'ERR'} ${url}: ${detail}`)
    return Promise.reject(error)
  }
)

export const sendChat = (payload) => api.post('/chat', payload)

export const uploadDocument = (formData, onProgress) =>
  api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) =>
      onProgress && onProgress(Math.round((e.loaded * 100) / (e.total || 1))),
  })

export const listDocuments = () => api.get('/documents/list')
export const getJobStatus  = (jobId) => api.get(`/jobs/${jobId}`)
export const getHealth     = () => api.get('/health')
export const getVoiceStatus = () => api.get('/voice/status')

export const speechToText = (audioBlob) => {
  const form = new FormData()
  // Use blob type to derive a file extension so backend knows the format
  const ext = audioBlob.type.includes('webm')
    ? 'webm'
    : audioBlob.type.includes('mp3') || audioBlob.type.includes('mpeg')
      ? 'mp3'
      : audioBlob.type.includes('ogg')
        ? 'ogg'
        : 'wav'
  form.append('audio', audioBlob, `recording.${ext}`)
  return api.post('/voice/stt', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const textToSpeech = (text) =>
  api.post('/voice/tts', { text }, { responseType: 'blob' })
