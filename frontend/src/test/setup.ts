import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';
import { installApiMock } from './apiMock';

function createLocalStorageMock(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key) {
      return values.get(String(key)) ?? null;
    },
    key(index) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key) {
      values.delete(String(key));
    },
    setItem(key, value) {
      values.set(String(key), String(value));
    },
  };
}

// Node 26 exposes a global localStorage getter that returns undefined unless
// --localstorage-file is provided. Vitest copies it over jsdom's implementation.
if (typeof window.localStorage === 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: createLocalStorageMock(),
  });
}

beforeEach(() => {
  installApiMock();
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
  configurable: true,
  value: vi.fn(),
});

Object.defineProperty(window, 'scrollTo', {
  configurable: true,
  value: vi.fn(),
});
