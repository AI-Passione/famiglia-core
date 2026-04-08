import "@testing-library/jest-dom";
import { vi } from "vitest";

// Global mocks for browser APIs
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

class IntersectionObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: IntersectionObserverMock,
});

// Mock ResizeObserver
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
});

// Mock scrollIntoView and scrollTo as they are not implemented in JSDOM
if (typeof Array !== 'undefined' && typeof window !== 'undefined') {
  window.Element.prototype.scrollIntoView = vi.fn();
  window.Element.prototype.scrollTo = vi.fn();
}

const localStorageStore = new Map<string, string>();

Object.defineProperty(window, 'localStorage', {
  writable: true,
  value: {
    getItem: (key: string) => localStorageStore.get(key) ?? null,
    setItem: (key: string, value: string) => localStorageStore.set(key, value),
    removeItem: (key: string) => localStorageStore.delete(key),
    clear: () => localStorageStore.clear(),
  },
});

// Mock Framer Motion to disable animations during tests
vi.mock('framer-motion', async () => {
  const React = await import('react');
  const actual = await vi.importActual('framer-motion') as any;
  
  const mockComponent = (tag: string) => {
    return React.forwardRef(({ children, ...props }: any, ref: any) => {
      // Filter out motion-specific props
      const filteredProps = { ...props };
      const motionProps = [
        'initial', 'animate', 'exit', 'transition', 'variants', 
        'whileHover', 'whileTap', 'whileDrag', 'whileFocus', 'whileInView', 
        'onAnimationStart', 'onAnimationComplete', 'onUpdate', 
        'onPan', 'onPanStart', 'onPanEnd', 'onTap', 'onTapStart', 'onTapCancel',
        'layout', 'layoutId', 'layoutRoot', 'drag', 'dragConstraints', 'dragElastic', 'dragSnapToOrigin'
      ];
      motionProps.forEach(p => delete filteredProps[p]);
      
      return React.createElement(tag, { ...filteredProps, ref }, children);
    });
  };

  return {
    ...actual,
    motion: {
      div: mockComponent('div'),
      span: mockComponent('span'),
      button: mockComponent('button'),
      h1: mockComponent('h1'),
      h2: mockComponent('h2'),
      h3: mockComponent('h3'),
      h4: mockComponent('h4'),
      p: mockComponent('p'),
      section: mockComponent('section'),
      ul: mockComponent('ul'),
      li: mockComponent('li'),
      nav: mockComponent('nav'),
      svg: mockComponent('svg'),
      path: mockComponent('path'),
    },
    AnimatePresence: ({ children }: any) => React.createElement(React.Fragment, null, children),
  };
});
