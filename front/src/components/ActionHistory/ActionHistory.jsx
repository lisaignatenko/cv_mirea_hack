import { useSegment } from '../../context/SegmentContext.jsx';
import styles from './ActionHistory.module.css';

function ActionHistory() {
  const { history, loading } = useSegment();

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <p className={styles.kicker}>События по действиям</p>
        <h2>История наблюдений и confidence</h2>
        <p className={styles.sub}>Фиксируем последние распознанные активности людей на камере.</p>
      </div>

      {history.length === 0 ? (
        <div className={styles.empty}>
          {loading ? 'Загружаем данные…' : 'История появится, как только придут новые действия.'}
        </div>
      ) : (
        <div className={styles.table}>
          <div className={styles.rowHead}>
            <span>Tick</span>
            <span>Участник</span>
            <span>Действие</span>
            <span>Зона</span>
            <span>Confidence</span>
          </div>
          {history.map((entry) => (
            <div key={entry.id} className={styles.row}>
              <span>{entry.tick}</span>
              <span>#{entry.trackId} · {entry.role}</span>
              <span>{entry.activity}</span>
              <span>{entry.zone}</span>
              <span>{entry.confidence != null ? `${entry.confidence}%` : '—'}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default ActionHistory;
