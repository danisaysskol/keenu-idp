import { useEffect, useState } from 'react'
import { getFileContent } from '../services/api'
import styles from './DataTable.module.css'

const MAX_CELL_LENGTH = 80

function truncate(val) {
  if (val === null || val === undefined) return null
  const s = String(val)
  return s.length > MAX_CELL_LENGTH ? s.slice(0, MAX_CELL_LENGTH) + '…' : s
}

export default function DataTable({ jobId, file, onClose }) {
  const [data, setData] = useState([])
  const [columns, setColumns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!jobId || !file) return
    setLoading(true)
    setError(null)

    getFileContent(jobId, file.filename)
      .then(res => {
        setData(res.data || [])
        setColumns(res.columns || [])
      })
      .catch(err => {
        setError(err?.response?.data?.detail || err.message || 'Failed to load file')
      })
      .finally(() => setLoading(false))
  }, [jobId, file])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <div className={styles.modalTitle}>
            <span className={styles.formatBadge}>{file.format.toUpperCase()}</span>
            <span className={styles.titleText}>{file.filename}</span>
          </div>
          <div className={styles.modalMeta}>
            <span>{file.record_count} records</span>
            <span>·</span>
            <span>{columns.length} columns</span>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className={styles.tableWrapper}>
          {loading && (
            <div className={styles.stateMsg}>Loading…</div>
          )}

          {error && (
            <div className={styles.errorMsg}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {!loading && !error && data.length === 0 && (
            <div className={styles.stateMsg}>No data found.</div>
          )}

          {!loading && !error && data.length > 0 && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.rowNum}>#</th>
                  {columns.map(col => (
                    <th key={col} title={col}>
                      {col.replace(/_/g, ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i}>
                    <td className={styles.rowNum}>{i + 1}</td>
                    {columns.map(col => {
                      const val = row[col]
                      const isNull = val === null || val === undefined || val === ''
                      const display = isNull ? null : truncate(val)
                      const full = isNull ? null : String(val)
                      return (
                        <td key={col} title={full ?? undefined} className={isNull ? styles.nullCell : ''}>
                          {isNull ? <span className={styles.nullValue}>—</span> : display}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
