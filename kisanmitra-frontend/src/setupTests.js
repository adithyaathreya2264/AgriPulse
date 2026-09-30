// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';

// jsdom has no IntersectionObserver / matchMedia / scrollTo, which the
// animations and the layout use.
class FakeIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}

global.ResizeObserver = global.ResizeObserver || FakeIntersectionObserver;
global.IntersectionObserver = global.IntersectionObserver || FakeIntersectionObserver;

window.matchMedia =
  window.matchMedia ||
  ((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }));

window.scrollTo = () => {};
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || (() => {});

// page transitions and animated panels take a moment in tests too

configure({ asyncUtilTimeout: 5000 });

// tests that cross a page transition need more than jest's default 5 seconds
jest.setTimeout(20000);
