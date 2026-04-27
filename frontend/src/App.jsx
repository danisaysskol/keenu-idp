import { useCallback, useEffect, useState } from 'react'
import Header from './components/Header'
import Footer from './components/Footer'
import Sidebar from './components/Sidebar'
import FileUploader from './components/FileUploader'
import ProcessingStatus from './components/ProcessingStatus'
import OutputPanel from './components/OutputPanel'
import { uploadFiles } from './services/api'
import styles from './App.module.css'

const LS_KEY = 'keenu_last_job'

function loadSavedJob() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return null
    const saved = JSON.parse(raw)
    if (Date.now() - saved._savedAt > 2 * 60 * 60 * 1000) {
      localStorage.removeItem(LS_KEY)
      return null
    }
    return saved.job
  } catch {
    return null
  }
}

export default function App() {
  const [files, setFiles] = useState([])
  const [phase, setPhase] = useState('upload') // upload | processing | done
  const [job, setJob] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [addedSampleUrls, setAddedSampleUrls] = useState(new Set())
  const [viewFile, setViewFile] = useState(null)

  // Restore last session on mount
  useEffect(() => {
    const saved = loadSavedJob()
    if (saved) {
      setJob(saved)
      setPhase('done')
    }
  }, [])

  const handleAddSample = useCallback(async (url, filename) => {
    try {
      const res = await fetch(url)
      const blob = await res.blob()
      const file = new File([blob], filename, { type: blob.type || 'image/jpeg' })
      setFiles(prev => {
        if (prev.length >= 10) return prev
        const names = new Set(prev.map(f => f.name + f.size))
        if (names.has(file.name + file.size)) return prev
        return [...prev, file]
      })
      setAddedSampleUrls(prev => new Set([...prev, url]))
    } catch (err) {
      console.error('Failed to load sample image:', err)
    }
  }, [])

  const handleFilesChange = useCallback((newFiles) => {
    setFiles(newFiles)
    if (newFiles.length === 0) setAddedSampleUrls(new Set())
  }, [])

  const handleUpload = async (filesToUpload) => {
    setUploadError(null)
    setJob(null)
    setPhase('processing')

    try {
      const finalJob = await uploadFiles(filesToUpload, (update) => {
        setJob({ ...update }) // live updates while streaming
      })
      if (finalJob) {
        setJob(finalJob)
        setPhase('done')
        localStorage.setItem(LS_KEY, JSON.stringify({ job: finalJob, _savedAt: Date.now() }))
      }
    } catch (err) {
      const msg = err?.message || 'Upload failed'
      setUploadError(msg)
      setPhase('upload')
    }
  }

  const handleNewUpload = () => {
    setJob(null)
    setFiles([])
    setUploadError(null)
    setViewFile(null)
    setAddedSampleUrls(new Set())
    setPhase('upload')
  }

  const showSidebar = phase === 'upload'
  const outputFiles = job?.output_files ?? []

  return (
    <div className={styles.app}>
      <Header />

      <div className={styles.body}>
        {showSidebar && (
          <Sidebar
            queuedUrls={addedSampleUrls}
            onAddSample={handleAddSample}
            disabled={false}
          />
        )}

        <main className={`${styles.main} ${!showSidebar ? styles.mainFull : ''}`}>
          <div className={styles.content}>

            {phase === 'upload' && (
              <>
                <div className={styles.hero}>
                  <h1 className={styles.heroTitle}>Intelligent Document Processing</h1>
                  <p className={styles.heroSubtitle}>
                    Upload scanned documents or pick samples from the sidebar.
                    AI classifies and extracts structured data automatically.
                  </p>
                </div>

                {uploadError && (
                  <div className={styles.alertError}>
                    <strong>Upload failed:</strong> {uploadError}
                  </div>
                )}

                <FileUploader
                  files={files}
                  onFilesChange={handleFilesChange}
                  onUpload={handleUpload}
                  isProcessing={false}
                />

                <section className={styles.guide}>
                  <h3 className={styles.guideTitle}>Supported document types</h3>
                  <div className={styles.guideGrid}>
                    {[
                      ['🪪', 'CNIC', 'Name, ID number, dates, gender'],
                      ['🚗', 'Driving Licence', 'Licence number, expiry, blood group'],
                      ['🧾', 'Invoice', 'Vendor, items, totals, tax'],
                      ['🛒', 'Receipt', 'Merchant, items, payment method'],
                      ['📄', 'Resume / CV', 'Skills, experience, education'],
                      ['📋', 'Forms', 'Any key-value form fields'],
                    ].map(([emoji, name, desc]) => (
                      <div key={name} className={styles.guideCard}>
                        <span className={styles.guideEmoji}>{emoji}</span>
                        <div>
                          <div className={styles.guideName}>{name}</div>
                          <div className={styles.guideDesc}>{desc}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            )}

            {phase === 'processing' && job && (
              <ProcessingStatus job={job} />
            )}

            {phase === 'processing' && !job && (
              <div className={styles.processingInit}>
                <div className={styles.spinner} />
                <p className={styles.processingHint}>Uploading…</p>
              </div>
            )}

            {phase === 'done' && (
              <>
                {outputFiles.length > 0 ? (
                  <OutputPanel
                    jobId={job?.job_id}
                    files={outputFiles}
                    onViewFile={(file) => setViewFile({ file })}
                  />
                ) : (
                  <div className={styles.alertInfo}>
                    Processing complete but no structured data was extracted.
                    All images may have errored or been unrecognised.
                  </div>
                )}

                <div className={styles.actions}>
                  <button className={styles.newBtn} onClick={handleNewUpload}>
                    ← Process new images
                  </button>
                </div>
              </>
            )}

          </div>
        </main>
      </div>

      {viewFile && (
        <FileViewer
          file={viewFile.file}
          onClose={() => setViewFile(null)}
        />
      )}

      <Footer />
    </div>
  )
}

// ── Inline file viewer modal ────────────────────────────────────────────────

function FileViewer({ file, onClose }) {
  const [parsed, setParsed] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!file?.content) { setError('Content not available'); return }
    try {
      if (file.format === 'json') {
        setParsed(JSON.parse(file.content))
      } else {
        const lines = file.content.trim().split('\n')
        const headers = lines[0].split(',').map(h => h.replace(/^"|"$/g, '').trim())
        const rows = lines.slice(1).map(line => {
          const vals = line.split(',').map(v => v.replace(/^"|"$/g, '').trim())
          return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']))
        })
        setParsed({ headers, rows })
      }
    } catch (e) {
      setError(String(e))
    }
  }, [file])

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const isJson = file.format === 'json'
  const rows = isJson ? parsed : parsed?.rows
  const headers = isJson ? (parsed?.[0] ? Object.keys(parsed[0]) : []) : parsed?.headers

  return (
    <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <div>
            <span className={styles.formatBadge}>{file.format.toUpperCase()}</span>
            <span className={styles.modalFilename}>{file.filename}</span>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>×</button>
        </div>

        <div className={styles.tableWrapper}>
          {error && <div className={styles.modalError}>{error}</div>}
          {!error && !parsed && <div className={styles.modalLoading}>Loading…</div>}
          {!error && parsed && rows?.length > 0 && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.rowNum}>#</th>
                  {headers.map(h => <th key={h}>{h.replace(/_/g, ' ')}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i}>
                    <td className={styles.rowNum}>{i + 1}</td>
                    {headers.map(h => {
                      const val = row[h]
                      const empty = val === null || val === undefined || val === ''
                      return (
                        <td key={h} className={empty ? styles.nullCell : ''}>
                          {empty ? <span className={styles.nullVal}>—</span> : String(val)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!error && parsed && !rows?.length && (
            <div className={styles.modalLoading}>No records found.</div>
          )}
        </div>
      </div>
    </div>
  )
}
