import styles from './Hero.module.css';

function Hero() {
  return (
    <section className={styles.hero}>
      <div className={styles.badge}>ИИ-мониторинг завода 24/7</div>
      <h1>
        «Умная» система анализа видео <span className={styles.accent}>для людей и процессов</span>
      </h1>
      <p className={styles.lead}>
        Находит людей на видеопотоке, понимает действия, фиксирует события и выводит наглядную статистику. Всё для
        повышения эффективности и безопасности цеха.
      </p>
      <div className={styles.grid}>
        <div className={styles.card}>
          <div className={styles.label}>Обнаружение</div>
          <div className={styles.value}>Люди, зоны, СИЗ</div>
        </div>
        <div className={styles.card}>
          <div className={styles.label}>Контекст</div>
          <div className={styles.value}>Действия, маршруты, инциденты</div>
        </div>
        <div className={styles.card}>
          <div className={styles.label}>Хранилище</div>
          <div className={styles.value}>События + клипы в базе</div>
        </div>
        <div className={styles.card}>
          <div className={styles.label}>Дашборд</div>
          <div className={styles.value}>Статистика и SLA в реальном времени</div>
        </div>
      </div>
    </section>
  );
}

export default Hero;
