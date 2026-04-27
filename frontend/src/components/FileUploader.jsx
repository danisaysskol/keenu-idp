import { useRef, useState } from 'react'
import styles from './FileUploader.module.css'

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const MAX_FILES = 10

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Fetch a remote URL as a File object (used for sample image drops)
async function urlToFile(url, filename) {
  const res = await fetch(url)
  const blob = await res.blob()
  return new File([blob], filename, { type: blob.type || 'image/jpeg' })
}

export default function FileUploader({ files, onFilesChange, onUpload, isProcessing }) {
  const [dragOver, setDragOver] = useState(false)
  const [errors, setErrors] = useState([])
  const inputRef = useRef(null)

  const validate = (incoming) => {
    const errs = []
    const valid = []
    for (const f of incoming) {
      if (!ACCEPTED_TYPES.includes(f.type)) {
        errs.push(`"${f.name}" is not a supported type (JPG, PNG, WebP)`)
        continue
      }
      if (f.size > MAX_FILE_SIZE) {
        errs.push(`"${f.name}" exceeds 10MB (${formatBytes(f.size)})`)
        continue
      }
      valid.push(f)
    }
    if (files.length + valid.length > MAX_FILES) {
      errs.push(`Maximum ${MAX_FILES} images at a time.`)
      return { valid: [], errs }
    }
    return { valid, errs }
  }

  const mergeFiles = (incoming) => {
    const { valid, errs } = validate(Array.from(incoming))
    setErrors(errs)
    if (!valid.length) return
    const names = new Set(files.map(f => f.name + f.size))
    const deduped = valid.filter(f => !names.has(f.name + f.size))
    onFilesChange([...files, ...deduped])
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setDragOver(false)

    // Check for sidebar sample-image drag
    const sampleData = e.dataTransfer.getData('application/sample-image')
    if (sampleData) {
      try {
        const { url, filename } = JSON.parse(sampleData)
        const file = await urlToFile(url, filename)
        mergeFiles([file])
      } catch (err) {
        setErrors([`Failed to load sample image: ${err.message}`])
      }
      return
    }

    mergeFiles(e.dataTransfer.files)
  }

  const handleChange = (e) => {
    mergeFiles(e.target.files)
    e.target.value = ''
  }

  const removeFile = (index) => {
    onFilesChange(files.filter((_, i) => i !== index))
  }

  const clearAll = () => {
    onFilesChange([])
    setErrors([])
  }

  const totalSize = files.reduce((acc, f) => acc + f.size, 0)

  return (
    <div className={styles.container}>
      <div
        className={`${styles.dropzone} ${dragOver ? styles.dragOver : ''} ${isProcessing ? styles.disabled : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !isProcessing && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && !isProcessing && inputRef.current?.click()}
        aria-label="Drop images here or click to browse"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.webp"
          onChange={handleChange}
          className={styles.hiddenInput}
          disabled={isProcessing}
        />
        <div className={styles.dropzoneIcon}>📁</div>
        <p className={styles.dropzoneTitle}>
          {dragOver ? 'Drop images here' : 'Drag & drop images, or click to browse'}
        </p>
        <p className={styles.dropzoneHint}>
          Or pick samples from the sidebar · Max {MAX_FILES} images · 10MB each
        </p>
      </div>

      {errors.length > 0 && (
        <div className={styles.errorList}>
          {errors.map((err, i) => (
            <div key={i} className={styles.errorItem}>⚠ {err}</div>
          ))}
        </div>
      )}

      {files.length > 0 && (
        <div className={styles.fileList}>
          <div className={styles.fileListHeader}>
            <span className={styles.fileCount}>
              {files.length} {files.length === 1 ? 'file' : 'files'}
              <span className={styles.totalSize}> · {formatBytes(totalSize)}</span>
            </span>
            <button className={styles.clearBtn} onClick={clearAll} disabled={isProcessing}>
              Clear all
            </button>
          </div>

          <div className={styles.fileItems}>
            {files.map((f, i) => (
              <div key={i} className={styles.fileItem}>
                <span className={styles.fileIcon}>🖼</span>
                <span className={styles.fileName} title={f.name}>{f.name}</span>
                <span className={styles.fileSize}>{formatBytes(f.size)}</span>
                {!isProcessing && (
                  <button
                    className={styles.removeBtn}
                    onClick={() => removeFile(i)}
                    aria-label={`Remove ${f.name}`}
                  >×</button>
                )}
              </div>
            ))}
          </div>

          <button
            className={styles.uploadBtn}
            onClick={() => onUpload(files)}
            disabled={isProcessing || files.length === 0}
          >
            {isProcessing
              ? 'Processing…'
              : `Process ${files.length} ${files.length === 1 ? 'Image' : 'Images'}`}
          </button>
        </div>
      )}
    </div>
  )
}
