import { useMemo } from 'react';
import { useSegment } from '../../context/SegmentContext.jsx';
import styles from './DataCards.module.css';

function DataCards() {
  const { segment } = useSegment();

  const cards = useMemo(() => {
    if (!segment) {
      return [
        { label: 'Людей в кадре', value: '—', accent: 'Нет данных' },
        { label: 'Нарушения', value: '—', accent: 'Нет данных' },
        { label: 'Последнее событие', value: '—', accent: 'Нет данных' }
      ];
    }

    const people = segment.people ?? [];
    const events = segment.events ?? [];
    const peopleCount = people.length;
    const violations = people.filter(
      (person) => !person.is_in_allowed_zone || !person.is_activity_allowed || Boolean(person.violation_type)
    ).length;
    const allowedPercent = peopleCount === 0 ? 100 : Math.round(((peopleCount - violations) / peopleCount) * 100);
    const lastEvent = events[events.length - 1];

    return [
      {
        label: 'Людей в кадре',
        value: String(peopleCount),
        accent: peopleCount > 0 ? 'Отслеживаем' : 'Кадр пуст'
      },
      {
        label: 'Нарушения',
        value: String(violations),
        accent: violations > 0 ? 'Требует внимания' : 'Норма'
      },
      {
        label: 'Последнее событие',
        value: lastEvent ? lastEvent.event_type : 'Нет событий',
        accent: lastEvent
          ? `${lastEvent.zone ?? '—'} · ${new Date(lastEvent.start_time).toLocaleTimeString()}`
          : 'Ожидаем данные'
      }
    ];
  }, [segment]);

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <p className={styles.kicker}>Структура данных</p>
        <h2>Фиксируем события, сохраняем клипы, выдаем аналитику в реальном времени</h2>
      </div>
      <div className={styles.cards}>
        {cards.map((card) => (
          <div key={card.label} className={styles.card}>
            <div className={styles.top}>
              <p className={styles.label}>{card.label}</p>
              <span className={styles.accent}>{card.accent}</span>
            </div>
            <p className={styles.value}>{card.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default DataCards;
