import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadDocument, listDocuments, getJobStatus } from '../api/client'

export default function DocumentPanel({ collection, addToast }) {
  const [docs, setDocs]     = useState([])
  const [jobs, setJobs]     = useState([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress]   = useState(0)

  // Load existing docs on mount
  useEffect(() => {
    listDocuments()
      .then(({ data }) => {
        if (data.documents?.length) {
          setDocs(data.documents.map(name => ({ name, collection: 'documind', pages: '?' })))
        }
      })
      .catch(() => {/* non-fatal */})
  }, [])

  const handleDelete = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) return
    try {
      const { deleteDocument } = await import('../api/client')
      await deleteDocument(filename, collection)
      setDocs(prev => prev.filter(d => d.name !== filename))
      addToast(`🗑️ "${filename}" deleted.`, 'success')
    } catch (e) {
      addToast('Failed to delete document.', 'error')
    }
  }

  const onDrop = useCallback(async (accepted, rejected) => {
    if (rejected?.length) {
      addToast('Only PDF files are supported. Please upload a .pdf file.', 'error')
      return
    }
    const file = accepted[0]
    if (!file) return
    setUploading(true)
    setProgress(0)
    const form = new FormData()
    form.append('file', file)
    form.append('collection', collection)
    try {
      const { data } = await uploadDocument(form, setProgress)

      // If Redis is unavailable, indexing ran synchronously — handle immediately
      if (data.job_id === 'sync-done') {
        addToast(`✅ "${file.name}" uploaded and indexed!`, 'success')
        setDocs(prev => [...prev, { name: file.name, collection, pages: '?' }])
        return
      }

      addToast(`📄 "${file.name}" uploaded! Indexing started…`, 'success')
      setJobs(prev => [...prev, { job_id: data.job_id, name: file.name, status: 'queued' }])
      pollJob(data.job_id, file.name)
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || 'Unknown error'
      addToast(`Upload failed: ${detail}`, 'error')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }, [collection])

  const pollJob = (jobId, name) => {
    let attempts = 0
    const MAX_POLLS = 120 // 5 minutes max (120 × 2.5s)
    const iv = setInterval(async () => {
      attempts++
      if (attempts > MAX_POLLS) {
        clearInterval(iv)
        addToast(`⚠️ Indexing "${name}" is taking longer than expected. Check server logs.`, 'info')
        setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, status: 'timeout' } : j))
        return
      }
      try {
        const { data } = await getJobStatus(jobId)
        const status = data.status
        setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, status } : j))

        if (status === 'finished') {
          clearInterval(iv)
          addToast(`✅ "${name}" indexed successfully! You can now chat about it.`, 'success')
          setDocs(prev => [...prev, { name, collection, pages: data.result?.pages || '?' }])
          // Remove from jobs list after 3s
          setTimeout(() => setJobs(prev => prev.filter(j => j.job_id !== jobId)), 3000)
        } else if (status === 'failed') {
          clearInterval(iv)
          const errorMsg = data.error ? ` — ${data.error}` : ''
          addToast(`❌ Indexing failed for "${name}"${errorMsg}`, 'error')
        }
      } catch {
        // Network blip — keep polling
      }
    }, 2500)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50 MB
  })

  const statusClass = (s) => {
    if (s === 'finished') return 'badge-finished'
    if (s === 'failed' || s === 'timeout') return 'badge-failed'
    if (s === 'started' || s === 'deferred') return 'badge-started'
    return 'badge-queued'
  }

  const statusLabel = (s) => {
    if (s === 'timeout') return 'timeout'
    if (s === 'queued') return 'queued'
    if (s === 'started') return 'indexing'
    if (s === 'deferred') return 'waiting'
    if (s === 'finished') return 'done'
    if (s === 'failed') return 'failed'
    return s
  }

  return (
    <div className="doc-panel">
      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        <div className="dropzone-icon">📂</div>
        <h3>{isDragActive ? 'Drop the PDF here…' : 'Drag & drop a PDF'}</h3>
        <p>or click to browse — your document will be chunked, embedded, and stored in Qdrant</p>
        {uploading && (
          <div style={{ width: '100%' }}>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
              Uploading… {progress}%
            </p>
          </div>
        )}
        {!uploading && <button className="btn-primary" onClick={e => e.stopPropagation()}>Browse PDF</button>}
      </div>

      {jobs.length > 0 && (
        <>
          <p className="sidebar-label" style={{ padding: '0 4px' }}>Indexing Jobs</p>
          <div className="doc-list">
            {jobs.map(j => (
              <div key={j.job_id} className="doc-card">
                <span className="doc-card-icon">⚙️</span>
                <div className="doc-card-info">
                  <div className="doc-card-name">{j.name}</div>
                  <div className="doc-card-meta">Job: {j.job_id.slice(0, 16)}…</div>
                  {j.status !== 'finished' && j.status !== 'failed' && j.status !== 'timeout' && (
                    <div className="progress-bar" style={{ marginTop: 6 }}>
                      <div className="progress-fill progress-indeterminate" />
                    </div>
                  )}
                </div>
                <span className={`badge ${statusClass(j.status)}`}>{statusLabel(j.status)}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {docs.length > 0 && (
        <>
          <p className="sidebar-label" style={{ padding: '0 4px' }}>Indexed Documents</p>
          <div className="doc-list">
            {docs.map((d, i) => (
              <div key={i} className="doc-card">
                <span className="doc-card-icon">📄</span>
                <div className="doc-card-info">
                  <div className="doc-card-name">{d.name}</div>
                  <div className="doc-card-meta">{d.pages !== '?' ? `${d.pages} pages · ` : ''}{d.collection}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge-finished">ready</span>
                  <button 
                    className="btn-icon" 
                    onClick={() => handleDelete(d.name)}
                    style={{ width: 28, height: 28, fontSize: 14, background: 'rgba(239,68,68,0.1)', color: 'var(--danger)' }}
                    title="Delete Document"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {jobs.length === 0 && docs.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', padding: '20px 0' }}>
          No documents uploaded yet. Upload a PDF to get started.
        </div>
      )}
    </div>
  )
}
