import styles from './Logo.module.css';

function Logo() {
  return (
    <div className={styles.logo}>
      <div className={styles.spark} />
      <div>
        <div className={styles.title}>VisionOps</div>
        <div className={styles.subtitle}>умная видео-аналитика</div>
      </div>
    </div>
  );
}

export default Logo;
