import "@testing-library/jest-dom"

// jsdom does not implement scrollIntoView — stub it globally.
Element.prototype.scrollIntoView = () => {}

// Node.js 25 ships a built-in localStorage that is incomplete (no .clear, no URL context).
// Override with a proper in-memory implementation so vitest/jsdom tests work correctly.
if (typeof localStorage === "undefined" || typeof localStorage.clear !== "function") {
  const store: Record<string, string> = {}
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = String(value) },
      removeItem: (key: string) => { delete store[key] },
      clear: () => { Object.keys(store).forEach((k) => delete store[k]) },
      get length() { return Object.keys(store).length },
      key: (index: number) => Object.keys(store)[index] ?? null,
    },
    writable: true,
    configurable: true,
  })
}
