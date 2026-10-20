import { useEffect, useRef, useState } from 'react';

// Ticks once per second down to 0, then calls onDone once. Pause with running = false.
export function useCountdown(initial: number, onDone: () => void, running = true) {
  const [left, setLeft] = useState(initial);
  const leftRef = useRef(initial);
  const done = useRef(onDone);
  useEffect(() => { done.current = onDone; });

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      const n = Math.max(0, leftRef.current - 1);
      leftRef.current = n;
      setLeft(n);
      if (n === 0) {
        clearInterval(id);
        done.current();
      }
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

  return left;
}
