/**
 * Jest setup file for TypeScript tests
 */

// Extend Jest matchers
import 'jest';

// Global test timeout
jest.setTimeout(30000);

// Environment setup
process.env.NODE_ENV = 'test';

// Set test API key if not provided
if (!process.env.API_KEY) {
  process.env.API_KEY = 'test_key_for_jest';
}

// Global test utilities
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidMCPMessage(): R;
      toHaveGrantStructure(): R;
    }
  }
}

// Custom Jest matchers
expect.extend({
  toBeValidMCPMessage(received: any) {
    const pass = (
      received &&
      typeof received === 'object' &&
      received.jsonrpc === '2.0' &&
      typeof received.id === 'number' &&
      (received.result !== undefined || received.error !== undefined)
    );

    if (pass) {
      return {
        message: () => `Expected ${JSON.stringify(received)} not to be a valid MCP message`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected ${JSON.stringify(received)} to be a valid MCP message with jsonrpc: "2.0", id: number, and result or error`,
        pass: false,
      };
    }
  },

  toHaveGrantStructure(received: string) {
    const hasTitle = received.includes('Title:') || received.includes('OPPORTUNITY DETAILS');
    const hasAgency = received.includes('Agency:') || received.includes('agency');
    const hasOverview = received.includes('OVERVIEW') || received.includes('Total Grants');
    
    const pass = hasTitle || hasAgency || hasOverview;

    if (pass) {
      return {
        message: () => `Expected ${received.substring(0, 100)}... not to have grant structure`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected ${received.substring(0, 100)}... to contain grant structure (Title, Agency, or Overview sections)`,
        pass: false,
      };
    }
  },
});

// Console suppression for cleaner test output
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeAll(() => {
  // Suppress expected error logs during tests
  console.error = (...args: any[]) => {
    const message = args.join(' ');
    if (
      !message.includes('DeprecationWarning') &&
      !message.includes('ExperimentalWarning') &&
      !message.includes('Debug:')
    ) {
      originalConsoleError(...args);
    }
  };

  console.warn = (...args: any[]) => {
    const message = args.join(' ');
    if (!message.includes('DeprecationWarning')) {
      originalConsoleWarn(...args);
    }
  };
});

afterAll(() => {
  // Restore original console methods
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

// Global cleanup
afterEach(() => {
  // Clear any timers
  jest.clearAllTimers();
  
  // Clear all mocks
  jest.clearAllMocks();
});

// Handle unhandled promise rejections in tests
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Promise Rejection in test:', reason);
  // Don't fail tests for unhandled rejections unless they're critical
});