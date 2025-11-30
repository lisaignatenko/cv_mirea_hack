import styles from './Header.module.css';
import Logo from '../Logo/Logo.jsx';

function Header() {
  return (
    <header className={styles.header}>
      <Logo />
      <nav className={styles.nav}>
        <a href="#features">Функции</a>
        <a href="#flow">Как работает</a>
        <a href="#dashboard">Дашборд</a>
      </nav>
    </header>
  );
}

export default Header;
