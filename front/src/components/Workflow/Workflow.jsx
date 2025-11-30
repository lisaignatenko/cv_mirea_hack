import styles from './Workflow.module.css';

const steps = [
  {
    title: '1. Видео и зоны',
    text: 'Подключаем поток с камер, задаем зоны контроля и правила: СИЗ, маршруты, посторонние.'
  },
  {
    title: '2. Детекция и классификация',
    text: 'ИИ находит людей, фиксирует позы и действия, сопоставляет с рабочими операциями.'
  },
  {
    title: '3. События в базе',
    text: 'Каждое событие сохраняется с метаданными и клипом: кто, что, где, когда.'
  },
  {
    title: '4. Дашборд и оповещения',
    text: 'Данные попадают в дашборд: SLA реагирования, инциденты, срез по сменам и участкам.'
  }
];

function Workflow() {
  return (
    <section id="flow" className={styles.section}>
      <div className={styles.header}>
        <p className={styles.kicker}>Как работает</p>
        <h2>От видеопотока до метрики безопасности и эффективности</h2>
        <p className={styles.sub}>
          Система строит цепочку: обнаружение — интерпретация — сохранение — аналитика. Понятная логика для пилота и
          масштабирования.
        </p>
      </div>
      <div className={styles.steps}>
        {steps.map((step) => (
          <div key={step.title} className={styles.step}>
            <div className={styles.badge}>{step.title}</div>
            <p>{step.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default Workflow;
