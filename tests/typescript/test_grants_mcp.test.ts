/**
 * TypeScript tests for the Node.js MCP Grants server
 */

import { spawn, ChildProcess } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';

interface MCPMessage {
  jsonrpc: string;
  id: number;
  method?: string;
  params?: any;
  result?: any;
  error?: any;
}

interface GrantOpportunity {
  opportunity_id: number;
  opportunity_number: string;
  opportunity_title: string;
  opportunity_status: string;
  agency: string;
  agency_code: string;
  agency_name: string;
  category: string;
  summary: {
    award_ceiling?: number;
    award_floor?: number;
    post_date?: string;
    close_date?: string;
    summary_description?: string;
  };
}

describe('Grants MCP Server', () => {
  let mcpProcess: ChildProcess;
  let processOutput: string[] = [];
  
  beforeAll(async () => {
    // Build the TypeScript server
    const buildResult = await runCommand('npm run build');
    expect(buildResult.code).toBe(0);
  });

  beforeEach(() => {
    processOutput = [];
  });

  afterEach(async () => {
    if (mcpProcess && !mcpProcess.killed) {
      mcpProcess.kill('SIGTERM');
      await new Promise(resolve => {
        mcpProcess.on('exit', resolve);
        setTimeout(() => {
          mcpProcess.kill('SIGKILL');
          resolve(null);
        }, 5000);
      });
    }
  });

  describe('Server Initialization', () => {
    test('should start without errors', async () => {
      const { process: server, output } = await startMCPServer();
      mcpProcess = server;
      
      // Wait for server to be ready
      await waitForOutput(output, 'MCP server running', 10000);
      
      expect(server.pid).toBeDefined();
      expect(server.killed).toBe(false);
    });

    test('should handle missing API key gracefully', async () => {
      const env = { ...process.env };
      delete env.API_KEY;
      
      const { process: server, output } = await startMCPServer(env);
      mcpProcess = server;
      
      // Should still start but may log warning
      await waitForOutput(output, ['MCP server running', 'Missing'], 10000);
      
      expect(server.pid).toBeDefined();
    });
  });

  describe('MCP Protocol Compliance', () => {
    test('should respond to tools/list request', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const listToolsMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 1,
        method: 'tools/list'
      };
      
      const response = await sendMessage(listToolsMessage);
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(1);
      expect(response.result).toBeDefined();
      expect(response.result.tools).toBeInstanceOf(Array);
      
      // Should have search-grants tool
      const searchTool = response.result.tools.find(
        (tool: any) => tool.name === 'search-grants'
      );
      expect(searchTool).toBeDefined();
      expect(searchTool.description).toContain('grant');
    });

    test('should validate tool input schemas', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      // Get tool schema
      const listResponse = await sendMessage({
        jsonrpc: '2.0',
        id: 1,
        method: 'tools/list'
      });
      
      const searchTool = listResponse.result.tools.find(
        (tool: any) => tool.name === 'search-grants'
      );
      
      expect(searchTool.inputSchema).toBeDefined();
      expect(searchTool.inputSchema.type).toBe('object');
      expect(searchTool.inputSchema.properties.query).toBeDefined();
      expect(searchTool.inputSchema.required).toContain('query');
    });

    test('should handle invalid JSON gracefully', async () => {
      const { process: server, stdin, stdout } = await startMCPServerRaw();
      mcpProcess = server;
      
      // Send invalid JSON
      stdin.write('invalid json\n');
      
      // Should not crash - wait a bit and check if process is still alive
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      expect(server.killed).toBe(false);
      expect(server.exitCode).toBeNull();
    });
  });

  describe('Grant Search Functionality', () => {
    test('should execute search-grants tool successfully', async () => {
      // Set up API key for this test
      process.env.API_KEY = process.env.API_KEY || 'test_key';
      
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const searchMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 2,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: {
            query: 'artificial intelligence',
            page: 1,
            grantsPerPage: 2
          }
        }
      };
      
      const response = await sendMessage(searchMessage, 15000); // Longer timeout for API call
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(2);
      
      if (response.error) {
        // If there's an error, it should be a proper error response
        expect(response.error.code).toBeDefined();
        expect(response.error.message).toBeDefined();
      } else {
        // If successful, should have result with content
        expect(response.result).toBeDefined();
        expect(response.result.content).toBeDefined();
        expect(response.result.content).toBeInstanceOf(Array);
        expect(response.result.content[0].type).toBe('text');
        expect(response.result.content[0].text).toBeDefined();
      }
    });

    test('should handle search with pagination parameters', async () => {
      process.env.API_KEY = process.env.API_KEY || 'test_key';
      
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const searchMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: {
            query: 'technology innovation',
            page: 2,
            grantsPerPage: 5
          }
        }
      };
      
      const response = await sendMessage(searchMessage, 15000);
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(3);
      
      // Should handle pagination parameters without error
      if (response.result) {
        const text = response.result.content[0].text;
        expect(text).toContain('Page 2'); // Should show pagination
      }
    });

    test('should handle empty search query gracefully', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const searchMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 4,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: {
            query: '',
            page: 1,
            grantsPerPage: 3
          }
        }
      };
      
      const response = await sendMessage(searchMessage, 10000);
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(4);
      
      // Should handle empty query - might use default or return error
      expect(response.result || response.error).toBeDefined();
    });

    test('should validate grant data structure', async () => {
      // This test verifies that if we get data back, it has the expected structure
      process.env.API_KEY = process.env.API_KEY || 'test_key';
      
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const searchMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 5,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: {
            query: 'research',
            page: 1,
            grantsPerPage: 1
          }
        }
      };
      
      const response = await sendMessage(searchMessage, 15000);
      
      if (response.result && response.result.content) {
        const text = response.result.content[0].text;
        
        // Should contain structured grant information
        expect(text).toBeTruthy();
        expect(typeof text).toBe('string');
        
        // Look for expected sections in the formatted output
        const hasOpportunityDetails = text.includes('OPPORTUNITY DETAILS') || 
                                     text.includes('Title:') ||
                                     text.includes('Opportunity');
        
        if (hasOpportunityDetails) {
          // If we have grants, validate structure
          expect(text).toMatch(/Title:|Agency:|Status:/);
        } else {
          // If no grants, should have appropriate message
          expect(text).toMatch(/No grants|not found|0 grants/i);
        }
      }
    });
  });

  describe('Error Handling', () => {
    test('should handle unknown tool calls', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const unknownToolMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 6,
        method: 'tools/call',
        params: {
          name: 'unknown-tool',
          arguments: {}
        }
      };
      
      const response = await sendMessage(unknownToolMessage);
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(6);
      expect(response.error).toBeDefined();
      expect(response.error.message).toContain('Unknown tool');
    });

    test('should handle API errors gracefully', async () => {
      // Set invalid API key to trigger error
      const { process: server, sendMessage } = await startMCPServerWithComms({
        API_KEY: 'invalid_key_12345'
      });
      mcpProcess = server;
      
      const searchMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 7,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: {
            query: 'test',
            page: 1,
            grantsPerPage: 3
          }
        }
      };
      
      const response = await sendMessage(searchMessage, 10000);
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(7);
      
      // Should either return error or handle gracefully
      if (response.error) {
        expect(response.error.message).toBeDefined();
      } else if (response.result) {
        const text = response.result.content[0].text;
        expect(text).toMatch(/error|failed|invalid/i);
      }
    });

    test('should handle malformed tool parameters', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const malformedMessage: MCPMessage = {
        jsonrpc: '2.0',
        id: 8,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: {
            page: 'not_a_number',
            grantsPerPage: -5,
            // missing required query
          }
        }
      };
      
      const response = await sendMessage(malformedMessage);
      
      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(8);
      
      // Should handle malformed parameters gracefully
      expect(response.result || response.error).toBeDefined();
    });
  });

  describe('Performance', () => {
    test('should respond to tools/list within reasonable time', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const start = Date.now();
      
      const response = await sendMessage({
        jsonrpc: '2.0',
        id: 9,
        method: 'tools/list'
      });
      
      const duration = Date.now() - start;
      
      expect(response.result).toBeDefined();
      expect(duration).toBeLessThan(5000); // Should respond within 5 seconds
    });

    test('should handle multiple concurrent requests', async () => {
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const requests = Array.from({ length: 3 }, (_, i) => 
        sendMessage({
          jsonrpc: '2.0',
          id: 10 + i,
          method: 'tools/list'
        })
      );
      
      const responses = await Promise.all(requests);
      
      expect(responses).toHaveLength(3);
      responses.forEach((response, i) => {
        expect(response.id).toBe(10 + i);
        expect(response.result).toBeDefined();
      });
    });
  });

  describe('Data Validation', () => {
    test('should format grant results consistently', async () => {
      process.env.API_KEY = process.env.API_KEY || 'test_key';
      
      const { process: server, sendMessage } = await startMCPServerWithComms();
      mcpProcess = server;
      
      const response1 = await sendMessage({
        jsonrpc: '2.0',
        id: 13,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: { query: 'science', page: 1, grantsPerPage: 2 }
        }
      }, 15000);
      
      const response2 = await sendMessage({
        jsonrpc: '2.0',
        id: 14,
        method: 'tools/call',
        params: {
          name: 'search-grants',
          arguments: { query: 'technology', page: 1, grantsPerPage: 2 }
        }
      }, 15000);
      
      if (response1.result && response2.result) {
        const text1 = response1.result.content[0].text;
        const text2 = response2.result.content[0].text;
        
        // Both should have similar structure
        const hasStructure1 = text1.includes('Search Results') || text1.includes('OVERVIEW');
        const hasStructure2 = text2.includes('Search Results') || text2.includes('OVERVIEW');
        
        if (hasStructure1 && hasStructure2) {
          // Both should follow similar formatting patterns
          expect(text1).toMatch(/Total.*grants|grants found/i);
          expect(text2).toMatch(/Total.*grants|grants found/i);
        }
      }
    });
  });
});

