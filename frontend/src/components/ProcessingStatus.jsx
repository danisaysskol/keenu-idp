import styles from './ProcessingStatus.module.css'

const CATEGORY_EMOJI = {
  cnic: '🪪',
  driving_licence: '🚗',
  forms: '📋',
  invoices: '🧾',
  receipt: '🛒',
  resumes: '📄',
  other: '📁',
}

const STATUS_LABEL = {
  pending: 'Waiting',
  processing: 'Analysing…',
  done: 'Done',
  error: 'Error',
}

export default function ProcessingStatus({ job }) {
  if (!job) return null

  const { status, total, processed, images = [] } = job
  const progress = total > 0 ? Math.round((processed / total) * 100) : 0
  const isComplete = status === 'complete'
  const isFailed = status === 'failed'

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={`${styles.badge} ${styles[status] || styles.processing}`}>
            {isComplete ? '✓ Complete' : isFailed ? '✕ Failed' : '⟳ Processing'}
          </span>
          <span className={styles.counter}>
            {processed} / {total} images
          </span>
        </div>
        <span className={styles.percent}>{progress}%</span>
      </div>

      {/* Progress bar */}
      <div className={styles.track}>
        <div
          className={`${styles.bar} ${isComplete ? styles.barComplete : ''}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Per-image cards */}
      {images.length > 0 && (
        <div className={styles.grid}>
          {images.map((img, i) => (
            <ImageCard key={i} img={img} />
          ))}
        </div>
      )}

      {job.error && (
        <div className={styles.jobError}>
          <strong>Error:</strong> {job.error}
        </div>
      )}
    </div>
  )
}

function ImageCard({ img }) {
  const isProcessing = img.status === 'processing'
  const isDone = img.status === 'done'
  const isError = img.status === 'error'

  return (
    <div className={`${styles.card} ${styles[`card_${img.status}`]}`}>
      <div className={styles.cardTop}>
        {isProcessing && <span className={styles.pulse} />}
        {isDone && <span className={styles.iconDone}>✓</span>}
        {isError && <span className={styles.iconError}>✕</span>}
        {img.status === 'pending' && <span className={styles.iconPending}>○</span>}

        <span className={styles.cardLabel}>
          {isDone && img.category
            ? `${CATEGORY_EMOJI[img.category] || '📁'} ${img.category.replace(/_/g, ' ')}`
            : STATUS_LABEL[img.status] || img.status}
        </span>
      </div>
      <div className={styles.cardFilename} title={img.filename}>
        {img.filename}
      </div>
      {isError && img.error && (
        <div className={styles.cardError}>{img.error}</div>
      )}
    </div>
  )
}
