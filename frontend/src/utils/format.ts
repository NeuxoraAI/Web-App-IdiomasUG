// mm:ss
export const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

export const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((w) => w[0] || '').join('').toUpperCase();
