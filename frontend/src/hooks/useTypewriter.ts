import { useEffect, useState } from 'react';

// Character count revealed so far, one more every 18 ms until `total`.
// Remount (change the key) to start over.
export function useTypewriter(total: number) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (count >= total) return;
    const id = setTimeout(() => setCount(count + 1), 18);
    return () => clearTimeout(id);
  }, [count, total]);
  return count;
}