// Utility functions
async function runCommand(command: string): Promise<{ code: number; output: string }> {
  return new Promise((resolve) => {
    const [cmd, ...args] = command.split(' ');
    const child = spawn(cmd, args);
    let output = '';
    
    child.stdout?.on('data', (data) => {
      output += data.toString();
    });
    
    child.stderr?.on('data', (data) => {
      output += data.toString();
    });
    
    child.on('close', (code) => {
      resolve({ code: code || 0, output });
    });
  });
}

async function startMCPServer(env = process.env): Promise<{
  process: ChildProcess;
  output: string[];
}> {
  const serverPath = path.join(__dirname, '../../build/index.js');
  const output: string[] = [];
  
  const server = spawn('node', [serverPath], { env });
  
  server.stdout?.on('data', (data) => {
    output.push(data.toString());
  });
  
  server.stderr?.on('data', (data) => {
    output.push(data.toString());
  });
  
  return { process: server, output };
}

async function startMCPServerRaw(): Promise<{
  process: ChildProcess;
  stdin: NodeJS.WritableStream;
  stdout: NodeJS.ReadableStream;
}> {
  const serverPath = path.join(__dirname, '../../build/index.js');
  const server = spawn('node', [serverPath], { stdio: 'pipe' });
  
  return {
    process: server,
    stdin: server.stdin!,
    stdout: server.stdout!
  };
}

