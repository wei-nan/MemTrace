/**
 * ReviewCounterBadge — T24
 * Shows the count of pending review proposals in the graph toolbar.
 * Clicking it triggers the review overlay.
 */
import { useEffect, useState, useCallback } from 'react';
import { Clock } from 'lucide-react';
import { review } from './api';

interface Props {
  wsId: string;
  onClick: () => void;
  /** Interval in ms to re-fetch the count (default: 30 000) */
  pollMs?: number;
}

export default function ReviewCounterBadge({ wsId, onClick, pollMs = 30_000 }: Props) {
  const [count, setCount] = useState<number | null>(null);

  const fetchCount = useCallback(async () => {
    if (!wsId) return;
    try {
      const items = await review.list(wsId, 'pending');
      setCount(items.length);
    } catch {
      // silently ignore — badge degrades gracefully
    }
  }, [wsId]);

  useEffect(() => {
    fetchCount();
    const id = setInterval(fetchCount, pollMs);
    return () => clearInterval(id);
  }, [fetchCount, pollMs]);

  if (count === null) return null;

  return (
    <button
      className={`review-counter-badge${count === 0 ? ' zero' : ''}`}
      onClick={onClick}
      title={count === 0 ? 'No pending reviews' : `${count} proposal${count === 1 ? '' : 's'} pending review`}
      id="review-counter-badge"
    >
      <Clock size={11} />
      <span>{count}</span>
    </button>
  );
}
