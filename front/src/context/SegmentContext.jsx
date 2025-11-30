import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';

const SegmentContext = createContext(null);
const REFRESH_INTERVAL_MS = 5000;

export function SegmentProvider({ children }) {
  const [segment, setSegment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [totalActions, setTotalActions] = useState(0);
  const [totalViolations, setTotalViolations] = useState(0);
  const segmentIndexRef = useRef(0);

  const fetchSegment = useCallback(async () => {
    setError('');
    setLoading(true);
    try {
      const frameId = segmentIndexRef.current;
      const data = await api.fetchSegment(frameId);
      setSegment(data);
      segmentIndexRef.current = frameId + 1;

      const people = data?.people ?? [];
      if (people.length > 0) {
        setTotalActions((prev) => prev + people.length);
        const violationsInSegment = people.filter(
          (person) => !person.is_in_allowed_zone || !person.is_activity_allowed || Boolean(person.violation_type)
        ).length;
        setTotalViolations((prev) => prev + violationsInSegment);
        setHistory((prev) => {
          const nextEntries = people.map((person) => ({
            id: `${data.tick}-${person.track_id}`,
            tick: data.tick,
            trackId: person.track_id,
            role: person.role ?? 'unknown',
            activity: person.activity ?? '—',
            zone: person.violation_type ?? '—',
            confidence:
              person.confidence?.person != null
                ? Math.round(person.confidence.person * 100)
                : null,
            timestamp: data.timestamp ?? new Date().toISOString()
          }));
          return [...nextEntries, ...prev];
        });
      }
    } catch (err) {
      setError(err.message ?? 'Не удалось получить сегмент');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSegment();
    const interval = setInterval(fetchSegment, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchSegment]);

  const value = useMemo(
    () => ({
      segment,
      loading,
      error,
      refresh: fetchSegment,
      history,
      totalActions,
      totalViolations
    }),
    [segment, loading, error, fetchSegment, history, totalActions, totalViolations]
  );

  return <SegmentContext.Provider value={value}>{children}</SegmentContext.Provider>;
}

export function useSegment() {
  const context = useContext(SegmentContext);
  if (context === null) {
    throw new Error('useSegment должен вызываться внутри SegmentProvider');
  }
  return context;
}
