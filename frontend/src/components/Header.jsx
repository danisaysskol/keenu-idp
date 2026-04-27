import styles from './Header.module.css'

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <div className={styles.brand}>
          <span className={styles.logo}>⬡</span>
          <div>
            <span className={styles.name}>Keenu</span>
            <span className={styles.tagline}>Simplifying Digital Payments</span>
          </div>
        </div>
        <div className={styles.badge}>
          <span className={styles.badgeDot} />
          IDP System
        </div>
      </div>
    </header>
  )
}
