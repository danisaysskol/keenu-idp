import { useState } from 'react'
import { SAMPLE_CATEGORIES } from '../data/samples'
import styles from './Sidebar.module.css'

export default function Sidebar({ queuedUrls, onAddSample, disabled }) {
  // All categories open by default
  const [open, setOpen] = useState(() =>
    Object.fromEntries(SAMPLE_CATEGORIES.map(c => [c.id, true]))
  )

  const toggle = (id) => setOpen(prev => ({ ...prev, [id]: !prev[id] }))

  const handleClick = (img) => {
    if (disabled) return
    onAddSample(img.url, img.filename)
  }

  const handleDragStart = (e, img) => {
    e.dataTransfer.setData(
      'application/sample-image',
      JSON.stringify({ url: img.url, filename: img.filename })
    )
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <span className={styles.headerIcon}>🗂</span>
        <div>
          <div className={styles.headerTitle}>Sample Documents</div>
          <div className={styles.headerSub}>Click or drag to add</div>
        </div>
      </div>

      <div className={styles.categories}>
        {SAMPLE_CATEGORIES.map(cat => {
          const isOpen = open[cat.id]
          return (
            <div key={cat.id} className={styles.category}>
              <button
                className={styles.categoryToggle}
                onClick={() => toggle(cat.id)}
                aria-expanded={isOpen}
              >
                <span className={styles.catEmoji}>{cat.emoji}</span>
                <span className={styles.catLabel}>{cat.label}</span>
                <span className={`${styles.caret} ${isOpen ? styles.caretOpen : ''}`}>
                  ›
                </span>
              </button>

              {isOpen && (
                <div className={styles.grid}>
                  {cat.images.map((img) => {
                    const inQueue = queuedUrls.has(img.url)
                    return (
                      <button
                        key={img.url}
                        className={`${styles.thumb} ${inQueue ? styles.inQueue : ''} ${disabled ? styles.thumbDisabled : ''}`}
                        onClick={() => handleClick(img)}
                        draggable={!disabled}
                        onDragStart={(e) => handleDragStart(e, img)}
                        title={inQueue ? `${img.filename} (in queue)` : img.filename}
                        aria-label={`Add ${img.filename}`}
                      >
                        <img
                          src={img.url}
                          alt={img.filename}
                          className={styles.thumbImg}
                          loading="lazy"
                        />
                        {inQueue && (
                          <span className={styles.checkmark} aria-hidden>✓</span>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </aside>
  )
}
