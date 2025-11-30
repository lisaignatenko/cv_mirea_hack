import { useMemo } from 'react';
import { useSegment } from '../../context/SegmentContext.jsx';
import styles from './DashboardPreview.module.css';

function DashboardPreview() {
  const { segment, totalViolations } = useSegment();

  const { eventStats, peopleCount, violations, zones, trainStatus } = useMemo(() => {
    if (!segment) {
      return { eventStats: [], peopleCount: 0, violations: 0, zones: 0, trainStatus: 'Нет данных' };
    }

    const events = segment.events ?? [];
    const people = segment.people ?? [];
    const statsMap = new Map();
    events.forEach((event) => {
      const key = event.event_type ?? 'unknown';
      statsMap.set(key, (statsMap.get(key) ?? 0) + 1);
    });
    const eventStats = Array.from(statsMap.entries())
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);

    const violations = people.filter(
      (person) => !person.is_in_allowed_zone || !person.is_activity_allowed || Boolean(person.violation_type)
    ).length;
    const zones = new Set(people.map((person) => person.zone).filter(Boolean)).size;
    const trainStatus = segment.train ? segment.train.status ?? 'Неизвестно' : 'Поезд отсутствует';

    return { eventStats, peopleCount: people.length, violations, zones, trainStatus };
  }, [segment]);

  const maxEventCount = Math.max(...eventStats.map((stat) => stat.count), 1);

  return (
    <section id="dashboard" className={styles.section}>
      <div className={styles.header}>
        <p className={styles.kicker}>Дашборд</p>
        <h2>Ключевые метрики в одном окне</h2>
        <p className={styles.sub}>Данные обновляются по последнему сегменту из CV.</p>
      </div>
      <div className={styles.preview}>
        <div className={styles.chartArea}>
          <div className={styles.chartHeader}>
            <span>События по типам</span>
            <span className={styles.pill}>{eventStats.length ? 'Актуальные данные' : 'Ожидаем события'}</span>
          </div>
          {eventStats.length > 0 ? (
            <div className={styles.bars}>
              {eventStats.map((stat) => (
                <div key={stat.type} className={styles.barGroup}>
                  <div
                    className={styles.bar}
                    style={{ height: `${30 + (stat.count / maxEventCount) * 70}px` }}
                  >
                    <span>{stat.count}</span>
                  </div>
                  <span className={styles.barLabel}>{stat.type}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className={styles.empty}>События ещё не поступали.</p>
          )}
        </div>
        <div className={styles.side}>
          <div className={styles.metric}>
            <p className={styles.metricLabel}>Людей в кадре</p>
            <p className={styles.metricValue}>{peopleCount}</p>
          </div>
          <div className={styles.metric}>
            <p className={styles.metricLabel}>Общее количество нарушений</p>
            <p className={styles.metricValue}>{totalViolations}</p>
          </div>
          <div className={styles.metric}>
            <p className={styles.metricLabel}>Активные зоны</p>
            <p className={styles.metricValue}>{zones}</p>
          </div>
          <div className={styles.metric}>
            <p className={styles.metricLabel}>Статус поезда</p>
            <p className={styles.metricValue}>{trainStatus}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default DashboardPreview;
