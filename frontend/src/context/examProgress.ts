// Current question index. The server keeps it too (PUT /intento/posicion) so
// the exam resumes on another device; sessionStorage covers a reload whose
// last position save didn't reach the server.

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

interface ExamProgress {
  q: number;
  setQ: (q: number) => void;
  reset: () => void;
}

export const useExamProgress = create<ExamProgress>()(
  persist(
    (set) => ({
      q: 0,
      setQ: (q) => set({ q }),
      reset: () => set({ q: 0 }),
    }),
    { name: 'exaubi-progreso', storage: createJSONStorage(() => sessionStorage) },
  ),
);
