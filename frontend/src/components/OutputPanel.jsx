import { useState } from 'react'
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

const FORMAT_LABEL = { json: 'JSON', csv: 'CSV', pdf: 'PDF' }

export default function OutputPanel({ jobId, files, onViewFile }) {
  const [expanded, setExpanded] = useState(null)

  if (!files || files.length === 0) return null

  // Group by category, keeping json/csv/pdf together
  const byCategory = {}
  for (const f of files) {
    if (!byCategory[f.category]) byCategory[f.category] = {}
    byCategory[f.category][f.format] = f
  }

  const categoryCount = Object.keys(byCategory).length

  return (
    <div className={styles.container}>
      <div className={styles.heading}>
        <span className={styles.headingIcon}>📦</span>
        <div>
          <h2 className={styles.title}>Generated Outputs</h2>
          <p className={styles.subtitle}>
            {categoryCount} {categoryCount === 1 ? 'category' : 'categories'} · {files.length} files
          </p>
        </div>
      </div>

      <div className={styles.categories}>
        {Object.entries(byCategory).map(([category, fmtMap]) => {
          const csvFile  = fmtMap['csv']
          const jsonFile = fmtMap['json']
          const pdfFile  = fmtMap['pdf']
          const recordCount = jsonFile?.record_count ?? csvFile?.record_count ?? 0
          const pageCount   = pdfFile?.record_count ?? 0
          const isExpanded  = expanded === category

          return (
            <div key={category} className={styles.categoryCard}>
              <button
                className={styles.categoryHeader}
                onClick={() => setExpanded(isExpanded ? null : category)}
                aria-expanded={isExpanded}
              >
                <div className={styles.categoryLeft}>
                  <span className={styles.categoryEmoji}>
                    {CATEGORY_EMOJI[category] || '📁'}
                  </span>
                  <div>
                    <span className={styles.categoryName}>
                      {category.replace(/_/g, ' ')}
                    </span>
                    <span className={styles.recordCount}>
                      {recordCount} {recordCount === 1 ? 'record' : 'records'}
                      {pdfFile && ` · ${pageCount}-page PDF`}
                    </span>
                  </div>
                </div>
                <span className={`${styles.chevron} ${isExpanded ? styles.open : ''}`}>›</span>
              </button>

              {isExpanded && (
                <div className={styles.fileActions}>
                  {/* JSON row */}
                  {jsonFile && (
                    <FileRow
                      file={jsonFile}
                      jobId={jobId}
                      label="JSON"
                      onView={() => onViewFile(jobId, jsonFile)}
                      canView
                    />
                  )}

                  {/* CSV row */}
                  {csvFile && (
                    <FileRow
                      file={csvFile}
                      jobId={jobId}
                      label="CSV"
                      onView={() => onViewFile(jobId, csvFile)}
                      canView
                    />
                  )}

                  {/* PDF row — open in new tab instead of table view */}
                  {pdfFile && (
                    <FileRow
                      file={pdfFile}
                      jobId={jobId}
                      label="PDF"
                      onView={null}
                      canView={false}
                      pageCount={pageCount}
                    />
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function FileRow({ file, jobId, label, onView, canView, pageCount }) {
  const downloadUrl = getDownloadUrl(jobId, file.filename)

  return (
    <div className={styles.fileRow}>
      <div className={styles.fileInfo}>
        <span className={`${styles.formatTag} ${styles[label.toLowerCase()]}`}>
          {FORMAT_LABEL[label.toLowerCase()] || label}
        </span>
        <span className={styles.filename} title={file.filename}>
          {file.filename}
        </span>
        {pageCount != null && label === 'PDF' && (
          <span className={styles.pageCount}>{pageCount} {pageCount === 1 ? 'page' : 'pages'}</span>
        )}
      </div>
      <div className={styles.actions}>
        {canView && (
          <button className={styles.viewBtn} onClick={onView}>
            View
          </button>
        )}
        {label === 'PDF' ? (
          <a
            className={styles.openBtn}
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open
          </a>
        ) : null}
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
