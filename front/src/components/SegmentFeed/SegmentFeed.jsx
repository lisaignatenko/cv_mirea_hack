import { useMemo } from 'react';
import { useSegment } from '../../context/SegmentContext.jsx';
import styles from './SegmentFeed.module.css';

function SegmentFeed() {
  const { segment, error, loading, refresh } = useSegment();

  const tickInfo = useMemo(() => {
    if (!segment) {
      return null;
    }
    const timestamp = new Date(segment.timestamp).toLocaleString();
    return `Тик ${segment.tick} · ${timestamp}`;
  }, [segment]);

  const trainInfo = useMemo(() => {
    if (!segment?.train) {
      return null;
    }
    const { train } = segment;
    const bbox = train.bbox
      ? `x1:${train.bbox.x1}, y1:${train.bbox.y1}, x2:${train.bbox.x2}, y2:${train.bbox.y2}`
      : '—';
    const bboxSize =
      train.bbox != null
        ? `(${train.bbox.x2 - train.bbox.x1}px × ${train.bbox.y2 - train.bbox.y1}px)`
        : '';
    const detectionConfidence = train.confidence?.detection ?? null;
    const statusConfidence = train.confidence?.status ?? null;

    return {
      isPresent: train.is_present ? 'Да' : 'Нет',
      status: train.status ?? '—',
      id: train.train_id ?? '—',
      bbox,
      bboxSize,
      detectionConfidence:
        detectionConfidence != null ? `${Math.round(detectionConfidence * 100)}%` : '—',
      statusConfidence:
        statusConfidence != null ? `${Math.round(statusConfidence * 100)}%` : '—'
    };
  }, [segment]);

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <p className={styles.kicker}>Поток сегментов</p>
        <h2>Последний пакет данных CV</h2>
        <p className={styles.sub}>
          Периодически запрашиваем эндпоинт <code>/segment</code> и отображаем распознанные объекты.
        </p>
        <div className={styles.actions}>
          <button className={styles.button} onClick={refresh} disabled={loading}>
            {loading ? 'Обновляем...' : 'Обновить сейчас'}
          </button>
          {tickInfo && <span className={styles.badge}>{tickInfo}</span>}
        </div>
        {error && <p className={styles.error}>{error}</p>}
      </div>

      {segment && (
        <div className={styles.grid}>
          <div className={styles.card}>
            <p className={styles.label}>Камера</p>
            <p className={styles.value}>{segment.camera ?? '—'}</p>
            {trainInfo && (
              <div className={styles.meta}>
                <span>Присутствие: {trainInfo.isPresent}</span>
                <span>ID: {trainInfo.id}</span>
                <span>Статус: {trainInfo.status}</span>
                <span>bbox: {trainInfo.bbox} {trainInfo.bboxSize}</span>
                <span>Conf. detection: {trainInfo.detectionConfidence}</span>
                <span>Conf. status: {trainInfo.statusConfidence}</span>
              </div>
            )}
          </div>

          <div className={styles.card}>
            <p className={styles.label}>Объекты</p>
            <p className={styles.value}>{segment.people?.length ?? 0}</p>
            <ul className={styles.list}>
              {(segment.people ?? []).map((person) => (
                <li key={person.track_id}>
                  <b>{person.role ?? 'unknown'}</b> · {person.activity ?? '—'} ·{' '}
                  {person.zone ?? '—'}
                </li>
              ))}
            </ul>
          </div>

          <div className={styles.card}>
            <p className={styles.label}>События</p>
            <p className={styles.value}>{segment.events?.length ?? 0}</p>
            <ul className={styles.list}>
              {(segment.events ?? []).map((event) => (
                <li key={event.event_id}>
                  <b>{event.event_type}</b> · {event.role ?? '—'} ·{' '}
                  {new Date(event.start_time).toLocaleTimeString()}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

    </section>
  );
}

export default SegmentFeed;
