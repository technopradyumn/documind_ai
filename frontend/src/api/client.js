import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const sendChat = (payload) => api.post('/chat', payload)
export const uploadDocument = (formData, onProgress) =>
  api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  })
export const listDocuments = () => api.get('/documents/list')
export const getJobStatus  = (jobId) => api.get(`/jobs/${jobId}`)
export const getHealth     = () => api.get('/health')
export const getVoiceStatus = () => api.get('/voice/status')
export const speechToText  = (audioBlob) => {
  const form = new FormData()
  form.append('audio', audioBlob, 'recording.wav')
  return api.post('/voice/stt', form, { headers: { 'Content-Type': 'multipart/form-data' } })
}
export const textToSpeech = (text) =>
  api.post('/voice/tts', { text }, { responseType: 'blob' })
