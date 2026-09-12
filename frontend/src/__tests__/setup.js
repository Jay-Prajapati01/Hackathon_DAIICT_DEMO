import '@testing-library/jest-dom/vitest';

// jsdom lacks ResizeObserver (used by Recharts' ResponsiveContainer)
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver || ResizeObserver;
window.scrollTo = () => {};

// Some jsdom/Vitest combinations do not expose localStorage on the global scope.
function memoryStorage() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(String(k)) ? store.get(String(k)) : null),
    setItem: (k, v) => store.set(String(k), String(v)),
    removeItem: (k) => store.delete(String(k)),
    clear: () => store.clear(),
    key: (i) => [...store.keys()][i] ?? null,
    get length() { return store.size; },
  };
}
let hasStorage = false;
try { hasStorage = typeof globalThis.localStorage?.getItem === 'function'; } catch { hasStorage = false; }
if (!hasStorage) {
  const storage = memoryStorage();
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true, writable: true });
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'localStorage', { value: storage, configurable: true, writable: true });
  }
}
