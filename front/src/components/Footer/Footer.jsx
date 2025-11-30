import styles from './Footer.module.css';
import Logo from '../Logo/Logo.jsx';

function Footer() {
  return (
    <footer className={styles.footer}>
      <Logo />
      <div className={styles.links}>
        <a href="#features">Функции</a>
        <a href="#flow">Процесс</a>
        <a href="#dashboard">Дашборд</a>
      </div>
      <p className={styles.copy}>© 2024 VisionOps. Демонстрация концепта.</p>
    </footer>
  );
}

export default Footer;
