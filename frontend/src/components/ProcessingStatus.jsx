import { useEffect, useRef } from 'react'
import styles from './ProcessingStatus.module.css'

const STATUS_ICON = {
  pending: '○',
  processing: '◌',
  done: '●',
  error: '✕',
}

const STATUS_LABEL = {
  pending: 'Waiting',
  processing: 'Processing',
  done: 'Done',
  error: 'Error',
}

const CATEGORY_EMOJI = {
  cnic: '🪪',
  driving_licence: '🚗',
  forms: '📋',
  invoices: '🧾',
  receipt: '🛒',
  resumes: '📄',
  other: '📁',
}

export default function ProcessingStatus({ job, onComplete }) {
  const prevStatus = useRef(null)

  useEffect(() => {
    if (job?.status === 'complete' && prevStatus.current !== 'complete') {
      onComplete?.()
    }
    prevStatus.current = job?.status
  }, [job?.status, onComplete])

  if (!job) return null

  const { status, total, processed, images = [] } = job
  const progress = total > 0 ? Math.round((processed / total) * 100) : 0
  const isComplete = status === 'complete'
  const isFailed = status === 'failed'

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={`${styles.statusBadge} ${styles[status]}`}>
            {isComplete ? '✓ Complete' : isFailed ? '✕ Failed' : '⟳ Processing'}
          </span>
          <span className={styles.subtitle}>
            {processed} / {total} images
          </span>
        </div>
        <span className={styles.percent}>{progress}%</span>
      </div>

      <div className={styles.progressTrack}>
        <div
          className={`${styles.progressBar} ${isComplete ? styles.complete : ''}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {images.length > 0 && (
        <div className={styles.imageGrid}>
          {images.map((img, i) => (
            <div
              key={i}
              className={`${styles.imageCard} ${styles[img.status]}`}
              title={img.error || img.filename}
            >
              <div className={styles.imageCardTop}>
                <span className={styles.statusIcon}>{STATUS_ICON[img.status] || '○'}</span>
                <span className={styles.imageCategory}>
                  {img.category ? `${CATEGORY_EMOJI[img.category] || '📁'} ${img.category}` : STATUS_LABEL[img.status]}
                </span>
              </div>
              <div className={styles.imageName} title={img.filename}>
                {img.filename}
              </div>
              {img.error && (
                <div className={styles.imageError}>{img.error}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {job.error && (
        <div className={styles.jobError}>
          <strong>Job failed:</strong> {job.error}
        </div>
      )}
    </div>
  )
}
