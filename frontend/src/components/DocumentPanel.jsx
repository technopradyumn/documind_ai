import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadDocument, listDocuments, getJobStatus } from '../api/client'

export default function DocumentPanel({ collection, addToast }) {
  const [docs, setDocs]     = useState([])
  const [jobs, setJobs]     = useState([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress]   = useState(0)

  const onDrop = useCallback(async (accepted) => {
    const file = accepted[0]
    if (!file) return
    setUploading(true)
    setProgress(0)
    const form = new FormData()
    form.append('file', file)
    form.append('collection', collection)
    try {
      const { data } = await uploadDocument(form, setProgress)
      addToast(`📄 "${file.name}" uploaded! Indexing started…`, 'success')
      setJobs(prev => [...prev, { job_id: data.job_id, name: file.name, status: 'queued' }])
      pollJob(data.job_id, file.name)
    } catch (e) {
      addToast('Upload failed: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setUploading(false)
    }
  }, [collection])

  const pollJob = (jobId, name) => {
    const iv = setInterval(async () => {
      try {
        const { data } = await getJobStatus(jobId)
        setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, status: data.status } : j))
        if (data.status === 'finished') {
          clearInterval(iv)
          addToast(`✅ "${name}" indexed successfully! You can now chat about it.`, 'success')
          setDocs(prev => [...prev, { name, collection, pages: data.result?.pages || '?' }])
        } else if (data.status === 'failed') {
          clearInterval(iv)
          const errorMsg = data.error ? `: ${data.error}` : ''
          addToast(`❌ Indexing failed for "${name}"${errorMsg}`, 'error')
        }
      } catch { clearInterval(iv) }
    }, 2500)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'] }, maxFiles: 1,
  })

  const statusClass = (s) => {
    if (s === 'finished') return 'badge-finished'
    if (s === 'failed')   return 'badge-failed'
    if (s === 'started' || s === 'deferred') return 'badge-started'
    return 'badge-queued'
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
                  {j.status !== 'finished' && j.status !== 'failed' && (
                    <div className="progress-bar" style={{ marginTop: 6 }}>
                      <div className="progress-fill" style={{ width: '60%' }} />
                    </div>
                  )}
                </div>
                <span className={`badge ${statusClass(j.status)}`}>{j.status}</span>
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
                  <div className="doc-card-meta">{d.pages} pages · {d.collection}</div>
                </div>
                <span className="badge badge-finished">ready</span>
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
