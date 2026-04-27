import { getDownloadUrl } from '../services/api'
import styles from './OutputPanel.module.css'

const CATEGORY_EMOJI = {
  cnic: '🪪',
  driving_licence: '🚗',
  forms: '📋',
  invoices: '🧾',
  receipt: '🛒',
  resumes: '📄',
  other: '📁',
}

export default function OutputPanel({ jobId, files, onViewFile }) {
  if (!files || files.length === 0) return null

  const byCategory = {}
  for (const f of files) {
    if (!byCategory[f.category]) byCategory[f.category] = {}
    byCategory[f.category][f.format] = f
  }

  const categoryCount = Object.keys(byCategory).length
  const totalRecords = files
    .filter(f => f.format !== 'pdf')
    .reduce((s, f) => s + (f.record_count || 0), 0) / 2 | 0 // json+csv counted once

  return (
    <div className={styles.container}>
      <div className={styles.heading}>
        <div className={styles.headingIcon}>✓</div>
        <div>
          <h2 className={styles.title}>Extraction complete</h2>
          <p className={styles.subtitle}>
            {categoryCount} {categoryCount === 1 ? 'category' : 'categories'} · {totalRecords} {totalRecords === 1 ? 'record' : 'records'} extracted
          </p>
        </div>
      </div>

      <div className={styles.categories}>
        {Object.entries(byCategory).map(([category, fmtMap]) => {
          const csvFile  = fmtMap['csv']
          const jsonFile = fmtMap['json']
          const pdfFile  = fmtMap['pdf']
          const recordCount = jsonFile?.record_count ?? csvFile?.record_count ?? 0

          return (
            <div key={category} className={styles.categoryCard}>
              <div className={styles.categoryHeader}>
                <span className={styles.categoryEmoji}>
                  {CATEGORY_EMOJI[category] || '📁'}
                </span>
                <div className={styles.categoryMeta}>
                  <span className={styles.categoryName}>
                    {category.replace(/_/g, ' ')}
                  </span>
                  <span className={styles.recordCount}>
                    {recordCount} {recordCount === 1 ? 'record' : 'records'}
                    {pdfFile && ` · ${pdfFile.record_count}-page PDF`}
                  </span>
                </div>
              </div>

              <div className={styles.fileGrid}>
                {jsonFile && (
                  <FileCard
                    file={jsonFile}
                    jobId={jobId}
                    label="JSON"
                    canView={!!jsonFile.content}
                    onView={() => onViewFile(jsonFile)}
                  />
                )}
                {csvFile && (
                  <FileCard
                    file={csvFile}
                    jobId={jobId}
                    label="CSV"
                    canView={!!csvFile.content}
                    onView={() => onViewFile(csvFile)}
                  />
                )}
                {pdfFile && (
                  <FileCard
                    file={pdfFile}
                    jobId={jobId}
                    label="PDF"
                    canView={false}
                    onView={null}
                  />
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function FileCard({ file, jobId, label, canView, onView }) {
  const downloadUrl = getDownloadUrl(jobId, file.filename)
  const isPdf = label === 'PDF'

  return (
    <div className={styles.fileCard}>
      <div className={styles.fileCardTop}>
        <span className={`${styles.formatTag} ${styles[label.toLowerCase()]}`}>
          {label}
        </span>
        <span className={styles.filename} title={file.filename}>
          {file.filename}
        </span>
      </div>
      <div className={styles.fileCardActions}>
        {canView && (
          <button className={styles.viewBtn} onClick={onView}>
            View
          </button>
        )}
        {isPdf && (
          <a
            className={styles.openBtn}
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open
          </a>
        )}
        <a
          className={styles.downloadBtn}
          href={downloadUrl}
          download={file.filename}
        >
          Download
        </a>
      </div>
    </div>
  )
}
