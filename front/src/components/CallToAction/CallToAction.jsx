import styles from './CallToAction.module.css';

function CallToAction() {
  return (
    <section className={styles.section}>
      <div className={styles.card}>
        <div>
          <p className={styles.kicker}>Старт пилота</p>
          <h3>Покажем пилотный дашборд за 2 недели</h3>
          <p className={styles.sub}>
            Подключим камеру, настроим зоны, соберем первые метрики и предоставим интерфейс для проверки гипотез.
          </p>
        </div>
        <button className={styles.button}>Запросить демо</button>
      </div>
    </section>
  );
}

export default CallToAction;
