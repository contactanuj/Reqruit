import "@testing-library/jest-dom";

// jsdom does not implement scrollIntoView — provide a stub
Element.prototype.scrollIntoView = () => {};

// jsdom does not implement window.matchMedia — provide a minimal stub
Object.defineProperty(window, "matchMedia", {
  writable: true,
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
