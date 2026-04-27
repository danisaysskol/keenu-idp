import { useCallback, useEffect, useRef, useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import FileUploader from './components/FileUploader'
import ProcessingStatus from './components/ProcessingStatus'
import OutputPanel from './components/OutputPanel'
import DataTable from './components/DataTable'
import { uploadFiles, getJobStatus, listJobFiles } from './services/api'
import styles from './App.module.css'

const POLL_INTERVAL_MS = 2000

export default function App() {
  // files state lifted here so Sidebar can add to it
  const [files, setFiles] = useState([])

  const [phase, setPhase] = useState('upload') // upload | processing | done
  const [job, setJob] = useState(null)
  const [outputFiles, setOutputFiles] = useState([])
  const [uploadError, setUploadError] = useState(null)
  const [viewFile, setViewFile] = useState(null)
  const pollTimer = useRef(null)

  const stopPolling = () => {
    if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null }
  }

  const startPolling = useCallback((jobId) => {
    stopPolling()
    pollTimer.current = setInterval(async () => {
      try {
        const updated = await getJobStatus(jobId)
        setJob(updated)
        if (updated.status === 'complete' || updated.status === 'failed') stopPolling()
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, POLL_INTERVAL_MS)
  }, [])

  useEffect(() => () => stopPolling(), [])

  // Add a sample image from the sidebar (fetched as a blob)
  const addSampleImage = useCallback(async (url, filename) => {
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
    } catch (err) {
      console.error('Failed to load sample image:', err)
    }
  }, [])

  // Set of sample URLs currently in the queue — used by Sidebar for checkmarks
  const queuedUrls = new Set(files.map(f => `/samples/${f.webkitRelativePath || f.name}`))
  // Simpler: track which sample URLs were added
  const [addedSampleUrls, setAddedSampleUrls] = useState(new Set())

  const handleAddSample = useCallback(async (url, filename) => {
    await addSampleImage(url, filename)
    setAddedSampleUrls(prev => new Set([...prev, url]))
  }, [addSampleImage])

  const handleFilesChange = useCallback((newFiles) => {
    setFiles(newFiles)
    // Remove checkmarks for files that were cleared
    if (newFiles.length === 0) setAddedSampleUrls(new Set())
  }, [])

  const handleUpload = async (filesToUpload) => {
    setUploadError(null)
    setOutputFiles([])
    setPhase('processing')

    try {
      const { job_id } = await uploadFiles(filesToUpload)
      const initial = await getJobStatus(job_id)
      setJob(initial)
      startPolling(job_id)
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Upload failed'
      setUploadError(msg)
      setPhase('upload')
    }
  }

  const handleJobComplete = useCallback(async () => {
    if (!job) return
    setPhase('done')
    try {
      const f = await listJobFiles(job.job_id)
      setOutputFiles(f)
    } catch (err) {
      console.error('Could not load output files:', err)
    }
  }, [job])

  const handleNewUpload = () => {
    stopPolling()
    setJob(null)
    setFiles([])
    setOutputFiles([])
    setUploadError(null)
    setViewFile(null)
    setAddedSampleUrls(new Set())
    setPhase('upload')
  }

  const isProcessing = phase === 'processing'
  const showSidebar = phase === 'upload'

  return (
    <div className={styles.app}>
      <Header />

      <div className={styles.body}>
        {/* Sidebar — only shown during upload phase */}
        {showSidebar && (
          <Sidebar
            queuedUrls={addedSampleUrls}
            onAddSample={handleAddSample}
            disabled={isProcessing}
          />
        )}

        <main className={`${styles.main} ${!showSidebar ? styles.mainFull : ''}`}>
          <div className={styles.content}>

            {phase === 'upload' && (
              <div className={styles.hero}>
                <h1 className={styles.heroTitle}>Intelligent Document Processing</h1>
                <p className={styles.heroSubtitle}>
                  Upload scanned documents or pick samples from the sidebar.
                  AI classifies and extracts structured data automatically.
                </p>
              </div>
            )}

            {uploadError && (
              <div className={styles.alertError}>
                <strong>Upload failed:</strong> {uploadError}
              </div>
            )}

            {phase === 'upload' && (
              <section>
                <FileUploader
                  files={files}
                  onFilesChange={handleFilesChange}
                  onUpload={handleUpload}
                  isProcessing={false}
                />
              </section>
            )}

            {(phase === 'processing' || phase === 'done') && job && (
              <section>
                <ProcessingStatus job={job} onComplete={handleJobComplete} />
              </section>
            )}

            {phase === 'done' && outputFiles.length > 0 && (
              <section>
                <OutputPanel
                  jobId={job?.job_id}
                  files={outputFiles}
                  onViewFile={setViewFile}
                />
              </section>
            )}

            {phase === 'done' && outputFiles.length === 0 && job?.status === 'complete' && (
              <div className={styles.alertInfo}>
                Processing complete but no structured data was extracted. All images may have errored.
              </div>
            )}

            {phase === 'done' && (
              <div className={styles.actions}>
                <button className={styles.newBtn} onClick={handleNewUpload}>
                  ← Process new images
                </button>
              </div>
            )}

            {phase === 'upload' && (
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
            )}
          </div>
        </main>
      </div>

      {viewFile && (
        <DataTable
          jobId={viewFile.jobId}
          file={viewFile.file}
          onClose={() => setViewFile(null)}
        />
      )}
    </div>
  )
}
