import styles from './Highlights.module.css';

const items = [
  { title: 'Поиск людей на видео', description: 'Трекинг по кадрам, тепловые карты, учет появления/исчезновения.' },
  { title: 'Понимание действий', description: 'Каталог типовых операций, аномалии, контроль СИЗ и зон риска.' },
  { title: 'Хранение и поиск', description: 'События и короткие клипы в удобном хранилище для быстрой проверки.' },
  { title: 'Дашборд эффективности', description: 'Статистика по сменам, SLA реагирования, отчетность для менеджмента.' }
];

function Highlights() {
  return (
    <section id="features" className={styles.section}>
      <div className={styles.header}>
        <p className={styles.kicker}>Зачем</p>
        <h2>Выжимаем ценность из видеопотока, а не просто сохраняем архив</h2>
        <p className={styles.sub}>
          Система работает в реальном времени, фиксирует контекст и превращает видео в цифры, понятные для бизнеса.
        </p>
      </div>
      <div className={styles.cards}>
        {items.map((item, index) => (
          <article key={item.title} className={styles.card}>
            <div className={styles.icon}>{index + 1}</div>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default Highlights;