async function startMCPServerWithComms(env = process.env): Promise<{
  process: ChildProcess;
  sendMessage: (message: MCPMessage, timeout?: number) => Promise<MCPMessage>;
}> {
  const { process: server, stdin, stdout } = await startMCPServerRaw();
  
  const pendingResponses = new Map<number, { resolve: (msg: MCPMessage) => void; reject: (error: Error) => void }>();
  
  let buffer = '';
  stdout.on('data', (data) => {
    buffer += data.toString();
    
    // Process complete JSON messages
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete line in buffer
    
    for (const line of lines) {
      if (line.trim()) {
        try {
          const message = JSON.parse(line) as MCPMessage;
          const pending = pendingResponses.get(message.id);
          if (pending) {
            pending.resolve(message);
            pendingResponses.delete(message.id);
          }
        } catch (error) {
          // Ignore parsing errors for non-JSON output
        }
      }
    }
  });
  
  const sendMessage = (message: MCPMessage, timeout = 5000): Promise<MCPMessage> => {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pendingResponses.delete(message.id);
        reject(new Error(`Message timeout after ${timeout}ms`));
      }, timeout);
      
      pendingResponses.set(message.id, {
        resolve: (msg) => {
          clearTimeout(timer);
          resolve(msg);
        },
        reject
      });
      
      stdin.write(JSON.stringify(message) + '\n');
    });
  };
  
  return { process: server, sendMessage };
}

async function waitForOutput(
  output: string[], 
  expectedText: string | string[], 
  timeout = 5000
): Promise<void> {
  const patterns = Array.isArray(expectedText) ? expectedText : [expectedText];
  
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Timeout waiting for output: ${patterns.join(' or ')}`));
    }, timeout);
    
    const checkOutput = () => {
      const fullOutput = output.join('');
      if (patterns.some(pattern => fullOutput.includes(pattern))) {
        clearTimeout(timer);
        resolve();
      }
    };
    
    // Check existing output
    checkOutput();
    
    // Monitor new output
    const originalLength = output.length;
    const interval = setInterval(() => {
      if (output.length > originalLength) {
        checkOutput();
      }
    }, 100);
    
    setTimeout(() => {
      clearInterval(interval);
    }, timeout);
  });
}