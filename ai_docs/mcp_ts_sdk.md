# This is the Typescript SDK Documentation for MCP

================================================
FILE: README.md
================================================
# MCP TypeScript SDK ![NPM Version](https://img.shields.io/npm/v/%40modelcontextprotocol%2Fsdk) ![MIT licensed](https://img.shields.io/npm/l/%40modelcontextprotocol%2Fsdk)

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quickstart](#quick-start)
- [What is MCP?](#what-is-mcp)
- [Core Concepts](#core-concepts)
  - [Server](#server)
  - [Resources](#resources)
  - [Tools](#tools)
  - [Prompts](#prompts)
  - [Completions](#completions)
  - [Sampling](#sampling)
- [Running Your Server](#running-your-server)
  - [stdio](#stdio)
  - [Streamable HTTP](#streamable-http)
  - [Testing and Debugging](#testing-and-debugging)
- [Examples](#examples)
  - [Echo Server](#echo-server)
  - [SQLite Explorer](#sqlite-explorer)
- [Advanced Usage](#advanced-usage)
  - [Dynamic Servers](#dynamic-servers)
  - [Low-Level Server](#low-level-server)
  - [Writing MCP Clients](#writing-mcp-clients)
  - [Proxy Authorization Requests Upstream](#proxy-authorization-requests-upstream)
  - [Backwards Compatibility](#backwards-compatibility)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Model Context Protocol allows applications to provide context for LLMs in a standardized way, separating the concerns of providing context from the actual LLM interaction. This TypeScript SDK implements the full MCP specification, making it easy to:

- Build MCP clients that can connect to any MCP server
- Create MCP servers that expose resources, prompts and tools
- Use standard transports like stdio and Streamable HTTP
- Handle all MCP protocol messages and lifecycle events

## Installation

```bash
npm install @modelcontextprotocol/sdk
```

> ⚠️ MCP requires Node.js v18.x or higher to work fine.

## Quick Start

Let's create a simple MCP server that exposes a calculator tool and some data:

```typescript
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// Create an MCP server
const server = new McpServer({
  name: "demo-server",
  version: "1.0.0"
});

// Add an addition tool
server.registerTool("add",
  {
    title: "Addition Tool",
    description: "Add two numbers",
    inputSchema: { a: z.number(), b: z.number() }
  },
  async ({ a, b }) => ({
    content: [{ type: "text", text: String(a + b) }]
  })
);

// Add a dynamic greeting resource
server.registerResource(
  "greeting",
  new ResourceTemplate("greeting://{name}", { list: undefined }),
  { 
    title: "Greeting Resource",      // Display name for UI
    description: "Dynamic greeting generator"
  },
  async (uri, { name }) => ({
    contents: [{
      uri: uri.href,
      text: `Hello, ${name}!`
    }]
  })
);

// Start receiving messages on stdin and sending messages on stdout
const transport = new StdioServerTransport();
await server.connect(transport);
```

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets you build servers that expose data and functionality to LLM applications in a secure, standardized way. Think of it like a web API, but specifically designed for LLM interactions. MCP servers can:

- Expose data through **Resources** (think of these sort of like GET endpoints; they are used to load information into the LLM's context)
- Provide functionality through **Tools** (sort of like POST endpoints; they are used to execute code or otherwise produce a side effect)
- Define interaction patterns through **Prompts** (reusable templates for LLM interactions)
- And more!

## Core Concepts

### Server

The McpServer is your core interface to the MCP protocol. It handles connection management, protocol compliance, and message routing:

```typescript
const server = new McpServer({
  name: "my-app",
  version: "1.0.0"
});
```

### Resources

Resources are how you expose data to LLMs. They're similar to GET endpoints in a REST API - they provide data but shouldn't perform significant computation or have side effects:

```typescript
// Static resource
server.registerResource(
  "config",
  "config://app",
  {
    title: "Application Config",
    description: "Application configuration data",
    mimeType: "text/plain"
  },
  async (uri) => ({
    contents: [{
      uri: uri.href,
      text: "App configuration here"
    }]
  })
);

// Dynamic resource with parameters
server.registerResource(
  "user-profile",
  new ResourceTemplate("users://{userId}/profile", { list: undefined }),
  {
    title: "User Profile",
    description: "User profile information"
  },
  async (uri, { userId }) => ({
    contents: [{
      uri: uri.href,
      text: `Profile data for user ${userId}`
    }]
  })
);

// Resource with context-aware completion
server.registerResource(
  "repository",
  new ResourceTemplate("github://repos/{owner}/{repo}", {
    list: undefined,
    complete: {
      // Provide intelligent completions based on previously resolved parameters
      repo: (value, context) => {
        if (context?.arguments?.["owner"] === "org1") {
          return ["project1", "project2", "project3"].filter(r => r.startsWith(value));
        }
        return ["default-repo"].filter(r => r.startsWith(value));
      }
    }
  }),
  {
    title: "GitHub Repository",
    description: "Repository information"
  },
  async (uri, { owner, repo }) => ({
    contents: [{
      uri: uri.href,
      text: `Repository: ${owner}/${repo}`
    }]
  })
);
```

### Tools

Tools let LLMs take actions through your server. Unlike resources, tools are expected to perform computation and have side effects:

```typescript
// Simple tool with parameters
server.registerTool(
  "calculate-bmi",
  {
    title: "BMI Calculator",
    description: "Calculate Body Mass Index",
    inputSchema: {
      weightKg: z.number(),
      heightM: z.number()
    }
  },
  async ({ weightKg, heightM }) => ({
    content: [{
      type: "text",
      text: String(weightKg / (heightM * heightM))
    }]
  })
);

// Async tool with external API call
server.registerTool(
  "fetch-weather",
  {
    title: "Weather Fetcher",
    description: "Get weather data for a city",
    inputSchema: { city: z.string() }
  },
  async ({ city }) => {
    const response = await fetch(`https://api.weather.com/${city}`);
    const data = await response.text();
    return {
      content: [{ type: "text", text: data }]
    };
  }
);

// Tool that returns ResourceLinks
server.registerTool(
  "list-files",
  {
    title: "List Files",
    description: "List project files",
    inputSchema: { pattern: z.string() }
  },
  async ({ pattern }) => ({
    content: [
      { type: "text", text: `Found files matching "${pattern}":` },
      // ResourceLinks let tools return references without file content
      {
        type: "resource_link",
        uri: "file:///project/README.md",
        name: "README.md",
        mimeType: "text/markdown",
        description: 'A README file'
      },
      {
        type: "resource_link",
        uri: "file:///project/src/index.ts",
        name: "index.ts",
        mimeType: "text/typescript",
        description: 'An index file'
      }
    ]
  })
);
```

#### ResourceLinks

Tools can return `ResourceLink` objects to reference resources without embedding their full content. This is essential for performance when dealing with large files or many resources - clients can then selectively read only the resources they need using the provided URIs.

### Prompts

Prompts are reusable templates that help LLMs interact with your server effectively:

```typescript
import { completable } from "@modelcontextprotocol/sdk/server/completable.js";

server.registerPrompt(
  "review-code",
  {
    title: "Code Review",
    description: "Review code for best practices and potential issues",
    argsSchema: { code: z.string() }
  },
  ({ code }) => ({
    messages: [{
      role: "user",
      content: {
        type: "text",
        text: `Please review this code:\n\n${code}`
      }
    }]
  })
);

// Prompt with context-aware completion
server.registerPrompt(
  "team-greeting",
  {
    title: "Team Greeting",
    description: "Generate a greeting for team members",
    argsSchema: {
      department: completable(z.string(), (value) => {
        // Department suggestions
        return ["engineering", "sales", "marketing", "support"].filter(d => d.startsWith(value));
      }),
      name: completable(z.string(), (value, context) => {
        // Name suggestions based on selected department
        const department = context?.arguments?.["department"];
        if (department === "engineering") {
          return ["Alice", "Bob", "Charlie"].filter(n => n.startsWith(value));
        } else if (department === "sales") {
          return ["David", "Eve", "Frank"].filter(n => n.startsWith(value));
        } else if (department === "marketing") {
          return ["Grace", "Henry", "Iris"].filter(n => n.startsWith(value));
        }
        return ["Guest"].filter(n => n.startsWith(value));
      })
    }
  },
  ({ department, name }) => ({
    messages: [{
      role: "assistant",
      content: {
        type: "text",
        text: `Hello ${name}, welcome to the ${department} team!`
      }
    }]
  })
);
```

### Completions

MCP supports argument completions to help users fill in prompt arguments and resource template parameters. See the examples above for [resource completions](#resources) and [prompt completions](#prompts).

#### Client Usage

```typescript
// Request completions for any argument
const result = await client.complete({
  ref: {
    type: "ref/prompt",  // or "ref/resource"
    name: "example"      // or uri: "template://..."
  },
  argument: {
    name: "argumentName",
    value: "partial"     // What the user has typed so far
  },
  context: {             // Optional: Include previously resolved arguments
    arguments: {
      previousArg: "value"
    }
  }
});

```

### Display Names and Metadata

All resources, tools, and prompts support an optional `title` field for better UI presentation. The `title` is used as a display name, while `name` remains the unique identifier.

**Note:** The `register*` methods (`registerTool`, `registerPrompt`, `registerResource`) are the recommended approach for new code. The older methods (`tool`, `prompt`, `resource`) remain available for backwards compatibility.

#### Title Precedence for Tools

For tools specifically, there are two ways to specify a title:
- `title` field in the tool configuration
- `annotations.title` field (when using the older `tool()` method with annotations)

The precedence order is: `title` → `annotations.title` → `name`

```typescript
// Using registerTool (recommended)
server.registerTool("my_tool", {
  title: "My Tool",              // This title takes precedence
  annotations: {
    title: "Annotation Title"    // This is ignored if title is set
  }
}, handler);

// Using tool with annotations (older API)
server.tool("my_tool", "description", {
  title: "Annotation Title"      // This is used as title
}, handler);
```

When building clients, use the provided utility to get the appropriate display name:

```typescript
import { getDisplayName } from "@modelcontextprotocol/sdk/shared/metadataUtils.js";

// Automatically handles the precedence: title → annotations.title → name
const displayName = getDisplayName(tool);
```

### Sampling

MCP servers can request LLM completions from connected clients that support sampling.

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const mcpServer = new McpServer({
  name: "tools-with-sample-server",
  version: "1.0.0",
});

// Tool that uses LLM sampling to summarize any text
mcpServer.registerTool(
  "summarize",
  {
    description: "Summarize any text using an LLM",
    inputSchema: {
      text: z.string().describe("Text to summarize"),
    },
  },
  async ({ text }) => {
    // Call the LLM through MCP sampling
    const response = await mcpServer.server.createMessage({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `Please summarize the following text concisely:\n\n${text}`,
          },
        },
      ],
      maxTokens: 500,
    });

    return {
      content: [
        {
          type: "text",
          text: response.content.type === "text" ? response.content.text : "Unable to generate summary",
        },
      ],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await mcpServer.connect(transport);
  console.log("MCP server is running...");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```


## Running Your Server

MCP servers in TypeScript need to be connected to a transport to communicate with clients. How you start the server depends on the choice of transport:

### stdio

For command-line tools and direct integrations:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "example-server",
  version: "1.0.0"
});

// ... set up server resources, tools, and prompts ...

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Streamable HTTP

For remote servers, set up a Streamable HTTP transport that handles both client requests and server-to-client notifications.

#### With Session Management

In some cases, servers need to be stateful. This is achieved by [session management](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#session-management).

```typescript
import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js"



const app = express();
app.use(express.json());

// Map to store transports by session ID
const transports: { [sessionId: string]: StreamableHTTPServerTransport } = {};

// Handle POST requests for client-to-server communication
app.post('/mcp', async (req, res) => {
  // Check for existing session ID
  const sessionId = req.headers['mcp-session-id'] as string | undefined;
  let transport: StreamableHTTPServerTransport;

  if (sessionId && transports[sessionId]) {
    // Reuse existing transport
    transport = transports[sessionId];
  } else if (!sessionId && isInitializeRequest(req.body)) {
    // New initialization request
    transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
      onsessioninitialized: (sessionId) => {
        // Store the transport by session ID
        transports[sessionId] = transport;
      },
      // DNS rebinding protection is disabled by default for backwards compatibility. If you are running this server
      // locally, make sure to set:
      // enableDnsRebindingProtection: true,
      // allowedHosts: ['127.0.0.1'],
    });

    // Clean up transport when closed
    transport.onclose = () => {
      if (transport.sessionId) {
        delete transports[transport.sessionId];
      }
    };
    const server = new McpServer({
      name: "example-server",
      version: "1.0.0"
    });

    // ... set up server resources, tools, and prompts ...

    // Connect to the MCP server
    await server.connect(transport);
  } else {
    // Invalid request
    res.status(400).json({
      jsonrpc: '2.0',
      error: {
        code: -32000,
        message: 'Bad Request: No valid session ID provided',
      },
      id: null,
    });
    return;
  }

  // Handle the request
  await transport.handleRequest(req, res, req.body);
});

// Reusable handler for GET and DELETE requests
const handleSessionRequest = async (req: express.Request, res: express.Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined;
  if (!sessionId || !transports[sessionId]) {
    res.status(400).send('Invalid or missing session ID');
    return;
  }
  
  const transport = transports[sessionId];
  await transport.handleRequest(req, res);
};

// Handle GET requests for server-to-client notifications via SSE
app.get('/mcp', handleSessionRequest);

// Handle DELETE requests for session termination
app.delete('/mcp', handleSessionRequest);

app.listen(3000);
```

> [!TIP]
> When using this in a remote environment, make sure to allow the header parameter `mcp-session-id` in CORS. Otherwise, it may result in a `Bad Request: No valid session ID provided` error. Read the following section for examples.


#### CORS Configuration for Browser-Based Clients

If you'd like your server to be accessible by browser-based MCP clients, you'll need to configure CORS headers. The `Mcp-Session-Id` header must be exposed for browser clients to access it:

```typescript
import cors from 'cors';

// Add CORS middleware before your MCP routes
app.use(cors({
  origin: '*', // Configure appropriately for production, for example:
  // origin: ['https://your-remote-domain.com', 'https://your-other-remote-domain.com'],
  exposedHeaders: ['Mcp-Session-Id'],
  allowedHeaders: ['Content-Type', 'mcp-session-id'],
}));
```

This configuration is necessary because:
- The MCP streamable HTTP transport uses the `Mcp-Session-Id` header for session management
- Browsers restrict access to response headers unless explicitly exposed via CORS
- Without this configuration, browser-based clients won't be able to read the session ID from initialization responses

#### Without Session Management (Stateless)

For simpler use cases where session management isn't needed:

```typescript
const app = express();
app.use(express.json());

app.post('/mcp', async (req: Request, res: Response) => {
  // In stateless mode, create a new instance of transport and server for each request
  // to ensure complete isolation. A single instance would cause request ID collisions
  // when multiple clients connect concurrently.
  
  try {
    const server = getServer(); 
    const transport: StreamableHTTPServerTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
    });
    res.on('close', () => {
      console.log('Request closed');
      transport.close();
      server.close();
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

// SSE notifications not supported in stateless mode
app.get('/mcp', async (req: Request, res: Response) => {
  console.log('Received GET MCP request');
  res.writeHead(405).end(JSON.stringify({
    jsonrpc: "2.0",
    error: {
      code: -32000,
      message: "Method not allowed."
    },
    id: null
  }));
});

// Session termination not needed in stateless mode
app.delete('/mcp', async (req: Request, res: Response) => {
  console.log('Received DELETE MCP request');
  res.writeHead(405).end(JSON.stringify({
    jsonrpc: "2.0",
    error: {
      code: -32000,
      message: "Method not allowed."
    },
    id: null
  }));
});


// Start the server
const PORT = 3000;
setupServer().then(() => {
  app.listen(PORT, (error) => {
    if (error) {
      console.error('Failed to start server:', error);
      process.exit(1);
    }
    console.log(`MCP Stateless Streamable HTTP Server listening on port ${PORT}`);
  });
}).catch(error => {
  console.error('Failed to set up the server:', error);
  process.exit(1);
});

```

This stateless approach is useful for:

- Simple API wrappers
- RESTful scenarios where each request is independent
- Horizontally scaled deployments without shared session state

#### DNS Rebinding Protection

The Streamable HTTP transport includes DNS rebinding protection to prevent security vulnerabilities. By default, this protection is **disabled** for backwards compatibility.

**Important**: If you are running this server locally, enable DNS rebinding protection:

```typescript
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: () => randomUUID(),
  enableDnsRebindingProtection: true,

  allowedHosts: ['127.0.0.1', ...],
  allowedOrigins: ['https://yourdomain.com', 'https://www.yourdomain.com']
});
```

### Testing and Debugging

To test your server, you can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector). See its README for more information.

## Examples

### Echo Server

A simple server demonstrating resources, tools, and prompts:

```typescript
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({
  name: "echo-server",
  version: "1.0.0"
});

server.registerResource(
  "echo",
  new ResourceTemplate("echo://{message}", { list: undefined }),
  {
    title: "Echo Resource",
    description: "Echoes back messages as resources"
  },
  async (uri, { message }) => ({
    contents: [{
      uri: uri.href,
      text: `Resource echo: ${message}`
    }]
  })
);

server.registerTool(
  "echo",
  {
    title: "Echo Tool",
    description: "Echoes back the provided message",
    inputSchema: { message: z.string() }
  },
  async ({ message }) => ({
    content: [{ type: "text", text: `Tool echo: ${message}` }]
  })
);

server.registerPrompt(
  "echo",
  {
    title: "Echo Prompt",
    description: "Creates a prompt to process a message",
    argsSchema: { message: z.string() }
  },
  ({ message }) => ({
    messages: [{
      role: "user",
      content: {
        type: "text",
        text: `Please process this message: ${message}`
      }
    }]
  })
);
```

### SQLite Explorer

A more complex example showing database integration:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import sqlite3 from "sqlite3";
import { promisify } from "util";
import { z } from "zod";

const server = new McpServer({
  name: "sqlite-explorer",
  version: "1.0.0"
});

// Helper to create DB connection
const getDb = () => {
  const db = new sqlite3.Database("database.db");
  return {
    all: promisify<string, any[]>(db.all.bind(db)),
    close: promisify(db.close.bind(db))
  };
};

server.registerResource(
  "schema",
  "schema://main",
  {
    title: "Database Schema",
    description: "SQLite database schema",
    mimeType: "text/plain"
  },
  async (uri) => {
    const db = getDb();
    try {
      const tables = await db.all(
        "SELECT sql FROM sqlite_master WHERE type='table'"
      );
      return {
        contents: [{
          uri: uri.href,
          text: tables.map((t: {sql: string}) => t.sql).join("\n")
        }]
      };
    } finally {
      await db.close();
    }
  }
);

server.registerTool(
  "query",
  {
    title: "SQL Query",
    description: "Execute SQL queries on the database",
    inputSchema: { sql: z.string() }
  },
  async ({ sql }) => {
    const db = getDb();
    try {
      const results = await db.all(sql);
      return {
        content: [{
          type: "text",
          text: JSON.stringify(results, null, 2)
        }]
      };
    } catch (err: unknown) {
      const error = err as Error;
      return {
        content: [{
          type: "text",
          text: `Error: ${error.message}`
        }],
        isError: true
      };
    } finally {
      await db.close();
    }
  }
);
```

## Advanced Usage

### Dynamic Servers

If you want to offer an initial set of tools/prompts/resources, but later add additional ones based on user action or external state change, you can add/update/remove them _after_ the Server is connected. This will automatically emit the corresponding `listChanged` notifications:

```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({
  name: "Dynamic Example",
  version: "1.0.0"
});

const listMessageTool = server.tool(
  "listMessages",
  { channel: z.string() },
  async ({ channel }) => ({
    content: [{ type: "text", text: await listMessages(channel) }]
  })
);

const putMessageTool = server.tool(
  "putMessage",
  { channel: z.string(), message: z.string() },
  async ({ channel, message }) => ({
    content: [{ type: "text", text: await putMessage(channel, message) }]
  })
);
// Until we upgrade auth, `putMessage` is disabled (won't show up in listTools)
putMessageTool.disable()

const upgradeAuthTool = server.tool(
  "upgradeAuth",
  { permission: z.enum(["write", "admin"])},
  // Any mutations here will automatically emit `listChanged` notifications
  async ({ permission }) => {
    const { ok, err, previous } = await upgradeAuthAndStoreToken(permission)
    if (!ok) return {content: [{ type: "text", text: `Error: ${err}` }]}

    // If we previously had read-only access, 'putMessage' is now available
    if (previous === "read") {
      putMessageTool.enable()
    }

    if (permission === 'write') {
      // If we've just upgraded to 'write' permissions, we can still call 'upgradeAuth' 
      // but can only upgrade to 'admin'. 
      upgradeAuthTool.update({
        paramsSchema: { permission: z.enum(["admin"]) }, // change validation rules
      })
    } else {
      // If we're now an admin, we no longer have anywhere to upgrade to, so fully remove that tool
      upgradeAuthTool.remove()
    }
  }
)

// Connect as normal
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Improving Network Efficiency with Notification Debouncing

When performing bulk updates that trigger notifications (e.g., enabling or disabling multiple tools in a loop), the SDK can send a large number of messages in a short period. To improve performance and reduce network traffic, you can enable notification debouncing.

This feature coalesces multiple, rapid calls for the same notification type into a single message. For example, if you disable five tools in a row, only one `notifications/tools/list_changed` message will be sent instead of five.

> [!IMPORTANT]
> This feature is designed for "simple" notifications that do not carry unique data in their parameters. To prevent silent data loss, debouncing is **automatically bypassed** for any notification that contains a `params` object or a `relatedRequestId`. Such notifications will always be sent immediately.

This is an opt-in feature configured during server initialization.

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer(
  {
    name: "efficient-server",
    version: "1.0.0"
  },
  {
    // Enable notification debouncing for specific methods
    debouncedNotificationMethods: [
      'notifications/tools/list_changed',
      'notifications/resources/list_changed',
      'notifications/prompts/list_changed'
    ]
  }
);

// Now, any rapid changes to tools, resources, or prompts will result
// in a single, consolidated notification for each type.
server.registerTool("tool1", ...).disable();
server.registerTool("tool2", ...).disable();
server.registerTool("tool3", ...).disable();
// Only one 'notifications/tools/list_changed' is sent.
```

### Low-Level Server

For more control, you can use the low-level Server class directly:

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListPromptsRequestSchema,
  GetPromptRequestSchema
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  {
    name: "example-server",
    version: "1.0.0"
  },
  {
    capabilities: {
      prompts: {}
    }
  }
);

server.setRequestHandler(ListPromptsRequestSchema, async () => {
  return {
    prompts: [{
      name: "example-prompt",
      description: "An example prompt template",
      arguments: [{
        name: "arg1",
        description: "Example argument",
        required: true
      }]
    }]
  };
});

server.setRequestHandler(GetPromptRequestSchema, async (request) => {
  if (request.params.name !== "example-prompt") {
    throw new Error("Unknown prompt");
  }
  return {
    description: "Example prompt",
    messages: [{
      role: "user",
      content: {
        type: "text",
        text: "Example prompt text"
      }
    }]
  };
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Eliciting User Input

MCP servers can request additional information from users through the elicitation feature. This is useful for interactive workflows where the server needs user input or confirmation:

```typescript
// Server-side: Restaurant booking tool that asks for alternatives
server.tool(
  "book-restaurant",
  { 
    restaurant: z.string(),
    date: z.string(),
    partySize: z.number()
  },
  async ({ restaurant, date, partySize }) => {
    // Check availability
    const available = await checkAvailability(restaurant, date, partySize);
    
    if (!available) {
      // Ask user if they want to try alternative dates
      const result = await server.server.elicitInput({
        message: `No tables available at ${restaurant} on ${date}. Would you like to check alternative dates?`,
        requestedSchema: {
          type: "object",
          properties: {
            checkAlternatives: {
              type: "boolean",
              title: "Check alternative dates",
              description: "Would you like me to check other dates?"
            },
            flexibleDates: {
              type: "string",
              title: "Date flexibility",
              description: "How flexible are your dates?",
              enum: ["next_day", "same_week", "next_week"],
              enumNames: ["Next day", "Same week", "Next week"]
            }
          },
          required: ["checkAlternatives"]
        }
      });

      if (result.action === "accept" && result.content?.checkAlternatives) {
        const alternatives = await findAlternatives(
          restaurant, 
          date, 
          partySize, 
          result.content.flexibleDates as string
        );
        return {
          content: [{
            type: "text",
            text: `Found these alternatives: ${alternatives.join(", ")}`
          }]
        };
      }
      
      return {
        content: [{
          type: "text",
          text: "No booking made. Original date not available."
        }]
      };
    }
    
    // Book the table
    await makeBooking(restaurant, date, partySize);
    return {
      content: [{
        type: "text",
        text: `Booked table for ${partySize} at ${restaurant} on ${date}`
      }]
    };
  }
);
```

Client-side: Handle elicitation requests

```typescript
// This is a placeholder - implement based on your UI framework
async function getInputFromUser(message: string, schema: any): Promise<{
  action: "accept" | "decline" | "cancel";
  data?: Record<string, any>;
}> {
  // This should be implemented depending on the app
  throw new Error("getInputFromUser must be implemented for your platform");
}

client.setRequestHandler(ElicitRequestSchema, async (request) => {
  const userResponse = await getInputFromUser(
    request.params.message, 
    request.params.requestedSchema
  );
  
  return {
    action: userResponse.action,
    content: userResponse.action === "accept" ? userResponse.data : undefined
  };
});
```

**Note**: Elicitation requires client support. Clients must declare the `elicitation` capability during initialization.

### Writing MCP Clients

The SDK provides a high-level client interface:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "node",
  args: ["server.js"]
});

const client = new Client(
  {
    name: "example-client",
    version: "1.0.0"
  }
);

await client.connect(transport);

// List prompts
const prompts = await client.listPrompts();

// Get a prompt
const prompt = await client.getPrompt({
  name: "example-prompt",
  arguments: {
    arg1: "value"
  }
});

// List resources
const resources = await client.listResources();

// Read a resource
const resource = await client.readResource({
  uri: "file:///example.txt"
});

// Call a tool
const result = await client.callTool({
  name: "example-tool",
  arguments: {
    arg1: "value"
  }
});

```

### Proxy Authorization Requests Upstream

You can proxy OAuth requests to an external authorization provider:

```typescript
import express from 'express';
import { ProxyOAuthServerProvider } from '@modelcontextprotocol/sdk/server/auth/providers/proxyProvider.js';
import { mcpAuthRouter } from '@modelcontextprotocol/sdk/server/auth/router.js';

const app = express();

const proxyProvider = new ProxyOAuthServerProvider({
    endpoints: {
        authorizationUrl: "https://auth.external.com/oauth2/v1/authorize",
        tokenUrl: "https://auth.external.com/oauth2/v1/token",
        revocationUrl: "https://auth.external.com/oauth2/v1/revoke",
    },
    verifyAccessToken: async (token) => {
        return {
            token,
            clientId: "123",
            scopes: ["openid", "email", "profile"],
        }
    },
    getClient: async (client_id) => {
        return {
            client_id,
            redirect_uris: ["http://localhost:3000/callback"],
        }
    }
})

app.use(mcpAuthRouter({
    provider: proxyProvider,
    issuerUrl: new URL("http://auth.external.com"),
    baseUrl: new URL("http://mcp.example.com"),
    serviceDocumentationUrl: new URL("https://docs.example.com/"),
}))
```

This setup allows you to:

- Forward OAuth requests to an external provider
- Add custom token validation logic
- Manage client registrations
- Provide custom documentation URLs
- Maintain control over the OAuth flow while delegating to an external provider

### Backwards Compatibility

Clients and servers with StreamableHttp transport can maintain [backwards compatibility](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility) with the deprecated HTTP+SSE transport (from protocol version 2024-11-05) as follows

#### Client-Side Compatibility

For clients that need to work with both Streamable HTTP and older SSE servers:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
let client: Client|undefined = undefined
const baseUrl = new URL(url);
try {
  client = new Client({
    name: 'streamable-http-client',
    version: '1.0.0'
  });
  const transport = new StreamableHTTPClientTransport(
    new URL(baseUrl)
  );
  await client.connect(transport);
  console.log("Connected using Streamable HTTP transport");
} catch (error) {
  // If that fails with a 4xx error, try the older SSE transport
  console.log("Streamable HTTP connection failed, falling back to SSE transport");
  client = new Client({
    name: 'sse-client',
    version: '1.0.0'
  });
  const sseTransport = new SSEClientTransport(baseUrl);
  await client.connect(sseTransport);
  console.log("Connected using SSE transport");
}
```

#### Server-Side Compatibility

For servers that need to support both Streamable HTTP and older clients:

```typescript
import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";

const server = new McpServer({
  name: "backwards-compatible-server",
  version: "1.0.0"
});

// ... set up server resources, tools, and prompts ...

const app = express();
app.use(express.json());

// Store transports for each session type
const transports = {
  streamable: {} as Record<string, StreamableHTTPServerTransport>,
  sse: {} as Record<string, SSEServerTransport>
};

// Modern Streamable HTTP endpoint
app.all('/mcp', async (req, res) => {
  // Handle Streamable HTTP transport for modern clients
  // Implementation as shown in the "With Session Management" example
  // ...
});

// Legacy SSE endpoint for older clients
app.get('/sse', async (req, res) => {
  // Create SSE transport for legacy clients
  const transport = new SSEServerTransport('/messages', res);
  transports.sse[transport.sessionId] = transport;
  
  res.on("close", () => {
    delete transports.sse[transport.sessionId];
  });
  
  await server.connect(transport);
});

// Legacy message endpoint for older clients
app.post('/messages', async (req, res) => {
  const sessionId = req.query.sessionId as string;
  const transport = transports.sse[sessionId];
  if (transport) {
    await transport.handlePostMessage(req, res, req.body);
  } else {
    res.status(400).send('No transport found for sessionId');
  }
});

app.listen(3000);
```

**Note**: The SSE transport is now deprecated in favor of Streamable HTTP. New implementations should use Streamable HTTP, and existing SSE implementations should plan to migrate.

## Documentation

- [Model Context Protocol documentation](https://modelcontextprotocol.io)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [Example Servers](https://github.com/modelcontextprotocol/servers)

## Contributing

Issues and pull requests are welcome on GitHub at <https://github.com/modelcontextprotocol/typescript-sdk>.

## License

This project is licensed under the MIT License—see the [LICENSE](LICENSE) file for details.



================================================
FILE: CLAUDE.md
================================================
# MCP TypeScript SDK Guide

## Build & Test Commands

```sh
npm run build        # Build ESM and CJS versions
npm run lint         # Run ESLint
npm test             # Run all tests
npx jest path/to/file.test.ts  # Run specific test file
npx jest -t "test name"        # Run tests matching pattern
```

## Code Style Guidelines

- **TypeScript**: Strict type checking, ES modules, explicit return types
- **Naming**: PascalCase for classes/types, camelCase for functions/variables
- **Files**: Lowercase with hyphens, test files with `.test.ts` suffix
- **Imports**: ES module style, include `.js` extension, group imports logically
- **Error Handling**: Use TypeScript's strict mode, explicit error checking in tests
- **Formatting**: 2-space indentation, semicolons required, single quotes preferred
- **Testing**: Co-locate tests with source files, use descriptive test names
- **Comments**: JSDoc for public APIs, inline comments for complex logic

## Project Structure

- `/src`: Source code with client, server, and shared modules
- Tests alongside source files with `.test.ts` suffix
- Node.js >= 18 required



================================================
FILE: CODE_OF_CONDUCT.md
================================================
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, religion, or sexual identity
and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment for our
community include:

* Demonstrating empathy and kindness toward other people
* Being respectful of differing opinions, viewpoints, and experiences
* Giving and gracefully accepting constructive feedback
* Accepting responsibility and apologizing to those affected by our mistakes,
  and learning from the experience
* Focusing on what is best not just for us as individuals, but for the
  overall community

Examples of unacceptable behavior include:

* The use of sexualized language or imagery, and sexual attention or
  advances of any kind
* Trolling, insulting or derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or email
  address, without their explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of
acceptable behavior and will take appropriate and fair corrective action in
response to any behavior that they deem inappropriate, threatening, offensive,
or harmful.

Community leaders have the right and responsibility to remove, edit, or reject
comments, commits, code, wiki edits, issues, and other contributions that are
not aligned to this Code of Conduct, and will communicate reasons for moderation
decisions when appropriate.

## Scope

This Code of Conduct applies within all community spaces, and also applies when
an individual is officially representing the community in public spaces.
Examples of representing our community include using an official e-mail address,
posting via an official social media account, or acting as an appointed
representative at an online or offline event.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the community leaders responsible for enforcement at
<mcp-coc@anthropic.com>.
All complaints will be reviewed and investigated promptly and fairly.

All community leaders are obligated to respect the privacy and security of the
reporter of any incident.

## Enforcement Guidelines

Community leaders will follow these Community Impact Guidelines in determining
the consequences for any action they deem in violation of this Code of Conduct:

### 1. Correction

**Community Impact**: Use of inappropriate language or other behavior deemed
unprofessional or unwelcome in the community.

**Consequence**: A private, written warning from community leaders, providing
clarity around the nature of the violation and an explanation of why the
behavior was inappropriate. A public apology may be requested.

### 2. Warning

**Community Impact**: A violation through a single incident or series
of actions.

**Consequence**: A warning with consequences for continued behavior. No
interaction with the people involved, including unsolicited interaction with
those enforcing the Code of Conduct, for a specified period of time. This
includes avoiding interactions in community spaces as well as external channels
like social media. Violating these terms may lead to a temporary or
permanent ban.

### 3. Temporary Ban

**Community Impact**: A serious violation of community standards, including
sustained inappropriate behavior.

**Consequence**: A temporary ban from any sort of interaction or public
communication with the community for a specified period of time. No public or
private interaction with the people involved, including unsolicited interaction
with those enforcing the Code of Conduct, is allowed during this period.
Violating these terms may lead to a permanent ban.

### 4. Permanent Ban

**Community Impact**: Demonstrating a pattern of violation of community
standards, including sustained inappropriate behavior,  harassment of an
individual, or aggression toward or disparagement of classes of individuals.

**Consequence**: A permanent ban from any sort of public interaction within
the community.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.0, available at
<https://www.contributor-covenant.org/version/2/0/code_of_conduct.html>.

Community Impact Guidelines were inspired by [Mozilla's code of conduct
enforcement ladder](https://github.com/mozilla/diversity).

[homepage]: https://www.contributor-covenant.org

For answers to common questions about this code of conduct, see the FAQ at
<https://www.contributor-covenant.org/faq>. Translations are available at
<https://www.contributor-covenant.org/translations>.



================================================
FILE: CONTRIBUTING.md
================================================
# Contributing to MCP TypeScript SDK

We welcome contributions to the Model Context Protocol TypeScript SDK! This document outlines the process for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/typescript-sdk.git`
3. Install dependencies: `npm install`
4. Build the project: `npm run build`
5. Run tests: `npm test`

## Development Process

1. Create a new branch for your changes
2. Make your changes
3. Run `npm run lint` to ensure code style compliance
4. Run `npm test` to verify all tests pass
5. Submit a pull request

## Pull Request Guidelines

- Follow the existing code style
- Include tests for new functionality
- Update documentation as needed
- Keep changes focused and atomic
- Provide a clear description of changes

## Running Examples

- Start the server: `npm run server`
- Run the client: `npm run client`

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). Please review it before contributing.

## Reporting Issues

- Use the [GitHub issue tracker](https://github.com/modelcontextprotocol/typescript-sdk/issues)
- Search existing issues before creating a new one
- Provide clear reproduction steps

## Security Issues

Please review our [Security Policy](SECURITY.md) for reporting security vulnerabilities.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.



================================================
FILE: eslint.config.mjs
================================================
// @ts-check

import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
    eslint.configs.recommended,
    ...tseslint.configs.recommended,
    {
        linterOptions: {
            reportUnusedDisableDirectives: false,
        },
        rules: {
            "@typescript-eslint/no-unused-vars": ["error",
                { "argsIgnorePattern": "^_" }
            ]
        }
    },
    {
        files: ["src/client/**/*.ts", "src/server/**/*.ts"],
        ignores: ["**/*.test.ts"],
        rules: {
            "no-console": "error"
        }
    }
);



================================================
FILE: jest.config.js
================================================
import { createDefaultEsmPreset } from "ts-jest";

const defaultEsmPreset = createDefaultEsmPreset();

/** @type {import('ts-jest').JestConfigWithTsJest} **/
export default {
  ...defaultEsmPreset,
  moduleNameMapper: {
    "^(\\.{1,2}/.*)\\.js$": "$1",
    "^pkce-challenge$": "<rootDir>/src/__mocks__/pkce-challenge.ts"
  },
  transformIgnorePatterns: [
    "/node_modules/(?!eventsource)/"
  ],
  testPathIgnorePatterns: ["/node_modules/", "/dist/"],
};



================================================
FILE: LICENSE
================================================
MIT License

Copyright (c) 2024 Anthropic, PBC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.



================================================
FILE: package.json
================================================
{
  "name": "@modelcontextprotocol/sdk",
  "version": "1.17.4",
  "description": "Model Context Protocol implementation for TypeScript",
  "license": "MIT",
  "author": "Anthropic, PBC (https://anthropic.com)",
  "homepage": "https://modelcontextprotocol.io",
  "bugs": "https://github.com/modelcontextprotocol/typescript-sdk/issues",
  "type": "module",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/modelcontextprotocol/typescript-sdk.git"
  },
  "engines": {
    "node": ">=18"
  },
  "keywords": [
    "modelcontextprotocol",
    "mcp"
  ],
  "exports": {
    ".": {
      "import": "./dist/esm/index.js",
      "require": "./dist/cjs/index.js"
    },
    "./client": {
      "import": "./dist/esm/client/index.js",
      "require": "./dist/cjs/client/index.js"
    },
    "./server": {
      "import": "./dist/esm/server/index.js",
      "require": "./dist/cjs/server/index.js"
    },
    "./*": {
      "import": "./dist/esm/*",
      "require": "./dist/cjs/*"
    }
  },
  "typesVersions": {
    "*": {
      "*": [
        "./dist/esm/*"
      ]
    }
  },
  "files": [
    "dist"
  ],
  "scripts": {
    "fetch:spec-types": "curl -o spec.types.ts https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/refs/heads/main/schema/draft/schema.ts",
    "build": "npm run build:esm && npm run build:cjs",
    "build:esm": "mkdir -p dist/esm && echo '{\"type\": \"module\"}' > dist/esm/package.json && tsc -p tsconfig.prod.json",
    "build:esm:w": "npm run build:esm -- -w",
    "build:cjs": "mkdir -p dist/cjs && echo '{\"type\": \"commonjs\"}' > dist/cjs/package.json && tsc -p tsconfig.cjs.json",
    "build:cjs:w": "npm run build:cjs -- -w",
    "examples:simple-server:w": "tsx --watch src/examples/server/simpleStreamableHttp.ts --oauth",
    "prepack": "npm run build:esm && npm run build:cjs",
    "lint": "eslint src/",
    "test": "npm run fetch:spec-types && jest",
    "start": "npm run server",
    "server": "tsx watch --clear-screen=false src/cli.ts server",
    "client": "tsx src/cli.ts client"
  },
  "dependencies": {
    "ajv": "^6.12.6",
    "content-type": "^1.0.5",
    "cors": "^2.8.5",
    "cross-spawn": "^7.0.5",
    "eventsource": "^3.0.2",
    "eventsource-parser": "^3.0.0",
    "express": "^5.0.1",
    "express-rate-limit": "^7.5.0",
    "pkce-challenge": "^5.0.0",
    "raw-body": "^3.0.0",
    "zod": "^3.23.8",
    "zod-to-json-schema": "^3.24.1"
  },
  "devDependencies": {
    "@eslint/js": "^9.8.0",
    "@jest-mock/express": "^3.0.0",
    "@types/content-type": "^1.1.8",
    "@types/cors": "^2.8.17",
    "@types/cross-spawn": "^6.0.6",
    "@types/eslint__js": "^8.42.3",
    "@types/eventsource": "^1.1.15",
    "@types/express": "^5.0.0",
    "@types/jest": "^29.5.12",
    "@types/node": "^22.0.2",
    "@types/supertest": "^6.0.2",
    "@types/ws": "^8.5.12",
    "eslint": "^9.8.0",
    "jest": "^29.7.0",
    "supertest": "^7.0.0",
    "ts-jest": "^29.2.4",
    "tsx": "^4.16.5",
    "typescript": "^5.5.4",
    "typescript-eslint": "^8.0.0",
    "ws": "^8.18.0"
  },
  "resolutions": {
    "strip-ansi": "6.0.1"
  }
}


================================================
FILE: SECURITY.md
================================================
# Security Policy

Thank you for helping us keep the SDKs and systems they interact with secure.

## Reporting Security Issues

This SDK is maintained by [Anthropic](https://www.anthropic.com/) as part of the Model Context Protocol project.

The security of our systems and user data is Anthropic’s top priority. We appreciate the work of security researchers acting in good faith in identifying and reporting potential vulnerabilities.

Our security program is managed on HackerOne and we ask that any validated vulnerability in this functionality be reported through their [submission form](https://hackerone.com/anthropic-vdp/reports/new?type=team&report_type=vulnerability).

## Vulnerability Disclosure Program

Our Vulnerability Program Guidelines are defined on our [HackerOne program page](https://hackerone.com/anthropic-vdp).



================================================
FILE: tsconfig.cjs.json
================================================
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "module": "commonjs",
    "moduleResolution": "node",
    "outDir": "./dist/cjs"
  },
  "exclude": ["**/*.test.ts", "src/__mocks__/**/*"]
}



================================================
FILE: tsconfig.json
================================================
{
  "compilerOptions": {
    "target": "es2018",
    "module": "Node16",
    "moduleResolution": "Node16",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": {
      "pkce-challenge": ["node_modules/pkce-challenge/dist/index.node"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}



================================================
FILE: tsconfig.prod.json
================================================
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./dist/esm"
  },
  "exclude": ["**/*.test.ts", "src/__mocks__/**/*"]
}



================================================
FILE: .git-blame-ignore-revs
================================================
[Empty file]


================================================
FILE: .npmrc
================================================
registry = "https://registry.npmjs.org/"



================================================
FILE: src/cli.ts
================================================
import WebSocket from "ws";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).WebSocket = WebSocket;

import express from "express";
import { Client } from "./client/index.js";
import { SSEClientTransport } from "./client/sse.js";
import { StdioClientTransport } from "./client/stdio.js";
import { WebSocketClientTransport } from "./client/websocket.js";
import { Server } from "./server/index.js";
import { SSEServerTransport } from "./server/sse.js";
import { StdioServerTransport } from "./server/stdio.js";
import { ListResourcesResultSchema } from "./types.js";

async function runClient(url_or_command: string, args: string[]) {
  const client = new Client(
    {
      name: "mcp-typescript test client",
      version: "0.1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  let clientTransport;

  let url: URL | undefined = undefined;
  try {
    url = new URL(url_or_command);
  } catch {
    // Ignore
  }

  if (url?.protocol === "http:" || url?.protocol === "https:") {
    clientTransport = new SSEClientTransport(new URL(url_or_command));
  } else if (url?.protocol === "ws:" || url?.protocol === "wss:") {
    clientTransport = new WebSocketClientTransport(new URL(url_or_command));
  } else {
    clientTransport = new StdioClientTransport({
      command: url_or_command,
      args,
    });
  }

  console.log("Connected to server.");

  await client.connect(clientTransport);
  console.log("Initialized.");

  await client.request({ method: "resources/list" }, ListResourcesResultSchema);

  await client.close();
  console.log("Closed.");
}

async function runServer(port: number | null) {
  if (port !== null) {
    const app = express();

    let servers: Server[] = [];

    app.get("/sse", async (req, res) => {
      console.log("Got new SSE connection");

      const transport = new SSEServerTransport("/message", res);
      const server = new Server(
        {
          name: "mcp-typescript test server",
          version: "0.1.0",
        },
        {
          capabilities: {},
        },
      );

      servers.push(server);

      server.onclose = () => {
        console.log("SSE connection closed");
        servers = servers.filter((s) => s !== server);
      };

      await server.connect(transport);
    });

    app.post("/message", async (req, res) => {
      console.log("Received message");

      const sessionId = req.query.sessionId as string;
      const transport = servers
        .map((s) => s.transport as SSEServerTransport)
        .find((t) => t.sessionId === sessionId);
      if (!transport) {
        res.status(404).send("Session not found");
        return;
      }

      await transport.handlePostMessage(req, res);
    });

    app.listen(port, (error) => {
      if (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
      }
      console.log(`Server running on http://localhost:${port}/sse`);
    });
  } else {
    const server = new Server(
      {
        name: "mcp-typescript test server",
        version: "0.1.0",
      },
      {
        capabilities: {
          prompts: {},
          resources: {},
          tools: {},
          logging: {},
        },
      },
    );

    const transport = new StdioServerTransport();
    await server.connect(transport);

    console.log("Server running on stdio");
  }
}

const args = process.argv.slice(2);
const command = args[0];
switch (command) {
  case "client":
    if (args.length < 2) {
      console.error("Usage: client <server_url_or_command> [args...]");
      process.exit(1);
    }

    runClient(args[1], args.slice(2)).catch((error) => {
      console.error(error);
      process.exit(1);
    });

    break;

  case "server": {
    const port = args[1] ? parseInt(args[1]) : null;
    runServer(port).catch((error) => {
      console.error(error);
      process.exit(1);
    });

    break;
  }

  default:
    console.error("Unrecognized command:", command);
}



================================================
FILE: src/inMemory.test.ts
================================================
import { InMemoryTransport } from "./inMemory.js";
import { JSONRPCMessage } from "./types.js";
import { AuthInfo } from "./server/auth/types.js";

describe("InMemoryTransport", () => {
  let clientTransport: InMemoryTransport;
  let serverTransport: InMemoryTransport;

  beforeEach(() => {
    [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  });

  test("should create linked pair", () => {
    expect(clientTransport).toBeDefined();
    expect(serverTransport).toBeDefined();
  });

  test("should start without error", async () => {
    await expect(clientTransport.start()).resolves.not.toThrow();
    await expect(serverTransport.start()).resolves.not.toThrow();
  });

  test("should send message from client to server", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      id: 1,
    };

    let receivedMessage: JSONRPCMessage | undefined;
    serverTransport.onmessage = (msg) => {
      receivedMessage = msg;
    };

    await clientTransport.send(message);
    expect(receivedMessage).toEqual(message);
  });

  test("should send message with auth info from client to server", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      id: 1,
    };

    const authInfo: AuthInfo = {
      token: "test-token",
      clientId: "test-client",
      scopes: ["read", "write"],
      expiresAt: Date.now() / 1000 + 3600,
    };

    let receivedMessage: JSONRPCMessage | undefined;
    let receivedAuthInfo: AuthInfo | undefined;
    serverTransport.onmessage = (msg, extra) => {
      receivedMessage = msg;
      receivedAuthInfo = extra?.authInfo;
    };

    await clientTransport.send(message, { authInfo });
    expect(receivedMessage).toEqual(message);
    expect(receivedAuthInfo).toEqual(authInfo);
  });

  test("should send message from server to client", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      id: 1,
    };

    let receivedMessage: JSONRPCMessage | undefined;
    clientTransport.onmessage = (msg) => {
      receivedMessage = msg;
    };

    await serverTransport.send(message);
    expect(receivedMessage).toEqual(message);
  });

  test("should handle close", async () => {
    let clientClosed = false;
    let serverClosed = false;

    clientTransport.onclose = () => {
      clientClosed = true;
    };

    serverTransport.onclose = () => {
      serverClosed = true;
    };

    await clientTransport.close();
    expect(clientClosed).toBe(true);
    expect(serverClosed).toBe(true);
  });

  test("should throw error when sending after close", async () => {
    await clientTransport.close();
    await expect(
      clientTransport.send({ jsonrpc: "2.0", method: "test", id: 1 }),
    ).rejects.toThrow("Not connected");
  });

  test("should queue messages sent before start", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      id: 1,
    };

    let receivedMessage: JSONRPCMessage | undefined;
    serverTransport.onmessage = (msg) => {
      receivedMessage = msg;
    };

    await clientTransport.send(message);
    await serverTransport.start();
    expect(receivedMessage).toEqual(message);
  });
});



================================================
FILE: src/inMemory.ts
================================================
import { Transport } from "./shared/transport.js";
import { JSONRPCMessage, RequestId } from "./types.js";
import { AuthInfo } from "./server/auth/types.js";

interface QueuedMessage {
  message: JSONRPCMessage;
  extra?: { authInfo?: AuthInfo };
}

/**
 * In-memory transport for creating clients and servers that talk to each other within the same process.
 */
export class InMemoryTransport implements Transport {
  private _otherTransport?: InMemoryTransport;
  private _messageQueue: QueuedMessage[] = [];

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage, extra?: { authInfo?: AuthInfo }) => void;
  sessionId?: string;

  /**
   * Creates a pair of linked in-memory transports that can communicate with each other. One should be passed to a Client and one to a Server.
   */
  static createLinkedPair(): [InMemoryTransport, InMemoryTransport] {
    const clientTransport = new InMemoryTransport();
    const serverTransport = new InMemoryTransport();
    clientTransport._otherTransport = serverTransport;
    serverTransport._otherTransport = clientTransport;
    return [clientTransport, serverTransport];
  }

  async start(): Promise<void> {
    // Process any messages that were queued before start was called
    while (this._messageQueue.length > 0) {
      const queuedMessage = this._messageQueue.shift()!;
      this.onmessage?.(queuedMessage.message, queuedMessage.extra);
    }
  }

  async close(): Promise<void> {
    const other = this._otherTransport;
    this._otherTransport = undefined;
    await other?.close();
    this.onclose?.();
  }

  /**
   * Sends a message with optional auth info.
   * This is useful for testing authentication scenarios.
   */
  async send(message: JSONRPCMessage, options?: { relatedRequestId?: RequestId, authInfo?: AuthInfo }): Promise<void> {
    if (!this._otherTransport) {
      throw new Error("Not connected");
    }

    if (this._otherTransport.onmessage) {
      this._otherTransport.onmessage(message, { authInfo: options?.authInfo });
    } else {
      this._otherTransport._messageQueue.push({ message, extra: { authInfo: options?.authInfo } });
    }
  }
}



================================================
FILE: src/spec.types.test.ts
================================================
/**
 * This contains:
 * - Static type checks to verify the Spec's types are compatible with the SDK's types
 *   (mutually assignable, w/ slight affordances to get rid of ZodObject.passthrough() index signatures, etc)
 * - Runtime checks to verify each Spec type has a static check
 *   (note: a few don't have SDK types, see MISSING_SDK_TYPES below)
 */
import * as SDKTypes from "./types.js";
import * as SpecTypes from "../spec.types.js";
import fs from "node:fs";

/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-unsafe-function-type */

// Removes index signatures added by ZodObject.passthrough().
type RemovePassthrough<T> = T extends object
  ? T extends Array<infer U>
    ? Array<RemovePassthrough<U>>
    : T extends Function
        ? T
        : {[K in keyof T as string extends K ? never : K]: RemovePassthrough<T[K]>}
    : T;

type IsUnknown<T> = [unknown] extends [T] ? [T] extends [unknown] ? true : false : false;

// Turns {x?: unknown} into {x: unknown} but keeps {_meta?: unknown} unchanged (and leaves other optional properties unchanged, e.g. {x?: string}).
// This works around an apparent quirk of ZodObject.unknown() (makes fields optional)
type MakeUnknownsNotOptional<T> =
  IsUnknown<T> extends true
    ? unknown
    : (T extends object
      ? (T extends Array<infer U>
        ? Array<MakeUnknownsNotOptional<U>>
        : (T extends Function
          ? T
          : Pick<T, never> & {
            // Start with empty object to avoid duplicates
            // Make unknown properties required (except _meta)
            [K in keyof T as '_meta' extends K ? never : IsUnknown<T[K]> extends true ? K : never]-?: unknown;
          } &
          Pick<T, {
            // Pick all _meta and non-unknown properties with original modifiers
            [K in keyof T]: '_meta' extends K ? K : IsUnknown<T[K]> extends true ? never : K
          }[keyof T]> & {
            // Recurse on the picked properties
            [K in keyof Pick<T, {[K in keyof T]: '_meta' extends K ? K : IsUnknown<T[K]> extends true ? never : K}[keyof T]>]: MakeUnknownsNotOptional<T[K]>
          }))
      : T);

function checkCancelledNotification(
  sdk: SDKTypes.CancelledNotification,
  spec: SpecTypes.CancelledNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkBaseMetadata(
  sdk: RemovePassthrough<SDKTypes.BaseMetadata>,
  spec: SpecTypes.BaseMetadata
) {
  sdk = spec;
  spec = sdk;
}
function checkImplementation(
  sdk: RemovePassthrough<SDKTypes.Implementation>,
  spec: SpecTypes.Implementation
) {
  sdk = spec;
  spec = sdk;
}
function checkProgressNotification(
  sdk: SDKTypes.ProgressNotification,
  spec: SpecTypes.ProgressNotification
) {
  sdk = spec;
  spec = sdk;
}

function checkSubscribeRequest(
  sdk: SDKTypes.SubscribeRequest,
  spec: SpecTypes.SubscribeRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkUnsubscribeRequest(
  sdk: SDKTypes.UnsubscribeRequest,
  spec: SpecTypes.UnsubscribeRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkPaginatedRequest(
  sdk: SDKTypes.PaginatedRequest,
  spec: SpecTypes.PaginatedRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkPaginatedResult(
  sdk: SDKTypes.PaginatedResult,
  spec: SpecTypes.PaginatedResult
) {
  sdk = spec;
  spec = sdk;
}
function checkListRootsRequest(
  sdk: SDKTypes.ListRootsRequest,
  spec: SpecTypes.ListRootsRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkListRootsResult(
  sdk: RemovePassthrough<SDKTypes.ListRootsResult>,
  spec: SpecTypes.ListRootsResult
) {
  sdk = spec;
  spec = sdk;
}
function checkRoot(
  sdk: RemovePassthrough<SDKTypes.Root>,
  spec: SpecTypes.Root
) {
  sdk = spec;
  spec = sdk;
}
function checkElicitRequest(
  sdk: RemovePassthrough<SDKTypes.ElicitRequest>,
  spec: SpecTypes.ElicitRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkElicitResult(
  sdk: RemovePassthrough<SDKTypes.ElicitResult>,
  spec: SpecTypes.ElicitResult
) {
  sdk = spec;
  spec = sdk;
}
function checkCompleteRequest(
  sdk: RemovePassthrough<SDKTypes.CompleteRequest>,
  spec: SpecTypes.CompleteRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkCompleteResult(
  sdk: SDKTypes.CompleteResult,
  spec: SpecTypes.CompleteResult
) {
  sdk = spec;
  spec = sdk;
}
function checkProgressToken(
  sdk: SDKTypes.ProgressToken,
  spec: SpecTypes.ProgressToken
) {
  sdk = spec;
  spec = sdk;
}
function checkCursor(
  sdk: SDKTypes.Cursor,
  spec: SpecTypes.Cursor
) {
  sdk = spec;
  spec = sdk;
}
function checkRequest(
  sdk: SDKTypes.Request,
  spec: SpecTypes.Request
) {
  sdk = spec;
  spec = sdk;
}
function checkResult(
  sdk: SDKTypes.Result,
  spec: SpecTypes.Result
) {
  sdk = spec;
  spec = sdk;
}
function checkRequestId(
  sdk: SDKTypes.RequestId,
  spec: SpecTypes.RequestId
) {
  sdk = spec;
  spec = sdk;
}
function checkJSONRPCRequest(
  sdk: SDKTypes.JSONRPCRequest,
  spec: SpecTypes.JSONRPCRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkJSONRPCNotification(
  sdk: SDKTypes.JSONRPCNotification,
  spec: SpecTypes.JSONRPCNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkJSONRPCResponse(
  sdk: SDKTypes.JSONRPCResponse,
  spec: SpecTypes.JSONRPCResponse
) {
  sdk = spec;
  spec = sdk;
}
function checkEmptyResult(
  sdk: SDKTypes.EmptyResult,
  spec: SpecTypes.EmptyResult
) {
  sdk = spec;
  spec = sdk;
}
function checkNotification(
  sdk: SDKTypes.Notification,
  spec: SpecTypes.Notification
) {
  sdk = spec;
  spec = sdk;
}
function checkClientResult(
  sdk: SDKTypes.ClientResult,
  spec: SpecTypes.ClientResult
) {
  sdk = spec;
  spec = sdk;
}
function checkClientNotification(
  sdk: SDKTypes.ClientNotification,
  spec: SpecTypes.ClientNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkServerResult(
  sdk: SDKTypes.ServerResult,
  spec: SpecTypes.ServerResult
) {
  sdk = spec;
  spec = sdk;
}
function checkResourceTemplateReference(
  sdk: RemovePassthrough<SDKTypes.ResourceTemplateReference>,
  spec: SpecTypes.ResourceTemplateReference
) {
  sdk = spec;
  spec = sdk;
}
function checkPromptReference(
  sdk: RemovePassthrough<SDKTypes.PromptReference>,
  spec: SpecTypes.PromptReference
) {
  sdk = spec;
  spec = sdk;
}
function checkToolAnnotations(
  sdk: RemovePassthrough<SDKTypes.ToolAnnotations>,
  spec: SpecTypes.ToolAnnotations
) {
  sdk = spec;
  spec = sdk;
}
function checkTool(
  sdk: RemovePassthrough<SDKTypes.Tool>,
  spec: SpecTypes.Tool
) {
  sdk = spec;
  spec = sdk;
}
function checkListToolsRequest(
  sdk: SDKTypes.ListToolsRequest,
  spec: SpecTypes.ListToolsRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkListToolsResult(
  sdk: RemovePassthrough<SDKTypes.ListToolsResult>,
  spec: SpecTypes.ListToolsResult
) {
  sdk = spec;
  spec = sdk;
}
function checkCallToolResult(
  sdk: RemovePassthrough<SDKTypes.CallToolResult>,
  spec: SpecTypes.CallToolResult
) {
  sdk = spec;
  spec = sdk;
}
function checkCallToolRequest(
  sdk: SDKTypes.CallToolRequest,
  spec: SpecTypes.CallToolRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkToolListChangedNotification(
  sdk: SDKTypes.ToolListChangedNotification,
  spec: SpecTypes.ToolListChangedNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkResourceListChangedNotification(
  sdk: SDKTypes.ResourceListChangedNotification,
  spec: SpecTypes.ResourceListChangedNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkPromptListChangedNotification(
  sdk: SDKTypes.PromptListChangedNotification,
  spec: SpecTypes.PromptListChangedNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkRootsListChangedNotification(
  sdk: SDKTypes.RootsListChangedNotification,
  spec: SpecTypes.RootsListChangedNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkResourceUpdatedNotification(
  sdk: SDKTypes.ResourceUpdatedNotification,
  spec: SpecTypes.ResourceUpdatedNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkSamplingMessage(
  sdk: RemovePassthrough<SDKTypes.SamplingMessage>,
  spec: SpecTypes.SamplingMessage
) {
  sdk = spec;
  spec = sdk;
}
function checkCreateMessageResult(
  sdk: RemovePassthrough<SDKTypes.CreateMessageResult>,
  spec: SpecTypes.CreateMessageResult
) {
  sdk = spec;
  spec = sdk;
}
function checkSetLevelRequest(
  sdk: SDKTypes.SetLevelRequest,
  spec: SpecTypes.SetLevelRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkPingRequest(
  sdk: SDKTypes.PingRequest,
  spec: SpecTypes.PingRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkInitializedNotification(
  sdk: SDKTypes.InitializedNotification,
  spec: SpecTypes.InitializedNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkListResourcesRequest(
  sdk: SDKTypes.ListResourcesRequest,
  spec: SpecTypes.ListResourcesRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkListResourcesResult(
  sdk: RemovePassthrough<SDKTypes.ListResourcesResult>,
  spec: SpecTypes.ListResourcesResult
) {
  sdk = spec;
  spec = sdk;
}
function checkListResourceTemplatesRequest(
  sdk: SDKTypes.ListResourceTemplatesRequest,
  spec: SpecTypes.ListResourceTemplatesRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkListResourceTemplatesResult(
  sdk: RemovePassthrough<SDKTypes.ListResourceTemplatesResult>,
  spec: SpecTypes.ListResourceTemplatesResult
) {
  sdk = spec;
  spec = sdk;
}
function checkReadResourceRequest(
  sdk: SDKTypes.ReadResourceRequest,
  spec: SpecTypes.ReadResourceRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkReadResourceResult(
  sdk: RemovePassthrough<SDKTypes.ReadResourceResult>,
  spec: SpecTypes.ReadResourceResult
) {
  sdk = spec;
  spec = sdk;
}
function checkResourceContents(
  sdk: RemovePassthrough<SDKTypes.ResourceContents>,
  spec: SpecTypes.ResourceContents
) {
  sdk = spec;
  spec = sdk;
}
function checkTextResourceContents(
  sdk: RemovePassthrough<SDKTypes.TextResourceContents>,
  spec: SpecTypes.TextResourceContents
) {
  sdk = spec;
  spec = sdk;
}
function checkBlobResourceContents(
  sdk: RemovePassthrough<SDKTypes.BlobResourceContents>,
  spec: SpecTypes.BlobResourceContents
) {
  sdk = spec;
  spec = sdk;
}
function checkResource(
  sdk: RemovePassthrough<SDKTypes.Resource>,
  spec: SpecTypes.Resource
) {
  sdk = spec;
  spec = sdk;
}
function checkResourceTemplate(
  sdk: RemovePassthrough<SDKTypes.ResourceTemplate>,
  spec: SpecTypes.ResourceTemplate
) {
  sdk = spec;
  spec = sdk;
}
function checkPromptArgument(
  sdk: RemovePassthrough<SDKTypes.PromptArgument>,
  spec: SpecTypes.PromptArgument
) {
  sdk = spec;
  spec = sdk;
}
function checkPrompt(
  sdk: RemovePassthrough<SDKTypes.Prompt>,
  spec: SpecTypes.Prompt
) {
  sdk = spec;
  spec = sdk;
}
function checkListPromptsRequest(
  sdk: SDKTypes.ListPromptsRequest,
  spec: SpecTypes.ListPromptsRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkListPromptsResult(
  sdk: RemovePassthrough<SDKTypes.ListPromptsResult>,
  spec: SpecTypes.ListPromptsResult
) {
  sdk = spec;
  spec = sdk;
}
function checkGetPromptRequest(
  sdk: SDKTypes.GetPromptRequest,
  spec: SpecTypes.GetPromptRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkTextContent(
  sdk: RemovePassthrough<SDKTypes.TextContent>,
  spec: SpecTypes.TextContent
) {
  sdk = spec;
  spec = sdk;
}
function checkImageContent(
  sdk: RemovePassthrough<SDKTypes.ImageContent>,
  spec: SpecTypes.ImageContent
) {
  sdk = spec;
  spec = sdk;
}
function checkAudioContent(
  sdk: RemovePassthrough<SDKTypes.AudioContent>,
  spec: SpecTypes.AudioContent
) {
  sdk = spec;
  spec = sdk;
}
function checkEmbeddedResource(
  sdk: RemovePassthrough<SDKTypes.EmbeddedResource>,
  spec: SpecTypes.EmbeddedResource
) {
  sdk = spec;
  spec = sdk;
}
function checkResourceLink(
  sdk: RemovePassthrough<SDKTypes.ResourceLink>,
  spec: SpecTypes.ResourceLink
) {
  sdk = spec;
  spec = sdk;
}
function checkContentBlock(
  sdk: RemovePassthrough<SDKTypes.ContentBlock>,
  spec: SpecTypes.ContentBlock
) {
  sdk = spec;
  spec = sdk;
}
function checkPromptMessage(
  sdk: RemovePassthrough<SDKTypes.PromptMessage>,
  spec: SpecTypes.PromptMessage
) {
  sdk = spec;
  spec = sdk;
}
function checkGetPromptResult(
  sdk: RemovePassthrough<SDKTypes.GetPromptResult>,
  spec: SpecTypes.GetPromptResult
) {
  sdk = spec;
  spec = sdk;
}
function checkBooleanSchema(
  sdk: RemovePassthrough<SDKTypes.BooleanSchema>,
  spec: SpecTypes.BooleanSchema
) {
  sdk = spec;
  spec = sdk;
}
function checkStringSchema(
  sdk: RemovePassthrough<SDKTypes.StringSchema>,
  spec: SpecTypes.StringSchema
) {
  sdk = spec;
  spec = sdk;
}
function checkNumberSchema(
  sdk: RemovePassthrough<SDKTypes.NumberSchema>,
  spec: SpecTypes.NumberSchema
) {
  sdk = spec;
  spec = sdk;
}
function checkEnumSchema(
  sdk: RemovePassthrough<SDKTypes.EnumSchema>,
  spec: SpecTypes.EnumSchema
) {
  sdk = spec;
  spec = sdk;
}
function checkPrimitiveSchemaDefinition(
  sdk: RemovePassthrough<SDKTypes.PrimitiveSchemaDefinition>,
  spec: SpecTypes.PrimitiveSchemaDefinition
) {
  sdk = spec;
  spec = sdk;
}
function checkJSONRPCError(
  sdk: SDKTypes.JSONRPCError,
  spec: SpecTypes.JSONRPCError
) {
  sdk = spec;
  spec = sdk;
}
function checkJSONRPCMessage(
  sdk: SDKTypes.JSONRPCMessage,
  spec: SpecTypes.JSONRPCMessage
) {
  sdk = spec;
  spec = sdk;
}
function checkCreateMessageRequest(
  sdk: RemovePassthrough<SDKTypes.CreateMessageRequest>,
  spec: SpecTypes.CreateMessageRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkInitializeRequest(
  sdk: RemovePassthrough<SDKTypes.InitializeRequest>,
  spec: SpecTypes.InitializeRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkInitializeResult(
  sdk: RemovePassthrough<SDKTypes.InitializeResult>,
  spec: SpecTypes.InitializeResult
) {
  sdk = spec;
  spec = sdk;
}
function checkClientCapabilities(
  sdk: RemovePassthrough<SDKTypes.ClientCapabilities>,
  spec: SpecTypes.ClientCapabilities
) {
  sdk = spec;
  spec = sdk;
}
function checkServerCapabilities(
  sdk: RemovePassthrough<SDKTypes.ServerCapabilities>,
  spec: SpecTypes.ServerCapabilities
) {
  sdk = spec;
  spec = sdk;
}
function checkClientRequest(
  sdk: RemovePassthrough<SDKTypes.ClientRequest>,
  spec: SpecTypes.ClientRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkServerRequest(
  sdk: RemovePassthrough<SDKTypes.ServerRequest>,
  spec: SpecTypes.ServerRequest
) {
  sdk = spec;
  spec = sdk;
}
function checkLoggingMessageNotification(
  sdk: MakeUnknownsNotOptional<SDKTypes.LoggingMessageNotification>,
  spec: SpecTypes.LoggingMessageNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkServerNotification(
  sdk: MakeUnknownsNotOptional<SDKTypes.ServerNotification>,
  spec: SpecTypes.ServerNotification
) {
  sdk = spec;
  spec = sdk;
}
function checkLoggingLevel(
  sdk: SDKTypes.LoggingLevel,
  spec: SpecTypes.LoggingLevel
) {
  sdk = spec;
  spec = sdk;
}

// This file is .gitignore'd, and fetched by `npm run fetch:spec-types` (called by `npm run test`)
const SPEC_TYPES_FILE  = 'spec.types.ts';
const SDK_TYPES_FILE  = 'src/types.ts';

const MISSING_SDK_TYPES = [
  // These are inlined in the SDK:
  'Role',

  // These aren't supported by the SDK yet:
  // TODO: Add definitions to the SDK
  'Annotations',
  'ModelHint',
  'ModelPreferences',
]

function extractExportedTypes(source: string): string[] {
  return [...source.matchAll(/export\s+(?:interface|class|type)\s+(\w+)\b/g)].map(m => m[1]);
}

describe('Spec Types', () => {
  const specTypes = extractExportedTypes(fs.readFileSync(SPEC_TYPES_FILE, 'utf-8'));
  const sdkTypes = extractExportedTypes(fs.readFileSync(SDK_TYPES_FILE, 'utf-8'));
  const testSource = fs.readFileSync(__filename, 'utf-8');

  it('should define some expected types', () => {
    expect(specTypes).toContain('JSONRPCNotification');
    expect(specTypes).toContain('ElicitResult');
    expect(specTypes).toHaveLength(91);
  });

  it('should have up to date list of missing sdk types', () => {
    for (const typeName of MISSING_SDK_TYPES) {
      expect(sdkTypes).not.toContain(typeName);
    }
  });

  for (const type of specTypes) {
    if (MISSING_SDK_TYPES.includes(type)) {
      continue; // Skip missing SDK types
    }
    it(`${type} should have a compatibility test`, () => {
      expect(testSource).toContain(`function check${type}(`);
    });
  }
});



================================================
FILE: src/types.test.ts
================================================
import {
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    ResourceLinkSchema,
    ContentBlockSchema,
    PromptMessageSchema,
    CallToolResultSchema,
    CompleteRequestSchema
} from "./types.js";

describe("Types", () => {

    test("should have correct latest protocol version", () => {
        expect(LATEST_PROTOCOL_VERSION).toBeDefined();
        expect(LATEST_PROTOCOL_VERSION).toBe("2025-06-18");
    });
    test("should have correct supported protocol versions", () => {
        expect(SUPPORTED_PROTOCOL_VERSIONS).toBeDefined();
        expect(SUPPORTED_PROTOCOL_VERSIONS).toBeInstanceOf(Array);
        expect(SUPPORTED_PROTOCOL_VERSIONS).toContain(LATEST_PROTOCOL_VERSION);
        expect(SUPPORTED_PROTOCOL_VERSIONS).toContain("2024-11-05");
        expect(SUPPORTED_PROTOCOL_VERSIONS).toContain("2024-10-07");
        expect(SUPPORTED_PROTOCOL_VERSIONS).toContain("2025-03-26");
    });

    describe("ResourceLink", () => {
        test("should validate a minimal ResourceLink", () => {
            const resourceLink = {
                type: "resource_link",
                uri: "file:///path/to/file.txt",
                name: "file.txt"
            };

            const result = ResourceLinkSchema.safeParse(resourceLink);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe("resource_link");
                expect(result.data.uri).toBe("file:///path/to/file.txt");
                expect(result.data.name).toBe("file.txt");
            }
        });

        test("should validate a ResourceLink with all optional fields", () => {
            const resourceLink = {
                type: "resource_link",
                uri: "https://example.com/resource",
                name: "Example Resource",
                title: "A comprehensive example resource",
                description: "This resource demonstrates all fields",
                mimeType: "text/plain",
                _meta: { custom: "metadata" }
            };

            const result = ResourceLinkSchema.safeParse(resourceLink);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.title).toBe("A comprehensive example resource");
                expect(result.data.description).toBe("This resource demonstrates all fields");
                expect(result.data.mimeType).toBe("text/plain");
                expect(result.data._meta).toEqual({ custom: "metadata" });
            }
        });

        test("should fail validation for invalid type", () => {
            const invalidResourceLink = {
                type: "invalid_type",
                uri: "file:///path/to/file.txt",
                name: "file.txt"
            };

            const result = ResourceLinkSchema.safeParse(invalidResourceLink);
            expect(result.success).toBe(false);
        });

        test("should fail validation for missing required fields", () => {
            const invalidResourceLink = {
                type: "resource_link",
                uri: "file:///path/to/file.txt"
                // missing name
            };

            const result = ResourceLinkSchema.safeParse(invalidResourceLink);
            expect(result.success).toBe(false);
        });
    });

    describe("ContentBlock", () => {
        test("should validate text content", () => {
            const textContent = {
                type: "text",
                text: "Hello, world!"
            };

            const result = ContentBlockSchema.safeParse(textContent);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe("text");
            }
        });

        test("should validate image content", () => {
            const imageContent = {
                type: "image",
                data: "aGVsbG8=", // base64 encoded "hello"
                mimeType: "image/png"
            };

            const result = ContentBlockSchema.safeParse(imageContent);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe("image");
            }
        });

        test("should validate audio content", () => {
            const audioContent = {
                type: "audio",
                data: "aGVsbG8=", // base64 encoded "hello"
                mimeType: "audio/mp3"
            };

            const result = ContentBlockSchema.safeParse(audioContent);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe("audio");
            }
        });

        test("should validate resource link content", () => {
            const resourceLink = {
                type: "resource_link",
                uri: "file:///path/to/file.txt",
                name: "file.txt",
                mimeType: "text/plain"
            };

            const result = ContentBlockSchema.safeParse(resourceLink);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe("resource_link");
            }
        });

        test("should validate embedded resource content", () => {
            const embeddedResource = {
                type: "resource",
                resource: {
                    uri: "file:///path/to/file.txt",
                    mimeType: "text/plain",
                    text: "File contents"
                }
            };

            const result = ContentBlockSchema.safeParse(embeddedResource);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.type).toBe("resource");
            }
        });
    });

    describe("PromptMessage with ContentBlock", () => {
        test("should validate prompt message with resource link", () => {
            const promptMessage = {
                role: "assistant",
                content: {
                    type: "resource_link",
                    uri: "file:///project/src/main.rs",
                    name: "main.rs",
                    description: "Primary application entry point",
                    mimeType: "text/x-rust"
                }
            };

            const result = PromptMessageSchema.safeParse(promptMessage);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.content.type).toBe("resource_link");
            }
        });
    });

    describe("CallToolResult with ContentBlock", () => {
        test("should validate tool result with resource links", () => {
            const toolResult = {
                content: [
                    {
                        type: "text",
                        text: "Found the following files:"
                    },
                    {
                        type: "resource_link",
                        uri: "file:///project/src/main.rs",
                        name: "main.rs",
                        description: "Primary application entry point",
                        mimeType: "text/x-rust"
                    },
                    {
                        type: "resource_link",
                        uri: "file:///project/src/lib.rs",
                        name: "lib.rs",
                        description: "Library exports",
                        mimeType: "text/x-rust"
                    }
                ]
            };

            const result = CallToolResultSchema.safeParse(toolResult);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.content).toHaveLength(3);
                expect(result.data.content[0].type).toBe("text");
                expect(result.data.content[1].type).toBe("resource_link");
                expect(result.data.content[2].type).toBe("resource_link");
            }
        });

        test("should validate empty content array with default", () => {
            const toolResult = {};

            const result = CallToolResultSchema.safeParse(toolResult);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.content).toEqual([]);
            }
        });
    });

    describe("CompleteRequest", () => {
        test("should validate a CompleteRequest without resolved field", () => {
            const request = {
                method: "completion/complete",
                params: {
                    ref: { type: "ref/prompt", name: "greeting" },
                    argument: { name: "name", value: "A" }
                }
            };

            const result = CompleteRequestSchema.safeParse(request);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.method).toBe("completion/complete");
                expect(result.data.params.ref.type).toBe("ref/prompt");
                expect(result.data.params.context).toBeUndefined();
            }
        });

        test("should validate a CompleteRequest with resolved field", () => {
            const request = {
                method: "completion/complete",
                params: {
                    ref: { type: "ref/resource", uri: "github://repos/{owner}/{repo}" },
                    argument: { name: "repo", value: "t" },
                    context: {
                        arguments: {
                            "{owner}": "microsoft"
                        }
                    }
                }
            };

            const result = CompleteRequestSchema.safeParse(request);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.params.context?.arguments).toEqual({
                    "{owner}": "microsoft"
                });
            }
        });

        test("should validate a CompleteRequest with empty resolved field", () => {
            const request = {
                method: "completion/complete",
                params: {
                    ref: { type: "ref/prompt", name: "test" },
                    argument: { name: "arg", value: "" },
                    context: {
                        arguments: {}
                    }
                }
            };

            const result = CompleteRequestSchema.safeParse(request);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.params.context?.arguments).toEqual({});
            }
        });

        test("should validate a CompleteRequest with multiple resolved variables", () => {
            const request = {
                method: "completion/complete",
                params: {
                    ref: { type: "ref/resource", uri: "api://v1/{tenant}/{resource}/{id}" },
                    argument: { name: "id", value: "123" },
                    context: {
                        arguments: {
                            "{tenant}": "acme-corp",
                            "{resource}": "users"
                        }
                    }
                }
            };

            const result = CompleteRequestSchema.safeParse(request);
            expect(result.success).toBe(true);
            if (result.success) {
                expect(result.data.params.context?.arguments).toEqual({
                    "{tenant}": "acme-corp",
                    "{resource}": "users"
                });
            }
        });
    });
});



================================================
FILE: src/__mocks__/pkce-challenge.ts
================================================
export default function pkceChallenge() {
  return {
    code_verifier: "test_verifier",
    code_challenge: "test_challenge",
  };
}


================================================
FILE: src/client/auth.ts
================================================
import pkceChallenge from "pkce-challenge";
import { LATEST_PROTOCOL_VERSION } from "../types.js";
import {
  OAuthClientMetadata,
  OAuthClientInformation,
  OAuthTokens,
  OAuthMetadata,
  OAuthClientInformationFull,
  OAuthProtectedResourceMetadata,
  OAuthErrorResponseSchema,
  AuthorizationServerMetadata,
  OpenIdProviderDiscoveryMetadataSchema
} from "../shared/auth.js";
import { OAuthClientInformationFullSchema, OAuthMetadataSchema, OAuthProtectedResourceMetadataSchema, OAuthTokensSchema } from "../shared/auth.js";
import { checkResourceAllowed, resourceUrlFromServerUrl } from "../shared/auth-utils.js";
import {
  InvalidClientError,
  InvalidGrantError,
  OAUTH_ERRORS,
  OAuthError,
  ServerError,
  UnauthorizedClientError
} from "../server/auth/errors.js";
import { FetchLike } from "../shared/transport.js";

/**
 * Implements an end-to-end OAuth client to be used with one MCP server.
 *
 * This client relies upon a concept of an authorized "session," the exact
 * meaning of which is application-defined. Tokens, authorization codes, and
 * code verifiers should not cross different sessions.
 */
export interface OAuthClientProvider {
  /**
   * The URL to redirect the user agent to after authorization.
   */
  get redirectUrl(): string | URL;

  /**
   * Metadata about this OAuth client.
   */
  get clientMetadata(): OAuthClientMetadata;

  /**
   * Returns a OAuth2 state parameter.
   */
  state?(): string | Promise<string>;

  /**
   * Loads information about this OAuth client, as registered already with the
   * server, or returns `undefined` if the client is not registered with the
   * server.
   */
  clientInformation(): OAuthClientInformation | undefined | Promise<OAuthClientInformation | undefined>;

  /**
   * If implemented, this permits the OAuth client to dynamically register with
   * the server. Client information saved this way should later be read via
   * `clientInformation()`.
   *
   * This method is not required to be implemented if client information is
   * statically known (e.g., pre-registered).
   */
  saveClientInformation?(clientInformation: OAuthClientInformationFull): void | Promise<void>;

  /**
   * Loads any existing OAuth tokens for the current session, or returns
   * `undefined` if there are no saved tokens.
   */
  tokens(): OAuthTokens | undefined | Promise<OAuthTokens | undefined>;

  /**
   * Stores new OAuth tokens for the current session, after a successful
   * authorization.
   */
  saveTokens(tokens: OAuthTokens): void | Promise<void>;

  /**
   * Invoked to redirect the user agent to the given URL to begin the authorization flow.
   */
  redirectToAuthorization(authorizationUrl: URL): void | Promise<void>;

  /**
   * Saves a PKCE code verifier for the current session, before redirecting to
   * the authorization flow.
   */
  saveCodeVerifier(codeVerifier: string): void | Promise<void>;

  /**
   * Loads the PKCE code verifier for the current session, necessary to validate
   * the authorization result.
   */
  codeVerifier(): string | Promise<string>;

  /**
   * Adds custom client authentication to OAuth token requests.
   *
   * This optional method allows implementations to customize how client credentials
   * are included in token exchange and refresh requests. When provided, this method
   * is called instead of the default authentication logic, giving full control over
   * the authentication mechanism.
   *
   * Common use cases include:
   * - Supporting authentication methods beyond the standard OAuth 2.0 methods
   * - Adding custom headers for proprietary authentication schemes
   * - Implementing client assertion-based authentication (e.g., JWT bearer tokens)
   *
   * @param headers - The request headers (can be modified to add authentication)
   * @param params - The request body parameters (can be modified to add credentials)
   * @param url - The token endpoint URL being called
   * @param metadata - Optional OAuth metadata for the server, which may include supported authentication methods
   */
  addClientAuthentication?(headers: Headers, params: URLSearchParams, url: string | URL, metadata?: AuthorizationServerMetadata): void | Promise<void>;

  /**
   * If defined, overrides the selection and validation of the
   * RFC 8707 Resource Indicator. If left undefined, default
   * validation behavior will be used.
   *
   * Implementations must verify the returned resource matches the MCP server.
   */
  validateResourceURL?(serverUrl: string | URL, resource?: string): Promise<URL | undefined>;

  /**
   * If implemented, provides a way for the client to invalidate (e.g. delete) the specified
   * credentials, in the case where the server has indicated that they are no longer valid.
   * This avoids requiring the user to intervene manually.
   */
  invalidateCredentials?(scope: 'all' | 'client' | 'tokens' | 'verifier'): void | Promise<void>;
}

export type AuthResult = "AUTHORIZED" | "REDIRECT";

export class UnauthorizedError extends Error {
  constructor(message?: string) {
    super(message ?? "Unauthorized");
  }
}

type ClientAuthMethod = 'client_secret_basic' | 'client_secret_post' | 'none';

/**
 * Determines the best client authentication method to use based on server support and client configuration.
 *
 * Priority order (highest to lowest):
 * 1. client_secret_basic (if client secret is available)
 * 2. client_secret_post (if client secret is available)
 * 3. none (for public clients)
 *
 * @param clientInformation - OAuth client information containing credentials
 * @param supportedMethods - Authentication methods supported by the authorization server
 * @returns The selected authentication method
 */
function selectClientAuthMethod(
  clientInformation: OAuthClientInformation,
  supportedMethods: string[]
): ClientAuthMethod {
  const hasClientSecret = clientInformation.client_secret !== undefined;

  // If server doesn't specify supported methods, use RFC 6749 defaults
  if (supportedMethods.length === 0) {
    return hasClientSecret ? "client_secret_post" : "none";
  }

  // Try methods in priority order (most secure first)
  if (hasClientSecret && supportedMethods.includes("client_secret_basic")) {
    return "client_secret_basic";
  }

  if (hasClientSecret && supportedMethods.includes("client_secret_post")) {
    return "client_secret_post";
  }

  if (supportedMethods.includes("none")) {
    return "none";
  }

  // Fallback: use what we have
  return hasClientSecret ? "client_secret_post" : "none";
}

/**
 * Applies client authentication to the request based on the specified method.
 *
 * Implements OAuth 2.1 client authentication methods:
 * - client_secret_basic: HTTP Basic authentication (RFC 6749 Section 2.3.1)
 * - client_secret_post: Credentials in request body (RFC 6749 Section 2.3.1)
 * - none: Public client authentication (RFC 6749 Section 2.1)
 *
 * @param method - The authentication method to use
 * @param clientInformation - OAuth client information containing credentials
 * @param headers - HTTP headers object to modify
 * @param params - URL search parameters to modify
 * @throws {Error} When required credentials are missing
 */
function applyClientAuthentication(
  method: ClientAuthMethod,
  clientInformation: OAuthClientInformation,
  headers: Headers,
  params: URLSearchParams
): void {
  const { client_id, client_secret } = clientInformation;

  switch (method) {
    case "client_secret_basic":
      applyBasicAuth(client_id, client_secret, headers);
      return;
    case "client_secret_post":
      applyPostAuth(client_id, client_secret, params);
      return;
    case "none":
      applyPublicAuth(client_id, params);
      return;
    default:
      throw new Error(`Unsupported client authentication method: ${method}`);
  }
}

/**
 * Applies HTTP Basic authentication (RFC 6749 Section 2.3.1)
 */
function applyBasicAuth(clientId: string, clientSecret: string | undefined, headers: Headers): void {
  if (!clientSecret) {
    throw new Error("client_secret_basic authentication requires a client_secret");
  }

  const credentials = btoa(`${clientId}:${clientSecret}`);
  headers.set("Authorization", `Basic ${credentials}`);
}

/**
 * Applies POST body authentication (RFC 6749 Section 2.3.1)
 */
function applyPostAuth(clientId: string, clientSecret: string | undefined, params: URLSearchParams): void {
  params.set("client_id", clientId);
  if (clientSecret) {
    params.set("client_secret", clientSecret);
  }
}

/**
 * Applies public client authentication (RFC 6749 Section 2.1)
 */
function applyPublicAuth(clientId: string, params: URLSearchParams): void {
  params.set("client_id", clientId);
}

/**
 * Parses an OAuth error response from a string or Response object.
 *
 * If the input is a standard OAuth2.0 error response, it will be parsed according to the spec
 * and an instance of the appropriate OAuthError subclass will be returned.
 * If parsing fails, it falls back to a generic ServerError that includes
 * the response status (if available) and original content.
 *
 * @param input - A Response object or string containing the error response
 * @returns A Promise that resolves to an OAuthError instance
 */
export async function parseErrorResponse(input: Response | string): Promise<OAuthError> {
  const statusCode = input instanceof Response ? input.status : undefined;
  const body = input instanceof Response ? await input.text() : input;

  try {
    const result = OAuthErrorResponseSchema.parse(JSON.parse(body));
    const { error, error_description, error_uri } = result;
    const errorClass = OAUTH_ERRORS[error] || ServerError;
    return new errorClass(error_description || '', error_uri);
  } catch (error) {
    // Not a valid OAuth error response, but try to inform the user of the raw data anyway
    const errorMessage = `${statusCode ? `HTTP ${statusCode}: ` : ''}Invalid OAuth error response: ${error}. Raw body: ${body}`;
    return new ServerError(errorMessage);
  }
}

/**
 * Orchestrates the full auth flow with a server.
 *
 * This can be used as a single entry point for all authorization functionality,
 * instead of linking together the other lower-level functions in this module.
 */
export async function auth(
  provider: OAuthClientProvider,
  options: {
    serverUrl: string | URL;
    authorizationCode?: string;
    scope?: string;
    resourceMetadataUrl?: URL;
    fetchFn?: FetchLike;
}): Promise<AuthResult> {
  try {
    return await authInternal(provider, options);
  } catch (error) {
    // Handle recoverable error types by invalidating credentials and retrying
    if (error instanceof InvalidClientError || error instanceof UnauthorizedClientError) {
      await provider.invalidateCredentials?.('all');
      return await authInternal(provider, options);
    } else if (error instanceof InvalidGrantError) {
      await provider.invalidateCredentials?.('tokens');
      return await authInternal(provider, options);
    }

    // Throw otherwise
    throw error
  }
}

async function authInternal(
  provider: OAuthClientProvider,
  { serverUrl,
    authorizationCode,
    scope,
    resourceMetadataUrl,
    fetchFn,
  }: {
    serverUrl: string | URL;
    authorizationCode?: string;
    scope?: string;
    resourceMetadataUrl?: URL;
    fetchFn?: FetchLike;
  },
): Promise<AuthResult> {

  let resourceMetadata: OAuthProtectedResourceMetadata | undefined;
  let authorizationServerUrl: string | URL | undefined;
  try {
    resourceMetadata = await discoverOAuthProtectedResourceMetadata(serverUrl, { resourceMetadataUrl }, fetchFn);
    if (resourceMetadata.authorization_servers && resourceMetadata.authorization_servers.length > 0) {
      authorizationServerUrl = resourceMetadata.authorization_servers[0];
    }
  } catch {
    // Ignore errors and fall back to /.well-known/oauth-authorization-server
  }

  /**
   * If we don't get a valid authorization server metadata from protected resource metadata,
   * fallback to the legacy MCP spec's implementation (version 2025-03-26): MCP server acts as the Authorization server.
   */
  if (!authorizationServerUrl) {
    authorizationServerUrl = serverUrl;
  }

  const resource: URL | undefined = await selectResourceURL(serverUrl, provider, resourceMetadata);

  const metadata = await discoverAuthorizationServerMetadata(authorizationServerUrl, {
    fetchFn,
  });

  // Handle client registration if needed
  let clientInformation = await Promise.resolve(provider.clientInformation());
  if (!clientInformation) {
    if (authorizationCode !== undefined) {
      throw new Error("Existing OAuth client information is required when exchanging an authorization code");
    }

    if (!provider.saveClientInformation) {
      throw new Error("OAuth client information must be saveable for dynamic registration");
    }

    const fullInformation = await registerClient(authorizationServerUrl, {
      metadata,
      clientMetadata: provider.clientMetadata,
      fetchFn,
    });

    await provider.saveClientInformation(fullInformation);
    clientInformation = fullInformation;
  }

  // Exchange authorization code for tokens
  if (authorizationCode !== undefined) {
    const codeVerifier = await provider.codeVerifier();
    const tokens = await exchangeAuthorization(authorizationServerUrl, {
      metadata,
      clientInformation,
      authorizationCode,
      codeVerifier,
      redirectUri: provider.redirectUrl,
      resource,
      addClientAuthentication: provider.addClientAuthentication,
      fetchFn: fetchFn,
    });

    await provider.saveTokens(tokens);
    return "AUTHORIZED"
  }

  const tokens = await provider.tokens();

  // Handle token refresh or new authorization
  if (tokens?.refresh_token) {
    try {
      // Attempt to refresh the token
      const newTokens = await refreshAuthorization(authorizationServerUrl, {
        metadata,
        clientInformation,
        refreshToken: tokens.refresh_token,
        resource,
        addClientAuthentication: provider.addClientAuthentication,
        fetchFn,
      });

      await provider.saveTokens(newTokens);
      return "AUTHORIZED"
    } catch (error) {
      // If this is a ServerError, or an unknown type, log it out and try to continue. Otherwise, escalate so we can fix things and retry.
      if (!(error instanceof OAuthError) || error instanceof ServerError) {
        // Could not refresh OAuth tokens
      } else {
        // Refresh failed for another reason, re-throw
        throw error;
      }
    }
  }

  const state = provider.state ? await provider.state() : undefined;

  // Start new authorization flow
  const { authorizationUrl, codeVerifier } = await startAuthorization(authorizationServerUrl, {
    metadata,
    clientInformation,
    state,
    redirectUrl: provider.redirectUrl,
    scope: scope || provider.clientMetadata.scope,
    resource,
  });

  await provider.saveCodeVerifier(codeVerifier);
  await provider.redirectToAuthorization(authorizationUrl);
  return "REDIRECT"
}

export async function selectResourceURL(serverUrl: string | URL, provider: OAuthClientProvider, resourceMetadata?: OAuthProtectedResourceMetadata): Promise<URL | undefined> {
  const defaultResource = resourceUrlFromServerUrl(serverUrl);

  // If provider has custom validation, delegate to it
  if (provider.validateResourceURL) {
    return await provider.validateResourceURL(defaultResource, resourceMetadata?.resource);
  }

  // Only include resource parameter when Protected Resource Metadata is present
  if (!resourceMetadata) {
    return undefined;
  }

  // Validate that the metadata's resource is compatible with our request
  if (!checkResourceAllowed({ requestedResource: defaultResource, configuredResource: resourceMetadata.resource })) {
    throw new Error(`Protected resource ${resourceMetadata.resource} does not match expected ${defaultResource} (or origin)`);
  }
  // Prefer the resource from metadata since it's what the server is telling us to request
  return new URL(resourceMetadata.resource);
}

/**
 * Extract resource_metadata from response header.
 */
export function extractResourceMetadataUrl(res: Response): URL | undefined {

  const authenticateHeader = res.headers.get("WWW-Authenticate");
  if (!authenticateHeader) {
    return undefined;
  }

  const [type, scheme] = authenticateHeader.split(' ');
  if (type.toLowerCase() !== 'bearer' || !scheme) {
    return undefined;
  }
  const regex = /resource_metadata="([^"]*)"/;
  const match = regex.exec(authenticateHeader);

  if (!match) {
    return undefined;
  }

  try {
    return new URL(match[1]);
  } catch {
    return undefined;
  }
}

/**
 * Looks up RFC 9728 OAuth 2.0 Protected Resource Metadata.
 *
 * If the server returns a 404 for the well-known endpoint, this function will
 * return `undefined`. Any other errors will be thrown as exceptions.
 */
export async function discoverOAuthProtectedResourceMetadata(
  serverUrl: string | URL,
  opts?: { protocolVersion?: string, resourceMetadataUrl?: string | URL },
  fetchFn: FetchLike = fetch,
): Promise<OAuthProtectedResourceMetadata> {
  const response = await discoverMetadataWithFallback(
    serverUrl,
    'oauth-protected-resource',
    fetchFn,
    {
      protocolVersion: opts?.protocolVersion,
      metadataUrl: opts?.resourceMetadataUrl,
    },
  );

  if (!response || response.status === 404) {
    throw new Error(`Resource server does not implement OAuth 2.0 Protected Resource Metadata.`);
  }

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status} trying to load well-known OAuth protected resource metadata.`,
    );
  }
  return OAuthProtectedResourceMetadataSchema.parse(await response.json());
}

/**
 * Helper function to handle fetch with CORS retry logic
 */
async function fetchWithCorsRetry(
  url: URL,
  headers?: Record<string, string>,
  fetchFn: FetchLike = fetch,
): Promise<Response | undefined> {
  try {
    return await fetchFn(url, { headers });
  } catch (error) {
    if (error instanceof TypeError) {
      if (headers) {
        // CORS errors come back as TypeError, retry without headers
        return fetchWithCorsRetry(url, undefined, fetchFn)
      } else {
        // We're getting CORS errors on retry too, return undefined
        return undefined
      }
    }
    throw error;
  }
}

/**
 * Constructs the well-known path for auth-related metadata discovery
 */
function buildWellKnownPath(
  wellKnownPrefix: 'oauth-authorization-server' | 'oauth-protected-resource' | 'openid-configuration',
  pathname: string = '',
  options: { prependPathname?: boolean } = {}
): string {
  // Strip trailing slash from pathname to avoid double slashes
  if (pathname.endsWith('/')) {
    pathname = pathname.slice(0, -1);
  }

  return options.prependPathname
    ? `${pathname}/.well-known/${wellKnownPrefix}`
    : `/.well-known/${wellKnownPrefix}${pathname}`;
}

/**
 * Tries to discover OAuth metadata at a specific URL
 */
async function tryMetadataDiscovery(
  url: URL,
  protocolVersion: string,
  fetchFn: FetchLike = fetch,
): Promise<Response | undefined> {
  const headers = {
    "MCP-Protocol-Version": protocolVersion
  };
  return await fetchWithCorsRetry(url, headers, fetchFn);
}

/**
 * Determines if fallback to root discovery should be attempted
 */
function shouldAttemptFallback(response: Response | undefined, pathname: string): boolean {
  return !response || (response.status >= 400 && response.status < 500) && pathname !== '/';
}

/**
 * Generic function for discovering OAuth metadata with fallback support
 */
async function discoverMetadataWithFallback(
  serverUrl: string | URL,
  wellKnownType: 'oauth-authorization-server' | 'oauth-protected-resource',
  fetchFn: FetchLike,
  opts?: { protocolVersion?: string; metadataUrl?: string | URL, metadataServerUrl?: string | URL },
): Promise<Response | undefined> {
  const issuer = new URL(serverUrl);
  const protocolVersion = opts?.protocolVersion ?? LATEST_PROTOCOL_VERSION;

  let url: URL;
  if (opts?.metadataUrl) {
    url = new URL(opts.metadataUrl);
  } else {
    // Try path-aware discovery first
    const wellKnownPath = buildWellKnownPath(wellKnownType, issuer.pathname);
    url = new URL(wellKnownPath, opts?.metadataServerUrl ?? issuer);
    url.search = issuer.search;
  }

  let response = await tryMetadataDiscovery(url, protocolVersion, fetchFn);

  // If path-aware discovery fails with 404 and we're not already at root, try fallback to root discovery
  if (!opts?.metadataUrl && shouldAttemptFallback(response, issuer.pathname)) {
    const rootUrl = new URL(`/.well-known/${wellKnownType}`, issuer);
    response = await tryMetadataDiscovery(rootUrl, protocolVersion, fetchFn);
  }

  return response;
}

/**
 * Looks up RFC 8414 OAuth 2.0 Authorization Server Metadata.
 *
 * If the server returns a 404 for the well-known endpoint, this function will
 * return `undefined`. Any other errors will be thrown as exceptions.
 *
 * @deprecated This function is deprecated in favor of `discoverAuthorizationServerMetadata`.
 */
export async function discoverOAuthMetadata(
  issuer: string | URL,
  {
    authorizationServerUrl,
    protocolVersion,
  }: {
    authorizationServerUrl?: string | URL,
    protocolVersion?: string,
  } = {},
  fetchFn: FetchLike = fetch,
): Promise<OAuthMetadata | undefined> {
  if (typeof issuer === 'string') {
    issuer = new URL(issuer);
  }
  if (!authorizationServerUrl) {
    authorizationServerUrl = issuer;
  }
  if (typeof authorizationServerUrl === 'string') {
    authorizationServerUrl = new URL(authorizationServerUrl);
  }
  protocolVersion ??= LATEST_PROTOCOL_VERSION ;

  const response = await discoverMetadataWithFallback(
    authorizationServerUrl,
    'oauth-authorization-server',
    fetchFn,
    {
      protocolVersion,
      metadataServerUrl: authorizationServerUrl,
    },
  );

  if (!response || response.status === 404) {
    return undefined;
  }

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status} trying to load well-known OAuth metadata`,
    );
  }

  return OAuthMetadataSchema.parse(await response.json());
}


/**
 * Builds a list of discovery URLs to try for authorization server metadata.
 * URLs are returned in priority order:
 * 1. OAuth metadata at the given URL
 * 2. OAuth metadata at root (if URL has path)
 * 3. OIDC metadata endpoints
 */
export function buildDiscoveryUrls(authorizationServerUrl: string | URL): { url: URL; type: 'oauth' | 'oidc' }[] {
  const url = typeof authorizationServerUrl === 'string' ? new URL(authorizationServerUrl) : authorizationServerUrl;
  const hasPath = url.pathname !== '/';
  const urlsToTry: { url: URL; type: 'oauth' | 'oidc' }[] = [];


  if (!hasPath) {
    // Root path: https://example.com/.well-known/oauth-authorization-server
    urlsToTry.push({
      url: new URL('/.well-known/oauth-authorization-server', url.origin),
      type: 'oauth'
    });

    // OIDC: https://example.com/.well-known/openid-configuration
    urlsToTry.push({
      url: new URL(`/.well-known/openid-configuration`, url.origin),
      type: 'oidc'
    });

    return urlsToTry;
  }

  // Strip trailing slash from pathname to avoid double slashes
  let pathname = url.pathname;
  if (pathname.endsWith('/')) {
    pathname = pathname.slice(0, -1);
  }

  // 1. OAuth metadata at the given URL
  // Insert well-known before the path: https://example.com/.well-known/oauth-authorization-server/tenant1
  urlsToTry.push({
    url: new URL(`/.well-known/oauth-authorization-server${pathname}`, url.origin),
    type: 'oauth'
  });

  // Root path: https://example.com/.well-known/oauth-authorization-server
  urlsToTry.push({
    url: new URL('/.well-known/oauth-authorization-server', url.origin),
    type: 'oauth'
  });

  // 3. OIDC metadata endpoints
  // RFC 8414 style: Insert /.well-known/openid-configuration before the path
  urlsToTry.push({
    url: new URL(`/.well-known/openid-configuration${pathname}`, url.origin),
    type: 'oidc'
  });
  // OIDC Discovery 1.0 style: Append /.well-known/openid-configuration after the path
  urlsToTry.push({
    url: new URL(`${pathname}/.well-known/openid-configuration`, url.origin),
    type: 'oidc'
  });

  return urlsToTry;
}

/**
 * Discovers authorization server metadata with support for RFC 8414 OAuth 2.0 Authorization Server Metadata
 * and OpenID Connect Discovery 1.0 specifications.
 *
 * This function implements a fallback strategy for authorization server discovery:
 * 1. Attempts RFC 8414 OAuth metadata discovery first
 * 2. If OAuth discovery fails, falls back to OpenID Connect Discovery
 *
 * @param authorizationServerUrl - The authorization server URL obtained from the MCP Server's
 *                                 protected resource metadata, or the MCP server's URL if the
 *                                 metadata was not found.
 * @param options - Configuration options
 * @param options.fetchFn - Optional fetch function for making HTTP requests, defaults to global fetch
 * @param options.protocolVersion - MCP protocol version to use, defaults to LATEST_PROTOCOL_VERSION
 * @returns Promise resolving to authorization server metadata, or undefined if discovery fails
 */
export async function discoverAuthorizationServerMetadata(
  authorizationServerUrl: string | URL,
  {
    fetchFn = fetch,
    protocolVersion = LATEST_PROTOCOL_VERSION,
  }: {
    fetchFn?: FetchLike;
    protocolVersion?: string;
  } = {}
): Promise<AuthorizationServerMetadata | undefined> {
  const headers = { 'MCP-Protocol-Version': protocolVersion };

  // Get the list of URLs to try
  const urlsToTry = buildDiscoveryUrls(authorizationServerUrl);

  // Try each URL in order
  for (const { url: endpointUrl, type } of urlsToTry) {
    const response = await fetchWithCorsRetry(endpointUrl, headers, fetchFn);

    if (!response) {
      /**
       * CORS error occurred - don't throw as the endpoint may not allow CORS,
       * continue trying other possible endpoints
       */
      continue;
    }

    if (!response.ok) {
      // Continue looking for any 4xx response code.
      if (response.status >= 400 && response.status < 500) {
        continue; // Try next URL
      }
      throw new Error(`HTTP ${response.status} trying to load ${type === 'oauth' ? 'OAuth' : 'OpenID provider'} metadata from ${endpointUrl}`);
    }

    // Parse and validate based on type
    if (type === 'oauth') {
      return OAuthMetadataSchema.parse(await response.json());
    } else {
      const metadata = OpenIdProviderDiscoveryMetadataSchema.parse(await response.json());

      // MCP spec requires OIDC providers to support S256 PKCE
      if (!metadata.code_challenge_methods_supported?.includes('S256')) {
        throw new Error(
          `Incompatible OIDC provider at ${endpointUrl}: does not support S256 code challenge method required by MCP specification`
        );
      }

      return metadata;
    }
  }

  return undefined;
}

/**
 * Begins the authorization flow with the given server, by generating a PKCE challenge and constructing the authorization URL.
 */
export async function startAuthorization(
  authorizationServerUrl: string | URL,
  {
    metadata,
    clientInformation,
    redirectUrl,
    scope,
    state,
    resource,
  }: {
    metadata?: AuthorizationServerMetadata;
    clientInformation: OAuthClientInformation;
    redirectUrl: string | URL;
    scope?: string;
    state?: string;
    resource?: URL;
  },
): Promise<{ authorizationUrl: URL; codeVerifier: string }> {
  const responseType = "code";
  const codeChallengeMethod = "S256";

  let authorizationUrl: URL;
  if (metadata) {
    authorizationUrl = new URL(metadata.authorization_endpoint);

    if (!metadata.response_types_supported.includes(responseType)) {
      throw new Error(
        `Incompatible auth server: does not support response type ${responseType}`,
      );
    }

    if (
      !metadata.code_challenge_methods_supported ||
      !metadata.code_challenge_methods_supported.includes(codeChallengeMethod)
    ) {
      throw new Error(
        `Incompatible auth server: does not support code challenge method ${codeChallengeMethod}`,
      );
    }
  } else {
    authorizationUrl = new URL("/authorize", authorizationServerUrl);
  }

  // Generate PKCE challenge
  const challenge = await pkceChallenge();
  const codeVerifier = challenge.code_verifier;
  const codeChallenge = challenge.code_challenge;

  authorizationUrl.searchParams.set("response_type", responseType);
  authorizationUrl.searchParams.set("client_id", clientInformation.client_id);
  authorizationUrl.searchParams.set("code_challenge", codeChallenge);
  authorizationUrl.searchParams.set(
    "code_challenge_method",
    codeChallengeMethod,
  );
  authorizationUrl.searchParams.set("redirect_uri", String(redirectUrl));

  if (state) {
    authorizationUrl.searchParams.set("state", state);
  }

  if (scope) {
    authorizationUrl.searchParams.set("scope", scope);
  }

  if (scope?.includes("offline_access")) {
    // if the request includes the OIDC-only "offline_access" scope,
    // we need to set the prompt to "consent" to ensure the user is prompted to grant offline access
    // https://openid.net/specs/openid-connect-core-1_0.html#OfflineAccess
    authorizationUrl.searchParams.append("prompt", "consent");
  }

  if (resource) {
    authorizationUrl.searchParams.set("resource", resource.href);
  }

  return { authorizationUrl, codeVerifier };
}

/**
 * Exchanges an authorization code for an access token with the given server.
 *
 * Supports multiple client authentication methods as specified in OAuth 2.1:
 * - Automatically selects the best authentication method based on server support
 * - Falls back to appropriate defaults when server metadata is unavailable
 *
 * @param authorizationServerUrl - The authorization server's base URL
 * @param options - Configuration object containing client info, auth code, etc.
 * @returns Promise resolving to OAuth tokens
 * @throws {Error} When token exchange fails or authentication is invalid
 */
export async function exchangeAuthorization(
  authorizationServerUrl: string | URL,
  {
    metadata,
    clientInformation,
    authorizationCode,
    codeVerifier,
    redirectUri,
    resource,
    addClientAuthentication,
    fetchFn,
  }: {
    metadata?: AuthorizationServerMetadata;
    clientInformation: OAuthClientInformation;
    authorizationCode: string;
    codeVerifier: string;
    redirectUri: string | URL;
    resource?: URL;
    addClientAuthentication?: OAuthClientProvider["addClientAuthentication"];
    fetchFn?: FetchLike;
  },
): Promise<OAuthTokens> {
  const grantType = "authorization_code";

  const tokenUrl = metadata?.token_endpoint
      ? new URL(metadata.token_endpoint)
      : new URL("/token", authorizationServerUrl);

  if (
      metadata?.grant_types_supported &&
      !metadata.grant_types_supported.includes(grantType)
  ) {
    throw new Error(
        `Incompatible auth server: does not support grant type ${grantType}`,
    );
  }

  // Exchange code for tokens
  const headers = new Headers({
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
  });
  const params = new URLSearchParams({
    grant_type: grantType,
    code: authorizationCode,
    code_verifier: codeVerifier,
    redirect_uri: String(redirectUri),
  });

  if (addClientAuthentication) {
    addClientAuthentication(headers, params, authorizationServerUrl, metadata);
  } else {
    // Determine and apply client authentication method
    const supportedMethods = metadata?.token_endpoint_auth_methods_supported ?? [];
    const authMethod = selectClientAuthMethod(clientInformation, supportedMethods);

    applyClientAuthentication(authMethod, clientInformation, headers, params);
  }

  if (resource) {
    params.set("resource", resource.href);
  }

  const response = await (fetchFn ?? fetch)(tokenUrl, {
    method: "POST",
    headers,
    body: params,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  return OAuthTokensSchema.parse(await response.json());
}

/**
 * Exchange a refresh token for an updated access token.
 *
 * Supports multiple client authentication methods as specified in OAuth 2.1:
 * - Automatically selects the best authentication method based on server support
 * - Preserves the original refresh token if a new one is not returned
 *
 * @param authorizationServerUrl - The authorization server's base URL
 * @param options - Configuration object containing client info, refresh token, etc.
 * @returns Promise resolving to OAuth tokens (preserves original refresh_token if not replaced)
 * @throws {Error} When token refresh fails or authentication is invalid
 */
export async function refreshAuthorization(
  authorizationServerUrl: string | URL,
  {
    metadata,
    clientInformation,
    refreshToken,
    resource,
    addClientAuthentication,
    fetchFn,
  }: {
    metadata?: AuthorizationServerMetadata;
    clientInformation: OAuthClientInformation;
    refreshToken: string;
    resource?: URL;
    addClientAuthentication?: OAuthClientProvider["addClientAuthentication"];
    fetchFn?: FetchLike;
  }
): Promise<OAuthTokens> {
  const grantType = "refresh_token";

  let tokenUrl: URL;
  if (metadata) {
    tokenUrl = new URL(metadata.token_endpoint);

    if (
      metadata.grant_types_supported &&
      !metadata.grant_types_supported.includes(grantType)
    ) {
      throw new Error(
        `Incompatible auth server: does not support grant type ${grantType}`,
      );
    }
  } else {
    tokenUrl = new URL("/token", authorizationServerUrl);
  }

  // Exchange refresh token
  const headers = new Headers({
    "Content-Type": "application/x-www-form-urlencoded",
  });
  const params = new URLSearchParams({
    grant_type: grantType,
    refresh_token: refreshToken,
  });

  if (addClientAuthentication) {
    addClientAuthentication(headers, params, authorizationServerUrl, metadata);
  } else {
    // Determine and apply client authentication method
    const supportedMethods = metadata?.token_endpoint_auth_methods_supported ?? [];
    const authMethod = selectClientAuthMethod(clientInformation, supportedMethods);

    applyClientAuthentication(authMethod, clientInformation, headers, params);
  }

  if (resource) {
    params.set("resource", resource.href);
  }

  const response = await (fetchFn ?? fetch)(tokenUrl, {
    method: "POST",
    headers,
    body: params,
  });
  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  return OAuthTokensSchema.parse({ refresh_token: refreshToken, ...(await response.json()) });
}

/**
 * Performs OAuth 2.0 Dynamic Client Registration according to RFC 7591.
 */
export async function registerClient(
  authorizationServerUrl: string | URL,
  {
    metadata,
    clientMetadata,
    fetchFn,
  }: {
    metadata?: AuthorizationServerMetadata;
    clientMetadata: OAuthClientMetadata;
    fetchFn?: FetchLike;
  },
): Promise<OAuthClientInformationFull> {
  let registrationUrl: URL;

  if (metadata) {
    if (!metadata.registration_endpoint) {
      throw new Error("Incompatible auth server: does not support dynamic client registration");
    }

    registrationUrl = new URL(metadata.registration_endpoint);
  } else {
    registrationUrl = new URL("/register", authorizationServerUrl);
  }

  const response = await (fetchFn ?? fetch)(registrationUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(clientMetadata),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  return OAuthClientInformationFullSchema.parse(await response.json());
}



================================================
FILE: src/client/cross-spawn.test.ts
================================================
import { StdioClientTransport, getDefaultEnvironment } from "./stdio.js";
import spawn from "cross-spawn";
import { JSONRPCMessage } from "../types.js";
import { ChildProcess } from "node:child_process";

// mock cross-spawn
jest.mock("cross-spawn");
const mockSpawn = spawn as jest.MockedFunction<typeof spawn>;

describe("StdioClientTransport using cross-spawn", () => {
  beforeEach(() => {
    // mock cross-spawn's return value
    mockSpawn.mockImplementation(() => {
      const mockProcess: {
        on: jest.Mock;
        stdin?: { on: jest.Mock; write: jest.Mock };
        stdout?: { on: jest.Mock };
        stderr?: null;
      } = {
        on: jest.fn((event: string, callback: () => void) => {
          if (event === "spawn") {
            callback();
          }
          return mockProcess;
        }),
        stdin: {
          on: jest.fn(),
          write: jest.fn().mockReturnValue(true)
        },
        stdout: {
          on: jest.fn()
        },
        stderr: null
      };
      return mockProcess as unknown as ChildProcess;
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test("should call cross-spawn correctly", async () => {
    const transport = new StdioClientTransport({
      command: "test-command",
      args: ["arg1", "arg2"]
    });

    await transport.start();

    // verify spawn is called correctly
    expect(mockSpawn).toHaveBeenCalledWith(
      "test-command",
      ["arg1", "arg2"],
      expect.objectContaining({
        shell: false
      })
    );
  });

  test("should pass environment variables correctly", async () => {
    const customEnv = { TEST_VAR: "test-value" };
    const transport = new StdioClientTransport({
      command: "test-command",
      env: customEnv
    });

    await transport.start();

    // verify environment variables are merged correctly
    expect(mockSpawn).toHaveBeenCalledWith(
      "test-command",
      [],
      expect.objectContaining({
        env: {
          ...getDefaultEnvironment(),
          ...customEnv
        }
      })
    );
  });

  test("should use default environment when env is undefined", async () => {
    const transport = new StdioClientTransport({
      command: "test-command",
      env: undefined
    });

    await transport.start();

    // verify default environment is used
    expect(mockSpawn).toHaveBeenCalledWith(
      "test-command",
      [],
      expect.objectContaining({
        env: getDefaultEnvironment()
      })
    );
  });

  test("should send messages correctly", async () => {
    const transport = new StdioClientTransport({
      command: "test-command"
    });

    // get the mock process object
    const mockProcess: {
      on: jest.Mock;
      stdin: {
        on: jest.Mock;
        write: jest.Mock;
        once: jest.Mock;
      };
      stdout: {
        on: jest.Mock;
      };
      stderr: null;
    } = {
      on: jest.fn((event: string, callback: () => void) => {
        if (event === "spawn") {
          callback();
        }
        return mockProcess;
      }),
      stdin: {
        on: jest.fn(),
        write: jest.fn().mockReturnValue(true),
        once: jest.fn()
      },
      stdout: {
        on: jest.fn()
      },
      stderr: null
    };

    mockSpawn.mockReturnValue(mockProcess as unknown as ChildProcess);

    await transport.start();

    // 关键修复：确保 jsonrpc 是字面量 "2.0"
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      id: "test-id",
      method: "test-method"
    };

    await transport.send(message);

    // verify message is sent correctly
    expect(mockProcess.stdin.write).toHaveBeenCalled();
  });
});


================================================
FILE: src/client/index.test.ts
================================================
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-constant-binary-expression */
/* eslint-disable @typescript-eslint/no-unused-expressions */
import { Client } from "./index.js";
import { z } from "zod";
import {
  RequestSchema,
  NotificationSchema,
  ResultSchema,
  LATEST_PROTOCOL_VERSION,
  SUPPORTED_PROTOCOL_VERSIONS,
  InitializeRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema,
  CreateMessageRequestSchema,
  ElicitRequestSchema,
  ListRootsRequestSchema,
  ErrorCode,
} from "../types.js";
import { Transport } from "../shared/transport.js";
import { Server } from "../server/index.js";
import { InMemoryTransport } from "../inMemory.js";

/***
 * Test: Initialize with Matching Protocol Version
 */
test("should initialize with matching protocol version", async () => {
  const clientTransport: Transport = {
    start: jest.fn().mockResolvedValue(undefined),
    close: jest.fn().mockResolvedValue(undefined),
    send: jest.fn().mockImplementation((message) => {
      if (message.method === "initialize") {
        clientTransport.onmessage?.({
          jsonrpc: "2.0",
          id: message.id,
          result: {
            protocolVersion: LATEST_PROTOCOL_VERSION,
            capabilities: {},
            serverInfo: {
              name: "test",
              version: "1.0",
            },
            instructions: "test instructions",
          },
        });
      }
      return Promise.resolve();
    }),
  };

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  await client.connect(clientTransport);

  // Should have sent initialize with latest version
  expect(clientTransport.send).toHaveBeenCalledWith(
    expect.objectContaining({
      method: "initialize",
      params: expect.objectContaining({
        protocolVersion: LATEST_PROTOCOL_VERSION,
      }),
    }),
    expect.objectContaining({
      relatedRequestId: undefined,
    }),
  );

  // Should have the instructions returned
  expect(client.getInstructions()).toEqual("test instructions");
});

/***
 * Test: Initialize with Supported Older Protocol Version
 */
test("should initialize with supported older protocol version", async () => {
  const OLD_VERSION = SUPPORTED_PROTOCOL_VERSIONS[1];
  const clientTransport: Transport = {
    start: jest.fn().mockResolvedValue(undefined),
    close: jest.fn().mockResolvedValue(undefined),
    send: jest.fn().mockImplementation((message) => {
      if (message.method === "initialize") {
        clientTransport.onmessage?.({
          jsonrpc: "2.0",
          id: message.id,
          result: {
            protocolVersion: OLD_VERSION,
            capabilities: {},
            serverInfo: {
              name: "test",
              version: "1.0",
            },
          },
        });
      }
      return Promise.resolve();
    }),
  };

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  await client.connect(clientTransport);

  // Connection should succeed with the older version
  expect(client.getServerVersion()).toEqual({
    name: "test",
    version: "1.0",
  });

  // Expect no instructions
  expect(client.getInstructions()).toBeUndefined();
});

/***
 * Test: Reject Unsupported Protocol Version
 */
test("should reject unsupported protocol version", async () => {
  const clientTransport: Transport = {
    start: jest.fn().mockResolvedValue(undefined),
    close: jest.fn().mockResolvedValue(undefined),
    send: jest.fn().mockImplementation((message) => {
      if (message.method === "initialize") {
        clientTransport.onmessage?.({
          jsonrpc: "2.0",
          id: message.id,
          result: {
            protocolVersion: "invalid-version",
            capabilities: {},
            serverInfo: {
              name: "test",
              version: "1.0",
            },
          },
        });
      }
      return Promise.resolve();
    }),
  };

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  await expect(client.connect(clientTransport)).rejects.toThrow(
    "Server's protocol version is not supported: invalid-version",
  );

  expect(clientTransport.close).toHaveBeenCalled();
});

/***
 * Test: Connect New Client to Old Supported Server Version
 */
test("should connect new client to old, supported server version", async () => {
  const OLD_VERSION = SUPPORTED_PROTOCOL_VERSIONS[1];
  const server = new Server(
      {
        name: "test server",
        version: "1.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      },
  );

  server.setRequestHandler(InitializeRequestSchema, (_request) => ({
    protocolVersion: OLD_VERSION,
    capabilities: {
      resources: {},
      tools: {},
    },
    serverInfo: {
      name: "old server",
      version: "1.0",
    },
  }));

  server.setRequestHandler(ListResourcesRequestSchema, () => ({
    resources: [],
  }));

  server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: [],
  }));

  const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();

  const client = new Client(
      {
        name: "new client",
        version: "1.0",
        protocolVersion: LATEST_PROTOCOL_VERSION,
      },
      {
        capabilities: {
          sampling: {},
        },
        enforceStrictCapabilities: true,
      },
  );

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  expect(client.getServerVersion()).toEqual({
    name: "old server",
    version: "1.0",
  });
});

/***
 * Test: Version Negotiation with Old Client and Newer Server
 */
test("should negotiate version when client is old, and newer server supports its version", async () => {
  const OLD_VERSION = SUPPORTED_PROTOCOL_VERSIONS[1];
  const server = new Server(
      {
        name: "new server",
        version: "1.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      },
  );

  server.setRequestHandler(InitializeRequestSchema, (_request) => ({
    protocolVersion: LATEST_PROTOCOL_VERSION,
    capabilities: {
      resources: {},
      tools: {},
    },
    serverInfo: {
      name: "new server",
      version: "1.0",
    },
  }));

  server.setRequestHandler(ListResourcesRequestSchema, () => ({
    resources: [],
  }));

  server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: [],
  }));

  const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();

  const client = new Client(
      {
        name: "old client",
        version: "1.0",
        protocolVersion: OLD_VERSION,
      },
      {
        capabilities: {
          sampling: {},
        },
        enforceStrictCapabilities: true,
      },
  );

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  expect(client.getServerVersion()).toEqual({
    name: "new server",
    version: "1.0",
  });
});

/***
 * Test: Throw when Old Client and Server Version Mismatch
 */
test("should throw when client is old, and server doesn't support its version", async () => {
  const OLD_VERSION = SUPPORTED_PROTOCOL_VERSIONS[1];
  const FUTURE_VERSION = "FUTURE_VERSION";
  const server = new Server(
      {
        name: "new server",
        version: "1.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      },
  );

  server.setRequestHandler(InitializeRequestSchema, (_request) => ({
    protocolVersion: FUTURE_VERSION,
    capabilities: {
      resources: {},
      tools: {},
    },
    serverInfo: {
      name: "new server",
      version: "1.0",
    },
  }));

  server.setRequestHandler(ListResourcesRequestSchema, () => ({
    resources: [],
  }));

  server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: [],
  }));

  const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();

  const client = new Client(
      {
        name: "old client",
        version: "1.0",
        protocolVersion: OLD_VERSION,
      },
      {
        capabilities: {
          sampling: {},
        },
        enforceStrictCapabilities: true,
      },
  );

  await Promise.all([
    expect(client.connect(clientTransport)).rejects.toThrow(
        "Server's protocol version is not supported: FUTURE_VERSION"
    ),
    server.connect(serverTransport),
  ]);

});

/***
 * Test: Respect Server Capabilities
 */
test("should respect server capabilities", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        resources: {},
        tools: {},
      },
    },
  );

  server.setRequestHandler(InitializeRequestSchema, (_request) => ({
    protocolVersion: LATEST_PROTOCOL_VERSION,
    capabilities: {
      resources: {},
      tools: {},
    },
    serverInfo: {
      name: "test",
      version: "1.0",
    },
  }));

  server.setRequestHandler(ListResourcesRequestSchema, () => ({
    resources: [],
  }));

  server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: [],
  }));

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Server supports resources and tools, but not prompts
  expect(client.getServerCapabilities()).toEqual({
    resources: {},
    tools: {},
  });

  // These should work
  await expect(client.listResources()).resolves.not.toThrow();
  await expect(client.listTools()).resolves.not.toThrow();

  // These should throw because prompts, logging, and completions are not supported
  await expect(client.listPrompts()).rejects.toThrow(
    "Server does not support prompts",
  );
  await expect(client.setLoggingLevel("error")).rejects.toThrow(
    "Server does not support logging",
  );
  await expect(
    client.complete({
      ref: { type: "ref/prompt", name: "test" },
      argument: { name: "test", value: "test" },
    }),
  ).rejects.toThrow("Server does not support completions");
});

/***
 * Test: Respect Client Notification Capabilities
 */
test("should respect client notification capabilities", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {},
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        roots: {
          listChanged: true,
        },
      },
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // This should work because the client has the roots.listChanged capability
  await expect(client.sendRootsListChanged()).resolves.not.toThrow();

  // Create a new client without the roots.listChanged capability
  const clientWithoutCapability = new Client(
    {
      name: "test client without capability",
      version: "1.0",
    },
    {
      capabilities: {},
      enforceStrictCapabilities: true,
    },
  );

  await clientWithoutCapability.connect(clientTransport);

  // This should throw because the client doesn't have the roots.listChanged capability
  await expect(clientWithoutCapability.sendRootsListChanged()).rejects.toThrow(
    /^Client does not support/,
  );
});

/***
 * Test: Respect Server Notification Capabilities
 */
test("should respect server notification capabilities", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        logging: {},
        resources: {
          listChanged: true,
        },
      },
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {},
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // These should work because the server has the corresponding capabilities
  await expect(
    server.sendLoggingMessage({ level: "info", data: "Test" }),
  ).resolves.not.toThrow();
  await expect(server.sendResourceListChanged()).resolves.not.toThrow();

  // This should throw because the server doesn't have the tools capability
  await expect(server.sendToolListChanged()).rejects.toThrow(
    "Server does not support notifying of tool list changes",
  );
});

/***
 * Test: Only Allow setRequestHandler for Declared Capabilities
 */
test("should only allow setRequestHandler for declared capabilities", () => {
  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  // This should work because sampling is a declared capability
  expect(() => {
    client.setRequestHandler(CreateMessageRequestSchema, () => ({
      model: "test-model",
      role: "assistant",
      content: {
        type: "text",
        text: "Test response",
      },
    }));
  }).not.toThrow();

  // This should throw because roots listing is not a declared capability
  expect(() => {
    client.setRequestHandler(ListRootsRequestSchema, () => ({}));
  }).toThrow("Client does not support roots capability");
});

test("should allow setRequestHandler for declared elicitation capability", () => {
  const client = new Client(
    {
      name: "test-client",
      version: "1.0.0",
    },
    {
      capabilities: {
        elicitation: {},
      },
    },
  );

  // This should work because elicitation is a declared capability
  expect(() => {
    client.setRequestHandler(ElicitRequestSchema, () => ({
      action: "accept",
      content: {
        username: "test-user",
        confirmed: true,
      },
    }));
  }).not.toThrow();

  // This should throw because sampling is not a declared capability
  expect(() => {
    client.setRequestHandler(CreateMessageRequestSchema, () => ({
      model: "test-model",
      role: "assistant",
      content: {
        type: "text",
        text: "Test response",
      },
    }));
  }).toThrow("Client does not support sampling capability");
});

/***
 * Test: Type Checking
 * Test that custom request/notification/result schemas can be used with the Client class.
 */
test("should typecheck", () => {
  const GetWeatherRequestSchema = RequestSchema.extend({
    method: z.literal("weather/get"),
    params: z.object({
      city: z.string(),
    }),
  });

  const GetForecastRequestSchema = RequestSchema.extend({
    method: z.literal("weather/forecast"),
    params: z.object({
      city: z.string(),
      days: z.number(),
    }),
  });

  const WeatherForecastNotificationSchema = NotificationSchema.extend({
    method: z.literal("weather/alert"),
    params: z.object({
      severity: z.enum(["warning", "watch"]),
      message: z.string(),
    }),
  });

  const WeatherRequestSchema = GetWeatherRequestSchema.or(
    GetForecastRequestSchema,
  );
  const WeatherNotificationSchema = WeatherForecastNotificationSchema;
  const WeatherResultSchema = ResultSchema.extend({
    temperature: z.number(),
    conditions: z.string(),
  });

  type WeatherRequest = z.infer<typeof WeatherRequestSchema>;
  type WeatherNotification = z.infer<typeof WeatherNotificationSchema>;
  type WeatherResult = z.infer<typeof WeatherResultSchema>;

  // Create a typed Client for weather data
  const weatherClient = new Client<
    WeatherRequest,
    WeatherNotification,
    WeatherResult
  >(
    {
      name: "WeatherClient",
      version: "1.0.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  // Typecheck that only valid weather requests/notifications/results are allowed
  false &&
    weatherClient.request(
      {
        method: "weather/get",
        params: {
          city: "Seattle",
        },
      },
      WeatherResultSchema,
    );

  false &&
    weatherClient.notification({
      method: "weather/alert",
      params: {
        severity: "warning",
        message: "Storm approaching",
      },
    });
});

/***
 * Test: Handle Client Cancelling a Request
 */
test("should handle client cancelling a request", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        resources: {},
      },
    },
  );

  // Set up server to delay responding to listResources
  server.setRequestHandler(
    ListResourcesRequestSchema,
    async (request, extra) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return {
        resources: [],
      };
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {},
    },
  );

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Set up abort controller
  const controller = new AbortController();

  // Issue request but cancel it immediately
  const listResourcesPromise = client.listResources(undefined, {
    signal: controller.signal,
  });
  controller.abort("Cancelled by test");

  // Request should be rejected
  await expect(listResourcesPromise).rejects.toBe("Cancelled by test");
});

/***
 * Test: Handle Request Timeout
 */
test("should handle request timeout", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        resources: {},
      },
    },
  );

  // Set up server with a delayed response
  server.setRequestHandler(
    ListResourcesRequestSchema,
    async (_request, extra) => {
      const timer = new Promise((resolve) => {
        const timeout = setTimeout(resolve, 100);
        extra.signal.addEventListener("abort", () => clearTimeout(timeout));
      });

      await timer;
      return {
        resources: [],
      };
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {},
    },
  );

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Request with 0 msec timeout should fail immediately
  await expect(
    client.listResources(undefined, { timeout: 0 }),
  ).rejects.toMatchObject({
    code: ErrorCode.RequestTimeout,
  });
});

describe('outputSchema validation', () => {
  /***
   * Test: Validate structuredContent Against outputSchema
   */
  test('should validate structuredContent against outputSchema', async () => {
    const server = new Server({
      name: 'test-server',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // Set up server handlers
    server.setRequestHandler(InitializeRequestSchema, async (request) => ({
      protocolVersion: request.params.protocolVersion,
      capabilities: {},
      serverInfo: {
        name: 'test-server',
        version: '1.0.0',
      }
    }));

    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'test-tool',
          description: 'A test tool',
          inputSchema: {
            type: 'object',
            properties: {},
          },
          outputSchema: {
            type: 'object',
            properties: {
              result: { type: 'string' },
              count: { type: 'number' },
            },
            required: ['result', 'count'],
            additionalProperties: false,
          },
        },
      ],
    }));

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'test-tool') {
        return {
          structuredContent: { result: 'success', count: 42 },
        };
      }
      throw new Error('Unknown tool');
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0',
    });

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);

    // List tools to cache the schemas
    await client.listTools();

    // Call the tool - should validate successfully
    const result = await client.callTool({ name: 'test-tool' });
    expect(result.structuredContent).toEqual({ result: 'success', count: 42 });
  });

  /***
   * Test: Throw Error when structuredContent Does Not Match Schema
   */
  test('should throw error when structuredContent does not match schema', async () => {
    const server = new Server({
      name: 'test-server',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // Set up server handlers
    server.setRequestHandler(InitializeRequestSchema, async (request) => ({
      protocolVersion: request.params.protocolVersion,
      capabilities: {},
      serverInfo: {
        name: 'test-server',
        version: '1.0.0',
      }
    }));

    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'test-tool',
          description: 'A test tool',
          inputSchema: {
            type: 'object',
            properties: {},
          },
          outputSchema: {
            type: 'object',
            properties: {
              result: { type: 'string' },
              count: { type: 'number' },
            },
            required: ['result', 'count'],
            additionalProperties: false,
          },
        },
      ],
    }));

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'test-tool') {
        // Return invalid structured content (count is string instead of number)
        return {
          structuredContent: { result: 'success', count: 'not a number' },
        };
      }
      throw new Error('Unknown tool');
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0',
    });

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);

    // List tools to cache the schemas
    await client.listTools();

    // Call the tool - should throw validation error
    await expect(client.callTool({ name: 'test-tool' })).rejects.toThrow(
      /Structured content does not match the tool's output schema/
    );
  });

  /***
   * Test: Throw Error when Tool with outputSchema Returns No structuredContent
   */
  test('should throw error when tool with outputSchema returns no structuredContent', async () => {
    const server = new Server({
      name: 'test-server',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // Set up server handlers
    server.setRequestHandler(InitializeRequestSchema, async (request) => ({
      protocolVersion: request.params.protocolVersion,
      capabilities: {},
      serverInfo: {
        name: 'test-server',
        version: '1.0.0',
      }
    }));

    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'test-tool',
          description: 'A test tool',
          inputSchema: {
            type: 'object',
            properties: {},
          },
          outputSchema: {
            type: 'object',
            properties: {
              result: { type: 'string' },
            },
            required: ['result'],
          },
        },
      ],
    }));

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'test-tool') {
        // Return content instead of structuredContent
        return {
          content: [{ type: 'text', text: 'This should be structured content' }],
        };
      }
      throw new Error('Unknown tool');
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0',
    });

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);

    // List tools to cache the schemas
    await client.listTools();

    // Call the tool - should throw error
    await expect(client.callTool({ name: 'test-tool' })).rejects.toThrow(
      /Tool test-tool has an output schema but did not return structured content/
    );
  });

  /***
   * Test: Handle Tools Without outputSchema Normally
   */
  test('should handle tools without outputSchema normally', async () => {
    const server = new Server({
      name: 'test-server',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // Set up server handlers
    server.setRequestHandler(InitializeRequestSchema, async (request) => ({
      protocolVersion: request.params.protocolVersion,
      capabilities: {},
      serverInfo: {
        name: 'test-server',
        version: '1.0.0',
      }
    }));

    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'test-tool',
          description: 'A test tool',
          inputSchema: {
            type: 'object',
            properties: {},
          },
          // No outputSchema
        },
      ],
    }));

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'test-tool') {
        // Return regular content
        return {
          content: [{ type: 'text', text: 'Normal response' }],
        };
      }
      throw new Error('Unknown tool');
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0',
    });

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);

    // List tools to cache the schemas
    await client.listTools();

    // Call the tool - should work normally without validation
    const result = await client.callTool({ name: 'test-tool' });
    expect(result.content).toEqual([{ type: 'text', text: 'Normal response' }]);
  });

  /***
   * Test: Handle Complex JSON Schema Validation
   */
  test('should handle complex JSON schema validation', async () => {
    const server = new Server({
      name: 'test-server',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // Set up server handlers
    server.setRequestHandler(InitializeRequestSchema, async (request) => ({
      protocolVersion: request.params.protocolVersion,
      capabilities: {},
      serverInfo: {
        name: 'test-server',
        version: '1.0.0',
      }
    }));

    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'complex-tool',
          description: 'A tool with complex schema',
          inputSchema: {
            type: 'object',
            properties: {},
          },
          outputSchema: {
            type: 'object',
            properties: {
              name: { type: 'string', minLength: 3 },
              age: { type: 'integer', minimum: 0, maximum: 120 },
              active: { type: 'boolean' },
              tags: {
                type: 'array',
                items: { type: 'string' },
                minItems: 1,
              },
              metadata: {
                type: 'object',
                properties: {
                  created: { type: 'string' },
                },
                required: ['created'],
              },
            },
            required: ['name', 'age', 'active', 'tags', 'metadata'],
            additionalProperties: false,
          },
        },
      ],
    }));

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'complex-tool') {
        return {
          structuredContent: {
            name: 'John Doe',
            age: 30,
            active: true,
            tags: ['user', 'admin'],
            metadata: {
              created: '2023-01-01T00:00:00Z',
            },
          },
        };
      }
      throw new Error('Unknown tool');
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0',
    });

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);

    // List tools to cache the schemas
    await client.listTools();

    // Call the tool - should validate successfully
    const result = await client.callTool({ name: 'complex-tool' });
    expect(result.structuredContent).toBeDefined();
    const structuredContent = result.structuredContent as { name: string; age: number };
    expect(structuredContent.name).toBe('John Doe');
    expect(structuredContent.age).toBe(30);
  });

  /***
   * Test: Fail Validation with Additional Properties When Not Allowed
   */
  test('should fail validation with additional properties when not allowed', async () => {
    const server = new Server({
      name: 'test-server',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    // Set up server handlers
    server.setRequestHandler(InitializeRequestSchema, async (request) => ({
      protocolVersion: request.params.protocolVersion,
      capabilities: {},
      serverInfo: {
        name: 'test-server',
        version: '1.0.0',
      }
    }));

    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'strict-tool',
          description: 'A tool with strict schema',
          inputSchema: {
            type: 'object',
            properties: {},
          },
          outputSchema: {
            type: 'object',
            properties: {
              name: { type: 'string' },
            },
            required: ['name'],
            additionalProperties: false,
          },
        },
      ],
    }));

    server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'strict-tool') {
        // Return structured content with extra property
        return {
          structuredContent: {
            name: 'John',
            extraField: 'not allowed',
          },
        };
      }
      throw new Error('Unknown tool');
    });

    const client = new Client({
      name: 'test-client',
      version: '1.0.0',
    });

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);

    // List tools to cache the schemas
    await client.listTools();

    // Call the tool - should throw validation error due to additional property
    await expect(client.callTool({ name: 'strict-tool' })).rejects.toThrow(
      /Structured content does not match the tool's output schema/
    );
  });


});



================================================
FILE: src/client/index.ts
================================================
import {
  mergeCapabilities,
  Protocol,
  ProtocolOptions,
  RequestOptions,
} from "../shared/protocol.js";
import { Transport } from "../shared/transport.js";
import {
  CallToolRequest,
  CallToolResultSchema,
  ClientCapabilities,
  ClientNotification,
  ClientRequest,
  ClientResult,
  CompatibilityCallToolResultSchema,
  CompleteRequest,
  CompleteResultSchema,
  EmptyResultSchema,
  GetPromptRequest,
  GetPromptResultSchema,
  Implementation,
  InitializeResultSchema,
  LATEST_PROTOCOL_VERSION,
  ListPromptsRequest,
  ListPromptsResultSchema,
  ListResourcesRequest,
  ListResourcesResultSchema,
  ListResourceTemplatesRequest,
  ListResourceTemplatesResultSchema,
  ListToolsRequest,
  ListToolsResultSchema,
  LoggingLevel,
  Notification,
  ReadResourceRequest,
  ReadResourceResultSchema,
  Request,
  Result,
  ServerCapabilities,
  SubscribeRequest,
  SUPPORTED_PROTOCOL_VERSIONS,
  UnsubscribeRequest,
  Tool,
  ErrorCode,
  McpError,
} from "../types.js";
import Ajv from "ajv";
import type { ValidateFunction } from "ajv";

export type ClientOptions = ProtocolOptions & {
  /**
   * Capabilities to advertise as being supported by this client.
   */
  capabilities?: ClientCapabilities;
};

/**
 * An MCP client on top of a pluggable transport.
 *
 * The client will automatically begin the initialization flow with the server when connect() is called.
 *
 * To use with custom types, extend the base Request/Notification/Result types and pass them as type parameters:
 *
 * ```typescript
 * // Custom schemas
 * const CustomRequestSchema = RequestSchema.extend({...})
 * const CustomNotificationSchema = NotificationSchema.extend({...})
 * const CustomResultSchema = ResultSchema.extend({...})
 *
 * // Type aliases
 * type CustomRequest = z.infer<typeof CustomRequestSchema>
 * type CustomNotification = z.infer<typeof CustomNotificationSchema>
 * type CustomResult = z.infer<typeof CustomResultSchema>
 *
 * // Create typed client
 * const client = new Client<CustomRequest, CustomNotification, CustomResult>({
 *   name: "CustomClient",
 *   version: "1.0.0"
 * })
 * ```
 */
export class Client<
  RequestT extends Request = Request,
  NotificationT extends Notification = Notification,
  ResultT extends Result = Result,
> extends Protocol<
  ClientRequest | RequestT,
  ClientNotification | NotificationT,
  ClientResult | ResultT
> {
  private _serverCapabilities?: ServerCapabilities;
  private _serverVersion?: Implementation;
  private _capabilities: ClientCapabilities;
  private _instructions?: string;
  private _cachedToolOutputValidators: Map<string, ValidateFunction> = new Map();
  private _ajv: InstanceType<typeof Ajv>;

  /**
   * Initializes this client with the given name and version information.
   */
  constructor(
    private _clientInfo: Implementation,
    options?: ClientOptions,
  ) {
    super(options);
    this._capabilities = options?.capabilities ?? {};
    this._ajv = new Ajv();
  }

  /**
   * Registers new capabilities. This can only be called before connecting to a transport.
   *
   * The new capabilities will be merged with any existing capabilities previously given (e.g., at initialization).
   */
  public registerCapabilities(capabilities: ClientCapabilities): void {
    if (this.transport) {
      throw new Error(
        "Cannot register capabilities after connecting to transport",
      );
    }

    this._capabilities = mergeCapabilities(this._capabilities, capabilities);
  }

  protected assertCapability(
    capability: keyof ServerCapabilities,
    method: string,
  ): void {
    if (!this._serverCapabilities?.[capability]) {
      throw new Error(
        `Server does not support ${capability} (required for ${method})`,
      );
    }
  }

  override async connect(transport: Transport, options?: RequestOptions): Promise<void> {
    await super.connect(transport);
    // When transport sessionId is already set this means we are trying to reconnect.
    // In this case we don't need to initialize again.
    if (transport.sessionId !== undefined) {
      return;
    }
    try {
      const result = await this.request(
        {
          method: "initialize",
          params: {
            protocolVersion: LATEST_PROTOCOL_VERSION,
            capabilities: this._capabilities,
            clientInfo: this._clientInfo,
          },
        },
        InitializeResultSchema,
        options
      );

      if (result === undefined) {
        throw new Error(`Server sent invalid initialize result: ${result}`);
      }

      if (!SUPPORTED_PROTOCOL_VERSIONS.includes(result.protocolVersion)) {
        throw new Error(
          `Server's protocol version is not supported: ${result.protocolVersion}`,
        );
      }

      this._serverCapabilities = result.capabilities;
      this._serverVersion = result.serverInfo;
      // HTTP transports must set the protocol version in each header after initialization.
      if (transport.setProtocolVersion) {
        transport.setProtocolVersion(result.protocolVersion);
      }

      this._instructions = result.instructions;

      await this.notification({
        method: "notifications/initialized",
      });
    } catch (error) {
      // Disconnect if initialization fails.
      void this.close();
      throw error;
    }
  }

  /**
   * After initialization has completed, this will be populated with the server's reported capabilities.
   */
  getServerCapabilities(): ServerCapabilities | undefined {
    return this._serverCapabilities;
  }

  /**
   * After initialization has completed, this will be populated with information about the server's name and version.
   */
  getServerVersion(): Implementation | undefined {
    return this._serverVersion;
  }

  /**
   * After initialization has completed, this may be populated with information about the server's instructions.
   */
  getInstructions(): string | undefined {
    return this._instructions;
  }

  protected assertCapabilityForMethod(method: RequestT["method"]): void {
    switch (method as ClientRequest["method"]) {
      case "logging/setLevel":
        if (!this._serverCapabilities?.logging) {
          throw new Error(
            `Server does not support logging (required for ${method})`,
          );
        }
        break;

      case "prompts/get":
      case "prompts/list":
        if (!this._serverCapabilities?.prompts) {
          throw new Error(
            `Server does not support prompts (required for ${method})`,
          );
        }
        break;

      case "resources/list":
      case "resources/templates/list":
      case "resources/read":
      case "resources/subscribe":
      case "resources/unsubscribe":
        if (!this._serverCapabilities?.resources) {
          throw new Error(
            `Server does not support resources (required for ${method})`,
          );
        }

        if (
          method === "resources/subscribe" &&
          !this._serverCapabilities.resources.subscribe
        ) {
          throw new Error(
            `Server does not support resource subscriptions (required for ${method})`,
          );
        }

        break;

      case "tools/call":
      case "tools/list":
        if (!this._serverCapabilities?.tools) {
          throw new Error(
            `Server does not support tools (required for ${method})`,
          );
        }
        break;

      case "completion/complete":
        if (!this._serverCapabilities?.completions) {
          throw new Error(
            `Server does not support completions (required for ${method})`,
          );
        }
        break;

      case "initialize":
        // No specific capability required for initialize
        break;

      case "ping":
        // No specific capability required for ping
        break;
    }
  }

  protected assertNotificationCapability(
    method: NotificationT["method"],
  ): void {
    switch (method as ClientNotification["method"]) {
      case "notifications/roots/list_changed":
        if (!this._capabilities.roots?.listChanged) {
          throw new Error(
            `Client does not support roots list changed notifications (required for ${method})`,
          );
        }
        break;

      case "notifications/initialized":
        // No specific capability required for initialized
        break;

      case "notifications/cancelled":
        // Cancellation notifications are always allowed
        break;

      case "notifications/progress":
        // Progress notifications are always allowed
        break;
    }
  }

  protected assertRequestHandlerCapability(method: string): void {
    switch (method) {
      case "sampling/createMessage":
        if (!this._capabilities.sampling) {
          throw new Error(
            `Client does not support sampling capability (required for ${method})`,
          );
        }
        break;

      case "elicitation/create":
        if (!this._capabilities.elicitation) {
          throw new Error(
            `Client does not support elicitation capability (required for ${method})`,
          );
        }
        break;

      case "roots/list":
        if (!this._capabilities.roots) {
          throw new Error(
            `Client does not support roots capability (required for ${method})`,
          );
        }
        break;

      case "ping":
        // No specific capability required for ping
        break;
    }
  }

  async ping(options?: RequestOptions) {
    return this.request({ method: "ping" }, EmptyResultSchema, options);
  }

  async complete(params: CompleteRequest["params"], options?: RequestOptions) {
    return this.request(
      { method: "completion/complete", params },
      CompleteResultSchema,
      options,
    );
  }

  async setLoggingLevel(level: LoggingLevel, options?: RequestOptions) {
    return this.request(
      { method: "logging/setLevel", params: { level } },
      EmptyResultSchema,
      options,
    );
  }

  async getPrompt(
    params: GetPromptRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "prompts/get", params },
      GetPromptResultSchema,
      options,
    );
  }

  async listPrompts(
    params?: ListPromptsRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "prompts/list", params },
      ListPromptsResultSchema,
      options,
    );
  }

  async listResources(
    params?: ListResourcesRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "resources/list", params },
      ListResourcesResultSchema,
      options,
    );
  }

  async listResourceTemplates(
    params?: ListResourceTemplatesRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "resources/templates/list", params },
      ListResourceTemplatesResultSchema,
      options,
    );
  }

  async readResource(
    params: ReadResourceRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "resources/read", params },
      ReadResourceResultSchema,
      options,
    );
  }

  async subscribeResource(
    params: SubscribeRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "resources/subscribe", params },
      EmptyResultSchema,
      options,
    );
  }

  async unsubscribeResource(
    params: UnsubscribeRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "resources/unsubscribe", params },
      EmptyResultSchema,
      options,
    );
  }

  async callTool(
    params: CallToolRequest["params"],
    resultSchema:
      | typeof CallToolResultSchema
      | typeof CompatibilityCallToolResultSchema = CallToolResultSchema,
    options?: RequestOptions,
  ) {
    const result = await this.request(
      { method: "tools/call", params },
      resultSchema,
      options,
    );

    // Check if the tool has an outputSchema
    const validator = this.getToolOutputValidator(params.name);
    if (validator) {
      // If tool has outputSchema, it MUST return structuredContent (unless it's an error)
      if (!result.structuredContent && !result.isError) {
        throw new McpError(
          ErrorCode.InvalidRequest,
          `Tool ${params.name} has an output schema but did not return structured content`
        );
      }

      // Only validate structured content if present (not when there's an error)
      if (result.structuredContent) {
        try {
          // Validate the structured content (which is already an object) against the schema
          const isValid = validator(result.structuredContent);

          if (!isValid) {
            throw new McpError(
              ErrorCode.InvalidParams,
              `Structured content does not match the tool's output schema: ${this._ajv.errorsText(validator.errors)}`
            );
          }
        } catch (error) {
          if (error instanceof McpError) {
            throw error;
          }
          throw new McpError(
            ErrorCode.InvalidParams,
            `Failed to validate structured content: ${error instanceof Error ? error.message : String(error)}`
          );
        }
      }
    }

    return result;
  }

  private cacheToolOutputSchemas(tools: Tool[]) {
    this._cachedToolOutputValidators.clear();

    for (const tool of tools) {
      // If the tool has an outputSchema, create and cache the Ajv validator
      if (tool.outputSchema) {
        try {
          const validator = this._ajv.compile(tool.outputSchema);
          this._cachedToolOutputValidators.set(tool.name, validator);
        } catch {
          // Ignore schema compilation errors
        }
      }
    }
  }

  private getToolOutputValidator(toolName: string): ValidateFunction | undefined {
    return this._cachedToolOutputValidators.get(toolName);
  }

  async listTools(
    params?: ListToolsRequest["params"],
    options?: RequestOptions,
  ) {
    const result = await this.request(
      { method: "tools/list", params },
      ListToolsResultSchema,
      options,
    );

    // Cache the tools and their output schemas for future validation
    this.cacheToolOutputSchemas(result.tools);

    return result;
  }

  async sendRootsListChanged() {
    return this.notification({ method: "notifications/roots/list_changed" });
  }
}



================================================
FILE: src/client/middleware.test.ts
================================================
import {
    withOAuth,
    withLogging,
    applyMiddlewares,
    createMiddleware,
} from "./middleware.js";
import { OAuthClientProvider } from "./auth.js";
import { FetchLike } from "../shared/transport.js";

jest.mock("../client/auth.js", () => {
  const actual = jest.requireActual("../client/auth.js");
  return {
    ...actual,
    auth: jest.fn(),
    extractResourceMetadataUrl: jest.fn(),
  };
});

import { auth, extractResourceMetadataUrl } from "./auth.js";

const mockAuth = auth as jest.MockedFunction<typeof auth>;
const mockExtractResourceMetadataUrl =
  extractResourceMetadataUrl as jest.MockedFunction<
    typeof extractResourceMetadataUrl
  >;

describe("withOAuth", () => {
  let mockProvider: jest.Mocked<OAuthClientProvider>;
  let mockFetch: jest.MockedFunction<FetchLike>;

  beforeEach(() => {
    jest.clearAllMocks();

    mockProvider = {
      get redirectUrl() {
        return "http://localhost/callback";
      },
      get clientMetadata() {
        return { redirect_uris: ["http://localhost/callback"] };
      },
      tokens: jest.fn(),
      saveTokens: jest.fn(),
      clientInformation: jest.fn(),
      redirectToAuthorization: jest.fn(),
      saveCodeVerifier: jest.fn(),
      codeVerifier: jest.fn(),
      invalidateCredentials: jest.fn(),
    };

    mockFetch = jest.fn();
  });

  it("should add Authorization header when tokens are available (with explicit baseUrl)", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    mockFetch.mockResolvedValue(new Response("success", { status: 200 }));

    const enhancedFetch = withOAuth(
      mockProvider,
      "https://api.example.com",
    )(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/data",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("should add Authorization header when tokens are available (without baseUrl)", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    mockFetch.mockResolvedValue(new Response("success", { status: 200 }));

    // Test without baseUrl - should extract from request URL
    const enhancedFetch = withOAuth(mockProvider)(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/data",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("should handle requests without tokens (without baseUrl)", async () => {
    mockProvider.tokens.mockResolvedValue(undefined);
    mockFetch.mockResolvedValue(new Response("success", { status: 200 }));

    // Test without baseUrl
    const enhancedFetch = withOAuth(mockProvider)(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("should retry request after successful auth on 401 response (with explicit baseUrl)", async () => {
    mockProvider.tokens
      .mockResolvedValueOnce({
        access_token: "old-token",
        token_type: "Bearer",
        expires_in: 3600,
      })
      .mockResolvedValueOnce({
        access_token: "new-token",
        token_type: "Bearer",
        expires_in: 3600,
      });

    const unauthorizedResponse = new Response("Unauthorized", {
      status: 401,
      headers: { "www-authenticate": 'Bearer realm="oauth"' },
    });
    const successResponse = new Response("success", { status: 200 });

    mockFetch
      .mockResolvedValueOnce(unauthorizedResponse)
      .mockResolvedValueOnce(successResponse);

    const mockResourceUrl = new URL(
      "https://oauth.example.com/.well-known/oauth-protected-resource",
    );
    mockExtractResourceMetadataUrl.mockReturnValue(mockResourceUrl);
    mockAuth.mockResolvedValue("AUTHORIZED");

    const enhancedFetch = withOAuth(
      mockProvider,
      "https://api.example.com",
    )(mockFetch);

    const result = await enhancedFetch("https://api.example.com/data");

    expect(result).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockAuth).toHaveBeenCalledWith(mockProvider, {
      serverUrl: "https://api.example.com",
      resourceMetadataUrl: mockResourceUrl,
      fetchFn: mockFetch,
    });

    // Verify the retry used the new token
    const retryCallArgs = mockFetch.mock.calls[1];
    const retryHeaders = retryCallArgs[1]?.headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer new-token");
  });

  it("should retry request after successful auth on 401 response (without baseUrl)", async () => {
    mockProvider.tokens
      .mockResolvedValueOnce({
        access_token: "old-token",
        token_type: "Bearer",
        expires_in: 3600,
      })
      .mockResolvedValueOnce({
        access_token: "new-token",
        token_type: "Bearer",
        expires_in: 3600,
      });

    const unauthorizedResponse = new Response("Unauthorized", {
      status: 401,
      headers: { "www-authenticate": 'Bearer realm="oauth"' },
    });
    const successResponse = new Response("success", { status: 200 });

    mockFetch
      .mockResolvedValueOnce(unauthorizedResponse)
      .mockResolvedValueOnce(successResponse);

    const mockResourceUrl = new URL(
      "https://oauth.example.com/.well-known/oauth-protected-resource",
    );
    mockExtractResourceMetadataUrl.mockReturnValue(mockResourceUrl);
    mockAuth.mockResolvedValue("AUTHORIZED");

    // Test without baseUrl - should extract from request URL
    const enhancedFetch = withOAuth(mockProvider)(mockFetch);

    const result = await enhancedFetch("https://api.example.com/data");

    expect(result).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockAuth).toHaveBeenCalledWith(mockProvider, {
      serverUrl: "https://api.example.com", // Should be extracted from request URL
      resourceMetadataUrl: mockResourceUrl,
      fetchFn: mockFetch,
    });

    // Verify the retry used the new token
    const retryCallArgs = mockFetch.mock.calls[1];
    const retryHeaders = retryCallArgs[1]?.headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer new-token");
  });

  it("should throw UnauthorizedError when auth returns REDIRECT (without baseUrl)", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    mockFetch.mockResolvedValue(new Response("Unauthorized", { status: 401 }));
    mockExtractResourceMetadataUrl.mockReturnValue(undefined);
    mockAuth.mockResolvedValue("REDIRECT");

    // Test without baseUrl
    const enhancedFetch = withOAuth(mockProvider)(mockFetch);

    await expect(enhancedFetch("https://api.example.com/data")).rejects.toThrow(
      "Authentication requires user authorization - redirect initiated",
    );
  });

  it("should throw UnauthorizedError when auth fails", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    mockFetch.mockResolvedValue(new Response("Unauthorized", { status: 401 }));
    mockExtractResourceMetadataUrl.mockReturnValue(undefined);
    mockAuth.mockRejectedValue(new Error("Network error"));

    const enhancedFetch = withOAuth(
      mockProvider,
      "https://api.example.com",
    )(mockFetch);

    await expect(enhancedFetch("https://api.example.com/data")).rejects.toThrow(
      "Failed to re-authenticate: Network error",
    );
  });

  it("should handle persistent 401 responses after auth", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    // Always return 401
    mockFetch.mockResolvedValue(new Response("Unauthorized", { status: 401 }));
    mockExtractResourceMetadataUrl.mockReturnValue(undefined);
    mockAuth.mockResolvedValue("AUTHORIZED");

    const enhancedFetch = withOAuth(
      mockProvider,
      "https://api.example.com",
    )(mockFetch);

    await expect(enhancedFetch("https://api.example.com/data")).rejects.toThrow(
      "Authentication failed for https://api.example.com/data",
    );

    // Should have made initial request + 1 retry after auth = 2 total
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockAuth).toHaveBeenCalledTimes(1);
  });

  it("should preserve original request method and body", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    mockFetch.mockResolvedValue(new Response("success", { status: 200 }));

    const enhancedFetch = withOAuth(
      mockProvider,
      "https://api.example.com",
    )(mockFetch);

    const requestBody = JSON.stringify({ data: "test" });
    await enhancedFetch("https://api.example.com/data", {
      method: "POST",
      body: requestBody,
      headers: { "Content-Type": "application/json" },
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/data",
      expect.objectContaining({
        method: "POST",
        body: requestBody,
        headers: expect.any(Headers),
      }),
    );

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("should handle non-401 errors normally", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    const serverErrorResponse = new Response("Server Error", { status: 500 });
    mockFetch.mockResolvedValue(serverErrorResponse);

    const enhancedFetch = withOAuth(
      mockProvider,
      "https://api.example.com",
    )(mockFetch);

    const result = await enhancedFetch("https://api.example.com/data");

    expect(result).toBe(serverErrorResponse);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockAuth).not.toHaveBeenCalled();
  });

  it("should handle URL object as input (without baseUrl)", async () => {
    mockProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    mockFetch.mockResolvedValue(new Response("success", { status: 200 }));

    // Test URL object without baseUrl - should extract origin from URL object
    const enhancedFetch = withOAuth(mockProvider)(mockFetch);

    await enhancedFetch(new URL("https://api.example.com/data"));

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(URL),
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
  });

  it("should handle URL object in auth retry (without baseUrl)", async () => {
    mockProvider.tokens
      .mockResolvedValueOnce({
        access_token: "old-token",
        token_type: "Bearer",
        expires_in: 3600,
      })
      .mockResolvedValueOnce({
        access_token: "new-token",
        token_type: "Bearer",
        expires_in: 3600,
      });

    const unauthorizedResponse = new Response("Unauthorized", { status: 401 });
    const successResponse = new Response("success", { status: 200 });

    mockFetch
      .mockResolvedValueOnce(unauthorizedResponse)
      .mockResolvedValueOnce(successResponse);

    mockExtractResourceMetadataUrl.mockReturnValue(undefined);
    mockAuth.mockResolvedValue("AUTHORIZED");

    const enhancedFetch = withOAuth(mockProvider)(mockFetch);

    const result = await enhancedFetch(new URL("https://api.example.com/data"));

    expect(result).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockAuth).toHaveBeenCalledWith(mockProvider, {
      serverUrl: "https://api.example.com", // Should extract origin from URL object
      resourceMetadataUrl: undefined,
      fetchFn: mockFetch,
    });
  });
});

describe("withLogging", () => {
  let mockFetch: jest.MockedFunction<FetchLike>;
  let mockLogger: jest.MockedFunction<
    (input: {
      method: string;
      url: string | URL;
      status: number;
      statusText: string;
      duration: number;
      requestHeaders?: Headers;
      responseHeaders?: Headers;
      error?: Error;
    }) => void
  >;
  let consoleErrorSpy: jest.SpyInstance;
  let consoleLogSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();

    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    consoleLogSpy = jest.spyOn(console, "log").mockImplementation(() => {});

    mockFetch = jest.fn();
    mockLogger = jest.fn();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleLogSpy.mockRestore();
  });

  it("should log successful requests with default logger", async () => {
    const response = new Response("success", { status: 200, statusText: "OK" });
    mockFetch.mockResolvedValue(response);

    const enhancedFetch = withLogging()(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    expect(consoleLogSpy).toHaveBeenCalledWith(
      expect.stringMatching(
        /HTTP GET https:\/\/api\.example\.com\/data 200 OK \(\d+\.\d+ms\)/,
      ),
    );
  });

  it("should log error responses with default logger", async () => {
    const response = new Response("Not Found", {
      status: 404,
      statusText: "Not Found",
    });
    mockFetch.mockResolvedValue(response);

    const enhancedFetch = withLogging()(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringMatching(
        /HTTP GET https:\/\/api\.example\.com\/data 404 Not Found \(\d+\.\d+ms\)/,
      ),
    );
  });

  it("should log network errors with default logger", async () => {
    const networkError = new Error("Network connection failed");
    mockFetch.mockRejectedValue(networkError);

    const enhancedFetch = withLogging()(mockFetch);

    await expect(enhancedFetch("https://api.example.com/data")).rejects.toThrow(
      "Network connection failed",
    );

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringMatching(
        /HTTP GET https:\/\/api\.example\.com\/data failed: Network connection failed \(\d+\.\d+ms\)/,
      ),
    );
  });

  it("should use custom logger when provided", async () => {
    const response = new Response("success", { status: 200, statusText: "OK" });
    mockFetch.mockResolvedValue(response);

    const enhancedFetch = withLogging({ logger: mockLogger })(mockFetch);

    await enhancedFetch("https://api.example.com/data", { method: "POST" });

    expect(mockLogger).toHaveBeenCalledWith({
      method: "POST",
      url: "https://api.example.com/data",
      status: 200,
      statusText: "OK",
      duration: expect.any(Number),
      requestHeaders: undefined,
      responseHeaders: undefined,
    });

    expect(consoleLogSpy).not.toHaveBeenCalled();
  });

  it("should include request headers when configured", async () => {
    const response = new Response("success", { status: 200, statusText: "OK" });
    mockFetch.mockResolvedValue(response);

    const enhancedFetch = withLogging({
      logger: mockLogger,
      includeRequestHeaders: true,
    })(mockFetch);

    await enhancedFetch("https://api.example.com/data", {
      headers: {
        Authorization: "Bearer token",
        "Content-Type": "application/json",
      },
    });

    expect(mockLogger).toHaveBeenCalledWith({
      method: "GET",
      url: "https://api.example.com/data",
      status: 200,
      statusText: "OK",
      duration: expect.any(Number),
      requestHeaders: expect.any(Headers),
      responseHeaders: undefined,
    });

    const logCall = mockLogger.mock.calls[0][0];
    expect(logCall.requestHeaders?.get("Authorization")).toBe("Bearer token");
    expect(logCall.requestHeaders?.get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("should include response headers when configured", async () => {
    const response = new Response("success", {
      status: 200,
      statusText: "OK",
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
      },
    });
    mockFetch.mockResolvedValue(response);

    const enhancedFetch = withLogging({
      logger: mockLogger,
      includeResponseHeaders: true,
    })(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    const logCall = mockLogger.mock.calls[0][0];
    expect(logCall.responseHeaders?.get("Content-Type")).toBe(
      "application/json",
    );
    expect(logCall.responseHeaders?.get("Cache-Control")).toBe("no-cache");
  });

  it("should respect statusLevel option", async () => {
    const successResponse = new Response("success", {
      status: 200,
      statusText: "OK",
    });
    const errorResponse = new Response("Server Error", {
      status: 500,
      statusText: "Internal Server Error",
    });

    mockFetch
      .mockResolvedValueOnce(successResponse)
      .mockResolvedValueOnce(errorResponse);

    const enhancedFetch = withLogging({
      logger: mockLogger,
      statusLevel: 400,
    })(mockFetch);

    // 200 response should not be logged (below statusLevel 400)
    await enhancedFetch("https://api.example.com/success");
    expect(mockLogger).not.toHaveBeenCalled();

    // 500 response should be logged (above statusLevel 400)
    await enhancedFetch("https://api.example.com/error");
    expect(mockLogger).toHaveBeenCalledWith({
      method: "GET",
      url: "https://api.example.com/error",
      status: 500,
      statusText: "Internal Server Error",
      duration: expect.any(Number),
      requestHeaders: undefined,
      responseHeaders: undefined,
    });
  });

  it("should always log network errors regardless of statusLevel", async () => {
    const networkError = new Error("Connection timeout");
    mockFetch.mockRejectedValue(networkError);

    const enhancedFetch = withLogging({
      logger: mockLogger,
      statusLevel: 500, // Very high log level
    })(mockFetch);

    await expect(enhancedFetch("https://api.example.com/data")).rejects.toThrow(
      "Connection timeout",
    );

    expect(mockLogger).toHaveBeenCalledWith({
      method: "GET",
      url: "https://api.example.com/data",
      status: 0,
      statusText: "Network Error",
      duration: expect.any(Number),
      requestHeaders: undefined,
      error: networkError,
    });
  });

  it("should include headers in default logger message when configured", async () => {
    const response = new Response("success", {
      status: 200,
      statusText: "OK",
      headers: { "Content-Type": "application/json" },
    });
    mockFetch.mockResolvedValue(response);

    const enhancedFetch = withLogging({
      includeRequestHeaders: true,
      includeResponseHeaders: true,
    })(mockFetch);

    await enhancedFetch("https://api.example.com/data", {
      headers: { Authorization: "Bearer token" },
    });

    expect(consoleLogSpy).toHaveBeenCalledWith(
      expect.stringContaining("Request Headers: {authorization: Bearer token}"),
    );
    expect(consoleLogSpy).toHaveBeenCalledWith(
      expect.stringContaining(
        "Response Headers: {content-type: application/json}",
      ),
    );
  });

  it("should measure request duration accurately", async () => {
    // Mock a slow response
    const response = new Response("success", { status: 200 });
    mockFetch.mockImplementation(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
      return response;
    });

    const enhancedFetch = withLogging({ logger: mockLogger })(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    const logCall = mockLogger.mock.calls[0][0];
    expect(logCall.duration).toBeGreaterThanOrEqual(90); // Allow some margin for timing
  });
});

describe("applyMiddleware", () => {
  let mockFetch: jest.MockedFunction<FetchLike>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch = jest.fn();
  });

  it("should compose no middleware correctly", () => {
    const response = new Response("success", { status: 200 });
    mockFetch.mockResolvedValue(response);

    const composedFetch = applyMiddlewares()(mockFetch);

    expect(composedFetch).toBe(mockFetch);
  });

  it("should compose single middleware correctly", async () => {
    const response = new Response("success", { status: 200 });
    mockFetch.mockResolvedValue(response);

    // Create a middleware that adds a header
    const middleware1 =
      (next: FetchLike) => async (input: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("X-Middleware-1", "applied");
        return next(input, { ...init, headers });
      };

    const composedFetch = applyMiddlewares(middleware1)(mockFetch);

    await composedFetch("https://api.example.com/data");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/data",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("X-Middleware-1")).toBe("applied");
  });

  it("should compose multiple middleware in order", async () => {
    const response = new Response("success", { status: 200 });
    mockFetch.mockResolvedValue(response);

    // Create middleware that add identifying headers
    const middleware1 =
      (next: FetchLike) => async (input: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("X-Middleware-1", "applied");
        return next(input, { ...init, headers });
      };

    const middleware2 =
      (next: FetchLike) => async (input: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("X-Middleware-2", "applied");
        return next(input, { ...init, headers });
      };

    const middleware3 =
      (next: FetchLike) => async (input: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("X-Middleware-3", "applied");
        return next(input, { ...init, headers });
      };

    const composedFetch = applyMiddlewares(
      middleware1,
      middleware2,
      middleware3,
    )(mockFetch);

    await composedFetch("https://api.example.com/data");

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("X-Middleware-1")).toBe("applied");
    expect(headers.get("X-Middleware-2")).toBe("applied");
    expect(headers.get("X-Middleware-3")).toBe("applied");
  });

  it("should work with real fetch middleware functions", async () => {
    const response = new Response("success", { status: 200, statusText: "OK" });
    mockFetch.mockResolvedValue(response);

    // Create middleware that add identifying headers
    const oauthMiddleware =
      (next: FetchLike) => async (input: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("Authorization", "Bearer test-token");
        return next(input, { ...init, headers });
      };

    // Use custom logger to avoid console output
    const mockLogger = jest.fn();
    const composedFetch = applyMiddlewares(
      oauthMiddleware,
      withLogging({ logger: mockLogger, statusLevel: 0 }),
    )(mockFetch);

    await composedFetch("https://api.example.com/data");

    // Should have both Authorization header and logging
    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-token");
    expect(mockLogger).toHaveBeenCalledWith({
      method: "GET",
      url: "https://api.example.com/data",
      status: 200,
      statusText: "OK",
      duration: expect.any(Number),
      requestHeaders: undefined,
      responseHeaders: undefined,
    });
  });

  it("should preserve error propagation through middleware", async () => {
    const errorMiddleware =
      (next: FetchLike) => async (input: string | URL, init?: RequestInit) => {
        try {
          return await next(input, init);
        } catch (error) {
          // Add context to the error
          throw new Error(
            `Middleware error: ${error instanceof Error ? error.message : String(error)}`,
          );
        }
      };

    const originalError = new Error("Network failure");
    mockFetch.mockRejectedValue(originalError);

    const composedFetch = applyMiddlewares(errorMiddleware)(mockFetch);

    await expect(composedFetch("https://api.example.com/data")).rejects.toThrow(
      "Middleware error: Network failure",
    );
  });
});

describe("Integration Tests", () => {
  let mockProvider: jest.Mocked<OAuthClientProvider>;
  let mockFetch: jest.MockedFunction<FetchLike>;

  beforeEach(() => {
    jest.clearAllMocks();

    mockProvider = {
      get redirectUrl() {
        return "http://localhost/callback";
      },
      get clientMetadata() {
        return { redirect_uris: ["http://localhost/callback"] };
      },
      tokens: jest.fn(),
      saveTokens: jest.fn(),
      clientInformation: jest.fn(),
      redirectToAuthorization: jest.fn(),
      saveCodeVerifier: jest.fn(),
      codeVerifier: jest.fn(),
      invalidateCredentials: jest.fn(),
    };

    mockFetch = jest.fn();
  });

  it("should work with SSE transport pattern", async () => {
    // Simulate how SSE transport might use the middleware
    mockProvider.tokens.mockResolvedValue({
      access_token: "sse-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    const response = new Response('{"jsonrpc":"2.0","id":1,"result":{}}', {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    mockFetch.mockResolvedValue(response);

    // Use custom logger to avoid console output
    const mockLogger = jest.fn();
    const enhancedFetch = applyMiddlewares(
      withOAuth(
        mockProvider as OAuthClientProvider,
        "https://mcp-server.example.com",
      ),
      withLogging({ logger: mockLogger, statusLevel: 400 }), // Only log errors
    )(mockFetch);

    // Simulate SSE POST request
    await enhancedFetch("https://mcp-server.example.com/endpoint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/list",
        id: 1,
      }),
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "https://mcp-server.example.com/endpoint",
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers),
        body: expect.any(String),
      }),
    );

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer sse-token");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("should work with StreamableHTTP transport pattern", async () => {
    // Simulate how StreamableHTTP transport might use the middleware
    mockProvider.tokens.mockResolvedValue({
      access_token: "streamable-token",
      token_type: "Bearer",
      expires_in: 3600,
    });

    const response = new Response(null, {
      status: 202,
      headers: { "mcp-session-id": "session-123" },
    });
    mockFetch.mockResolvedValue(response);

    // Use custom logger to avoid console output
    const mockLogger = jest.fn();
    const enhancedFetch = applyMiddlewares(
      withOAuth(
        mockProvider as OAuthClientProvider,
        "https://streamable-server.example.com",
      ),
      withLogging({
        logger: mockLogger,
        includeResponseHeaders: true,
        statusLevel: 0,
      }),
    )(mockFetch);

    // Simulate StreamableHTTP initialization request
    await enhancedFetch("https://streamable-server.example.com/mcp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "initialize",
        params: { protocolVersion: "2025-03-26", clientInfo: { name: "test" } },
        id: 1,
      }),
    });

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer streamable-token");
    expect(headers.get("Accept")).toBe("application/json, text/event-stream");
  });

  it("should handle auth retry in transport-like scenario", async () => {
    mockProvider.tokens
      .mockResolvedValueOnce({
        access_token: "expired-token",
        token_type: "Bearer",
        expires_in: 3600,
      })
      .mockResolvedValueOnce({
        access_token: "fresh-token",
        token_type: "Bearer",
        expires_in: 3600,
      });

    const unauthorizedResponse = new Response('{"error":"invalid_token"}', {
      status: 401,
      headers: { "www-authenticate": 'Bearer realm="mcp"' },
    });
    const successResponse = new Response(
      '{"jsonrpc":"2.0","id":1,"result":{}}',
      {
        status: 200,
      },
    );

    mockFetch
      .mockResolvedValueOnce(unauthorizedResponse)
      .mockResolvedValueOnce(successResponse);

    mockExtractResourceMetadataUrl.mockReturnValue(
      new URL("https://auth.example.com/.well-known/oauth-protected-resource"),
    );
    mockAuth.mockResolvedValue("AUTHORIZED");

    // Use custom logger to avoid console output
    const mockLogger = jest.fn();
    const enhancedFetch = applyMiddlewares(
      withOAuth(
        mockProvider as OAuthClientProvider,
        "https://mcp-server.example.com",
      ),
      withLogging({ logger: mockLogger, statusLevel: 0 }),
    )(mockFetch);

    const result = await enhancedFetch(
      "https://mcp-server.example.com/endpoint",
      {
        method: "POST",
        body: JSON.stringify({ jsonrpc: "2.0", method: "test", id: 1 }),
      },
    );

    expect(result).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockAuth).toHaveBeenCalledWith(mockProvider, {
      serverUrl: "https://mcp-server.example.com",
      resourceMetadataUrl: new URL(
        "https://auth.example.com/.well-known/oauth-protected-resource",
      ),
      fetchFn: mockFetch,
    });
  });
});

describe("createMiddleware", () => {
  let mockFetch: jest.MockedFunction<FetchLike>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch = jest.fn();
  });

  it("should create middleware with cleaner syntax", async () => {
    const response = new Response("success", { status: 200 });
    mockFetch.mockResolvedValue(response);

    const customMiddleware = createMiddleware(async (next, input, init) => {
      const headers = new Headers(init?.headers);
      headers.set("X-Custom-Header", "custom-value");
      return next(input, { ...init, headers });
    });

    const enhancedFetch = customMiddleware(mockFetch);
    await enhancedFetch("https://api.example.com/data");

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/data",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("X-Custom-Header")).toBe("custom-value");
  });

  it("should support conditional middleware logic", async () => {
    const apiResponse = new Response("api response", { status: 200 });
    const publicResponse = new Response("public response", { status: 200 });
    mockFetch
      .mockResolvedValueOnce(apiResponse)
      .mockResolvedValueOnce(publicResponse);

    const conditionalMiddleware = createMiddleware(
      async (next, input, init) => {
        const url = typeof input === "string" ? input : input.toString();

        if (url.includes("/api/")) {
          const headers = new Headers(init?.headers);
          headers.set("X-API-Version", "v2");
          return next(input, { ...init, headers });
        }

        return next(input, init);
      },
    );

    const enhancedFetch = conditionalMiddleware(mockFetch);

    // Test API route
    await enhancedFetch("https://example.com/api/users");
    let callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("X-API-Version")).toBe("v2");

    // Test non-API route
    await enhancedFetch("https://example.com/public/page");
    callArgs = mockFetch.mock.calls[1];
    const maybeHeaders = callArgs[1]?.headers as Headers | undefined;
    expect(maybeHeaders?.get("X-API-Version")).toBeUndefined();
  });

  it("should support short-circuit responses", async () => {
    const customMiddleware = createMiddleware(async (next, input, init) => {
      const url = typeof input === "string" ? input : input.toString();

      // Short-circuit for specific URL
      if (url.includes("/cached")) {
        return new Response("cached data", { status: 200 });
      }

      return next(input, init);
    });

    const enhancedFetch = customMiddleware(mockFetch);

    // Test cached route (should not call mockFetch)
    const cachedResponse = await enhancedFetch(
      "https://example.com/cached/data",
    );
    expect(await cachedResponse.text()).toBe("cached data");
    expect(mockFetch).not.toHaveBeenCalled();

    // Test normal route
    mockFetch.mockResolvedValue(new Response("fresh data", { status: 200 }));
    const normalResponse = await enhancedFetch("https://example.com/normal/data");
    expect(await normalResponse.text()).toBe("fresh data");
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("should handle response transformation", async () => {
    const originalResponse = new Response('{"data": "original"}', {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    mockFetch.mockResolvedValue(originalResponse);

    const transformMiddleware = createMiddleware(async (next, input, init) => {
      const response = await next(input, init);

      if (response.headers.get("content-type")?.includes("application/json")) {
        const data = await response.json();
        const transformed = { ...data, timestamp: 123456789 };

        return new Response(JSON.stringify(transformed), {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
        });
      }

      return response;
    });

    const enhancedFetch = transformMiddleware(mockFetch);
    const response = await enhancedFetch("https://api.example.com/data");
    const result = await response.json();

    expect(result).toEqual({
      data: "original",
      timestamp: 123456789,
    });
  });

  it("should support error handling and recovery", async () => {
    let attemptCount = 0;
    mockFetch.mockImplementation(async () => {
      attemptCount++;
      if (attemptCount === 1) {
        throw new Error("Network error");
      }
      return new Response("success", { status: 200 });
    });

    const retryMiddleware = createMiddleware(async (next, input, init) => {
      try {
        return await next(input, init);
      } catch (error) {
        // Retry once on network error
        console.log("Retrying request after error:", error);
        return await next(input, init);
      }
    });

    const enhancedFetch = retryMiddleware(mockFetch);
    const response = await enhancedFetch("https://api.example.com/data");

    expect(await response.text()).toBe("success");
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("should compose well with other middleware", async () => {
    const response = new Response("success", { status: 200 });
    mockFetch.mockResolvedValue(response);

    // Create custom middleware using createMiddleware
    const customAuth = createMiddleware(async (next, input, init) => {
      const headers = new Headers(init?.headers);
      headers.set("Authorization", "Custom token");
      return next(input, { ...init, headers });
    });

    const customLogging = createMiddleware(async (next, input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      console.log(`Request to: ${url}`);
      const response = await next(input, init);
      console.log(`Response status: ${response.status}`);
      return response;
    });

    // Compose with existing middleware
    const enhancedFetch = applyMiddlewares(
      customAuth,
      customLogging,
      withLogging({ statusLevel: 400 }),
    )(mockFetch);

    await enhancedFetch("https://api.example.com/data");

    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Custom token");
  });

  it("should have access to both input types (string and URL)", async () => {
    const response = new Response("success", { status: 200 });
    mockFetch.mockResolvedValue(response);

    let capturedInputType: string | undefined;
    const inspectMiddleware = createMiddleware(async (next, input, init) => {
      capturedInputType = typeof input === "string" ? "string" : "URL";
      return next(input, init);
    });

    const enhancedFetch = inspectMiddleware(mockFetch);

    // Test with string input
    await enhancedFetch("https://api.example.com/data");
    expect(capturedInputType).toBe("string");

    // Test with URL input
    await enhancedFetch(new URL("https://api.example.com/data"));
    expect(capturedInputType).toBe("URL");
  });
});



================================================
FILE: src/client/middleware.ts
================================================
import {
  auth,
  extractResourceMetadataUrl,
  OAuthClientProvider,
  UnauthorizedError,
} from "./auth.js";
import { FetchLike } from "../shared/transport.js";

/**
 * Middleware function that wraps and enhances fetch functionality.
 * Takes a fetch handler and returns an enhanced fetch handler.
 */
export type Middleware = (next: FetchLike) => FetchLike;

/**
 * Creates a fetch wrapper that handles OAuth authentication automatically.
 *
 * This wrapper will:
 * - Add Authorization headers with access tokens
 * - Handle 401 responses by attempting re-authentication
 * - Retry the original request after successful auth
 * - Handle OAuth errors appropriately (InvalidClientError, etc.)
 *
 * The baseUrl parameter is optional and defaults to using the domain from the request URL.
 * However, you should explicitly provide baseUrl when:
 * - Making requests to multiple subdomains (e.g., api.example.com, cdn.example.com)
 * - Using API paths that differ from OAuth discovery paths (e.g., requesting /api/v1/data but OAuth is at /)
 * - The OAuth server is on a different domain than your API requests
 * - You want to ensure consistent OAuth behavior regardless of request URLs
 *
 * For MCP transports, set baseUrl to the same URL you pass to the transport constructor.
 *
 * Note: This wrapper is designed for general-purpose fetch operations.
 * MCP transports (SSE and StreamableHTTP) already have built-in OAuth handling
 * and should not need this wrapper.
 *
 * @param provider - OAuth client provider for authentication
 * @param baseUrl - Base URL for OAuth server discovery (defaults to request URL domain)
 * @returns A fetch middleware function
 */
export const withOAuth =
  (provider: OAuthClientProvider, baseUrl?: string | URL): Middleware =>
  (next) => {
    return async (input, init) => {
      const makeRequest = async (): Promise<Response> => {
        const headers = new Headers(init?.headers);

        // Add authorization header if tokens are available
        const tokens = await provider.tokens();
        if (tokens) {
          headers.set("Authorization", `Bearer ${tokens.access_token}`);
        }

        return await next(input, { ...init, headers });
      };

      let response = await makeRequest();

      // Handle 401 responses by attempting re-authentication
      if (response.status === 401) {
        try {
          const resourceMetadataUrl = extractResourceMetadataUrl(response);

          // Use provided baseUrl or extract from request URL
          const serverUrl =
            baseUrl ||
            (typeof input === "string" ? new URL(input).origin : input.origin);

          const result = await auth(provider, {
            serverUrl,
            resourceMetadataUrl,
            fetchFn: next,
          });

          if (result === "REDIRECT") {
            throw new UnauthorizedError(
              "Authentication requires user authorization - redirect initiated",
            );
          }

          if (result !== "AUTHORIZED") {
            throw new UnauthorizedError(
              `Authentication failed with result: ${result}`,
            );
          }

          // Retry the request with fresh tokens
          response = await makeRequest();
        } catch (error) {
          if (error instanceof UnauthorizedError) {
            throw error;
          }
          throw new UnauthorizedError(
            `Failed to re-authenticate: ${error instanceof Error ? error.message : String(error)}`,
          );
        }
      }

      // If we still have a 401 after re-auth attempt, throw an error
      if (response.status === 401) {
        const url = typeof input === "string" ? input : input.toString();
        throw new UnauthorizedError(`Authentication failed for ${url}`);
      }

      return response;
    };
  };

/**
 * Logger function type for HTTP requests
 */
export type RequestLogger = (input: {
  method: string;
  url: string | URL;
  status: number;
  statusText: string;
  duration: number;
  requestHeaders?: Headers;
  responseHeaders?: Headers;
  error?: Error;
}) => void;

/**
 * Configuration options for the logging middleware
 */
export type LoggingOptions = {
  /**
   * Custom logger function, defaults to console logging
   */
  logger?: RequestLogger;

  /**
   * Whether to include request headers in logs
   * @default false
   */
  includeRequestHeaders?: boolean;

  /**
   * Whether to include response headers in logs
   * @default false
   */
  includeResponseHeaders?: boolean;

  /**
   * Status level filter - only log requests with status >= this value
   * Set to 0 to log all requests, 400 to log only errors
   * @default 0
   */
  statusLevel?: number;
};

/**
 * Creates a fetch middleware that logs HTTP requests and responses.
 *
 * When called without arguments `withLogging()`, it uses the default logger that:
 * - Logs successful requests (2xx) to `console.log`
 * - Logs error responses (4xx/5xx) and network errors to `console.error`
 * - Logs all requests regardless of status (statusLevel: 0)
 * - Does not include request or response headers in logs
 * - Measures and displays request duration in milliseconds
 *
 * Important: the default logger uses both `console.log` and `console.error` so it should not be used with
 * `stdio` transports and applications.
 *
 * @param options - Logging configuration options
 * @returns A fetch middleware function
 */
export const withLogging = (options: LoggingOptions = {}): Middleware => {
  const {
    logger,
    includeRequestHeaders = false,
    includeResponseHeaders = false,
    statusLevel = 0,
  } = options;

  const defaultLogger: RequestLogger = (input) => {
    const {
      method,
      url,
      status,
      statusText,
      duration,
      requestHeaders,
      responseHeaders,
      error,
    } = input;

    let message = error
      ? `HTTP ${method} ${url} failed: ${error.message} (${duration}ms)`
      : `HTTP ${method} ${url} ${status} ${statusText} (${duration}ms)`;

    // Add headers to message if requested
    if (includeRequestHeaders && requestHeaders) {
      const reqHeaders = Array.from(requestHeaders.entries())
        .map(([key, value]) => `${key}: ${value}`)
        .join(", ");
      message += `\n  Request Headers: {${reqHeaders}}`;
    }

    if (includeResponseHeaders && responseHeaders) {
      const resHeaders = Array.from(responseHeaders.entries())
        .map(([key, value]) => `${key}: ${value}`)
        .join(", ");
      message += `\n  Response Headers: {${resHeaders}}`;
    }

    if (error || status >= 400) {
      // eslint-disable-next-line no-console
      console.error(message);
    } else {
      // eslint-disable-next-line no-console
      console.log(message);
    }
  };

  const logFn = logger || defaultLogger;

  return (next) => async (input, init) => {
    const startTime = performance.now();
    const method = init?.method || "GET";
    const url = typeof input === "string" ? input : input.toString();
    const requestHeaders = includeRequestHeaders
      ? new Headers(init?.headers)
      : undefined;

    try {
      const response = await next(input, init);
      const duration = performance.now() - startTime;

      // Only log if status meets the log level threshold
      if (response.status >= statusLevel) {
        logFn({
          method,
          url,
          status: response.status,
          statusText: response.statusText,
          duration,
          requestHeaders,
          responseHeaders: includeResponseHeaders
            ? response.headers
            : undefined,
        });
      }

      return response;
    } catch (error) {
      const duration = performance.now() - startTime;

      // Always log errors regardless of log level
      logFn({
        method,
        url,
        status: 0,
        statusText: "Network Error",
        duration,
        requestHeaders,
        error: error as Error,
      });

      throw error;
    }
  };
};

/**
 * Composes multiple fetch middleware functions into a single middleware pipeline.
 * Middleware are applied in the order they appear, creating a chain of handlers.
 *
 * @example
 * ```typescript
 * // Create a middleware pipeline that handles both OAuth and logging
 * const enhancedFetch = applyMiddlewares(
 *   withOAuth(oauthProvider, 'https://api.example.com'),
 *   withLogging({ statusLevel: 400 })
 * )(fetch);
 *
 * // Use the enhanced fetch - it will handle auth and log errors
 * const response = await enhancedFetch('https://api.example.com/data');
 * ```
 *
 * @param middleware - Array of fetch middleware to compose into a pipeline
 * @returns A single composed middleware function
 */
export const applyMiddlewares = (
  ...middleware: Middleware[]
): Middleware => {
  return (next) => {
    return middleware.reduce((handler, mw) => mw(handler), next);
  };
};

/**
 * Helper function to create custom fetch middleware with cleaner syntax.
 * Provides the next handler and request details as separate parameters for easier access.
 *
 * @example
 * ```typescript
 * // Create custom authentication middleware
 * const customAuthMiddleware = createMiddleware(async (next, input, init) => {
 *   const headers = new Headers(init?.headers);
 *   headers.set('X-Custom-Auth', 'my-token');
 *
 *   const response = await next(input, { ...init, headers });
 *
 *   if (response.status === 401) {
 *     console.log('Authentication failed');
 *   }
 *
 *   return response;
 * });
 *
 * // Create conditional middleware
 * const conditionalMiddleware = createMiddleware(async (next, input, init) => {
 *   const url = typeof input === 'string' ? input : input.toString();
 *
 *   // Only add headers for API routes
 *   if (url.includes('/api/')) {
 *     const headers = new Headers(init?.headers);
 *     headers.set('X-API-Version', 'v2');
 *     return next(input, { ...init, headers });
 *   }
 *
 *   // Pass through for non-API routes
 *   return next(input, init);
 * });
 *
 * // Create caching middleware
 * const cacheMiddleware = createMiddleware(async (next, input, init) => {
 *   const cacheKey = typeof input === 'string' ? input : input.toString();
 *
 *   // Check cache first
 *   const cached = await getFromCache(cacheKey);
 *   if (cached) {
 *     return new Response(cached, { status: 200 });
 *   }
 *
 *   // Make request and cache result
 *   const response = await next(input, init);
 *   if (response.ok) {
 *     await saveToCache(cacheKey, await response.clone().text());
 *   }
 *
 *   return response;
 * });
 * ```
 *
 * @param handler - Function that receives the next handler and request parameters
 * @returns A fetch middleware function
 */
export const createMiddleware = (
  handler: (
    next: FetchLike,
    input: string | URL,
    init?: RequestInit,
  ) => Promise<Response>,
): Middleware => {
  return (next) => (input, init) => handler(next, input as string | URL, init);
};



================================================
FILE: src/client/sse.test.ts
================================================
import { createServer, ServerResponse, type IncomingMessage, type Server } from "http";
import { AddressInfo } from "net";
import { JSONRPCMessage } from "../types.js";
import { SSEClientTransport } from "./sse.js";
import { OAuthClientProvider, UnauthorizedError } from "./auth.js";
import { OAuthTokens } from "../shared/auth.js";
import { InvalidClientError, InvalidGrantError, UnauthorizedClientError } from "../server/auth/errors.js";

describe("SSEClientTransport", () => {
  let resourceServer: Server;
  let authServer: Server;
  let transport: SSEClientTransport;
  let resourceBaseUrl: URL;
  let authBaseUrl: URL;
  let lastServerRequest: IncomingMessage;
  let sendServerMessage: ((message: string) => void) | null = null;

  beforeEach((done) => {
    // Reset state
    lastServerRequest = null as unknown as IncomingMessage;
    sendServerMessage = null;

    authServer = createServer((req, res) => {
      if (req.url === "/.well-known/oauth-authorization-server") {
        res.writeHead(200, {
          "Content-Type": "application/json"
        });
        res.end(JSON.stringify({
          issuer: "https://auth.example.com",
          authorization_endpoint: "https://auth.example.com/authorize",
          token_endpoint: "https://auth.example.com/token",
          registration_endpoint: "https://auth.example.com/register",
          response_types_supported: ["code"],
          code_challenge_methods_supported: ["S256"],
        }));
        return;
      }
      res.writeHead(401).end();
    });

    // Create a test server that will receive the EventSource connection
    resourceServer = createServer((req, res) => {
      lastServerRequest = req;

      // Send SSE headers
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      });

      // Send the endpoint event
      res.write("event: endpoint\n");
      res.write(`data: ${resourceBaseUrl.href}\n\n`);

      // Store reference to send function for tests
      sendServerMessage = (message: string) => {
        res.write(`data: ${message}\n\n`);
      };

      // Handle request body for POST endpoints
      if (req.method === "POST") {
        let body = "";
        req.on("data", (chunk) => {
          body += chunk;
        });
        req.on("end", () => {
          (req as IncomingMessage & { body: string }).body = body;
          res.end();
        });
      }
    });

    // Start server on random port
    resourceServer.listen(0, "127.0.0.1", () => {
      const addr = resourceServer.address() as AddressInfo;
      resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
      done();
    });

    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(async () => {
    await transport.close();
    await resourceServer.close();
    await authServer.close();

    jest.clearAllMocks();
  });

  describe("connection handling", () => {
    it("establishes SSE connection and receives endpoint", async () => {
      transport = new SSEClientTransport(resourceBaseUrl);
      await transport.start();

      expect(lastServerRequest.headers.accept).toBe("text/event-stream");
      expect(lastServerRequest.method).toBe("GET");
    });

    it("rejects if server returns non-200 status", async () => {
      // Create a server that returns 403
      await resourceServer.close();

      resourceServer = createServer((req, res) => {
        res.writeHead(403);
        res.end();
      });

      await new Promise<void>((resolve) => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl);
      await expect(transport.start()).rejects.toThrow();
    });

    it("closes EventSource connection on close()", async () => {
      transport = new SSEClientTransport(resourceBaseUrl);
      await transport.start();

      const closePromise = new Promise((resolve) => {
        lastServerRequest.on("close", resolve);
      });

      await transport.close();
      await closePromise;
    });
  });

  describe("message handling", () => {
    it("receives and parses JSON-RPC messages", async () => {
      const receivedMessages: JSONRPCMessage[] = [];
      transport = new SSEClientTransport(resourceBaseUrl);
      transport.onmessage = (msg) => receivedMessages.push(msg);

      await transport.start();

      const testMessage: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "test-1",
        method: "test",
        params: { foo: "bar" },
      };

      sendServerMessage!(JSON.stringify(testMessage));

      // Wait for message processing
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual(testMessage);
    });

    it("handles malformed JSON messages", async () => {
      const errors: Error[] = [];
      transport = new SSEClientTransport(resourceBaseUrl);
      transport.onerror = (err) => errors.push(err);

      await transport.start();

      sendServerMessage!("invalid json");

      // Wait for message processing
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(errors).toHaveLength(1);
      expect(errors[0].message).toMatch(/JSON/);
    });

    it("handles messages via POST requests", async () => {
      transport = new SSEClientTransport(resourceBaseUrl);
      await transport.start();

      const testMessage: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "test-1",
        method: "test",
        params: { foo: "bar" },
      };

      await transport.send(testMessage);

      // Wait for request processing
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(lastServerRequest.method).toBe("POST");
      expect(lastServerRequest.headers["content-type"]).toBe(
        "application/json",
      );
      expect(
        JSON.parse(
          (lastServerRequest as IncomingMessage & { body: string }).body,
        ),
      ).toEqual(testMessage);
    });

    it("handles POST request failures", async () => {
      // Create a server that returns 500 for POST
      await resourceServer.close();

      resourceServer = createServer((req, res) => {
        if (req.method === "GET") {
          res.writeHead(200, {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
          });
          res.write("event: endpoint\n");
          res.write(`data: ${resourceBaseUrl.href}\n\n`);
        } else {
          res.writeHead(500);
          res.end("Internal error");
        }
      });

      await new Promise<void>((resolve) => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl);
      await transport.start();

      const testMessage: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "test-1",
        method: "test",
        params: {},
      };

      await expect(transport.send(testMessage)).rejects.toThrow(/500/);
    });
  });

  describe("header handling", () => {
    it("uses custom fetch implementation from EventSourceInit to add auth headers", async () => {
      const authToken = "Bearer test-token";

      // Create a fetch wrapper that adds auth header
      const fetchWithAuth = (url: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("Authorization", authToken);
        return fetch(url.toString(), { ...init, headers });
      };

      transport = new SSEClientTransport(resourceBaseUrl, {
        eventSourceInit: {
          fetch: fetchWithAuth,
        },
      });

      await transport.start();

      // Verify the auth header was received by the server
      expect(lastServerRequest.headers.authorization).toBe(authToken);
    });

    it("uses custom fetch implementation from options", async () => {
      const authToken = "Bearer custom-token";

      const fetchWithAuth = jest.fn((url: string | URL, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        headers.set("Authorization", authToken);
        return fetch(url.toString(), { ...init, headers });
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        fetch: fetchWithAuth,
      });

      await transport.start();

      expect(lastServerRequest.headers.authorization).toBe(authToken);

      // Send a message to verify fetchWithAuth used for POST as well
      const message: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "1",
        method: "test",
        params: {},
      };

      await transport.send(message);

      expect(fetchWithAuth).toHaveBeenCalledTimes(2);
      expect(lastServerRequest.method).toBe("POST");
      expect(lastServerRequest.headers.authorization).toBe(authToken);
    });

    it("passes custom headers to fetch requests", async () => {
      const customHeaders = {
        Authorization: "Bearer test-token",
        "X-Custom-Header": "custom-value",
      };

      transport = new SSEClientTransport(resourceBaseUrl, {
        requestInit: {
          headers: customHeaders,
        },
      });

      await transport.start();

      // Store original fetch
      const originalFetch = global.fetch;

      try {
        // Mock fetch for the message sending test
        global.fetch = jest.fn().mockResolvedValue({
          ok: true,
        });

        const message: JSONRPCMessage = {
          jsonrpc: "2.0",
          id: "1",
          method: "test",
          params: {},
        };

        await transport.send(message);

        // Verify fetch was called with correct headers
        expect(global.fetch).toHaveBeenCalledWith(
          expect.any(URL),
          expect.objectContaining({
            headers: expect.any(Headers),
          }),
        );

        const calledHeaders = (global.fetch as jest.Mock).mock.calls[0][1]
          .headers;
        expect(calledHeaders.get("Authorization")).toBe(
          customHeaders.Authorization,
        );
        expect(calledHeaders.get("X-Custom-Header")).toBe(
          customHeaders["X-Custom-Header"],
        );
        expect(calledHeaders.get("content-type")).toBe("application/json");
      } finally {
        // Restore original fetch
        global.fetch = originalFetch;
      }
    });
  });

  describe("auth handling", () => {
    const authServerMetadataUrls = [
      "/.well-known/oauth-authorization-server",
      "/.well-known/openid-configuration",
    ];

    let mockAuthProvider: jest.Mocked<OAuthClientProvider>;

    beforeEach(() => {
      mockAuthProvider = {
        get redirectUrl() { return "http://localhost/callback"; },
        get clientMetadata() { return { redirect_uris: ["http://localhost/callback"] }; },
        clientInformation: jest.fn(() => ({ client_id: "test-client-id", client_secret: "test-client-secret" })),
        tokens: jest.fn(),
        saveTokens: jest.fn(),
        redirectToAuthorization: jest.fn(),
        saveCodeVerifier: jest.fn(),
        codeVerifier: jest.fn(),
        invalidateCredentials: jest.fn(),
      };
    });

    it("attaches auth header from provider on SSE connection", async () => {
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "test-token",
        token_type: "Bearer"
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await transport.start();

      expect(lastServerRequest.headers.authorization).toBe("Bearer test-token");
      expect(mockAuthProvider.tokens).toHaveBeenCalled();
    });

    it("attaches custom header from provider on initial SSE connection", async () => {
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "test-token",
        token_type: "Bearer"
      });
      const customHeaders = {
        "X-Custom-Header": "custom-value",
      };

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
        requestInit: {
          headers: customHeaders,
        },
      });

      await transport.start();

      expect(lastServerRequest.headers.authorization).toBe("Bearer test-token");
      expect(lastServerRequest.headers["x-custom-header"]).toBe("custom-value");
      expect(mockAuthProvider.tokens).toHaveBeenCalled();
    });

    it("attaches auth header from provider on POST requests", async () => {
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "test-token",
        token_type: "Bearer"
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await transport.start();

      const message: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "1",
        method: "test",
        params: {},
      };

      await transport.send(message);

      expect(lastServerRequest.headers.authorization).toBe("Bearer test-token");
      expect(mockAuthProvider.tokens).toHaveBeenCalled();
    });

    it("attempts auth flow on 401 during SSE connection", async () => {

      // Create server that returns 401s
      resourceServer.close();
      authServer.close();

      // Start auth server on random port
      await new Promise<void>(resolve => {
        authServer.listen(0, "127.0.0.1", () => {
          const addr = authServer.address() as AddressInfo;
          authBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      resourceServer = createServer((req, res) => {
        lastServerRequest = req;

        if (req.url === "/.well-known/oauth-protected-resource") {
          res.writeHead(200, {
            'Content-Type': 'application/json',
          })
          .end(JSON.stringify({
            resource: resourceBaseUrl.href,
            authorization_servers: [`${authBaseUrl}`],
          }));
          return;
        }

        if (req.url !== "/") {
            res.writeHead(404).end();
        } else {
          res.writeHead(401).end();
        }
      });

      await new Promise<void>(resolve => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await expect(() => transport.start()).rejects.toThrow(UnauthorizedError);
      expect(mockAuthProvider.redirectToAuthorization.mock.calls).toHaveLength(1);
    });

    it("attempts auth flow on 401 during POST request", async () => {
      // Create server that accepts SSE but returns 401 on POST
      resourceServer.close();
      authServer.close();

      await new Promise<void>(resolve => {
        authServer.listen(0, "127.0.0.1", () => {
          const addr = authServer.address() as AddressInfo;
          authBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      resourceServer = createServer((req, res) => {
        lastServerRequest = req;

        switch (req.method) {
          case "GET":
            if (req.url === "/.well-known/oauth-protected-resource") {
              res.writeHead(200, {
                'Content-Type': 'application/json',
              })
              .end(JSON.stringify({
                resource: resourceBaseUrl.href,
                authorization_servers: [`${authBaseUrl}`],
              }));
              return;
            }

            if (req.url !== "/") {
              res.writeHead(404).end();
              return;
            }

            res.writeHead(200, {
              "Content-Type": "text/event-stream",
              "Cache-Control": "no-cache, no-transform",
              Connection: "keep-alive",
            });
            res.write("event: endpoint\n");
            res.write(`data: ${resourceBaseUrl.href}\n\n`);
            break;

          case "POST":
          res.writeHead(401);
          res.end();
            break;
        }
      });

      await new Promise<void>(resolve => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await transport.start();

      const message: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "1",
        method: "test",
        params: {},
      };

      await expect(() => transport.send(message)).rejects.toThrow(UnauthorizedError);
      expect(mockAuthProvider.redirectToAuthorization.mock.calls).toHaveLength(1);
    });

    it("respects custom headers when using auth provider", async () => {
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "test-token",
        token_type: "Bearer"
      });

      const customHeaders = {
        "X-Custom-Header": "custom-value",
      };

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
        requestInit: {
          headers: customHeaders,
        },
      });

      await transport.start();

      const message: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "1",
        method: "test",
        params: {},
      };

      await transport.send(message);

      expect(lastServerRequest.headers.authorization).toBe("Bearer test-token");
      expect(lastServerRequest.headers["x-custom-header"]).toBe("custom-value");
    });

    it("refreshes expired token during SSE connection", async () => {
      // Mock tokens() to return expired token until saveTokens is called
      let currentTokens: OAuthTokens = {
        access_token: "expired-token",
        token_type: "Bearer",
        refresh_token: "refresh-token"
      };
      mockAuthProvider.tokens.mockImplementation(() => currentTokens);
      mockAuthProvider.saveTokens.mockImplementation((tokens) => {
        currentTokens = tokens;
      });

      // Create server that returns 401 for expired token, then accepts new token
      resourceServer.close();
      authServer.close();

      authServer = createServer((req, res) => {
        if (req.url && authServerMetadataUrls.includes(req.url)) {
          res.writeHead(404).end();
          return;
        }

        if (req.url === "/token" && req.method === "POST") {
          // Handle token refresh request
          let body = "";
          req.on("data", chunk => { body += chunk; });
          req.on("end", () => {
            const params = new URLSearchParams(body);
            if (params.get("grant_type") === "refresh_token" &&
              params.get("refresh_token") === "refresh-token" &&
              params.get("client_id") === "test-client-id" &&
              params.get("client_secret") === "test-client-secret") {
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({
                access_token: "new-token",
                token_type: "Bearer",
                refresh_token: "new-refresh-token"
              }));
            } else {
              res.writeHead(400).end();
            }
          });
          return;
        }

        res.writeHead(401).end();

      });

      // Start auth server on random port
      await new Promise<void>(resolve => {
        authServer.listen(0, "127.0.0.1", () => {
          const addr = authServer.address() as AddressInfo;
          authBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      let connectionAttempts = 0;
      resourceServer = createServer((req, res) => {
        lastServerRequest = req;

        if (req.url === "/.well-known/oauth-protected-resource") {
          res.writeHead(200, {
            'Content-Type': 'application/json',
          })
          .end(JSON.stringify({
            resource: resourceBaseUrl.href,
            authorization_servers: [`${authBaseUrl}`],
          }));
          return;
        }

        if (req.url !== "/") {
          res.writeHead(404).end();
          return;
        }

          const auth = req.headers.authorization;
          if (auth === "Bearer expired-token") {
            res.writeHead(401).end();
            return;
          }

        if (auth === "Bearer new-token") {
          res.writeHead(200, {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
          });
          res.write("event: endpoint\n");
          res.write(`data: ${resourceBaseUrl.href}\n\n`);
          connectionAttempts++;
          return;
        }

          res.writeHead(401).end();
      });

      await new Promise<void>(resolve => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await transport.start();

      expect(mockAuthProvider.saveTokens).toHaveBeenCalledWith({
        access_token: "new-token",
        token_type: "Bearer",
        refresh_token: "new-refresh-token"
      });
      expect(connectionAttempts).toBe(1);
      expect(lastServerRequest.headers.authorization).toBe("Bearer new-token");
    });

    it("refreshes expired token during POST request", async () => {
      // Mock tokens() to return expired token until saveTokens is called
      let currentTokens: OAuthTokens = {
        access_token: "expired-token",
        token_type: "Bearer",
        refresh_token: "refresh-token"
      };
      mockAuthProvider.tokens.mockImplementation(() => currentTokens);
      mockAuthProvider.saveTokens.mockImplementation((tokens) => {
        currentTokens = tokens;
      });

      // Create server that returns 401 for expired token, then accepts new token
      resourceServer.close();
      authServer.close();

      authServer = createServer((req, res) => {
        if (req.url && authServerMetadataUrls.includes(req.url)) {
          res.writeHead(404).end();
          return;
        }

        if (req.url === "/token" && req.method === "POST") {
          // Handle token refresh request
          let body = "";
          req.on("data", chunk => { body += chunk; });
          req.on("end", () => {
            const params = new URLSearchParams(body);
            if (params.get("grant_type") === "refresh_token" &&
              params.get("refresh_token") === "refresh-token" &&
              params.get("client_id") === "test-client-id" &&
              params.get("client_secret") === "test-client-secret") {
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({
                access_token: "new-token",
                token_type: "Bearer",
                refresh_token: "new-refresh-token"
              }));
            } else {
              res.writeHead(400).end();
            }
          });
          return;
        }

        res.writeHead(401).end();

      });

      // Start auth server on random port
      await new Promise<void>(resolve => {
        authServer.listen(0, "127.0.0.1", () => {
          const addr = authServer.address() as AddressInfo;
          authBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      let postAttempts = 0;
      resourceServer = createServer((req, res) => {
        lastServerRequest = req;

        if (req.url === "/.well-known/oauth-protected-resource") {
          res.writeHead(200, {
            'Content-Type': 'application/json',
          })
          .end(JSON.stringify({
            resource: resourceBaseUrl.href,
            authorization_servers: [`${authBaseUrl}`],
          }));
          return;
        }

        switch (req.method) {
          case "GET":
            if (req.url !== "/") {
              res.writeHead(404).end();
              return;
            }

            res.writeHead(200, {
              "Content-Type": "text/event-stream",
              "Cache-Control": "no-cache, no-transform",
              Connection: "keep-alive",
            });
            res.write("event: endpoint\n");
            res.write(`data: ${resourceBaseUrl.href}\n\n`);
            break;

          case "POST": {
            if (req.url !== "/") {
              res.writeHead(404).end();
              return;
            }

          const auth = req.headers.authorization;
          if (auth === "Bearer expired-token") {
            res.writeHead(401).end();
            return;
          }

          if (auth === "Bearer new-token") {
            res.writeHead(200).end();
            postAttempts++;
            return;
          }

          res.writeHead(401).end();
            break;
          }
        }
      });

      await new Promise<void>(resolve => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await transport.start();

      const message: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "1",
        method: "test",
        params: {},
      };

      await transport.send(message);

      expect(mockAuthProvider.saveTokens).toHaveBeenCalledWith({
        access_token: "new-token",
        token_type: "Bearer",
        refresh_token: "new-refresh-token"
      });
      expect(postAttempts).toBe(1);
      expect(lastServerRequest.headers.authorization).toBe("Bearer new-token");
    });

    it("redirects to authorization if refresh token flow fails", async () => {
      // Mock tokens() to return expired token until saveTokens is called
      let currentTokens: OAuthTokens = {
        access_token: "expired-token",
        token_type: "Bearer",
        refresh_token: "refresh-token"
      };
      mockAuthProvider.tokens.mockImplementation(() => currentTokens);
      mockAuthProvider.saveTokens.mockImplementation((tokens) => {
        currentTokens = tokens;
      });

      // Create server that returns 401 for all tokens
      resourceServer.close();
      authServer.close();

      authServer = createServer((req, res) => {
        if (req.url && authServerMetadataUrls.includes(req.url)) {
          res.writeHead(404).end();
          return;
        }

        if (req.url === "/token" && req.method === "POST") {
          // Handle token refresh request - always fail
          res.writeHead(400).end();
          return;
        }

        res.writeHead(401).end();

      });


      // Start auth server on random port
      await new Promise<void>(resolve => {
        authServer.listen(0, "127.0.0.1", () => {
          const addr = authServer.address() as AddressInfo;
          authBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      resourceServer = createServer((req, res) => {
        lastServerRequest = req;

        if (req.url === "/.well-known/oauth-protected-resource") {
          res.writeHead(200, {
            'Content-Type': 'application/json',
          })
          .end(JSON.stringify({
            resource: resourceBaseUrl.href,
            authorization_servers: [`${authBaseUrl}`],
          }));
          return;
        }

        if (req.url !== "/") {
          res.writeHead(404).end();
          return;
        }
        res.writeHead(401).end();
      });

      await new Promise<void>(resolve => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
      });

      await expect(() => transport.start()).rejects.toThrow(UnauthorizedError);
      expect(mockAuthProvider.redirectToAuthorization).toHaveBeenCalled();
    });

    it("invalidates all credentials on InvalidClientError during token refresh", async () => {
      // Mock tokens() to return token with refresh token
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "expired-token",
        token_type: "Bearer",
        refresh_token: "refresh-token"
      });

      let baseUrl = resourceBaseUrl;

      // Create server that returns InvalidClientError on token refresh
      const server = createServer((req, res) => {
        lastServerRequest = req;

        // Handle OAuth metadata discovery
        if (req.url === "/.well-known/oauth-authorization-server" && req.method === "GET") {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            issuer: baseUrl.href,
            authorization_endpoint: `${baseUrl.href}authorize`,
            token_endpoint: `${baseUrl.href}token`,
            response_types_supported: ["code"],
            code_challenge_methods_supported: ["S256"],
          }));
          return;
        }

        if (req.url === "/token" && req.method === "POST") {
          // Handle token refresh request - return InvalidClientError
          const error = new InvalidClientError("Client authentication failed");
          res.writeHead(400, { 'Content-Type': 'application/json' })
            .end(JSON.stringify(error.toResponseObject()));
          return;
        }

        if (req.url !== "/") {
          res.writeHead(404).end();
          return;
        }
        res.writeHead(401).end();
      });

      await new Promise<void>(resolve => {
        server.listen(0, "127.0.0.1", () => {
          const addr = server.address() as AddressInfo;
          baseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(baseUrl, {
        authProvider: mockAuthProvider,
      });

      await expect(() => transport.start()).rejects.toThrow(InvalidClientError);
      expect(mockAuthProvider.invalidateCredentials).toHaveBeenCalledWith('all');
    });

    it("invalidates all credentials on UnauthorizedClientError during token refresh", async () => {
      // Mock tokens() to return token with refresh token
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "expired-token",
        token_type: "Bearer",
        refresh_token: "refresh-token"
      });

      let baseUrl = resourceBaseUrl;

      const server = createServer((req, res) => {
        lastServerRequest = req;

        // Handle OAuth metadata discovery
        if (req.url === "/.well-known/oauth-authorization-server" && req.method === "GET") {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            issuer: baseUrl.href,
            authorization_endpoint: `${baseUrl.href}authorize`,
            token_endpoint: `${baseUrl.href}token`,
            response_types_supported: ["code"],
            code_challenge_methods_supported: ["S256"],
          }));
          return;
        }

        if (req.url === "/token" && req.method === "POST") {
          // Handle token refresh request - return UnauthorizedClientError
          const error = new UnauthorizedClientError("Client not authorized");
          res.writeHead(400, { 'Content-Type': 'application/json' })
            .end(JSON.stringify(error.toResponseObject()));
          return;
        }

        if (req.url !== "/") {
          res.writeHead(404).end();
          return;
        }
        res.writeHead(401).end();
      });

      await new Promise<void>(resolve => {
        server.listen(0, "127.0.0.1", () => {
          const addr = server.address() as AddressInfo;
          baseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(baseUrl, {
        authProvider: mockAuthProvider,
      });

      await expect(() => transport.start()).rejects.toThrow(UnauthorizedClientError);
      expect(mockAuthProvider.invalidateCredentials).toHaveBeenCalledWith('all');
    });

    it("invalidates tokens on InvalidGrantError during token refresh", async () => {
      // Mock tokens() to return token with refresh token
      mockAuthProvider.tokens.mockResolvedValue({
        access_token: "expired-token",
        token_type: "Bearer",
        refresh_token: "refresh-token"
      });
      let baseUrl = resourceBaseUrl;

      const server = createServer((req, res) => {
        lastServerRequest = req;

        // Handle OAuth metadata discovery
        if (req.url === "/.well-known/oauth-authorization-server" && req.method === "GET") {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            issuer: baseUrl.href,
            authorization_endpoint: `${baseUrl.href}authorize`,
            token_endpoint: `${baseUrl.href}token`,
            response_types_supported: ["code"],
            code_challenge_methods_supported: ["S256"],
          }));
          return;
        }

        if (req.url === "/token" && req.method === "POST") {
          // Handle token refresh request - return InvalidGrantError
          const error = new InvalidGrantError("Invalid refresh token");
          res.writeHead(400, { 'Content-Type': 'application/json' })
            .end(JSON.stringify(error.toResponseObject()));
          return;
        }

        if (req.url !== "/") {
          res.writeHead(404).end();
          return;
        }
        res.writeHead(401).end();
      });

      await new Promise<void>(resolve => {
        server.listen(0, "127.0.0.1", () => {
          const addr = server.address() as AddressInfo;
          baseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });

      transport = new SSEClientTransport(baseUrl, {
        authProvider: mockAuthProvider,
      });

      await expect(() => transport.start()).rejects.toThrow(InvalidGrantError);
      expect(mockAuthProvider.invalidateCredentials).toHaveBeenCalledWith('tokens');
    });
  });

  describe("custom fetch in auth code paths", () => {
    let customFetch: jest.MockedFunction<typeof fetch>;
    let globalFetchSpy: jest.SpyInstance;
    let mockAuthProvider: jest.Mocked<OAuthClientProvider>;
    let resourceServerHandler: jest.Mock<void, [IncomingMessage, ServerResponse<IncomingMessage> & {
      req: IncomingMessage;
    }], void>;

    /**
     * Helper function to create a mock auth provider with configurable behavior
     */
    const createMockAuthProvider = (config: {
      hasTokens?: boolean;
      tokensExpired?: boolean;
      hasRefreshToken?: boolean;
      clientRegistered?: boolean;
      authorizationCode?: string;
    } = {}): jest.Mocked<OAuthClientProvider> => {
      const tokens = config.hasTokens ? {
        access_token: config.tokensExpired ? "expired-token" : "valid-token",
        token_type: "Bearer" as const,
        ...(config.hasRefreshToken && { refresh_token: "refresh-token" })
      } : undefined;

      const clientInfo = config.clientRegistered ? {
        client_id: "test-client-id",
        client_secret: "test-client-secret"
      } : undefined;

      return {
        get redirectUrl() { return "http://localhost/callback"; },
        get clientMetadata() { 
          return { 
            redirect_uris: ["http://localhost/callback"],
            client_name: "Test Client"
          }; 
        },
        clientInformation: jest.fn().mockResolvedValue(clientInfo),
        tokens: jest.fn().mockResolvedValue(tokens),
        saveTokens: jest.fn(),
        redirectToAuthorization: jest.fn(),
        saveCodeVerifier: jest.fn(),
        codeVerifier: jest.fn().mockResolvedValue("test-verifier"),
        invalidateCredentials: jest.fn(),
      };
    };

    const createCustomFetchMockAuthServer = async () => {
      authServer = createServer((req, res) => {
        if (req.url === "/.well-known/oauth-authorization-server") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            issuer: `http://127.0.0.1:${(authServer.address() as AddressInfo).port}`,
            authorization_endpoint: `http://127.0.0.1:${(authServer.address() as AddressInfo).port}/authorize`,
            token_endpoint: `http://127.0.0.1:${(authServer.address() as AddressInfo).port}/token`,
            registration_endpoint: `http://127.0.0.1:${(authServer.address() as AddressInfo).port}/register`,
            response_types_supported: ["code"],
            code_challenge_methods_supported: ["S256"],
          }));
          return;
        }
  
        if (req.url === "/token" && req.method === "POST") {
          // Handle token exchange request
          let body = "";
          req.on("data", chunk => { body += chunk; });
          req.on("end", () => {
            const params = new URLSearchParams(body);
            if (params.get("grant_type") === "authorization_code" &&
                params.get("code") === "test-auth-code" &&
                params.get("client_id") === "test-client-id") {
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({
                access_token: "new-access-token",
                token_type: "Bearer",
                expires_in: 3600,
                refresh_token: "new-refresh-token"
              }));
            } else {
              res.writeHead(400).end();
            }
          });
          return;
        }
  
        res.writeHead(404).end();
      });

      // Start auth server on random port
      await new Promise<void>(resolve => {
        authServer.listen(0, "127.0.0.1", () => {
          const addr = authServer.address() as AddressInfo;
          authBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });
    };

    const createCustomFetchMockResourceServer = async () => {
      // Set up resource server that provides OAuth metadata
      resourceServer = createServer((req, res) => {
        lastServerRequest = req;

        if (req.url === "/.well-known/oauth-protected-resource") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({
            resource: resourceBaseUrl.href,
            authorization_servers: [authBaseUrl.href],
          }));
          return;
        }

        resourceServerHandler(req, res);
      });

      // Start resource server on random port
      await new Promise<void>(resolve => {
        resourceServer.listen(0, "127.0.0.1", () => {
          const addr = resourceServer.address() as AddressInfo;
          resourceBaseUrl = new URL(`http://127.0.0.1:${addr.port}`);
          resolve();
        });
      });
    };

    beforeEach(async () => {
      // Close existing servers to set up custom auth flow servers
      resourceServer.close();
      authServer.close();

      const originalFetch = fetch;

      // Create custom fetch spy that delegates to real fetch
      customFetch = jest.fn((url, init) => {
        return originalFetch(url.toString(), init);
      });

      // Spy on global fetch to detect unauthorized usage
      globalFetchSpy = jest.spyOn(global, 'fetch');

      // Create mock auth provider with default configuration
      mockAuthProvider = createMockAuthProvider({
        hasTokens: false,
        clientRegistered: true
      });

      // Set up auth server that handles OAuth discovery and token requests
      await createCustomFetchMockAuthServer();

      // Set up resource server
      resourceServerHandler = jest.fn((_req: IncomingMessage, res: ServerResponse<IncomingMessage> & {
        req: IncomingMessage;
      }) => {
        res.writeHead(404).end();
      });
      await createCustomFetchMockResourceServer();
    });

    afterEach(() => {
      globalFetchSpy.mockRestore();
    });

    it("uses custom fetch during auth flow on SSE connection 401 - no global fetch fallback", async () => {
      // Set up resource server that returns 401 on SSE connection and provides OAuth metadata
      resourceServerHandler.mockImplementation((req, res) => {
        if (req.url === "/") {
          // Return 401 to trigger auth flow
          res.writeHead(401, {
            "WWW-Authenticate": `Bearer realm="mcp", resource_metadata="${resourceBaseUrl.href}.well-known/oauth-protected-resource"`
          });
          res.end();
          return;
        }

        res.writeHead(404).end();
      });

      // Create transport with custom fetch and auth provider
      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
        fetch: customFetch,
      });

      // Attempt to start - should trigger auth flow and eventually fail with UnauthorizedError
      await expect(transport.start()).rejects.toThrow(UnauthorizedError);

      // Verify custom fetch was used
      expect(customFetch).toHaveBeenCalled();
      
      // Verify specific OAuth endpoints were called with custom fetch
      const customFetchCalls = customFetch.mock.calls;
      const callUrls = customFetchCalls.map(([url]) => url.toString());
      
      // Should have called resource metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-protected-resource'))).toBe(true);
      
      // Should have called OAuth authorization server metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-authorization-server'))).toBe(true);

      // Verify auth provider was called to redirect to authorization
      expect(mockAuthProvider.redirectToAuthorization).toHaveBeenCalled();

      // Global fetch should never have been called
      expect(globalFetchSpy).not.toHaveBeenCalled();
    });

    it("uses custom fetch during auth flow on POST request 401 - no global fetch fallback", async () => {
      // Set up resource server that accepts SSE connection but returns 401 on POST
      resourceServerHandler.mockImplementation((req, res) => {
        switch (req.method) {
          case "GET":
            if (req.url === "/") {
              // Accept SSE connection
              res.writeHead(200, {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache, no-transform",
                Connection: "keep-alive",
              });
              res.write("event: endpoint\n");
              res.write(`data: ${resourceBaseUrl.href}\n\n`);
              return;
            }
            break;

          case "POST":
            if (req.url === "/") {
              // Return 401 to trigger auth retry
              res.writeHead(401, {
                "WWW-Authenticate": `Bearer realm="mcp", resource_metadata="${resourceBaseUrl.href}.well-known/oauth-protected-resource"`
              });
              res.end();
              return;
            }
            break;
        }

        res.writeHead(404).end();
      });

      // Create transport with custom fetch and auth provider
      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: mockAuthProvider,
        fetch: customFetch,
      });

      // Start the transport (should succeed)
      await transport.start();

      // Send a message that should trigger 401 and auth retry
      const message: JSONRPCMessage = {
        jsonrpc: "2.0",
        id: "1",
        method: "test",
        params: {},
      };

      // Attempt to send message - should trigger auth flow and eventually fail
      await expect(transport.send(message)).rejects.toThrow(UnauthorizedError);

      // Verify custom fetch was used
      expect(customFetch).toHaveBeenCalled();
      
      // Verify specific OAuth endpoints were called with custom fetch
      const customFetchCalls = customFetch.mock.calls;
      const callUrls = customFetchCalls.map(([url]) => url.toString());
      
      // Should have called resource metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-protected-resource'))).toBe(true);
      
      // Should have called OAuth authorization server metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-authorization-server'))).toBe(true);

      // Should have attempted the POST request that triggered the 401
      const postCalls = customFetchCalls.filter(([url, options]) => 
        url.toString() === resourceBaseUrl.href && options?.method === "POST"
      );
      expect(postCalls.length).toBeGreaterThan(0);

      // Verify auth provider was called to redirect to authorization
      expect(mockAuthProvider.redirectToAuthorization).toHaveBeenCalled();

      // Global fetch should never have been called
      expect(globalFetchSpy).not.toHaveBeenCalled();
    });

    it("uses custom fetch in finishAuth method - no global fetch fallback", async () => {
      // Create mock auth provider that expects to save tokens
      const authProviderWithCode = createMockAuthProvider({
        clientRegistered: true,
        authorizationCode: "test-auth-code"
      });

      // Create transport with custom fetch and auth provider
      transport = new SSEClientTransport(resourceBaseUrl, {
        authProvider: authProviderWithCode,
        fetch: customFetch,
      });

      // Call finishAuth with authorization code
      await transport.finishAuth("test-auth-code");

      // Verify custom fetch was used
      expect(customFetch).toHaveBeenCalled();
      
      // Verify specific OAuth endpoints were called with custom fetch
      const customFetchCalls = customFetch.mock.calls;
      const callUrls = customFetchCalls.map(([url]) => url.toString());
      
      // Should have called resource metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-protected-resource'))).toBe(true);
      
      // Should have called OAuth authorization server metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-authorization-server'))).toBe(true);

      // Should have called token endpoint for authorization code exchange
      const tokenCalls = customFetchCalls.filter(([url, options]) => 
        url.toString().includes('/token') && options?.method === "POST"
      );
      expect(tokenCalls.length).toBeGreaterThan(0);

      // Verify tokens were saved
      expect(authProviderWithCode.saveTokens).toHaveBeenCalledWith({
        access_token: "new-access-token",
        token_type: "Bearer",
        expires_in: 3600,
        refresh_token: "new-refresh-token"
      });

      // Global fetch should never have been called
      expect(globalFetchSpy).not.toHaveBeenCalled();
    });
  });
});



================================================
FILE: src/client/sse.ts
================================================
import { EventSource, type ErrorEvent, type EventSourceInit } from "eventsource";
import { Transport, FetchLike } from "../shared/transport.js";
import { JSONRPCMessage, JSONRPCMessageSchema } from "../types.js";
import { auth, AuthResult, extractResourceMetadataUrl, OAuthClientProvider, UnauthorizedError } from "./auth.js";

export class SseError extends Error {
  constructor(
    public readonly code: number | undefined,
    message: string | undefined,
    public readonly event: ErrorEvent,
  ) {
    super(`SSE error: ${message}`);
  }
}

/**
 * Configuration options for the `SSEClientTransport`.
 */
export type SSEClientTransportOptions = {
  /**
   * An OAuth client provider to use for authentication.
   *
   * When an `authProvider` is specified and the SSE connection is started:
   * 1. The connection is attempted with any existing access token from the `authProvider`.
   * 2. If the access token has expired, the `authProvider` is used to refresh the token.
   * 3. If token refresh fails or no access token exists, and auth is required, `OAuthClientProvider.redirectToAuthorization` is called, and an `UnauthorizedError` will be thrown from `connect`/`start`.
   *
   * After the user has finished authorizing via their user agent, and is redirected back to the MCP client application, call `SSEClientTransport.finishAuth` with the authorization code before retrying the connection.
   *
   * If an `authProvider` is not provided, and auth is required, an `UnauthorizedError` will be thrown.
   *
   * `UnauthorizedError` might also be thrown when sending any message over the SSE transport, indicating that the session has expired, and needs to be re-authed and reconnected.
   */
  authProvider?: OAuthClientProvider;

  /**
   * Customizes the initial SSE request to the server (the request that begins the stream).
   *
   * NOTE: Setting this property will prevent an `Authorization` header from
   * being automatically attached to the SSE request, if an `authProvider` is
   * also given. This can be worked around by setting the `Authorization` header
   * manually.
   */
  eventSourceInit?: EventSourceInit;

  /**
   * Customizes recurring POST requests to the server.
   */
  requestInit?: RequestInit;

  /**
   * Custom fetch implementation used for all network requests.
   */
  fetch?: FetchLike;
};

/**
 * Client transport for SSE: this will connect to a server using Server-Sent Events for receiving
 * messages and make separate POST requests for sending messages.
 */
export class SSEClientTransport implements Transport {
  private _eventSource?: EventSource;
  private _endpoint?: URL;
  private _abortController?: AbortController;
  private _url: URL;
  private _resourceMetadataUrl?: URL;
  private _eventSourceInit?: EventSourceInit;
  private _requestInit?: RequestInit;
  private _authProvider?: OAuthClientProvider;
  private _fetch?: FetchLike;
  private _protocolVersion?: string;

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;

  constructor(
    url: URL,
    opts?: SSEClientTransportOptions,
  ) {
    this._url = url;
    this._resourceMetadataUrl = undefined;
    this._eventSourceInit = opts?.eventSourceInit;
    this._requestInit = opts?.requestInit;
    this._authProvider = opts?.authProvider;
    this._fetch = opts?.fetch;
  }

  private async _authThenStart(): Promise<void> {
    if (!this._authProvider) {
      throw new UnauthorizedError("No auth provider");
    }

    let result: AuthResult;
    try {
      result = await auth(this._authProvider, { serverUrl: this._url, resourceMetadataUrl: this._resourceMetadataUrl, fetchFn: this._fetch });
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }

    if (result !== "AUTHORIZED") {
      throw new UnauthorizedError();
    }

    return await this._startOrAuth();
  }

  private async _commonHeaders(): Promise<Headers> {
    const headers: HeadersInit = {};
    if (this._authProvider) {
      const tokens = await this._authProvider.tokens();
      if (tokens) {
        headers["Authorization"] = `Bearer ${tokens.access_token}`;
      }
    }
    if (this._protocolVersion) {
      headers["mcp-protocol-version"] = this._protocolVersion;
    }

    return new Headers(
      { ...headers, ...this._requestInit?.headers }
    );
  }

  private _startOrAuth(): Promise<void> {
    const fetchImpl = (this?._eventSourceInit?.fetch ?? this._fetch ?? fetch) as typeof fetch
    return new Promise((resolve, reject) => {
      this._eventSource = new EventSource(
        this._url.href,
        {
          ...this._eventSourceInit,
          fetch: async (url, init) => {
            const headers = await this._commonHeaders();
            headers.set("Accept", "text/event-stream");
            const response = await fetchImpl(url, {
              ...init,
              headers,
            })

            if (response.status === 401 && response.headers.has('www-authenticate')) {
              this._resourceMetadataUrl = extractResourceMetadataUrl(response);
            }

            return response
          },
        },
      );
      this._abortController = new AbortController();

      this._eventSource.onerror = (event) => {
        if (event.code === 401 && this._authProvider) {

          this._authThenStart().then(resolve, reject);
          return;
        }

        const error = new SseError(event.code, event.message, event);
        reject(error);
        this.onerror?.(error);
      };

      this._eventSource.onopen = () => {
        // The connection is open, but we need to wait for the endpoint to be received.
      };

      this._eventSource.addEventListener("endpoint", (event: Event) => {
        const messageEvent = event as MessageEvent;

        try {
          this._endpoint = new URL(messageEvent.data, this._url);
          if (this._endpoint.origin !== this._url.origin) {
            throw new Error(
              `Endpoint origin does not match connection origin: ${this._endpoint.origin}`,
            );
          }
        } catch (error) {
          reject(error);
          this.onerror?.(error as Error);

          void this.close();
          return;
        }

        resolve();
      });

      this._eventSource.onmessage = (event: Event) => {
        const messageEvent = event as MessageEvent;
        let message: JSONRPCMessage;
        try {
          message = JSONRPCMessageSchema.parse(JSON.parse(messageEvent.data));
        } catch (error) {
          this.onerror?.(error as Error);
          return;
        }

        this.onmessage?.(message);
      };
    });
  }

  async start() {
    if (this._eventSource) {
      throw new Error(
        "SSEClientTransport already started! If using Client class, note that connect() calls start() automatically.",
      );
    }

    return await this._startOrAuth();
  }

  /**
   * Call this method after the user has finished authorizing via their user agent and is redirected back to the MCP client application. This will exchange the authorization code for an access token, enabling the next connection attempt to successfully auth.
   */
  async finishAuth(authorizationCode: string): Promise<void> {
    if (!this._authProvider) {
      throw new UnauthorizedError("No auth provider");
    }

    const result = await auth(this._authProvider, { serverUrl: this._url, authorizationCode, resourceMetadataUrl: this._resourceMetadataUrl, fetchFn: this._fetch });
    if (result !== "AUTHORIZED") {
      throw new UnauthorizedError("Failed to authorize");
    }
  }

  async close(): Promise<void> {
    this._abortController?.abort();
    this._eventSource?.close();
    this.onclose?.();
  }

  async send(message: JSONRPCMessage): Promise<void> {
    if (!this._endpoint) {
      throw new Error("Not connected");
    }

    try {
      const headers = await this._commonHeaders();
      headers.set("content-type", "application/json");
      const init = {
        ...this._requestInit,
        method: "POST",
        headers,
        body: JSON.stringify(message),
        signal: this._abortController?.signal,
      };

      const response = await (this._fetch ?? fetch)(this._endpoint, init);
      if (!response.ok) {
        if (response.status === 401 && this._authProvider) {

          this._resourceMetadataUrl = extractResourceMetadataUrl(response);

          const result = await auth(this._authProvider, { serverUrl: this._url, resourceMetadataUrl: this._resourceMetadataUrl, fetchFn: this._fetch });
          if (result !== "AUTHORIZED") {
            throw new UnauthorizedError();
          }

          // Purposely _not_ awaited, so we don't call onerror twice
          return this.send(message);
        }

        const text = await response.text().catch(() => null);
        throw new Error(
          `Error POSTing to endpoint (HTTP ${response.status}): ${text}`,
        );
      }
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }
  }

  setProtocolVersion(version: string): void {
    this._protocolVersion = version;
  }
}



================================================
FILE: src/client/stdio.test.ts
================================================
import { JSONRPCMessage } from "../types.js";
import { StdioClientTransport, StdioServerParameters } from "./stdio.js";

// Configure default server parameters based on OS
// Uses 'more' command for Windows and 'tee' command for Unix/Linux
const getDefaultServerParameters = (): StdioServerParameters => {
  if (process.platform === "win32") {
    return { command: "more" };
  }
  return { command: "/usr/bin/tee" };
};

const serverParameters = getDefaultServerParameters();

test("should start then close cleanly", async () => {
  const client = new StdioClientTransport(serverParameters);
  client.onerror = (error) => {
    throw error;
  };

  let didClose = false;
  client.onclose = () => {
    didClose = true;
  };

  await client.start();
  expect(didClose).toBeFalsy();
  await client.close();
  expect(didClose).toBeTruthy();
});

test("should read messages", async () => {
  const client = new StdioClientTransport(serverParameters);
  client.onerror = (error) => {
    throw error;
  };

  const messages: JSONRPCMessage[] = [
    {
      jsonrpc: "2.0",
      id: 1,
      method: "ping",
    },
    {
      jsonrpc: "2.0",
      method: "notifications/initialized",
    },
  ];

  const readMessages: JSONRPCMessage[] = [];
  const finished = new Promise<void>((resolve) => {
    client.onmessage = (message) => {
      readMessages.push(message);

      if (JSON.stringify(message) === JSON.stringify(messages[1])) {
        resolve();
      }
    };
  });

  await client.start();
  await client.send(messages[0]);
  await client.send(messages[1]);
  await finished;
  expect(readMessages).toEqual(messages);

  await client.close();
});

test("should return child process pid", async () => {
  const client = new StdioClientTransport(serverParameters);

  await client.start();
  expect(client.pid).not.toBeNull();
  await client.close();
  expect(client.pid).toBeNull();
});



================================================
FILE: src/client/stdio.ts
================================================
import { ChildProcess, IOType } from "node:child_process";
import spawn from "cross-spawn";
import process from "node:process";
import { Stream, PassThrough } from "node:stream";
import { ReadBuffer, serializeMessage } from "../shared/stdio.js";
import { Transport } from "../shared/transport.js";
import { JSONRPCMessage } from "../types.js";

export type StdioServerParameters = {
  /**
   * The executable to run to start the server.
   */
  command: string;

  /**
   * Command line arguments to pass to the executable.
   */
  args?: string[];

  /**
   * The environment to use when spawning the process.
   *
   * If not specified, the result of getDefaultEnvironment() will be used.
   */
  env?: Record<string, string>;

  /**
   * How to handle stderr of the child process. This matches the semantics of Node's `child_process.spawn`.
   *
   * The default is "inherit", meaning messages to stderr will be printed to the parent process's stderr.
   */
  stderr?: IOType | Stream | number;

  /**
   * The working directory to use when spawning the process.
   *
   * If not specified, the current working directory will be inherited.
   */
  cwd?: string;
};

/**
 * Environment variables to inherit by default, if an environment is not explicitly given.
 */
export const DEFAULT_INHERITED_ENV_VARS =
  process.platform === "win32"
    ? [
        "APPDATA",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "PATH",
        "PROCESSOR_ARCHITECTURE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "USERNAME",
        "USERPROFILE",
        "PROGRAMFILES",
      ]
    : /* list inspired by the default env inheritance of sudo */
      ["HOME", "LOGNAME", "PATH", "SHELL", "TERM", "USER"];

/**
 * Returns a default environment object including only environment variables deemed safe to inherit.
 */
export function getDefaultEnvironment(): Record<string, string> {
  const env: Record<string, string> = {};

  for (const key of DEFAULT_INHERITED_ENV_VARS) {
    const value = process.env[key];
    if (value === undefined) {
      continue;
    }

    if (value.startsWith("()")) {
      // Skip functions, which are a security risk.
      continue;
    }

    env[key] = value;
  }

  return env;
}

/**
 * Client transport for stdio: this will connect to a server by spawning a process and communicating with it over stdin/stdout.
 *
 * This transport is only available in Node.js environments.
 */
export class StdioClientTransport implements Transport {
  private _process?: ChildProcess;
  private _abortController: AbortController = new AbortController();
  private _readBuffer: ReadBuffer = new ReadBuffer();
  private _serverParams: StdioServerParameters;
  private _stderrStream: PassThrough | null = null;

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;

  constructor(server: StdioServerParameters) {
    this._serverParams = server;
    if (server.stderr === "pipe" || server.stderr === "overlapped") {
      this._stderrStream = new PassThrough();
    }
  }

  /**
   * Starts the server process and prepares to communicate with it.
   */
  async start(): Promise<void> {
    if (this._process) {
      throw new Error(
        "StdioClientTransport already started! If using Client class, note that connect() calls start() automatically."
      );
    }

    return new Promise((resolve, reject) => {
      this._process = spawn(
        this._serverParams.command,
        this._serverParams.args ?? [],
        {
          // merge default env with server env because mcp server needs some env vars
          env: {
            ...getDefaultEnvironment(),
            ...this._serverParams.env,
          },
          stdio: ["pipe", "pipe", this._serverParams.stderr ?? "inherit"],
          shell: false,
          signal: this._abortController.signal,
          windowsHide: process.platform === "win32" && isElectron(),
          cwd: this._serverParams.cwd,
        }
      );

      this._process.on("error", (error) => {
        if (error.name === "AbortError") {
          // Expected when close() is called.
          this.onclose?.();
          return;
        }

        reject(error);
        this.onerror?.(error);
      });

      this._process.on("spawn", () => {
        resolve();
      });

      this._process.on("close", (_code) => {
        this._process = undefined;
        this.onclose?.();
      });

      this._process.stdin?.on("error", (error) => {
        this.onerror?.(error);
      });

      this._process.stdout?.on("data", (chunk) => {
        this._readBuffer.append(chunk);
        this.processReadBuffer();
      });

      this._process.stdout?.on("error", (error) => {
        this.onerror?.(error);
      });

      if (this._stderrStream && this._process.stderr) {
        this._process.stderr.pipe(this._stderrStream);
      }
    });
  }

  /**
   * The stderr stream of the child process, if `StdioServerParameters.stderr` was set to "pipe" or "overlapped".
   *
   * If stderr piping was requested, a PassThrough stream is returned _immediately_, allowing callers to
   * attach listeners before the start method is invoked. This prevents loss of any early
   * error output emitted by the child process.
   */
  get stderr(): Stream | null {
    if (this._stderrStream) {
      return this._stderrStream;
    }

    return this._process?.stderr ?? null;
  }

  /**
   * The child process pid spawned by this transport.
   *
   * This is only available after the transport has been started.
   */
  get pid(): number | null {
    return this._process?.pid ?? null;
  }

  private processReadBuffer() {
    while (true) {
      try {
        const message = this._readBuffer.readMessage();
        if (message === null) {
          break;
        }

        this.onmessage?.(message);
      } catch (error) {
        this.onerror?.(error as Error);
      }
    }
  }

  async close(): Promise<void> {
    this._abortController.abort();
    this._process = undefined;
    this._readBuffer.clear();
  }

  send(message: JSONRPCMessage): Promise<void> {
    return new Promise((resolve) => {
      if (!this._process?.stdin) {
        throw new Error("Not connected");
      }

      const json = serializeMessage(message);
      if (this._process.stdin.write(json)) {
        resolve();
      } else {
        this._process.stdin.once("drain", resolve);
      }
    });
  }
}

function isElectron() {
  return "type" in process;
}



================================================
FILE: src/client/streamableHttp.test.ts
================================================
import { StartSSEOptions, StreamableHTTPClientTransport, StreamableHTTPReconnectionOptions } from "./streamableHttp.js";
import { OAuthClientProvider, UnauthorizedError } from "./auth.js";
import { JSONRPCMessage, JSONRPCRequest } from "../types.js";
import { InvalidClientError, InvalidGrantError, UnauthorizedClientError } from "../server/auth/errors.js";


describe("StreamableHTTPClientTransport", () => {
  let transport: StreamableHTTPClientTransport;
  let mockAuthProvider: jest.Mocked<OAuthClientProvider>;

  beforeEach(() => {
    mockAuthProvider = {
      get redirectUrl() { return "http://localhost/callback"; },
      get clientMetadata() { return { redirect_uris: ["http://localhost/callback"] }; },
      clientInformation: jest.fn(() => ({ client_id: "test-client-id", client_secret: "test-client-secret" })),
      tokens: jest.fn(),
      saveTokens: jest.fn(),
      redirectToAuthorization: jest.fn(),
      saveCodeVerifier: jest.fn(),
      codeVerifier: jest.fn(),
      invalidateCredentials: jest.fn(),
    };
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), { authProvider: mockAuthProvider });
    jest.spyOn(global, "fetch");
  });

  afterEach(async () => {
    await transport.close().catch(() => { });
    jest.clearAllMocks();
  });

  it("should send JSON-RPC messages via POST", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 202,
      headers: new Headers(),
    });

    await transport.send(message);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers),
        body: JSON.stringify(message)
      })
    );
  });

  it("should send batch messages", async () => {
    const messages: JSONRPCMessage[] = [
      { jsonrpc: "2.0", method: "test1", params: {}, id: "id1" },
      { jsonrpc: "2.0", method: "test2", params: {}, id: "id2" }
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: null
    });

    await transport.send(messages);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers),
        body: JSON.stringify(messages)
      })
    );
  });

  it("should store session ID received during initialization", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "initialize",
      params: {
        clientInfo: { name: "test-client", version: "1.0" },
        protocolVersion: "2025-03-26"
      },
      id: "init-id"
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream", "mcp-session-id": "test-session-id" }),
    });

    await transport.send(message);

    // Send a second message that should include the session ID
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 202,
      headers: new Headers()
    });

    await transport.send({ jsonrpc: "2.0", method: "test", params: {} } as JSONRPCMessage);

    // Check that second request included session ID header
    const calls = (global.fetch as jest.Mock).mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall[1].headers).toBeDefined();
    expect(lastCall[1].headers.get("mcp-session-id")).toBe("test-session-id");
  });

  it("should terminate session with DELETE request", async () => {
    // First, simulate getting a session ID
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "initialize",
      params: {
        clientInfo: { name: "test-client", version: "1.0" },
        protocolVersion: "2025-03-26"
      },
      id: "init-id"
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream", "mcp-session-id": "test-session-id" }),
    });

    await transport.send(message);
    expect(transport.sessionId).toBe("test-session-id");

    // Now terminate the session
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers()
    });

    await transport.terminateSession();

    // Verify the DELETE request was sent with the session ID
    const calls = (global.fetch as jest.Mock).mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall[1].method).toBe("DELETE");
    expect(lastCall[1].headers.get("mcp-session-id")).toBe("test-session-id");

    // The session ID should be cleared after successful termination
    expect(transport.sessionId).toBeUndefined();
  });

  it("should handle 405 response when server doesn't support session termination", async () => {
    // First, simulate getting a session ID
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "initialize",
      params: {
        clientInfo: { name: "test-client", version: "1.0" },
        protocolVersion: "2025-03-26"
      },
      id: "init-id"
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream", "mcp-session-id": "test-session-id" }),
    });

    await transport.send(message);

    // Now terminate the session, but server responds with 405
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 405,
      statusText: "Method Not Allowed",
      headers: new Headers()
    });

    await expect(transport.terminateSession()).resolves.not.toThrow();
  });

  it("should handle 404 response when session expires", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      text: () => Promise.resolve("Session not found"),
      headers: new Headers()
    });

    const errorSpy = jest.fn();
    transport.onerror = errorSpy;

    await expect(transport.send(message)).rejects.toThrow("Error POSTing to endpoint (HTTP 404)");
    expect(errorSpy).toHaveBeenCalled();
  });

  it("should handle non-streaming JSON response", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    const responseMessage: JSONRPCMessage = {
      jsonrpc: "2.0",
      result: { success: true },
      id: "test-id"
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve(responseMessage)
    });

    const messageSpy = jest.fn();
    transport.onmessage = messageSpy;

    await transport.send(message);

    expect(messageSpy).toHaveBeenCalledWith(responseMessage);
  });

  it("should attempt initial GET connection and handle 405 gracefully", async () => {
    // Mock the server not supporting GET for SSE (returning 405)
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 405,
      statusText: "Method Not Allowed"
    });

    // We expect the 405 error to be caught and handled gracefully
    // This should not throw an error that breaks the transport
    await transport.start();
    await expect(transport["_startOrAuthSse"]({})).resolves.not.toThrow("Failed to open SSE stream: Method Not Allowed");
    // Check that GET was attempted
    expect(global.fetch).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        method: "GET",
        headers: expect.any(Headers)
      })
    );

    // Verify transport still works after 405
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 202,
      headers: new Headers()
    });

    await transport.send({ jsonrpc: "2.0", method: "test", params: {} } as JSONRPCMessage);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it("should handle successful initial GET connection for SSE", async () => {
    // Set up readable stream for SSE events
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        // Send a server notification via SSE
        const event = "event: message\ndata: {\"jsonrpc\": \"2.0\", \"method\": \"serverNotification\", \"params\": {}}\n\n";
        controller.enqueue(encoder.encode(event));
      }
    });

    // Mock successful GET connection
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: stream
    });

    const messageSpy = jest.fn();
    transport.onmessage = messageSpy;

    await transport.start();
    await transport["_startOrAuthSse"]({});

    // Give time for the SSE event to be processed
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(messageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        jsonrpc: "2.0",
        method: "serverNotification",
        params: {}
      })
    );
  });

  it("should handle multiple concurrent SSE streams", async () => {
    // Mock two POST requests that return SSE streams
    const makeStream = (id: string) => {
      const encoder = new TextEncoder();
      return new ReadableStream({
        start(controller) {
          const event = `event: message\ndata: {"jsonrpc": "2.0", "result": {"id": "${id}"}, "id": "${id}"}\n\n`;
          controller.enqueue(encoder.encode(event));
        }
      });
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "text/event-stream" }),
        body: makeStream("request1")
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "text/event-stream" }),
        body: makeStream("request2")
      });

    const messageSpy = jest.fn();
    transport.onmessage = messageSpy;

    // Send two concurrent requests
    await Promise.all([
      transport.send({ jsonrpc: "2.0", method: "test1", params: {}, id: "request1" }),
      transport.send({ jsonrpc: "2.0", method: "test2", params: {}, id: "request2" })
    ]);

    // Give time for SSE processing
    await new Promise(resolve => setTimeout(resolve, 100));

    // Both streams should have delivered their messages
    expect(messageSpy).toHaveBeenCalledTimes(2);

    // Verify received messages without assuming specific order
    expect(messageSpy.mock.calls.some(call => {
      const msg = call[0];
      return msg.id === "request1" && msg.result?.id === "request1";
    })).toBe(true);

    expect(messageSpy.mock.calls.some(call => {
      const msg = call[0];
      return msg.id === "request2" && msg.result?.id === "request2";
    })).toBe(true);
  });

  it("should support custom reconnection options", () => {
    // Create a transport with custom reconnection options
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
      reconnectionOptions: {
        initialReconnectionDelay: 500,
        maxReconnectionDelay: 10000,
        reconnectionDelayGrowFactor: 2,
        maxRetries: 5,
      }
    });

    // Verify options were set correctly (checking implementation details)
    // Access private properties for testing
    const transportInstance = transport as unknown as {
      _reconnectionOptions: StreamableHTTPReconnectionOptions;
    };
    expect(transportInstance._reconnectionOptions.initialReconnectionDelay).toBe(500);
    expect(transportInstance._reconnectionOptions.maxRetries).toBe(5);
  });

  it("should pass lastEventId when reconnecting", async () => {
    // Create a fresh transport
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"));

    // Mock fetch to verify headers sent
    const fetchSpy = global.fetch as jest.Mock;
    fetchSpy.mockReset();
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: new ReadableStream()
    });

    // Call the reconnect method directly with a lastEventId
    await transport.start();
    // Type assertion to access private method
    const transportWithPrivateMethods = transport as unknown as {
      _startOrAuthSse: (options: { resumptionToken?: string }) => Promise<void>
    };
    await transportWithPrivateMethods._startOrAuthSse({ resumptionToken: "test-event-id" });

    // Verify fetch was called with the lastEventId header
    expect(fetchSpy).toHaveBeenCalled();
    const fetchCall = fetchSpy.mock.calls[0];
    const headers = fetchCall[1].headers;
    expect(headers.get("last-event-id")).toBe("test-event-id");
  });

  it("should throw error when invalid content-type is received", async () => {
    // Clear any previous state from other tests
    jest.clearAllMocks();

    // Create a fresh transport instance
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"));

    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("invalid text response"));
        controller.close();
      }
    });

    const errorSpy = jest.fn();
    transport.onerror = errorSpy;

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/plain" }),
      body: stream
    });

    await transport.start();
    await expect(transport.send(message)).rejects.toThrow("Unexpected content type: text/plain");
    expect(errorSpy).toHaveBeenCalled();
  });

  it("uses custom fetch implementation if provided", async () => {
    // Create custom fetch
    const customFetch = jest.fn()
      .mockResolvedValueOnce(
        new Response(null, { status: 200, headers: { "content-type": "text/event-stream" } })
      )
      .mockResolvedValueOnce(new Response(null, { status: 202 }));

    // Create transport instance
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
      fetch: customFetch
    });

    await transport.start();
    await (transport as unknown as { _startOrAuthSse: (opts: StartSSEOptions) => Promise<void> })._startOrAuthSse({});

    await transport.send({ jsonrpc: "2.0", method: "test", params: {}, id: "1" } as JSONRPCMessage);

    // Verify custom fetch was used
    expect(customFetch).toHaveBeenCalled();

    // Global fetch should never have been called
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("should always send specified custom headers", async () => {
    const requestInit = {
      headers: {
        "X-Custom-Header": "CustomValue"
      }
    };
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
      requestInit: requestInit
    });

    let actualReqInit: RequestInit = {};

    ((global.fetch as jest.Mock)).mockImplementation(
      async (_url, reqInit) => {
        actualReqInit = reqInit;
        return new Response(null, { status: 200, headers: { "content-type": "text/event-stream" } });
      }
    );

    await transport.start();

    await transport["_startOrAuthSse"]({});
    expect((actualReqInit.headers as Headers).get("x-custom-header")).toBe("CustomValue");

    requestInit.headers["X-Custom-Header"] = "SecondCustomValue";

    await transport.send({ jsonrpc: "2.0", method: "test", params: {} } as JSONRPCMessage);
    expect((actualReqInit.headers as Headers).get("x-custom-header")).toBe("SecondCustomValue");

    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it("should always send specified custom headers (Headers class)", async () => {
    const requestInit = {
      headers: new Headers({
        "X-Custom-Header": "CustomValue"
      })
    };
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
      requestInit: requestInit
    });

    let actualReqInit: RequestInit = {};

    ((global.fetch as jest.Mock)).mockImplementation(
      async (_url, reqInit) => {
        actualReqInit = reqInit;
        return new Response(null, { status: 200, headers: { "content-type": "text/event-stream" } });
      }
    );

    await transport.start();

    await transport["_startOrAuthSse"]({});
    expect((actualReqInit.headers as Headers).get("x-custom-header")).toBe("CustomValue");

    (requestInit.headers as Headers).set("X-Custom-Header","SecondCustomValue");

    await transport.send({ jsonrpc: "2.0", method: "test", params: {} } as JSONRPCMessage);
    expect((actualReqInit.headers as Headers).get("x-custom-header")).toBe("SecondCustomValue");

    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it("should have exponential backoff with configurable maxRetries", () => {
    // This test verifies the maxRetries and backoff calculation directly

    // Create transport with specific options for testing
    transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
      reconnectionOptions: {
        initialReconnectionDelay: 100,
        maxReconnectionDelay: 5000,
        reconnectionDelayGrowFactor: 2,
        maxRetries: 3,
      }
    });

    // Get access to the internal implementation
    const getDelay = transport["_getNextReconnectionDelay"].bind(transport);

    // First retry - should use initial delay
    expect(getDelay(0)).toBe(100);

    // Second retry - should double (2^1 * 100 = 200)
    expect(getDelay(1)).toBe(200);

    // Third retry - should double again (2^2 * 100 = 400)
    expect(getDelay(2)).toBe(400);

    // Fourth retry - should double again (2^3 * 100 = 800)
    expect(getDelay(3)).toBe(800);

    // Tenth retry - should be capped at maxReconnectionDelay
    expect(getDelay(10)).toBe(5000);
  });

  it("attempts auth flow on 401 during POST request", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        headers: new Headers()
      })
      .mockResolvedValue({
        ok: false,
        status: 404
      });

    await expect(transport.send(message)).rejects.toThrow(UnauthorizedError);
    expect(mockAuthProvider.redirectToAuthorization.mock.calls).toHaveLength(1);
  });

  describe('Reconnection Logic', () => {
    let transport: StreamableHTTPClientTransport;

    // Use fake timers to control setTimeout and make the test instant.
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    it('should reconnect a GET-initiated notification stream that fails', async () => {
      // ARRANGE
      transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
        reconnectionOptions: {
          initialReconnectionDelay: 10,
          maxRetries: 1,
          maxReconnectionDelay: 1000,  // Ensure it doesn't retry indefinitely
          reconnectionDelayGrowFactor: 1  // No exponential backoff for simplicity
         }
      });

      const errorSpy = jest.fn();
      transport.onerror = errorSpy;

      const failingStream = new ReadableStream({
        start(controller) { controller.error(new Error("Network failure")); }
      });

      const fetchMock = global.fetch as jest.Mock;
      // Mock the initial GET request, which will fail.
      fetchMock.mockResolvedValueOnce({
        ok: true, status: 200,
        headers: new Headers({ "content-type": "text/event-stream" }),
        body: failingStream,
      });
      // Mock the reconnection GET request, which will succeed.
      fetchMock.mockResolvedValueOnce({
        ok: true, status: 200,
        headers: new Headers({ "content-type": "text/event-stream" }),
        body: new ReadableStream(),
      });

      // ACT
      await transport.start();
      // Trigger the GET stream directly using the internal method for a clean test.
      await transport["_startOrAuthSse"]({});
      await jest.advanceTimersByTimeAsync(20); // Trigger reconnection timeout

      // ASSERT
      expect(errorSpy).toHaveBeenCalledWith(expect.objectContaining({
        message: expect.stringContaining('SSE stream disconnected: Error: Network failure'),
      }));
      // THE KEY ASSERTION: A second fetch call proves reconnection was attempted.
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(fetchMock.mock.calls[0][1]?.method).toBe('GET');
      expect(fetchMock.mock.calls[1][1]?.method).toBe('GET');
    });

    it('should NOT reconnect a POST-initiated stream that fails', async () => {
      // ARRANGE
      transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
        reconnectionOptions: {
          initialReconnectionDelay: 10,
          maxRetries: 1,
          maxReconnectionDelay: 1000,  // Ensure it doesn't retry indefinitely
          reconnectionDelayGrowFactor: 1  // No exponential backoff for simplicity
         }
      });

      const errorSpy = jest.fn();
      transport.onerror = errorSpy;

      const failingStream = new ReadableStream({
        start(controller) { controller.error(new Error("Network failure")); }
      });

      const fetchMock = global.fetch as jest.Mock;
      // Mock the POST request. It returns a streaming content-type but a failing body.
      fetchMock.mockResolvedValueOnce({
        ok: true, status: 200,
        headers: new Headers({ "content-type": "text/event-stream" }),
        body: failingStream,
      });

      // A dummy request message to trigger the `send` logic.
      const requestMessage: JSONRPCRequest = {
        jsonrpc: '2.0',
        method: 'long_running_tool',
        id: 'request-1',
        params: {},
      };

      // ACT
      await transport.start();
      // Use the public `send` method to initiate a POST that gets a stream response.
      await transport.send(requestMessage);
      await jest.advanceTimersByTimeAsync(20); // Advance time to check for reconnections

      // ASSERT
      expect(errorSpy).toHaveBeenCalledWith(expect.objectContaining({
        message: expect.stringContaining('SSE stream disconnected: Error: Network failure'),
      }));
      // THE KEY ASSERTION: Fetch was only called ONCE. No reconnection was attempted.
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
    });
  });

  it("invalidates all credentials on InvalidClientError during auth", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    mockAuthProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      refresh_token: "test-refresh"
    });

    const unauthedResponse = {
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      headers: new Headers()
    };
    (global.fetch as jest.Mock)
      // Initial connection
      .mockResolvedValueOnce(unauthedResponse)
      // Resource discovery, path aware
      .mockResolvedValueOnce(unauthedResponse)
      // Resource discovery, root
      .mockResolvedValueOnce(unauthedResponse)
      // OAuth metadata discovery
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          issuer: "http://localhost:1234",
          authorization_endpoint: "http://localhost:1234/authorize",
          token_endpoint: "http://localhost:1234/token",
          response_types_supported: ["code"],
          code_challenge_methods_supported: ["S256"],
        }),
      })
      // Token refresh fails with InvalidClientError
      .mockResolvedValueOnce(Response.json(
        new InvalidClientError("Client authentication failed").toResponseObject(),
        { status: 400 }
      ))
      // Fallback should fail to complete the flow
      .mockResolvedValue({
        ok: false,
        status: 404
      });

    await expect(transport.send(message)).rejects.toThrow(UnauthorizedError);
    expect(mockAuthProvider.invalidateCredentials).toHaveBeenCalledWith('all');
  });

  it("invalidates all credentials on UnauthorizedClientError during auth", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    mockAuthProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      refresh_token: "test-refresh"
    });

    const unauthedResponse = {
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      headers: new Headers()
    };
    (global.fetch as jest.Mock)
      // Initial connection
      .mockResolvedValueOnce(unauthedResponse)
      // Resource discovery, path aware
      .mockResolvedValueOnce(unauthedResponse)
      // Resource discovery, root
      .mockResolvedValueOnce(unauthedResponse)
      // OAuth metadata discovery
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          issuer: "http://localhost:1234",
          authorization_endpoint: "http://localhost:1234/authorize",
          token_endpoint: "http://localhost:1234/token",
          response_types_supported: ["code"],
          code_challenge_methods_supported: ["S256"],
        }),
      })
      // Token refresh fails with UnauthorizedClientError
      .mockResolvedValueOnce(Response.json(
        new UnauthorizedClientError("Client not authorized").toResponseObject(),
        { status: 400 }
      ))
      // Fallback should fail to complete the flow
      .mockResolvedValue({
        ok: false,
        status: 404
      });

    await expect(transport.send(message)).rejects.toThrow(UnauthorizedError);
    expect(mockAuthProvider.invalidateCredentials).toHaveBeenCalledWith('all');
  });

  it("invalidates tokens on InvalidGrantError during auth", async () => {
    const message: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "test",
      params: {},
      id: "test-id"
    };

    mockAuthProvider.tokens.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      refresh_token: "test-refresh"
    });

    const unauthedResponse = {
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      headers: new Headers()
    };
    (global.fetch as jest.Mock)
      // Initial connection
      .mockResolvedValueOnce(unauthedResponse)
      // Resource discovery, path aware
      .mockResolvedValueOnce(unauthedResponse)
      // Resource discovery, root
      .mockResolvedValueOnce(unauthedResponse)
      // OAuth metadata discovery
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          issuer: "http://localhost:1234",
          authorization_endpoint: "http://localhost:1234/authorize",
          token_endpoint: "http://localhost:1234/token",
          response_types_supported: ["code"],
          code_challenge_methods_supported: ["S256"],
        }),
      })
      // Token refresh fails with InvalidGrantError
      .mockResolvedValueOnce(Response.json(
        new InvalidGrantError("Invalid refresh token").toResponseObject(),
        { status: 400 }
      ))
      // Fallback should fail to complete the flow
      .mockResolvedValue({
        ok: false,
        status: 404
      });

    await expect(transport.send(message)).rejects.toThrow(UnauthorizedError);
    expect(mockAuthProvider.invalidateCredentials).toHaveBeenCalledWith('tokens');
  });

  describe("custom fetch in auth code paths", () => {
    it("uses custom fetch during auth flow on 401 - no global fetch fallback", async () => {
      const unauthedResponse = {
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        headers: new Headers()
      };

      // Create custom fetch
      const customFetch = jest.fn()
        // Initial connection
        .mockResolvedValueOnce(unauthedResponse)
        // Resource discovery
        .mockResolvedValueOnce(unauthedResponse)
        // OAuth metadata discovery
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            issuer: "http://localhost:1234",
            authorization_endpoint: "http://localhost:1234/authorize",
            token_endpoint: "http://localhost:1234/token",
            response_types_supported: ["code"],
            code_challenge_methods_supported: ["S256"],
          }),
        })
        // Token refresh fails with InvalidClientError
        .mockResolvedValueOnce(Response.json(
          new InvalidClientError("Client authentication failed").toResponseObject(),
          { status: 400 }
        ))
        // Fallback should fail to complete the flow
        .mockResolvedValue({
          ok: false,
          status: 404
        });

      // Create transport instance
      transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
        authProvider: mockAuthProvider,
        fetch: customFetch
      });

      // Attempt to start - should trigger auth flow and eventually fail with UnauthorizedError
      await transport.start();
      await expect((transport as unknown as { _startOrAuthSse: (opts: StartSSEOptions) => Promise<void> })._startOrAuthSse({})).rejects.toThrow(UnauthorizedError);

      // Verify custom fetch was used
      expect(customFetch).toHaveBeenCalled();

      // Verify specific OAuth endpoints were called with custom fetch
      const customFetchCalls = customFetch.mock.calls;
      const callUrls = customFetchCalls.map(([url]) => url.toString());

      // Should have called resource metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-protected-resource'))).toBe(true);

      // Should have called OAuth authorization server metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-authorization-server'))).toBe(true);

      // Verify auth provider was called to redirect to authorization
      expect(mockAuthProvider.redirectToAuthorization).toHaveBeenCalled();

      // Global fetch should never have been called
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("uses custom fetch in finishAuth method - no global fetch fallback", async () => {
      // Create custom fetch
      const customFetch = jest.fn()
        // Protected resource metadata discovery
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            authorization_servers: ["http://localhost:1234"],
            resource: "http://localhost:1234/mcp"
          }),
        })
        // OAuth metadata discovery
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            issuer: "http://localhost:1234",
            authorization_endpoint: "http://localhost:1234/authorize",
            token_endpoint: "http://localhost:1234/token",
            response_types_supported: ["code"],
            code_challenge_methods_supported: ["S256"],
          }),
        })
        // Code exchange
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
            token_type: "Bearer",
            expires_in: 3600,
          }),
        });

      // Create transport instance
      transport = new StreamableHTTPClientTransport(new URL("http://localhost:1234/mcp"), {
        authProvider: mockAuthProvider,
        fetch: customFetch
      });

      // Call finishAuth with authorization code
      await transport.finishAuth("test-auth-code");

      // Verify custom fetch was used
      expect(customFetch).toHaveBeenCalled();

      // Verify specific OAuth endpoints were called with custom fetch
      const customFetchCalls = customFetch.mock.calls;
      const callUrls = customFetchCalls.map(([url]) => url.toString());

      // Should have called resource metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-protected-resource'))).toBe(true);

      // Should have called OAuth authorization server metadata discovery
      expect(callUrls.some(url => url.includes('/.well-known/oauth-authorization-server'))).toBe(true);

      // Should have called token endpoint for authorization code exchange
      const tokenCalls = customFetchCalls.filter(([url, options]) =>
        url.toString().includes('/token') && options?.method === "POST"
      );
      expect(tokenCalls.length).toBeGreaterThan(0);

      // Verify tokens were saved
      expect(mockAuthProvider.saveTokens).toHaveBeenCalledWith({
        access_token: "new-access-token",
        token_type: "Bearer",
        expires_in: 3600,
        refresh_token: "new-refresh-token"
      });

      // Global fetch should never have been called
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });
});



================================================
FILE: src/client/streamableHttp.ts
================================================
import { Transport, FetchLike } from "../shared/transport.js";
import { isInitializedNotification, isJSONRPCRequest, isJSONRPCResponse, JSONRPCMessage, JSONRPCMessageSchema } from "../types.js";
import { auth, AuthResult, extractResourceMetadataUrl, OAuthClientProvider, UnauthorizedError } from "./auth.js";
import { EventSourceParserStream } from "eventsource-parser/stream";

// Default reconnection options for StreamableHTTP connections
const DEFAULT_STREAMABLE_HTTP_RECONNECTION_OPTIONS: StreamableHTTPReconnectionOptions = {
  initialReconnectionDelay: 1000,
  maxReconnectionDelay: 30000,
  reconnectionDelayGrowFactor: 1.5,
  maxRetries: 2,
};

export class StreamableHTTPError extends Error {
  constructor(
    public readonly code: number | undefined,
    message: string | undefined,
  ) {
    super(`Streamable HTTP error: ${message}`);
  }
}

/**
 * Options for starting or authenticating an SSE connection
 */
export interface StartSSEOptions {
  /**
   * The resumption token used to continue long-running requests that were interrupted.
   *
   * This allows clients to reconnect and continue from where they left off.
   */
  resumptionToken?: string;

  /**
   * A callback that is invoked when the resumption token changes.
   *
   * This allows clients to persist the latest token for potential reconnection.
   */
  onresumptiontoken?: (token: string) => void;

  /**
  * Override Message ID to associate with the replay message
  * so that response can be associate with the new resumed request.
  */
  replayMessageId?: string | number;
}

/**
 * Configuration options for reconnection behavior of the StreamableHTTPClientTransport.
 */
export interface StreamableHTTPReconnectionOptions {
  /**
   * Maximum backoff time between reconnection attempts in milliseconds.
   * Default is 30000 (30 seconds).
   */
  maxReconnectionDelay: number;

  /**
   * Initial backoff time between reconnection attempts in milliseconds.
   * Default is 1000 (1 second).
   */
  initialReconnectionDelay: number;

  /**
   * The factor by which the reconnection delay increases after each attempt.
   * Default is 1.5.
   */
  reconnectionDelayGrowFactor: number;

  /**
   * Maximum number of reconnection attempts before giving up.
   * Default is 2.
   */
  maxRetries: number;
}

/**
 * Configuration options for the `StreamableHTTPClientTransport`.
 */
export type StreamableHTTPClientTransportOptions = {
  /**
   * An OAuth client provider to use for authentication.
   *
   * When an `authProvider` is specified and the connection is started:
   * 1. The connection is attempted with any existing access token from the `authProvider`.
   * 2. If the access token has expired, the `authProvider` is used to refresh the token.
   * 3. If token refresh fails or no access token exists, and auth is required, `OAuthClientProvider.redirectToAuthorization` is called, and an `UnauthorizedError` will be thrown from `connect`/`start`.
   *
   * After the user has finished authorizing via their user agent, and is redirected back to the MCP client application, call `StreamableHTTPClientTransport.finishAuth` with the authorization code before retrying the connection.
   *
   * If an `authProvider` is not provided, and auth is required, an `UnauthorizedError` will be thrown.
   *
   * `UnauthorizedError` might also be thrown when sending any message over the transport, indicating that the session has expired, and needs to be re-authed and reconnected.
   */
  authProvider?: OAuthClientProvider;

  /**
   * Customizes HTTP requests to the server.
   */
  requestInit?: RequestInit;

  /**
   * Custom fetch implementation used for all network requests.
   */
  fetch?: FetchLike;

  /**
   * Options to configure the reconnection behavior.
   */
  reconnectionOptions?: StreamableHTTPReconnectionOptions;

  /**
   * Session ID for the connection. This is used to identify the session on the server.
   * When not provided and connecting to a server that supports session IDs, the server will generate a new session ID.
   */
  sessionId?: string;
};

/**
 * Client transport for Streamable HTTP: this implements the MCP Streamable HTTP transport specification.
 * It will connect to a server using HTTP POST for sending messages and HTTP GET with Server-Sent Events
 * for receiving messages.
 */
export class StreamableHTTPClientTransport implements Transport {
  private _abortController?: AbortController;
  private _url: URL;
  private _resourceMetadataUrl?: URL;
  private _requestInit?: RequestInit;
  private _authProvider?: OAuthClientProvider;
  private _fetch?: FetchLike;
  private _sessionId?: string;
  private _reconnectionOptions: StreamableHTTPReconnectionOptions;
  private _protocolVersion?: string;

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;

  constructor(
    url: URL,
    opts?: StreamableHTTPClientTransportOptions,
  ) {
    this._url = url;
    this._resourceMetadataUrl = undefined;
    this._requestInit = opts?.requestInit;
    this._authProvider = opts?.authProvider;
    this._fetch = opts?.fetch;
    this._sessionId = opts?.sessionId;
    this._reconnectionOptions = opts?.reconnectionOptions ?? DEFAULT_STREAMABLE_HTTP_RECONNECTION_OPTIONS;
  }

  private async _authThenStart(): Promise<void> {
    if (!this._authProvider) {
      throw new UnauthorizedError("No auth provider");
    }

    let result: AuthResult;
    try {
      result = await auth(this._authProvider, { serverUrl: this._url, resourceMetadataUrl: this._resourceMetadataUrl, fetchFn: this._fetch });
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }

    if (result !== "AUTHORIZED") {
      throw new UnauthorizedError();
    }

    return await this._startOrAuthSse({ resumptionToken: undefined });
  }

  private async _commonHeaders(): Promise<Headers> {
    const headers: HeadersInit & Record<string, string> = {};
    if (this._authProvider) {
      const tokens = await this._authProvider.tokens();
      if (tokens) {
        headers["Authorization"] = `Bearer ${tokens.access_token}`;
      }
    }

    if (this._sessionId) {
      headers["mcp-session-id"] = this._sessionId;
    }
    if (this._protocolVersion) {
      headers["mcp-protocol-version"] = this._protocolVersion;
    }

    const extraHeaders = this._normalizeHeaders(this._requestInit?.headers);

    return new Headers({
      ...headers,
      ...extraHeaders,
    });
  }


  private async _startOrAuthSse(options: StartSSEOptions): Promise<void> {
    const { resumptionToken } = options;
    try {
      // Try to open an initial SSE stream with GET to listen for server messages
      // This is optional according to the spec - server may not support it
      const headers = await this._commonHeaders();
      headers.set("Accept", "text/event-stream");

      // Include Last-Event-ID header for resumable streams if provided
      if (resumptionToken) {
        headers.set("last-event-id", resumptionToken);
      }

      const response = await (this._fetch ?? fetch)(this._url, {
        method: "GET",
        headers,
        signal: this._abortController?.signal,
      });

      if (!response.ok) {
        if (response.status === 401 && this._authProvider) {
          // Need to authenticate
          return await this._authThenStart();
        }

        // 405 indicates that the server does not offer an SSE stream at GET endpoint
        // This is an expected case that should not trigger an error
        if (response.status === 405) {
          return;
        }

        throw new StreamableHTTPError(
          response.status,
          `Failed to open SSE stream: ${response.statusText}`,
        );
      }

      this._handleSseStream(response.body, options, true);
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }
  }


  /**
   * Calculates the next reconnection delay using  backoff algorithm
   *
   * @param attempt Current reconnection attempt count for the specific stream
   * @returns Time to wait in milliseconds before next reconnection attempt
   */
  private _getNextReconnectionDelay(attempt: number): number {
    // Access default values directly, ensuring they're never undefined
    const initialDelay = this._reconnectionOptions.initialReconnectionDelay;
    const growFactor = this._reconnectionOptions.reconnectionDelayGrowFactor;
    const maxDelay = this._reconnectionOptions.maxReconnectionDelay;

    // Cap at maximum delay
    return Math.min(initialDelay * Math.pow(growFactor, attempt), maxDelay);

  }

    private _normalizeHeaders(headers: HeadersInit | undefined): Record<string, string> {
    if (!headers) return {};

    if (headers instanceof Headers) {
      return Object.fromEntries(headers.entries());
    }

    if (Array.isArray(headers)) {
      return Object.fromEntries(headers);
    }

    return { ...headers as Record<string, string> };
  }

  /**
   * Schedule a reconnection attempt with exponential backoff
   *
   * @param lastEventId The ID of the last received event for resumability
   * @param attemptCount Current reconnection attempt count for this specific stream
   */
  private _scheduleReconnection(options: StartSSEOptions, attemptCount = 0): void {
    // Use provided options or default options
    const maxRetries = this._reconnectionOptions.maxRetries;

    // Check if we've exceeded maximum retry attempts
    if (maxRetries > 0 && attemptCount >= maxRetries) {
      this.onerror?.(new Error(`Maximum reconnection attempts (${maxRetries}) exceeded.`));
      return;
    }

    // Calculate next delay based on current attempt count
    const delay = this._getNextReconnectionDelay(attemptCount);

    // Schedule the reconnection
    setTimeout(() => {
      // Use the last event ID to resume where we left off
      this._startOrAuthSse(options).catch(error => {
        this.onerror?.(new Error(`Failed to reconnect SSE stream: ${error instanceof Error ? error.message : String(error)}`));
        // Schedule another attempt if this one failed, incrementing the attempt counter
        this._scheduleReconnection(options, attemptCount + 1);
      });
    }, delay);
  }

  private _handleSseStream(
    stream: ReadableStream<Uint8Array> | null, 
    options: StartSSEOptions,
    isReconnectable: boolean,
  ): void {
    if (!stream) {
      return;
    }
    const { onresumptiontoken, replayMessageId } = options;

    let lastEventId: string | undefined;
    const processStream = async () => {
      // this is the closest we can get to trying to catch network errors
      // if something happens reader will throw
      try {
        // Create a pipeline: binary stream -> text decoder -> SSE parser
        const reader = stream
          .pipeThrough(new TextDecoderStream())
          .pipeThrough(new EventSourceParserStream())
          .getReader();


        while (true) {
          const { value: event, done } = await reader.read();
          if (done) {
            break;
          }

          // Update last event ID if provided
          if (event.id) {
            lastEventId = event.id;
            onresumptiontoken?.(event.id);
          }

          if (!event.event || event.event === "message") {
            try {
              const message = JSONRPCMessageSchema.parse(JSON.parse(event.data));
              if (replayMessageId !== undefined && isJSONRPCResponse(message)) {
                message.id = replayMessageId;
              }
              this.onmessage?.(message);
            } catch (error) {
              this.onerror?.(error as Error);
            }
          }
        }
      } catch (error) {
        // Handle stream errors - likely a network disconnect
        this.onerror?.(new Error(`SSE stream disconnected: ${error}`));

        // Attempt to reconnect if the stream disconnects unexpectedly and we aren't closing
        if (
          isReconnectable && 
          this._abortController && 
          !this._abortController.signal.aborted
        ) {
          // Use the exponential backoff reconnection strategy
          try {
            this._scheduleReconnection({
              resumptionToken: lastEventId,
              onresumptiontoken,
              replayMessageId
            }, 0);
          }
          catch (error) {
            this.onerror?.(new Error(`Failed to reconnect: ${error instanceof Error ? error.message : String(error)}`));

          }
        }
      }
    };
    processStream();
  }

  async start() {
    if (this._abortController) {
      throw new Error(
        "StreamableHTTPClientTransport already started! If using Client class, note that connect() calls start() automatically.",
      );
    }

    this._abortController = new AbortController();
  }

  /**
   * Call this method after the user has finished authorizing via their user agent and is redirected back to the MCP client application. This will exchange the authorization code for an access token, enabling the next connection attempt to successfully auth.
   */
  async finishAuth(authorizationCode: string): Promise<void> {
    if (!this._authProvider) {
      throw new UnauthorizedError("No auth provider");
    }

    const result = await auth(this._authProvider, { serverUrl: this._url, authorizationCode, resourceMetadataUrl: this._resourceMetadataUrl, fetchFn: this._fetch });
    if (result !== "AUTHORIZED") {
      throw new UnauthorizedError("Failed to authorize");
    }
  }

  async close(): Promise<void> {
    // Abort any pending requests
    this._abortController?.abort();

    this.onclose?.();
  }

  async send(message: JSONRPCMessage | JSONRPCMessage[], options?: { resumptionToken?: string, onresumptiontoken?: (token: string) => void }): Promise<void> {
    try {
      const { resumptionToken, onresumptiontoken } = options || {};

      if (resumptionToken) {
        // If we have at last event ID, we need to reconnect the SSE stream
        this._startOrAuthSse({ resumptionToken, replayMessageId: isJSONRPCRequest(message) ? message.id : undefined }).catch(err => this.onerror?.(err));
        return;
      }

      const headers = await this._commonHeaders();
      headers.set("content-type", "application/json");
      headers.set("accept", "application/json, text/event-stream");

      const init = {
        ...this._requestInit,
        method: "POST",
        headers,
        body: JSON.stringify(message),
        signal: this._abortController?.signal,
      };

      const response = await (this._fetch ?? fetch)(this._url, init);

      // Handle session ID received during initialization
      const sessionId = response.headers.get("mcp-session-id");
      if (sessionId) {
        this._sessionId = sessionId;
      }

      if (!response.ok) {
        if (response.status === 401 && this._authProvider) {

          this._resourceMetadataUrl = extractResourceMetadataUrl(response);

          const result = await auth(this._authProvider, { serverUrl: this._url, resourceMetadataUrl: this._resourceMetadataUrl, fetchFn: this._fetch });
          if (result !== "AUTHORIZED") {
            throw new UnauthorizedError();
          }

          // Purposely _not_ awaited, so we don't call onerror twice
          return this.send(message);
        }

        const text = await response.text().catch(() => null);
        throw new Error(
          `Error POSTing to endpoint (HTTP ${response.status}): ${text}`,
        );
      }

      // If the response is 202 Accepted, there's no body to process
      if (response.status === 202) {
        // if the accepted notification is initialized, we start the SSE stream
        // if it's supported by the server
        if (isInitializedNotification(message)) {
          // Start without a lastEventId since this is a fresh connection
          this._startOrAuthSse({ resumptionToken: undefined }).catch(err => this.onerror?.(err));
        }
        return;
      }

      // Get original message(s) for detecting request IDs
      const messages = Array.isArray(message) ? message : [message];

      const hasRequests = messages.filter(msg => "method" in msg && "id" in msg && msg.id !== undefined).length > 0;

      // Check the response type
      const contentType = response.headers.get("content-type");

      if (hasRequests) {
        if (contentType?.includes("text/event-stream")) {
          // Handle SSE stream responses for requests
          // We use the same handler as standalone streams, which now supports
          // reconnection with the last event ID
          this._handleSseStream(response.body, { onresumptiontoken }, false);
        } else if (contentType?.includes("application/json")) {
          // For non-streaming servers, we might get direct JSON responses
          const data = await response.json();
          const responseMessages = Array.isArray(data)
            ? data.map(msg => JSONRPCMessageSchema.parse(msg))
            : [JSONRPCMessageSchema.parse(data)];

          for (const msg of responseMessages) {
            this.onmessage?.(msg);
          }
        } else {
          throw new StreamableHTTPError(
            -1,
            `Unexpected content type: ${contentType}`,
          );
        }
      }
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }
  }

  get sessionId(): string | undefined {
    return this._sessionId;
  }

  /**
   * Terminates the current session by sending a DELETE request to the server.
   *
   * Clients that no longer need a particular session
   * (e.g., because the user is leaving the client application) SHOULD send an
   * HTTP DELETE to the MCP endpoint with the Mcp-Session-Id header to explicitly
   * terminate the session.
   *
   * The server MAY respond with HTTP 405 Method Not Allowed, indicating that
   * the server does not allow clients to terminate sessions.
   */
  async terminateSession(): Promise<void> {
    if (!this._sessionId) {
      return; // No session to terminate
    }

    try {
      const headers = await this._commonHeaders();

      const init = {
        ...this._requestInit,
        method: "DELETE",
        headers,
        signal: this._abortController?.signal,
      };

      const response = await (this._fetch ?? fetch)(this._url, init);

      // We specifically handle 405 as a valid response according to the spec,
      // meaning the server does not support explicit session termination
      if (!response.ok && response.status !== 405) {
        throw new StreamableHTTPError(
          response.status,
          `Failed to terminate session: ${response.statusText}`
        );
      }

      this._sessionId = undefined;
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }
  }

  setProtocolVersion(version: string): void {
    this._protocolVersion = version;
  }
  get protocolVersion(): string | undefined {
    return this._protocolVersion;
  }
}



================================================
FILE: src/client/websocket.ts
================================================
import { Transport } from "../shared/transport.js";
import { JSONRPCMessage, JSONRPCMessageSchema } from "../types.js";

const SUBPROTOCOL = "mcp";

/**
 * Client transport for WebSocket: this will connect to a server over the WebSocket protocol.
 */
export class WebSocketClientTransport implements Transport {
  private _socket?: WebSocket;
  private _url: URL;

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;

  constructor(url: URL) {
    this._url = url;
  }

  start(): Promise<void> {
    if (this._socket) {
      throw new Error(
        "WebSocketClientTransport already started! If using Client class, note that connect() calls start() automatically.",
      );
    }

    return new Promise((resolve, reject) => {
      this._socket = new WebSocket(this._url, SUBPROTOCOL);

      this._socket.onerror = (event) => {
        const error =
          "error" in event
            ? (event.error as Error)
            : new Error(`WebSocket error: ${JSON.stringify(event)}`);
        reject(error);
        this.onerror?.(error);
      };

      this._socket.onopen = () => {
        resolve();
      };

      this._socket.onclose = () => {
        this.onclose?.();
      };

      this._socket.onmessage = (event: MessageEvent) => {
        let message: JSONRPCMessage;
        try {
          message = JSONRPCMessageSchema.parse(JSON.parse(event.data));
        } catch (error) {
          this.onerror?.(error as Error);
          return;
        }

        this.onmessage?.(message);
      };
    });
  }

  async close(): Promise<void> {
    this._socket?.close();
  }

  send(message: JSONRPCMessage): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this._socket) {
        reject(new Error("Not connected"));
        return;
      }

      this._socket?.send(JSON.stringify(message));
      resolve();
    });
  }
}



================================================
FILE: src/examples/README.md
================================================
# MCP TypeScript SDK Examples

This directory contains example implementations of MCP clients and servers using the TypeScript SDK.

## Table of Contents

- [Client Implementations](#client-implementations)
  - [Streamable HTTP Client](#streamable-http-client)
  - [Backwards Compatible Client](#backwards-compatible-client)
- [Server Implementations](#server-implementations)
  - [Single Node Deployment](#single-node-deployment)
    - [Streamable HTTP Transport](#streamable-http-transport)
    - [Deprecated SSE Transport](#deprecated-sse-transport)
    - [Backwards Compatible Server](#streamable-http-backwards-compatible-server-with-sse)
  - [Multi-Node Deployment](#multi-node-deployment)
- [Backwards Compatibility](#testing-streamable-http-backwards-compatibility-with-sse)

## Client Implementations

### Streamable HTTP Client

A full-featured interactive client that connects to a Streamable HTTP server, demonstrating how to:

- Establish and manage a connection to an MCP server
- List and call tools with arguments
- Handle notifications through the SSE stream
- List and get prompts with arguments
- List available resources
- Handle session termination and reconnection
- Support for resumability with Last-Event-ID tracking

```bash
npx tsx src/examples/client/simpleStreamableHttp.ts
```

Example client with OAuth:

```bash
npx tsx src/examples/client/simpleOAuthClient.js
```

### Backwards Compatible Client

A client that implements backwards compatibility according to the [MCP specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility), allowing it to work with both new and legacy servers. This client demonstrates:

- The client first POSTs an initialize request to the server URL:
  - If successful, it uses the Streamable HTTP transport
  - If it fails with a 4xx status, it attempts a GET request to establish an SSE stream

```bash
npx tsx src/examples/client/streamableHttpWithSseFallbackClient.ts
```

## Server Implementations

### Single Node Deployment

These examples demonstrate how to set up an MCP server on a single node with different transport options.

#### Streamable HTTP Transport

##### Simple Streamable HTTP Server

A server that implements the Streamable HTTP transport (protocol version 2025-03-26). 

- Basic server setup with Express and the Streamable HTTP transport
- Session management with an in-memory event store for resumability
- Tool implementation with the `greet` and `multi-greet` tools
- Prompt implementation with the `greeting-template` prompt
- Static resource exposure
- Support for notifications via SSE stream established by GET requests
- Session termination via DELETE requests

```bash
npx tsx src/examples/server/simpleStreamableHttp.ts

# To add a demo of authentication to this example, use:
npx tsx src/examples/server/simpleStreamableHttp.ts --oauth

# To mitigate impersonation risks, enable strict Resource Identifier verification:
npx tsx src/examples/server/simpleStreamableHttp.ts --oauth --oauth-strict
```

##### JSON Response Mode Server

A server that uses Streamable HTTP transport with JSON response mode enabled (no SSE). 

- Streamable HTTP with JSON response mode, which returns responses directly in the response body
- Limited support for notifications (since SSE is disabled)
- Proper response handling according to the MCP specification for servers that don't support SSE
- Returning appropriate HTTP status codes for unsupported methods

```bash
npx tsx src/examples/server/jsonResponseStreamableHttp.ts
```

##### Streamable HTTP with server notifications

A server that demonstrates server notifications using Streamable HTTP. 

- Resource list change notifications with dynamically added resources
- Automatic resource creation on a timed interval


```bash
npx tsx src/examples/server/standaloneSseWithGetStreamableHttp.ts
```

#### Deprecated SSE Transport

A server that implements the deprecated HTTP+SSE transport (protocol version 2024-11-05). This example only used for testing backwards compatibility for clients.

- Two separate endpoints: `/mcp` for the SSE stream (GET) and `/messages` for client messages (POST)
- Tool implementation with a `start-notification-stream` tool that demonstrates sending periodic notifications

```bash
npx tsx src/examples/server/simpleSseServer.ts
```

#### Streamable Http Backwards Compatible Server with SSE 

A server that supports both Streamable HTTP and SSE transports, adhering to the [MCP specification for backwards compatibility](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility). 

- Single MCP server instance with multiple transport options
- Support for Streamable HTTP requests at `/mcp` endpoint (GET/POST/DELETE)
- Support for deprecated SSE transport with `/sse` (GET) and `/messages` (POST)
- Session type tracking to avoid mixing transport types
- Notifications and tool execution across both transport types

```bash
npx tsx src/examples/server/sseAndStreamableHttpCompatibleServer.ts
```

### Multi-Node Deployment

When deploying MCP servers in a horizontally scaled environment (multiple server instances), there are a few different options that can be useful for different use cases:
- **Stateless mode** - No need to maintain state between calls to MCP servers. Useful for simple API wrapper servers.
- **Persistent storage mode** - No local state needed, but session data is stored in a database. Example: an MCP server for online ordering where the shopping cart is stored in a database.
- **Local state with message routing** - Local state is needed, and all requests for a session must be routed to the correct node. This can be done with a message queue and pub/sub system.

#### Stateless Mode

The Streamable HTTP transport can be configured to operate without tracking sessions. This is perfect for simple API proxies or when each request is completely independent.

##### Implementation

To enable stateless mode, configure the `StreamableHTTPServerTransport` with:
```typescript
sessionIdGenerator: undefined
```

This disables session management entirely, and the server won't generate or expect session IDs.

- No session ID headers are sent or expected
- Any server node can process any request
- No state is preserved between requests
- Perfect for RESTful or stateless API scenarios
- Simplest deployment model with minimal infrastructure requirements

```
┌─────────────────────────────────────────────┐
│                  Client                     │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                Load Balancer                │
└─────────────────────────────────────────────┘
          │                       │
          ▼                       ▼
┌─────────────────┐     ┌─────────────────────┐
│  MCP Server #1  │     │    MCP Server #2    │
│ (Node.js)       │     │  (Node.js)          │
└─────────────────┘     └─────────────────────┘
```



#### Persistent Storage Mode

For cases where you need session continuity but don't need to maintain in-memory state on specific nodes, you can use a database to persist session data while still allowing any node to handle requests.

##### Implementation

Configure the transport with session management, but retrieve and store all state in an external persistent storage:

```typescript
sessionIdGenerator: () => randomUUID(),
eventStore: databaseEventStore
```

All session state is stored in the database, and any node can serve any client by retrieving the state when needed.

- Maintains sessions with unique IDs
- Stores all session data in an external database
- Provides resumability through the database-backed EventStore
- Any node can handle any request for the same session
- No node-specific memory state means no need for message routing
- Good for applications where state can be fully externalized
- Somewhat higher latency due to database access for each request


```
┌─────────────────────────────────────────────┐
│                  Client                     │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                Load Balancer                │
└─────────────────────────────────────────────┘
          │                       │
          ▼                       ▼
┌─────────────────┐     ┌─────────────────────┐
│  MCP Server #1  │     │    MCP Server #2    │
│ (Node.js)       │     │  (Node.js)          │
└─────────────────┘     └─────────────────────┘
          │                       │
          │                       │
          ▼                       ▼
┌─────────────────────────────────────────────┐
│           Database (PostgreSQL)             │
│                                             │
│  • Session state                            │
│  • Event storage for resumability           │
└─────────────────────────────────────────────┘
```



#### Streamable HTTP with Distributed Message Routing

For scenarios where local in-memory state must be maintained on specific nodes (such as Computer Use or complex session state), the Streamable HTTP transport can be combined with a pub/sub system to route messages to the correct node handling each session.

1. **Bidirectional Message Queue Integration**:
   - All nodes both publish to and subscribe from the message queue
   - Each node registers the sessions it's actively handling
   - Messages are routed based on session ownership

2. **Request Handling Flow**:
   - When a client connects to Node A with an existing `mcp-session-id`
   - If Node A doesn't own this session, it:
     - Establishes and maintains the SSE connection with the client
     - Publishes the request to the message queue with the session ID
     - Node B (which owns the session) receives the request from the queue
     - Node B processes the request with its local session state
     - Node B publishes responses/notifications back to the queue
     - Node A subscribes to the response channel and forwards to the client

3. **Channel Identification**:
   - Each message channel combines both `mcp-session-id` and `stream-id`
   - This ensures responses are correctly routed back to the originating connection

```
┌─────────────────────────────────────────────┐
│                  Client                     │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                Load Balancer                │
└─────────────────────────────────────────────┘
          │                       │
          ▼                       ▼
┌─────────────────┐     ┌─────────────────────┐
│  MCP Server #1  │◄───►│    MCP Server #2    │
│ (Has Session A) │     │  (Has Session B)    │
└─────────────────┘     └─────────────────────┘
          ▲│                     ▲│
          │▼                     │▼
┌─────────────────────────────────────────────┐
│         Message Queue / Pub-Sub             │
│                                             │
│  • Session ownership registry               │
│  • Bidirectional message routing            │
│  • Request/response forwarding              │
└─────────────────────────────────────────────┘
```


- Maintains session affinity for stateful operations without client redirection
- Enables horizontal scaling while preserving complex in-memory state
- Provides fault tolerance through the message queue as intermediary


## Backwards Compatibility

### Testing Streamable HTTP Backwards Compatibility with SSE

To test the backwards compatibility features:

1. Start one of the server implementations:
   ```bash
   # Legacy SSE server (protocol version 2024-11-05)
   npx tsx src/examples/server/simpleSseServer.ts
   
   # Streamable HTTP server (protocol version 2025-03-26)
   npx tsx src/examples/server/simpleStreamableHttp.ts
   
   # Backwards compatible server (supports both protocols)
   npx tsx src/examples/server/sseAndStreamableHttpCompatibleServer.ts
   ```

2. Then run the backwards compatible client:
   ```bash
   npx tsx src/examples/client/streamableHttpWithSseFallbackClient.ts
   ```

This demonstrates how the MCP ecosystem ensures interoperability between clients and servers regardless of which protocol version they were built for.


================================================
FILE: src/examples/client/multipleClientsParallel.ts
================================================
import { Client } from '../../client/index.js';
import { StreamableHTTPClientTransport } from '../../client/streamableHttp.js';
import {
  CallToolRequest,
  CallToolResultSchema,
  LoggingMessageNotificationSchema,
  CallToolResult,
} from '../../types.js';

/**
 * Multiple Clients MCP Example
 * 
 * This client demonstrates how to:
 * 1. Create multiple MCP clients in parallel
 * 2. Each client calls a single tool 
 * 3. Track notifications from each client independently
 */

// Command line args processing
const args = process.argv.slice(2);
const serverUrl = args[0] || 'http://localhost:3000/mcp';

interface ClientConfig {
  id: string;
  name: string;
  toolName: string;
  toolArguments: Record<string, string | number | boolean>;
}

async function createAndRunClient(config: ClientConfig): Promise<{ id: string; result: CallToolResult }> {
  console.log(`[${config.id}] Creating client: ${config.name}`);

  const client = new Client({
    name: config.name,
    version: '1.0.0'
  });

  const transport = new StreamableHTTPClientTransport(new URL(serverUrl));

  // Set up client-specific error handler
  client.onerror = (error) => {
    console.error(`[${config.id}] Client error:`, error);
  };

  // Set up client-specific notification handler
  client.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
    console.log(`[${config.id}] Notification: ${notification.params.data}`);
  });

  try {
    // Connect to the server
    await client.connect(transport);
    console.log(`[${config.id}] Connected to MCP server`);

    // Call the specified tool
    console.log(`[${config.id}] Calling tool: ${config.toolName}`);
    const toolRequest: CallToolRequest = {
      method: 'tools/call',
      params: {
        name: config.toolName,
        arguments: {
          ...config.toolArguments,
          // Add client ID to arguments for identification in notifications
          caller: config.id
        }
      }
    };

    const result = await client.request(toolRequest, CallToolResultSchema);
    console.log(`[${config.id}] Tool call completed`);

    // Keep the connection open for a bit to receive notifications
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Disconnect
    await transport.close();
    console.log(`[${config.id}] Disconnected from MCP server`);

    return { id: config.id, result };
  } catch (error) {
    console.error(`[${config.id}] Error:`, error);
    throw error;
  }
}

async function main(): Promise<void> {
  console.log('MCP Multiple Clients Example');
  console.log('============================');
  console.log(`Server URL: ${serverUrl}`);
  console.log('');

  try {
    // Define client configurations
    const clientConfigs: ClientConfig[] = [
      {
        id: 'client1',
        name: 'basic-client-1',
        toolName: 'start-notification-stream',
        toolArguments: {
          interval: 3, // 1 second between notifications
          count: 5     // Send 5 notifications
        }
      },
      {
        id: 'client2',
        name: 'basic-client-2',
        toolName: 'start-notification-stream',
        toolArguments: {
          interval: 2, // 2 seconds between notifications
          count: 3     // Send 3 notifications
        }
      },
      {
        id: 'client3',
        name: 'basic-client-3',
        toolName: 'start-notification-stream',
        toolArguments: {
          interval: 1, // 0.5 second between notifications
          count: 8       // Send 8 notifications
        }
      }
    ];

    // Start all clients in parallel
    console.log(`Starting ${clientConfigs.length} clients in parallel...`);
    console.log('');

    const clientPromises = clientConfigs.map(config => createAndRunClient(config));
    const results = await Promise.all(clientPromises);

    // Display results from all clients
    console.log('\n=== Final Results ===');
    results.forEach(({ id, result }) => {
      console.log(`\n[${id}] Tool result:`);
      if (Array.isArray(result.content)) {
        result.content.forEach((item: { type: string; text?: string }) => {
          if (item.type === 'text' && item.text) {
            console.log(`  ${item.text}`);
          } else {
            console.log(`  ${item.type} content:`, item);
          }
        });
      } else {
        console.log(`  Unexpected result format:`, result);
      }
    });

    console.log('\n=== All clients completed successfully ===');

  } catch (error) {
    console.error('Error running multiple clients:', error);
    process.exit(1);
  }
}

// Start the example
main().catch((error: unknown) => {
  console.error('Error running MCP multiple clients example:', error);
  process.exit(1);
});


================================================
FILE: src/examples/client/parallelToolCallsClient.ts
================================================
import { Client } from '../../client/index.js';
import { StreamableHTTPClientTransport } from '../../client/streamableHttp.js';
import {
  ListToolsRequest,
  ListToolsResultSchema,
  CallToolResultSchema,
  LoggingMessageNotificationSchema,
  CallToolResult,
} from '../../types.js';

/**
 * Parallel Tool Calls MCP Client
 * 
 * This client demonstrates how to:
 * 1. Start multiple tool calls in parallel
 * 2. Track notifications from each tool call using a caller parameter
 */

// Command line args processing
const args = process.argv.slice(2);
const serverUrl = args[0] || 'http://localhost:3000/mcp';

async function main(): Promise<void> {
  console.log('MCP Parallel Tool Calls Client');
  console.log('==============================');
  console.log(`Connecting to server at: ${serverUrl}`);

  let client: Client;
  let transport: StreamableHTTPClientTransport;

  try {
    // Create client with streamable HTTP transport
    client = new Client({
      name: 'parallel-tool-calls-client',
      version: '1.0.0'
    });

    client.onerror = (error) => {
      console.error('Client error:', error);
    };

    // Connect to the server
    transport = new StreamableHTTPClientTransport(new URL(serverUrl));
    await client.connect(transport);
    console.log('Successfully connected to MCP server');

    // Set up notification handler with caller identification
    client.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
      console.log(`Notification: ${notification.params.data}`);
    });

    console.log("List tools")
    const toolsRequest = await listTools(client);
    console.log("Tools: ", toolsRequest)


    // 2. Start multiple notification tools in parallel
    console.log('\n=== Starting Multiple Notification Streams in Parallel ===');
    const toolResults = await startParallelNotificationTools(client);

    // Log the results from each tool call
    for (const [caller, result] of Object.entries(toolResults)) {
      console.log(`\n=== Tool result for ${caller} ===`);
      result.content.forEach((item: { type: string; text?: string; }) => {
        if (item.type === 'text') {
          console.log(`  ${item.text}`);
        } else {
          console.log(`  ${item.type} content:`, item);
        }
      });
    }

    // 3. Wait for all notifications (10 seconds)
    console.log('\n=== Waiting for all notifications ===');
    await new Promise(resolve => setTimeout(resolve, 10000));

    // 4. Disconnect
    console.log('\n=== Disconnecting ===');
    await transport.close();
    console.log('Disconnected from MCP server');

  } catch (error) {
    console.error('Error running client:', error);
    process.exit(1);
  }
}

/**
 * List available tools on the server
 */
async function listTools(client: Client): Promise<void> {
  try {
    const toolsRequest: ListToolsRequest = {
      method: 'tools/list',
      params: {}
    };
    const toolsResult = await client.request(toolsRequest, ListToolsResultSchema);

    console.log('Available tools:');
    if (toolsResult.tools.length === 0) {
      console.log('  No tools available');
    } else {
      for (const tool of toolsResult.tools) {
        console.log(`  - ${tool.name}: ${tool.description}`);
      }
    }
  } catch (error) {
    console.log(`Tools not supported by this server: ${error}`);
  }
}

/**
 * Start multiple notification tools in parallel with different configurations
 * Each tool call includes a caller parameter to identify its notifications
 */
async function startParallelNotificationTools(client: Client): Promise<Record<string, CallToolResult>> {
  try {
    // Define multiple tool calls with different configurations
    const toolCalls = [
      {
        caller: 'fast-notifier',
        request: {
          method: 'tools/call',
          params: {
            name: 'start-notification-stream',
            arguments: {
              interval: 2,  // 0.5 second between notifications
              count: 10,      // Send 10 notifications
              caller: 'fast-notifier' // Identify this tool call
            }
          }
        }
      },
      {
        caller: 'slow-notifier',
        request: {
          method: 'tools/call',
          params: {
            name: 'start-notification-stream',
            arguments: {
              interval: 5, // 2 seconds between notifications
              count: 5,       // Send 5 notifications
              caller: 'slow-notifier' // Identify this tool call
            }
          }
        }
      },
      {
        caller: 'burst-notifier',
        request: {
          method: 'tools/call',
          params: {
            name: 'start-notification-stream',
            arguments: {
              interval: 1,  // 0.1 second between notifications
              count: 3,       // Send just 3 notifications
              caller: 'burst-notifier' // Identify this tool call
            }
          }
        }
      }
    ];

    console.log(`Starting ${toolCalls.length} notification tools in parallel...`);

    // Start all tool calls in parallel
    const toolPromises = toolCalls.map(({ caller, request }) => {
      console.log(`Starting tool call for ${caller}...`);
      return client.request(request, CallToolResultSchema)
        .then(result => ({ caller, result }))
        .catch(error => {
          console.error(`Error in tool call for ${caller}:`, error);
          throw error;
        });
    });

    // Wait for all tool calls to complete
    const results = await Promise.all(toolPromises);

    // Organize results by caller
    const resultsByTool: Record<string, CallToolResult> = {};
    results.forEach(({ caller, result }) => {
      resultsByTool[caller] = result;
    });

    return resultsByTool;
  } catch (error) {
    console.error(`Error starting parallel notification tools:`, error);
    throw error;
  }
}

// Start the client
main().catch((error: unknown) => {
  console.error('Error running MCP client:', error);
  process.exit(1);
});


================================================
FILE: src/examples/client/simpleOAuthClient.ts
================================================
#!/usr/bin/env node

import { createServer } from 'node:http';
import { createInterface } from 'node:readline';
import { URL } from 'node:url';
import { exec } from 'node:child_process';
import { Client } from '../../client/index.js';
import { StreamableHTTPClientTransport } from '../../client/streamableHttp.js';
import { OAuthClientInformation, OAuthClientInformationFull, OAuthClientMetadata, OAuthTokens } from '../../shared/auth.js';
import {
  CallToolRequest,
  ListToolsRequest,
  CallToolResultSchema,
  ListToolsResultSchema
} from '../../types.js';
import { OAuthClientProvider, UnauthorizedError } from '../../client/auth.js';

// Configuration
const DEFAULT_SERVER_URL = 'http://localhost:3000/mcp';
const CALLBACK_PORT = 8090; // Use different port than auth server (3001)
const CALLBACK_URL = `http://localhost:${CALLBACK_PORT}/callback`;

/**
 * In-memory OAuth client provider for demonstration purposes
 * In production, you should persist tokens securely
 */
class InMemoryOAuthClientProvider implements OAuthClientProvider {
  private _clientInformation?: OAuthClientInformationFull;
  private _tokens?: OAuthTokens;
  private _codeVerifier?: string;

  constructor(
    private readonly _redirectUrl: string | URL,
    private readonly _clientMetadata: OAuthClientMetadata,
    onRedirect?: (url: URL) => void
  ) {
    this._onRedirect = onRedirect || ((url) => {
      console.log(`Redirect to: ${url.toString()}`);
    });
  }

  private _onRedirect: (url: URL) => void;

  get redirectUrl(): string | URL {
    return this._redirectUrl;
  }

  get clientMetadata(): OAuthClientMetadata {
    return this._clientMetadata;
  }

  clientInformation(): OAuthClientInformation | undefined {
    return this._clientInformation;
  }

  saveClientInformation(clientInformation: OAuthClientInformationFull): void {
    this._clientInformation = clientInformation;
  }

  tokens(): OAuthTokens | undefined {
    return this._tokens;
  }

  saveTokens(tokens: OAuthTokens): void {
    this._tokens = tokens;
  }

  redirectToAuthorization(authorizationUrl: URL): void {
    this._onRedirect(authorizationUrl);
  }

  saveCodeVerifier(codeVerifier: string): void {
    this._codeVerifier = codeVerifier;
  }

  codeVerifier(): string {
    if (!this._codeVerifier) {
      throw new Error('No code verifier saved');
    }
    return this._codeVerifier;
  }
}
/**
 * Interactive MCP client with OAuth authentication
 * Demonstrates the complete OAuth flow with browser-based authorization
 */
class InteractiveOAuthClient {
  private client: Client | null = null;
  private readonly rl = createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  constructor(private serverUrl: string) { }

  /**
   * Prompts user for input via readline
   */
  private async question(query: string): Promise<string> {
    return new Promise((resolve) => {
      this.rl.question(query, resolve);
    });
  }

  /**
   * Opens the authorization URL in the user's default browser
   */
  private async openBrowser(url: string): Promise<void> {
    console.log(`🌐 Opening browser for authorization: ${url}`);

    const command = `open "${url}"`;

    exec(command, (error) => {
      if (error) {
        console.error(`Failed to open browser: ${error.message}`);
        console.log(`Please manually open: ${url}`);
      }
    });
  }
  /**
   * Example OAuth callback handler - in production, use a more robust approach
   * for handling callbacks and storing tokens
   */
  /**
   * Starts a temporary HTTP server to receive the OAuth callback
   */
  private async waitForOAuthCallback(): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      const server = createServer((req, res) => {
        // Ignore favicon requests
        if (req.url === '/favicon.ico') {
          res.writeHead(404);
          res.end();
          return;
        }

        console.log(`📥 Received callback: ${req.url}`);
        const parsedUrl = new URL(req.url || '', 'http://localhost');
        const code = parsedUrl.searchParams.get('code');
        const error = parsedUrl.searchParams.get('error');

        if (code) {
          console.log(`✅ Authorization code received: ${code?.substring(0, 10)}...`);
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(`
            <html>
              <body>
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <script>setTimeout(() => window.close(), 2000);</script>
              </body>
            </html>
          `);

          resolve(code);
          setTimeout(() => server.close(), 3000);
        } else if (error) {
          console.log(`❌ Authorization error: ${error}`);
          res.writeHead(400, { 'Content-Type': 'text/html' });
          res.end(`
            <html>
              <body>
                <h1>Authorization Failed</h1>
                <p>Error: ${error}</p>
              </body>
            </html>
          `);
          reject(new Error(`OAuth authorization failed: ${error}`));
        } else {
          console.log(`❌ No authorization code or error in callback`);
          res.writeHead(400);
          res.end('Bad request');
          reject(new Error('No authorization code provided'));
        }
      });

      server.listen(CALLBACK_PORT, () => {
        console.log(`OAuth callback server started on http://localhost:${CALLBACK_PORT}`);
      });
    });
  }

  private async attemptConnection(oauthProvider: InMemoryOAuthClientProvider): Promise<void> {
    console.log('🚢 Creating transport with OAuth provider...');
    const baseUrl = new URL(this.serverUrl);
    const transport = new StreamableHTTPClientTransport(baseUrl, {
      authProvider: oauthProvider
    });
    console.log('🚢 Transport created');

    try {
      console.log('🔌 Attempting connection (this will trigger OAuth redirect)...');
      await this.client!.connect(transport);
      console.log('✅ Connected successfully');
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        console.log('🔐 OAuth required - waiting for authorization...');
        const callbackPromise = this.waitForOAuthCallback();
        const authCode = await callbackPromise;
        await transport.finishAuth(authCode);
        console.log('🔐 Authorization code received:', authCode);
        console.log('🔌 Reconnecting with authenticated transport...');
        await this.attemptConnection(oauthProvider);
      } else {
        console.error('❌ Connection failed with non-auth error:', error);
        throw error;
      }
    }
  }

  /**
   * Establishes connection to the MCP server with OAuth authentication
   */
  async connect(): Promise<void> {
    console.log(`🔗 Attempting to connect to ${this.serverUrl}...`);

    const clientMetadata: OAuthClientMetadata = {
      client_name: 'Simple OAuth MCP Client',
      redirect_uris: [CALLBACK_URL],
      grant_types: ['authorization_code', 'refresh_token'],
      response_types: ['code'],
      token_endpoint_auth_method: 'client_secret_post',
      scope: 'mcp:tools'
    };

    console.log('🔐 Creating OAuth provider...');
    const oauthProvider = new InMemoryOAuthClientProvider(
      CALLBACK_URL,
      clientMetadata,
      (redirectUrl: URL) => {
        console.log(`📌 OAuth redirect handler called - opening browser`);
        console.log(`Opening browser to: ${redirectUrl.toString()}`);
        this.openBrowser(redirectUrl.toString());
      }
    );
    console.log('🔐 OAuth provider created');

    console.log('👤 Creating MCP client...');
    this.client = new Client({
      name: 'simple-oauth-client',
      version: '1.0.0',
    }, { capabilities: {} });
    console.log('👤 Client created');

    console.log('🔐 Starting OAuth flow...');

    await this.attemptConnection(oauthProvider);

    // Start interactive loop
    await this.interactiveLoop();
  }

  /**
   * Main interactive loop for user commands
   */
  async interactiveLoop(): Promise<void> {
    console.log('\n🎯 Interactive MCP Client with OAuth');
    console.log('Commands:');
    console.log('  list - List available tools');
    console.log('  call <tool_name> [args] - Call a tool');
    console.log('  quit - Exit the client');
    console.log();

    while (true) {
      try {
        const command = await this.question('mcp> ');

        if (!command.trim()) {
          continue;
        }

        if (command === 'quit') {
          console.log('\n👋 Goodbye!');
          this.close();
          process.exit(0);
        } else if (command === 'list') {
          await this.listTools();
        } else if (command.startsWith('call ')) {
          await this.handleCallTool(command);
        } else {
          console.log('❌ Unknown command. Try \'list\', \'call <tool_name>\', or \'quit\'');
        }
      } catch (error) {
        if (error instanceof Error && error.message === 'SIGINT') {
          console.log('\n\n👋 Goodbye!');
          break;
        }
        console.error('❌ Error:', error);
      }
    }
  }

  private async listTools(): Promise<void> {
    if (!this.client) {
      console.log('❌ Not connected to server');
      return;
    }

    try {
      const request: ListToolsRequest = {
        method: 'tools/list',
        params: {},
      };

      const result = await this.client.request(request, ListToolsResultSchema);

      if (result.tools && result.tools.length > 0) {
        console.log('\n📋 Available tools:');
        result.tools.forEach((tool, index) => {
          console.log(`${index + 1}. ${tool.name}`);
          if (tool.description) {
            console.log(`   Description: ${tool.description}`);
          }
          console.log();
        });
      } else {
        console.log('No tools available');
      }
    } catch (error) {
      console.error('❌ Failed to list tools:', error);
    }
  }

  private async handleCallTool(command: string): Promise<void> {
    const parts = command.split(/\s+/);
    const toolName = parts[1];

    if (!toolName) {
      console.log('❌ Please specify a tool name');
      return;
    }

    // Parse arguments (simple JSON-like format)
    let toolArgs: Record<string, unknown> = {};
    if (parts.length > 2) {
      const argsString = parts.slice(2).join(' ');
      try {
        toolArgs = JSON.parse(argsString);
      } catch {
        console.log('❌ Invalid arguments format (expected JSON)');
        return;
      }
    }

    await this.callTool(toolName, toolArgs);
  }

  private async callTool(toolName: string, toolArgs: Record<string, unknown>): Promise<void> {
    if (!this.client) {
      console.log('❌ Not connected to server');
      return;
    }

    try {
      const request: CallToolRequest = {
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: toolArgs,
        },
      };

      const result = await this.client.request(request, CallToolResultSchema);

      console.log(`\n🔧 Tool '${toolName}' result:`);
      if (result.content) {
        result.content.forEach((content) => {
          if (content.type === 'text') {
            console.log(content.text);
          } else {
            console.log(content);
          }
        });
      } else {
        console.log(result);
      }
    } catch (error) {
      console.error(`❌ Failed to call tool '${toolName}':`, error);
    }
  }

  close(): void {
    this.rl.close();
    if (this.client) {
      // Note: Client doesn't have a close method in the current implementation
      // This would typically close the transport connection
    }
  }
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  const serverUrl = process.env.MCP_SERVER_URL || DEFAULT_SERVER_URL;

  console.log('🚀 Simple MCP OAuth Client');
  console.log(`Connecting to: ${serverUrl}`);
  console.log();

  const client = new InteractiveOAuthClient(serverUrl);

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n\n👋 Goodbye!');
    client.close();
    process.exit(0);
  });

  try {
    await client.connect();
  } catch (error) {
    console.error('Failed to start client:', error);
    process.exit(1);
  } finally {
    client.close();
  }
}

// Run if this file is executed directly
main().catch((error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});


================================================
FILE: src/examples/client/simpleStreamableHttp.ts
================================================
import { Client } from '../../client/index.js';
import { StreamableHTTPClientTransport } from '../../client/streamableHttp.js';
import { createInterface } from 'node:readline';
import {
  ListToolsRequest,
  ListToolsResultSchema,
  CallToolRequest,
  CallToolResultSchema,
  ListPromptsRequest,
  ListPromptsResultSchema,
  GetPromptRequest,
  GetPromptResultSchema,
  ListResourcesRequest,
  ListResourcesResultSchema,
  LoggingMessageNotificationSchema,
  ResourceListChangedNotificationSchema,
  ElicitRequestSchema,
  ResourceLink,
  ReadResourceRequest,
  ReadResourceResultSchema,
} from '../../types.js';
import { getDisplayName } from '../../shared/metadataUtils.js';
import Ajv from "ajv";

// Create readline interface for user input
const readline = createInterface({
  input: process.stdin,
  output: process.stdout
});

// Track received notifications for debugging resumability
let notificationCount = 0;

// Global client and transport for interactive commands
let client: Client | null = null;
let transport: StreamableHTTPClientTransport | null = null;
let serverUrl = 'http://localhost:3000/mcp';
let notificationsToolLastEventId: string | undefined = undefined;
let sessionId: string | undefined = undefined;

async function main(): Promise<void> {
  console.log('MCP Interactive Client');
  console.log('=====================');

  // Connect to server immediately with default settings
  await connect();

  // Print help and start the command loop
  printHelp();
  commandLoop();
}

function printHelp(): void {
  console.log('\nAvailable commands:');
  console.log('  connect [url]              - Connect to MCP server (default: http://localhost:3000/mcp)');
  console.log('  disconnect                 - Disconnect from server');
  console.log('  terminate-session          - Terminate the current session');
  console.log('  reconnect                  - Reconnect to the server');
  console.log('  list-tools                 - List available tools');
  console.log('  call-tool <name> [args]    - Call a tool with optional JSON arguments');
  console.log('  greet [name]               - Call the greet tool');
  console.log('  multi-greet [name]         - Call the multi-greet tool with notifications');
  console.log('  collect-info [type]        - Test elicitation with collect-user-info tool (contact/preferences/feedback)');
  console.log('  start-notifications [interval] [count] - Start periodic notifications');
  console.log('  run-notifications-tool-with-resumability [interval] [count] - Run notification tool with resumability');
  console.log('  list-prompts               - List available prompts');
  console.log('  get-prompt [name] [args]   - Get a prompt with optional JSON arguments');
  console.log('  list-resources             - List available resources');
  console.log('  read-resource <uri>        - Read a specific resource by URI');
  console.log('  help                       - Show this help');
  console.log('  quit                       - Exit the program');
}

function commandLoop(): void {
  readline.question('\n> ', async (input) => {
    const args = input.trim().split(/\s+/);
    const command = args[0]?.toLowerCase();

    try {
      switch (command) {
        case 'connect':
          await connect(args[1]);
          break;

        case 'disconnect':
          await disconnect();
          break;

        case 'terminate-session':
          await terminateSession();
          break;

        case 'reconnect':
          await reconnect();
          break;

        case 'list-tools':
          await listTools();
          break;

        case 'call-tool':
          if (args.length < 2) {
            console.log('Usage: call-tool <name> [args]');
          } else {
            const toolName = args[1];
            let toolArgs = {};
            if (args.length > 2) {
              try {
                toolArgs = JSON.parse(args.slice(2).join(' '));
              } catch {
                console.log('Invalid JSON arguments. Using empty args.');
              }
            }
            await callTool(toolName, toolArgs);
          }
          break;

        case 'greet':
          await callGreetTool(args[1] || 'MCP User');
          break;

        case 'multi-greet':
          await callMultiGreetTool(args[1] || 'MCP User');
          break;

        case 'collect-info':
          await callCollectInfoTool(args[1] || 'contact');
          break;

        case 'start-notifications': {
          const interval = args[1] ? parseInt(args[1], 10) : 2000;
          const count = args[2] ? parseInt(args[2], 10) : 10;
          await startNotifications(interval, count);
          break;
        }

        case 'run-notifications-tool-with-resumability': {
          const interval = args[1] ? parseInt(args[1], 10) : 2000;
          const count = args[2] ? parseInt(args[2], 10) : 10;
          await runNotificationsToolWithResumability(interval, count);
          break;
        }

        case 'list-prompts':
          await listPrompts();
          break;

        case 'get-prompt':
          if (args.length < 2) {
            console.log('Usage: get-prompt <name> [args]');
          } else {
            const promptName = args[1];
            let promptArgs = {};
            if (args.length > 2) {
              try {
                promptArgs = JSON.parse(args.slice(2).join(' '));
              } catch {
                console.log('Invalid JSON arguments. Using empty args.');
              }
            }
            await getPrompt(promptName, promptArgs);
          }
          break;

        case 'list-resources':
          await listResources();
          break;

        case 'read-resource':
          if (args.length < 2) {
            console.log('Usage: read-resource <uri>');
          } else {
            await readResource(args[1]);
          }
          break;

        case 'help':
          printHelp();
          break;

        case 'quit':
        case 'exit':
          await cleanup();
          return;

        default:
          if (command) {
            console.log(`Unknown command: ${command}`);
          }
          break;
      }
    } catch (error) {
      console.error(`Error executing command: ${error}`);
    }

    // Continue the command loop
    commandLoop();
  });
}

async function connect(url?: string): Promise<void> {
  if (client) {
    console.log('Already connected. Disconnect first.');
    return;
  }

  if (url) {
    serverUrl = url;
  }

  console.log(`Connecting to ${serverUrl}...`);

  try {
    // Create a new client with elicitation capability
    client = new Client({
      name: 'example-client',
      version: '1.0.0'
    }, {
      capabilities: {
        elicitation: {},
      },
    });
    client.onerror = (error) => {
      console.error('\x1b[31mClient error:', error, '\x1b[0m');
    }

    // Set up elicitation request handler with proper validation
    client.setRequestHandler(ElicitRequestSchema, async (request) => {
      console.log('\n🔔 Elicitation Request Received:');
      console.log(`Message: ${request.params.message}`);
      console.log('Requested Schema:');
      console.log(JSON.stringify(request.params.requestedSchema, null, 2));

      const schema = request.params.requestedSchema;
      const properties = schema.properties;
      const required = schema.required || [];

      // Set up AJV validator for the requested schema
      const ajv = new Ajv();
      const validate = ajv.compile(schema);

      let attempts = 0;
      const maxAttempts = 3;

      while (attempts < maxAttempts) {
        attempts++;
        console.log(`\nPlease provide the following information (attempt ${attempts}/${maxAttempts}):`);

        const content: Record<string, unknown> = {};
        let inputCancelled = false;

        // Collect input for each field
        for (const [fieldName, fieldSchema] of Object.entries(properties)) {
          const field = fieldSchema as {
            type?: string;
            title?: string;
            description?: string;
            default?: unknown;
            enum?: string[];
            minimum?: number;
            maximum?: number;
            minLength?: number;
            maxLength?: number;
            format?: string;
          };

          const isRequired = required.includes(fieldName);
          let prompt = `${field.title || fieldName}`;

          // Add helpful information to the prompt
          if (field.description) {
            prompt += ` (${field.description})`;
          }
          if (field.enum) {
            prompt += ` [options: ${field.enum.join(', ')}]`;
          }
          if (field.type === 'number' || field.type === 'integer') {
            if (field.minimum !== undefined && field.maximum !== undefined) {
              prompt += ` [${field.minimum}-${field.maximum}]`;
            } else if (field.minimum !== undefined) {
              prompt += ` [min: ${field.minimum}]`;
            } else if (field.maximum !== undefined) {
              prompt += ` [max: ${field.maximum}]`;
            }
          }
          if (field.type === 'string' && field.format) {
            prompt += ` [format: ${field.format}]`;
          }
          if (isRequired) {
            prompt += ' *required*';
          }
          if (field.default !== undefined) {
            prompt += ` [default: ${field.default}]`;
          }

          prompt += ': ';

          const answer = await new Promise<string>((resolve) => {
            readline.question(prompt, (input) => {
              resolve(input.trim());
            });
          });

          // Check for cancellation
          if (answer.toLowerCase() === 'cancel' || answer.toLowerCase() === 'c') {
            inputCancelled = true;
            break;
          }

          // Parse and validate the input
          try {
            if (answer === '' && field.default !== undefined) {
              content[fieldName] = field.default;
            } else if (answer === '' && !isRequired) {
              // Skip optional empty fields
              continue;
            } else if (answer === '') {
              throw new Error(`${fieldName} is required`);
            } else {
              // Parse the value based on type
              let parsedValue: unknown;

              if (field.type === 'boolean') {
                parsedValue = answer.toLowerCase() === 'true' || answer.toLowerCase() === 'yes' || answer === '1';
              } else if (field.type === 'number') {
                parsedValue = parseFloat(answer);
                if (isNaN(parsedValue as number)) {
                  throw new Error(`${fieldName} must be a valid number`);
                }
              } else if (field.type === 'integer') {
                parsedValue = parseInt(answer, 10);
                if (isNaN(parsedValue as number)) {
                  throw new Error(`${fieldName} must be a valid integer`);
                }
              } else if (field.enum) {
                if (!field.enum.includes(answer)) {
                  throw new Error(`${fieldName} must be one of: ${field.enum.join(', ')}`);
                }
                parsedValue = answer;
              } else {
                parsedValue = answer;
              }

              content[fieldName] = parsedValue;
            }
          } catch (error) {
            console.log(`❌ Error: ${error}`);
            // Continue to next attempt
            break;
          }
        }

        if (inputCancelled) {
          return { action: 'cancel' };
        }

        // If we didn't complete all fields due to an error, try again
        if (Object.keys(content).length !== Object.keys(properties).filter(name =>
          required.includes(name) || content[name] !== undefined
        ).length) {
          if (attempts < maxAttempts) {
            console.log('Please try again...');
            continue;
          } else {
            console.log('Maximum attempts reached. Declining request.');
            return { action: 'decline' };
          }
        }

        // Validate the complete object against the schema
        const isValid = validate(content);

        if (!isValid) {
          console.log('❌ Validation errors:');
          validate.errors?.forEach(error => {
            console.log(`  - ${error.dataPath || 'root'}: ${error.message}`);
          });

          if (attempts < maxAttempts) {
            console.log('Please correct the errors and try again...');
            continue;
          } else {
            console.log('Maximum attempts reached. Declining request.');
            return { action: 'decline' };
          }
        }

        // Show the collected data and ask for confirmation
        console.log('\n✅ Collected data:');
        console.log(JSON.stringify(content, null, 2));

        const confirmAnswer = await new Promise<string>((resolve) => {
          readline.question('\nSubmit this information? (yes/no/cancel): ', (input) => {
            resolve(input.trim().toLowerCase());
          });
        });


        if (confirmAnswer === 'yes' || confirmAnswer === 'y') {
          return {
            action: 'accept',
            content,
          };
        } else if (confirmAnswer === 'cancel' || confirmAnswer === 'c') {
          return { action: 'cancel' };
        } else if (confirmAnswer === 'no' || confirmAnswer === 'n') {
          if (attempts < maxAttempts) {
            console.log('Please re-enter the information...');
            continue;
          } else {
            return { action: 'decline' };
          }
        }
      }

      console.log('Maximum attempts reached. Declining request.');
      return { action: 'decline' };
    });

    transport = new StreamableHTTPClientTransport(
      new URL(serverUrl),
      {
        sessionId: sessionId
      }
    );

    // Set up notification handlers
    client.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
      notificationCount++;
      console.log(`\nNotification #${notificationCount}: ${notification.params.level} - ${notification.params.data}`);
      // Re-display the prompt
      process.stdout.write('> ');
    });

    client.setNotificationHandler(ResourceListChangedNotificationSchema, async (_) => {
      console.log(`\nResource list changed notification received!`);
      try {
        if (!client) {
          console.log('Client disconnected, cannot fetch resources');
          return;
        }
        const resourcesResult = await client.request({
          method: 'resources/list',
          params: {}
        }, ListResourcesResultSchema);
        console.log('Available resources count:', resourcesResult.resources.length);
      } catch {
        console.log('Failed to list resources after change notification');
      }
      // Re-display the prompt
      process.stdout.write('> ');
    });

    // Connect the client
    await client.connect(transport);
    sessionId = transport.sessionId
    console.log('Transport created with session ID:', sessionId);
    console.log('Connected to MCP server');
  } catch (error) {
    console.error('Failed to connect:', error);
    client = null;
    transport = null;
  }
}

async function disconnect(): Promise<void> {
  if (!client || !transport) {
    console.log('Not connected.');
    return;
  }

  try {
    await transport.close();
    console.log('Disconnected from MCP server');
    client = null;
    transport = null;
  } catch (error) {
    console.error('Error disconnecting:', error);
  }
}

async function terminateSession(): Promise<void> {
  if (!client || !transport) {
    console.log('Not connected.');
    return;
  }

  try {
    console.log('Terminating session with ID:', transport.sessionId);
    await transport.terminateSession();
    console.log('Session terminated successfully');

    // Check if sessionId was cleared after termination
    if (!transport.sessionId) {
      console.log('Session ID has been cleared');
      sessionId = undefined;

      // Also close the transport and clear client objects
      await transport.close();
      console.log('Transport closed after session termination');
      client = null;
      transport = null;
    } else {
      console.log('Server responded with 405 Method Not Allowed (session termination not supported)');
      console.log('Session ID is still active:', transport.sessionId);
    }
  } catch (error) {
    console.error('Error terminating session:', error);
  }
}

async function reconnect(): Promise<void> {
  if (client) {
    await disconnect();
  }
  await connect();
}

async function listTools(): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    const toolsRequest: ListToolsRequest = {
      method: 'tools/list',
      params: {}
    };
    const toolsResult = await client.request(toolsRequest, ListToolsResultSchema);

    console.log('Available tools:');
    if (toolsResult.tools.length === 0) {
      console.log('  No tools available');
    } else {
      for (const tool of toolsResult.tools) {
        console.log(`  - id: ${tool.name}, name: ${getDisplayName(tool)}, description: ${tool.description}`);
      }
    }
  } catch (error) {
    console.log(`Tools not supported by this server (${error})`);
  }
}

async function callTool(name: string, args: Record<string, unknown>): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    const request: CallToolRequest = {
      method: 'tools/call',
      params: {
        name,
        arguments: args
      }
    };

    console.log(`Calling tool '${name}' with args:`, args);
    const result = await client.request(request, CallToolResultSchema);

    console.log('Tool result:');
    const resourceLinks: ResourceLink[] = [];

    result.content.forEach(item => {
      if (item.type === 'text') {
        console.log(`  ${item.text}`);
      } else if (item.type === 'resource_link') {
        const resourceLink = item as ResourceLink;
        resourceLinks.push(resourceLink);
        console.log(`  📁 Resource Link: ${resourceLink.name}`);
        console.log(`     URI: ${resourceLink.uri}`);
        if (resourceLink.mimeType) {
          console.log(`     Type: ${resourceLink.mimeType}`);
        }
        if (resourceLink.description) {
          console.log(`     Description: ${resourceLink.description}`);
        }
      } else if (item.type === 'resource') {
        console.log(`  [Embedded Resource: ${item.resource.uri}]`);
      } else if (item.type === 'image') {
        console.log(`  [Image: ${item.mimeType}]`);
      } else if (item.type === 'audio') {
        console.log(`  [Audio: ${item.mimeType}]`);
      } else {
        console.log(`  [Unknown content type]:`, item);
      }
    });

    // Offer to read resource links
    if (resourceLinks.length > 0) {
      console.log(`\nFound ${resourceLinks.length} resource link(s). Use 'read-resource <uri>' to read their content.`);
    }
  } catch (error) {
    console.log(`Error calling tool ${name}: ${error}`);
  }
}


async function callGreetTool(name: string): Promise<void> {
  await callTool('greet', { name });
}

async function callMultiGreetTool(name: string): Promise<void> {
  console.log('Calling multi-greet tool with notifications...');
  await callTool('multi-greet', { name });
}

async function callCollectInfoTool(infoType: string): Promise<void> {
  console.log(`Testing elicitation with collect-user-info tool (${infoType})...`);
  await callTool('collect-user-info', { infoType });
}

async function startNotifications(interval: number, count: number): Promise<void> {
  console.log(`Starting notification stream: interval=${interval}ms, count=${count || 'unlimited'}`);
  await callTool('start-notification-stream', { interval, count });
}

async function runNotificationsToolWithResumability(interval: number, count: number): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    console.log(`Starting notification stream with resumability: interval=${interval}ms, count=${count || 'unlimited'}`);
    console.log(`Using resumption token: ${notificationsToolLastEventId || 'none'}`);

    const request: CallToolRequest = {
      method: 'tools/call',
      params: {
        name: 'start-notification-stream',
        arguments: { interval, count }
      }
    };

    const onLastEventIdUpdate = (event: string) => {
      notificationsToolLastEventId = event;
      console.log(`Updated resumption token: ${event}`);
    };

    const result = await client.request(request, CallToolResultSchema, {
      resumptionToken: notificationsToolLastEventId,
      onresumptiontoken: onLastEventIdUpdate
    });

    console.log('Tool result:');
    result.content.forEach(item => {
      if (item.type === 'text') {
        console.log(`  ${item.text}`);
      } else {
        console.log(`  ${item.type} content:`, item);
      }
    });
  } catch (error) {
    console.log(`Error starting notification stream: ${error}`);
  }
}

async function listPrompts(): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    const promptsRequest: ListPromptsRequest = {
      method: 'prompts/list',
      params: {}
    };
    const promptsResult = await client.request(promptsRequest, ListPromptsResultSchema);
    console.log('Available prompts:');
    if (promptsResult.prompts.length === 0) {
      console.log('  No prompts available');
    } else {
      for (const prompt of promptsResult.prompts) {
        console.log(`  - id: ${prompt.name}, name: ${getDisplayName(prompt)}, description: ${prompt.description}`);
      }
    }
  } catch (error) {
    console.log(`Prompts not supported by this server (${error})`);
  }
}

async function getPrompt(name: string, args: Record<string, unknown>): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    const promptRequest: GetPromptRequest = {
      method: 'prompts/get',
      params: {
        name,
        arguments: args as Record<string, string>
      }
    };

    const promptResult = await client.request(promptRequest, GetPromptResultSchema);
    console.log('Prompt template:');
    promptResult.messages.forEach((msg, index) => {
      console.log(`  [${index + 1}] ${msg.role}: ${msg.content.text}`);
    });
  } catch (error) {
    console.log(`Error getting prompt ${name}: ${error}`);
  }
}

async function listResources(): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    const resourcesRequest: ListResourcesRequest = {
      method: 'resources/list',
      params: {}
    };
    const resourcesResult = await client.request(resourcesRequest, ListResourcesResultSchema);

    console.log('Available resources:');
    if (resourcesResult.resources.length === 0) {
      console.log('  No resources available');
    } else {
      for (const resource of resourcesResult.resources) {
        console.log(`  - id: ${resource.name}, name: ${getDisplayName(resource)}, description: ${resource.uri}`);
      }
    }
  } catch (error) {
    console.log(`Resources not supported by this server (${error})`);
  }
}

async function readResource(uri: string): Promise<void> {
  if (!client) {
    console.log('Not connected to server.');
    return;
  }

  try {
    const request: ReadResourceRequest = {
      method: 'resources/read',
      params: { uri }
    };

    console.log(`Reading resource: ${uri}`);
    const result = await client.request(request, ReadResourceResultSchema);

    console.log('Resource contents:');
    for (const content of result.contents) {
      console.log(`  URI: ${content.uri}`);
      if (content.mimeType) {
        console.log(`  Type: ${content.mimeType}`);
      }

      if ('text' in content && typeof content.text === 'string') {
        console.log('  Content:');
        console.log('  ---');
        console.log(content.text.split('\n').map((line: string) => '  ' + line).join('\n'));
        console.log('  ---');
      } else if ('blob' in content && typeof content.blob === 'string') {
        console.log(`  [Binary data: ${content.blob.length} bytes]`);
      }
    }
  } catch (error) {
    console.log(`Error reading resource ${uri}: ${error}`);
  }
}

async function cleanup(): Promise<void> {
  if (client && transport) {
    try {
      // First try to terminate the session gracefully
      if (transport.sessionId) {
        try {
          console.log('Terminating session before exit...');
          await transport.terminateSession();
          console.log('Session terminated successfully');
        } catch (error) {
          console.error('Error terminating session:', error);
        }
      }

      // Then close the transport
      await transport.close();
    } catch (error) {
      console.error('Error closing transport:', error);
    }
  }

  process.stdin.setRawMode(false);
  readline.close();
  console.log('\nGoodbye!');
  process.exit(0);
}

// Set up raw mode for keyboard input to capture Escape key
process.stdin.setRawMode(true);
process.stdin.on('data', async (data) => {
  // Check for Escape key (27)
  if (data.length === 1 && data[0] === 27) {
    console.log('\nESC key pressed. Disconnecting from server...');

    // Abort current operation and disconnect from server
    if (client && transport) {
      await disconnect();
      console.log('Disconnected. Press Enter to continue.');
    } else {
      console.log('Not connected to server.');
    }

    // Re-display the prompt
    process.stdout.write('> ');
  }
});

// Handle Ctrl+C
process.on('SIGINT', async () => {
  console.log('\nReceived SIGINT. Cleaning up...');
  await cleanup();
});

// Start the interactive client
main().catch((error: unknown) => {
  console.error('Error running MCP client:', error);
  process.exit(1);
});


================================================
FILE: src/examples/client/streamableHttpWithSseFallbackClient.ts
================================================
import { Client } from '../../client/index.js';
import { StreamableHTTPClientTransport } from '../../client/streamableHttp.js';
import { SSEClientTransport } from '../../client/sse.js';
import {
  ListToolsRequest,
  ListToolsResultSchema,
  CallToolRequest,
  CallToolResultSchema,
  LoggingMessageNotificationSchema,
} from '../../types.js';

/**
 * Simplified Backwards Compatible MCP Client
 * 
 * This client demonstrates backward compatibility with both:
 * 1. Modern servers using Streamable HTTP transport (protocol version 2025-03-26)
 * 2. Older servers using HTTP+SSE transport (protocol version 2024-11-05)
 * 
 * Following the MCP specification for backwards compatibility:
 * - Attempts to POST an initialize request to the server URL first (modern transport)
 * - If that fails with 4xx status, falls back to GET request for SSE stream (older transport)
 */

// Command line args processing
const args = process.argv.slice(2);
const serverUrl = args[0] || 'http://localhost:3000/mcp';

async function main(): Promise<void> {
  console.log('MCP Backwards Compatible Client');
  console.log('===============================');
  console.log(`Connecting to server at: ${serverUrl}`);

  let client: Client;
  let transport: StreamableHTTPClientTransport | SSEClientTransport;

  try {
    // Try connecting with automatic transport detection
    const connection = await connectWithBackwardsCompatibility(serverUrl);
    client = connection.client;
    transport = connection.transport;

    // Set up notification handler
    client.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
      console.log(`Notification: ${notification.params.level} - ${notification.params.data}`);
    });

    // DEMO WORKFLOW:
    // 1. List available tools
    console.log('\n=== Listing Available Tools ===');
    await listTools(client);

    // 2. Call the notification tool
    console.log('\n=== Starting Notification Stream ===');
    await startNotificationTool(client);

    // 3. Wait for all notifications (5 seconds)
    console.log('\n=== Waiting for all notifications ===');
    await new Promise(resolve => setTimeout(resolve, 5000));

    // 4. Disconnect
    console.log('\n=== Disconnecting ===');
    await transport.close();
    console.log('Disconnected from MCP server');

  } catch (error) {
    console.error('Error running client:', error);
    process.exit(1);
  }
}

/**
 * Connect to an MCP server with backwards compatibility
 * Following the spec for client backward compatibility
 */
async function connectWithBackwardsCompatibility(url: string): Promise<{
  client: Client,
  transport: StreamableHTTPClientTransport | SSEClientTransport,
  transportType: 'streamable-http' | 'sse'
}> {
  console.log('1. Trying Streamable HTTP transport first...');

  // Step 1: Try Streamable HTTP transport first
  const client = new Client({
    name: 'backwards-compatible-client',
    version: '1.0.0'
  });

  client.onerror = (error) => {
    console.error('Client error:', error);
  };
  const baseUrl = new URL(url);

  try {
    // Create modern transport
    const streamableTransport = new StreamableHTTPClientTransport(baseUrl);
    await client.connect(streamableTransport);

    console.log('Successfully connected using modern Streamable HTTP transport.');
    return {
      client,
      transport: streamableTransport,
      transportType: 'streamable-http'
    };
  } catch (error) {
    // Step 2: If transport fails, try the older SSE transport
    console.log(`StreamableHttp transport connection failed: ${error}`);
    console.log('2. Falling back to deprecated HTTP+SSE transport...');

    try {
      // Create SSE transport pointing to /sse endpoint
      const sseTransport = new SSEClientTransport(baseUrl);
      const sseClient = new Client({
        name: 'backwards-compatible-client',
        version: '1.0.0'
      });
      await sseClient.connect(sseTransport);

      console.log('Successfully connected using deprecated HTTP+SSE transport.');
      return {
        client: sseClient,
        transport: sseTransport,
        transportType: 'sse'
      };
    } catch (sseError) {
      console.error(`Failed to connect with either transport method:\n1. Streamable HTTP error: ${error}\n2. SSE error: ${sseError}`);
      throw new Error('Could not connect to server with any available transport');
    }
  }
}

/**
 * List available tools on the server
 */
async function listTools(client: Client): Promise<void> {
  try {
    const toolsRequest: ListToolsRequest = {
      method: 'tools/list',
      params: {}
    };
    const toolsResult = await client.request(toolsRequest, ListToolsResultSchema);

    console.log('Available tools:');
    if (toolsResult.tools.length === 0) {
      console.log('  No tools available');
    } else {
      for (const tool of toolsResult.tools) {
        console.log(`  - ${tool.name}: ${tool.description}`);
      }
    }
  } catch (error) {
    console.log(`Tools not supported by this server: ${error}`);
  }
}

/**
 * Start a notification stream by calling the notification tool
 */
async function startNotificationTool(client: Client): Promise<void> {
  try {
    // Call the notification tool using reasonable defaults
    const request: CallToolRequest = {
      method: 'tools/call',
      params: {
        name: 'start-notification-stream',
        arguments: {
          interval: 1000, // 1 second between notifications
          count: 5       // Send 5 notifications
        }
      }
    };

    console.log('Calling notification tool...');
    const result = await client.request(request, CallToolResultSchema);

    console.log('Tool result:');
    result.content.forEach(item => {
      if (item.type === 'text') {
        console.log(`  ${item.text}`);
      } else {
        console.log(`  ${item.type} content:`, item);
      }
    });
  } catch (error) {
    console.log(`Error calling notification tool: ${error}`);
  }
}

// Start the client
main().catch((error: unknown) => {
  console.error('Error running MCP client:', error);
  process.exit(1);
});


================================================
FILE: src/examples/server/demoInMemoryOAuthProvider.ts
================================================
import { randomUUID } from 'node:crypto';
import { AuthorizationParams, OAuthServerProvider } from '../../server/auth/provider.js';
import { OAuthRegisteredClientsStore } from '../../server/auth/clients.js';
import { OAuthClientInformationFull, OAuthMetadata, OAuthTokens } from '../../shared/auth.js';
import express, { Request, Response } from "express";
import { AuthInfo } from '../../server/auth/types.js';
import { createOAuthMetadata, mcpAuthRouter } from '../../server/auth/router.js';
import { resourceUrlFromServerUrl } from '../../shared/auth-utils.js';


export class DemoInMemoryClientsStore implements OAuthRegisteredClientsStore {
  private clients = new Map<string, OAuthClientInformationFull>();

  async getClient(clientId: string) {
    return this.clients.get(clientId);
  }

  async registerClient(clientMetadata: OAuthClientInformationFull) {
    this.clients.set(clientMetadata.client_id, clientMetadata);
    return clientMetadata;
  }
}

/**
 * 🚨 DEMO ONLY - NOT FOR PRODUCTION
 *
 * This example demonstrates MCP OAuth flow but lacks some of the features required for production use,
 * for example:
 * - Persistent token storage
 * - Rate limiting
 */
export class DemoInMemoryAuthProvider implements OAuthServerProvider {
  clientsStore = new DemoInMemoryClientsStore();
  private codes = new Map<string, {
    params: AuthorizationParams,
    client: OAuthClientInformationFull}>();
  private tokens = new Map<string, AuthInfo>();

  constructor(private validateResource?: (resource?: URL) => boolean) {}

  async authorize(
    client: OAuthClientInformationFull,
    params: AuthorizationParams,
    res: Response
  ): Promise<void> {
    const code = randomUUID();

    const searchParams = new URLSearchParams({
      code,
    });
    if (params.state !== undefined) {
      searchParams.set('state', params.state);
    }

    this.codes.set(code, {
      client,
      params
    });

    const targetUrl = new URL(client.redirect_uris[0]);
    targetUrl.search = searchParams.toString();
    res.redirect(targetUrl.toString());
  }

  async challengeForAuthorizationCode(
    client: OAuthClientInformationFull,
    authorizationCode: string
  ): Promise<string> {

    // Store the challenge with the code data
    const codeData = this.codes.get(authorizationCode);
    if (!codeData) {
      throw new Error('Invalid authorization code');
    }

    return codeData.params.codeChallenge;
  }

  async exchangeAuthorizationCode(
    client: OAuthClientInformationFull,
    authorizationCode: string,
    // Note: code verifier is checked in token.ts by default
    // it's unused here for that reason.
    _codeVerifier?: string
  ): Promise<OAuthTokens> {
    const codeData = this.codes.get(authorizationCode);
    if (!codeData) {
      throw new Error('Invalid authorization code');
    }

    if (codeData.client.client_id !== client.client_id) {
      throw new Error(`Authorization code was not issued to this client, ${codeData.client.client_id} != ${client.client_id}`);
    }

    if (this.validateResource && !this.validateResource(codeData.params.resource)) {
      throw new Error(`Invalid resource: ${codeData.params.resource}`);
    }

    this.codes.delete(authorizationCode);
    const token = randomUUID();

    const tokenData = {
      token,
      clientId: client.client_id,
      scopes: codeData.params.scopes || [],
      expiresAt: Date.now() + 3600000, // 1 hour
      resource: codeData.params.resource,
      type: 'access',
    };

    this.tokens.set(token, tokenData);

    return {
      access_token: token,
      token_type: 'bearer',
      expires_in: 3600,
      scope: (codeData.params.scopes || []).join(' '),
    };
  }

  async exchangeRefreshToken(
    _client: OAuthClientInformationFull,
    _refreshToken: string,
    _scopes?: string[],
    _resource?: URL
  ): Promise<OAuthTokens> {
    throw new Error('Not implemented for example demo');
  }

  async verifyAccessToken(token: string): Promise<AuthInfo> {
    const tokenData = this.tokens.get(token);
    if (!tokenData || !tokenData.expiresAt || tokenData.expiresAt < Date.now()) {
      throw new Error('Invalid or expired token');
    }

    return {
      token,
      clientId: tokenData.clientId,
      scopes: tokenData.scopes,
      expiresAt: Math.floor(tokenData.expiresAt / 1000),
      resource: tokenData.resource,
    };
  }
}


export const setupAuthServer = ({authServerUrl, mcpServerUrl, strictResource}: {authServerUrl: URL, mcpServerUrl: URL, strictResource: boolean}): OAuthMetadata => {
  // Create separate auth server app
  // NOTE: This is a separate app on a separate port to illustrate
  // how to separate an OAuth Authorization Server from a Resource
  // server in the SDK. The SDK is not intended to be provide a standalone
  // authorization server.

  const validateResource = strictResource ? (resource?: URL) => {
    if (!resource) return false;
    const expectedResource = resourceUrlFromServerUrl(mcpServerUrl);
    return resource.toString() === expectedResource.toString();
  } : undefined;

  const provider = new DemoInMemoryAuthProvider(validateResource);
  const authApp = express();
  authApp.use(express.json());
  // For introspection requests
  authApp.use(express.urlencoded());

  // Add OAuth routes to the auth server
  // NOTE: this will also add a protected resource metadata route,
  // but it won't be used, so leave it.
  authApp.use(mcpAuthRouter({
    provider,
    issuerUrl: authServerUrl,
    scopesSupported: ['mcp:tools'],
  }));

  authApp.post('/introspect', async (req: Request, res: Response) => {
    try {
      const { token } = req.body;
      if (!token) {
        res.status(400).json({ error: 'Token is required' });
        return;
      }

      const tokenInfo = await provider.verifyAccessToken(token);
      res.json({
        active: true,
        client_id: tokenInfo.clientId,
        scope: tokenInfo.scopes.join(' '),
        exp: tokenInfo.expiresAt,
        aud: tokenInfo.resource,
      });
      return
    } catch (error) {
      res.status(401).json({
        active: false,
        error: 'Unauthorized',
        error_description: `Invalid token: ${error}`
      });
    }
  });

  const auth_port = authServerUrl.port;
  // Start the auth server
  authApp.listen(auth_port, (error) => {
    if (error) {
      console.error('Failed to start server:', error);
      process.exit(1);
    }
    console.log(`OAuth Authorization Server listening on port ${auth_port}`);
  });

  // Note: we could fetch this from the server, but then we end up
  // with some top level async which gets annoying.
  const oauthMetadata: OAuthMetadata = createOAuthMetadata({
    provider,
    issuerUrl: authServerUrl,
    scopesSupported: ['mcp:tools'],
  })

  oauthMetadata.introspection_endpoint = new URL("/introspect", authServerUrl).href;

  return oauthMetadata;
}



================================================
FILE: src/examples/server/jsonResponseStreamableHttp.ts
================================================
import express, { Request, Response } from 'express';
import { randomUUID } from 'node:crypto';
import { McpServer } from '../../server/mcp.js';
import { StreamableHTTPServerTransport } from '../../server/streamableHttp.js';
import { z } from 'zod';
import { CallToolResult, isInitializeRequest } from '../../types.js';
import cors from 'cors';


// Create an MCP server with implementation details
const getServer = () => {
  const server = new McpServer({
    name: 'json-response-streamable-http-server',
    version: '1.0.0',
  }, {
    capabilities: {
      logging: {},
    }
  });

  // Register a simple tool that returns a greeting
  server.tool(
    'greet',
    'A simple greeting tool',
    {
      name: z.string().describe('Name to greet'),
    },
    async ({ name }): Promise<CallToolResult> => {
      return {
        content: [
          {
            type: 'text',
            text: `Hello, ${name}!`,
          },
        ],
      };
    }
  );

  // Register a tool that sends multiple greetings with notifications
  server.tool(
    'multi-greet',
    'A tool that sends different greetings with delays between them',
    {
      name: z.string().describe('Name to greet'),
    },
    async ({ name }, { sendNotification }): Promise<CallToolResult> => {
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

      await sendNotification({
        method: "notifications/message",
        params: { level: "debug", data: `Starting multi-greet for ${name}` }
      });

      await sleep(1000); // Wait 1 second before first greeting

      await sendNotification({
        method: "notifications/message",
        params: { level: "info", data: `Sending first greeting to ${name}` }
      });

      await sleep(1000); // Wait another second before second greeting

      await sendNotification({
        method: "notifications/message",
        params: { level: "info", data: `Sending second greeting to ${name}` }
      });

      return {
        content: [
          {
            type: 'text',
            text: `Good morning, ${name}!`,
          }
        ],
      };
    }
  );
  return server;
}

const app = express();
app.use(express.json());

// Configure CORS to expose Mcp-Session-Id header for browser-based clients
app.use(cors({
  origin: '*', // Allow all origins - adjust as needed for production
  exposedHeaders: ['Mcp-Session-Id']
}));

// Map to store transports by session ID
const transports: { [sessionId: string]: StreamableHTTPServerTransport } = {};

app.post('/mcp', async (req: Request, res: Response) => {
  console.log('Received MCP request:', req.body);
  try {
    // Check for existing session ID
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
      // Reuse existing transport
      transport = transports[sessionId];
    } else if (!sessionId && isInitializeRequest(req.body)) {
      // New initialization request - use JSON response mode
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        enableJsonResponse: true, // Enable JSON response mode
        onsessioninitialized: (sessionId) => {
          // Store the transport by session ID when session is initialized
          // This avoids race conditions where requests might come in before the session is stored
          console.log(`Session initialized with ID: ${sessionId}`);
          transports[sessionId] = transport;
        }
      });

      // Connect the transport to the MCP server BEFORE handling the request
      const server = getServer();
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
      return; // Already handled
    } else {
      // Invalid request - no session ID or not initialization request
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided',
        },
        id: null,
      });
      return;
    }

    // Handle the request with existing transport - no need to reconnect
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

// Handle GET requests for SSE streams according to spec
app.get('/mcp', async (req: Request, res: Response) => {
  // Since this is a very simple example, we don't support GET requests for this server
  // The spec requires returning 405 Method Not Allowed in this case
  res.status(405).set('Allow', 'POST').send('Method Not Allowed');
});

// Start the server
const PORT = 3000;
app.listen(PORT, (error) => {
  if (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
  console.log(`MCP Streamable HTTP Server listening on port ${PORT}`);
});

// Handle server shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');
  process.exit(0);
});


================================================
FILE: src/examples/server/mcpServerOutputSchema.ts
================================================
#!/usr/bin/env node
/**
 * Example MCP server using the high-level McpServer API with outputSchema
 * This demonstrates how to easily create tools with structured output
 */

import { McpServer } from "../../server/mcp.js";
import { StdioServerTransport } from "../../server/stdio.js";
import { z } from "zod";

const server = new McpServer(
  {
    name: "mcp-output-schema-high-level-example",
    version: "1.0.0",
  }
);

// Define a tool with structured output - Weather data
server.registerTool(
  "get_weather",
  {
    description: "Get weather information for a city",
    inputSchema: {
      city: z.string().describe("City name"),
      country: z.string().describe("Country code (e.g., US, UK)")
    },
    outputSchema: {
      temperature: z.object({
        celsius: z.number(),
        fahrenheit: z.number()
      }),
      conditions: z.enum(["sunny", "cloudy", "rainy", "stormy", "snowy"]),
      humidity: z.number().min(0).max(100),
      wind: z.object({
        speed_kmh: z.number(),
        direction: z.string()
      })
    },
  },
  async ({ city, country }) => {
    // Parameters are available but not used in this example
    void city;
    void country;
    // Simulate weather API call
    const temp_c = Math.round((Math.random() * 35 - 5) * 10) / 10;
    const conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"][Math.floor(Math.random() * 5)];

    const structuredContent = {
      temperature: {
        celsius: temp_c,
        fahrenheit: Math.round((temp_c * 9 / 5 + 32) * 10) / 10
      },
      conditions,
      humidity: Math.round(Math.random() * 100),
      wind: {
        speed_kmh: Math.round(Math.random() * 50),
        direction: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][Math.floor(Math.random() * 8)]
      }
    };

    return {
      content: [{
        type: "text",
        text: JSON.stringify(structuredContent, null, 2)
      }],
      structuredContent
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("High-level Output Schema Example Server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});


================================================
FILE: src/examples/server/simpleSseServer.ts
================================================
import express, { Request, Response } from 'express';
import { McpServer } from '../../server/mcp.js';
import { SSEServerTransport } from '../../server/sse.js';
import { z } from 'zod';
import { CallToolResult } from '../../types.js';

/**
 * This example server demonstrates the deprecated HTTP+SSE transport 
 * (protocol version 2024-11-05). It mainly used for testing backward compatible clients.
 * 
 * The server exposes two endpoints:
 * - /mcp: For establishing the SSE stream (GET)
 * - /messages: For receiving client messages (POST)
 * 
 */

// Create an MCP server instance
const getServer = () => {
  const server = new McpServer({
    name: 'simple-sse-server',
    version: '1.0.0',
  }, { capabilities: { logging: {} } });

  server.tool(
    'start-notification-stream',
    'Starts sending periodic notifications',
    {
      interval: z.number().describe('Interval in milliseconds between notifications').default(1000),
      count: z.number().describe('Number of notifications to send').default(10),
    },
    async ({ interval, count }, { sendNotification }): Promise<CallToolResult> => {
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
      let counter = 0;

      // Send the initial notification
      await sendNotification({
        method: "notifications/message",
        params: {
          level: "info",
          data: `Starting notification stream with ${count} messages every ${interval}ms`
        }
      });

      // Send periodic notifications
      while (counter < count) {
        counter++;
        await sleep(interval);

        try {
          await sendNotification({
            method: "notifications/message",
            params: {
              level: "info",
              data: `Notification #${counter} at ${new Date().toISOString()}`
            }
          });
        }
        catch (error) {
          console.error("Error sending notification:", error);
        }
      }

      return {
        content: [
          {
            type: 'text',
            text: `Completed sending ${count} notifications every ${interval}ms`,
          }
        ],
      };
    }
  );
  return server;
};

const app = express();
app.use(express.json());

// Store transports by session ID
const transports: Record<string, SSEServerTransport> = {};

// SSE endpoint for establishing the stream
app.get('/mcp', async (req: Request, res: Response) => {
  console.log('Received GET request to /sse (establishing SSE stream)');

  try {
    // Create a new SSE transport for the client
    // The endpoint for POST messages is '/messages'
    const transport = new SSEServerTransport('/messages', res);

    // Store the transport by session ID
    const sessionId = transport.sessionId;
    transports[sessionId] = transport;

    // Set up onclose handler to clean up transport when closed
    transport.onclose = () => {
      console.log(`SSE transport closed for session ${sessionId}`);
      delete transports[sessionId];
    };

    // Connect the transport to the MCP server
    const server = getServer();
    await server.connect(transport);

    console.log(`Established SSE stream with session ID: ${sessionId}`);
  } catch (error) {
    console.error('Error establishing SSE stream:', error);
    if (!res.headersSent) {
      res.status(500).send('Error establishing SSE stream');
    }
  }
});

// Messages endpoint for receiving client JSON-RPC requests
app.post('/messages', async (req: Request, res: Response) => {
  console.log('Received POST request to /messages');

  // Extract session ID from URL query parameter
  // In the SSE protocol, this is added by the client based on the endpoint event
  const sessionId = req.query.sessionId as string | undefined;

  if (!sessionId) {
    console.error('No session ID provided in request URL');
    res.status(400).send('Missing sessionId parameter');
    return;
  }

  const transport = transports[sessionId];
  if (!transport) {
    console.error(`No active transport found for session ID: ${sessionId}`);
    res.status(404).send('Session not found');
    return;
  }

  try {
    // Handle the POST message with the transport
    await transport.handlePostMessage(req, res, req.body);
  } catch (error) {
    console.error('Error handling request:', error);
    if (!res.headersSent) {
      res.status(500).send('Error handling request');
    }
  }
});

// Start the server
const PORT = 3000;
app.listen(PORT, (error) => {
  if (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
  console.log(`Simple SSE Server (deprecated protocol version 2024-11-05) listening on port ${PORT}`);
});

// Handle server shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');

  // Close all active transports to properly clean up resources
  for (const sessionId in transports) {
    try {
      console.log(`Closing transport for session ${sessionId}`);
      await transports[sessionId].close();
      delete transports[sessionId];
    } catch (error) {
      console.error(`Error closing transport for session ${sessionId}:`, error);
    }
  }
  console.log('Server shutdown complete');
  process.exit(0);
});


================================================
FILE: src/examples/server/simpleStatelessStreamableHttp.ts
================================================
import express, { Request, Response } from 'express';
import { McpServer } from '../../server/mcp.js';
import { StreamableHTTPServerTransport } from '../../server/streamableHttp.js';
import { z } from 'zod';
import { CallToolResult, GetPromptResult, ReadResourceResult } from '../../types.js';
import cors from 'cors';

const getServer = () => {
  // Create an MCP server with implementation details
  const server = new McpServer({
    name: 'stateless-streamable-http-server',
    version: '1.0.0',
  }, { capabilities: { logging: {} } });

  // Register a simple prompt
  server.prompt(
    'greeting-template',
    'A simple greeting prompt template',
    {
      name: z.string().describe('Name to include in greeting'),
    },
    async ({ name }): Promise<GetPromptResult> => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Please greet ${name} in a friendly manner.`,
            },
          },
        ],
      };
    }
  );

  // Register a tool specifically for testing resumability
  server.tool(
    'start-notification-stream',
    'Starts sending periodic notifications for testing resumability',
    {
      interval: z.number().describe('Interval in milliseconds between notifications').default(100),
      count: z.number().describe('Number of notifications to send (0 for 100)').default(10),
    },
    async ({ interval, count }, { sendNotification }): Promise<CallToolResult> => {
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
      let counter = 0;

      while (count === 0 || counter < count) {
        counter++;
        try {
          await sendNotification({
            method: "notifications/message",
            params: {
              level: "info",
              data: `Periodic notification #${counter} at ${new Date().toISOString()}`
            }
          });
        }
        catch (error) {
          console.error("Error sending notification:", error);
        }
        // Wait for the specified interval
        await sleep(interval);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Started sending periodic notifications every ${interval}ms`,
          }
        ],
      };
    }
  );

  // Create a simple resource at a fixed URI
  server.resource(
    'greeting-resource',
    'https://example.com/greetings/default',
    { mimeType: 'text/plain' },
    async (): Promise<ReadResourceResult> => {
      return {
        contents: [
          {
            uri: 'https://example.com/greetings/default',
            text: 'Hello, world!',
          },
        ],
      };
    }
  );
  return server;
}

const app = express();
app.use(express.json());

// Configure CORS to expose Mcp-Session-Id header for browser-based clients
app.use(cors({
  origin: '*', // Allow all origins - adjust as needed for production
  exposedHeaders: ['Mcp-Session-Id']
}));

app.post('/mcp', async (req: Request, res: Response) => {
  const server = getServer();
  try {
    const transport: StreamableHTTPServerTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
    res.on('close', () => {
      console.log('Request closed');
      transport.close();
      server.close();
    });
  } catch (error) {
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

app.get('/mcp', async (req: Request, res: Response) => {
  console.log('Received GET MCP request');
  res.writeHead(405).end(JSON.stringify({
    jsonrpc: "2.0",
    error: {
      code: -32000,
      message: "Method not allowed."
    },
    id: null
  }));
});

app.delete('/mcp', async (req: Request, res: Response) => {
  console.log('Received DELETE MCP request');
  res.writeHead(405).end(JSON.stringify({
    jsonrpc: "2.0",
    error: {
      code: -32000,
      message: "Method not allowed."
    },
    id: null
  }));
});


// Start the server
const PORT = 3000;
app.listen(PORT, (error) => {
  if (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
  console.log(`MCP Stateless Streamable HTTP Server listening on port ${PORT}`);
});

// Handle server shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');
  process.exit(0);
});


================================================
FILE: src/examples/server/simpleStreamableHttp.ts
================================================
import express, { Request, Response } from 'express';
import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { McpServer } from '../../server/mcp.js';
import { StreamableHTTPServerTransport } from '../../server/streamableHttp.js';
import { getOAuthProtectedResourceMetadataUrl, mcpAuthMetadataRouter } from '../../server/auth/router.js';
import { requireBearerAuth } from '../../server/auth/middleware/bearerAuth.js';
import { CallToolResult, GetPromptResult, isInitializeRequest, PrimitiveSchemaDefinition, ReadResourceResult, ResourceLink } from '../../types.js';
import { InMemoryEventStore } from '../shared/inMemoryEventStore.js';
import { setupAuthServer } from './demoInMemoryOAuthProvider.js';
import { OAuthMetadata } from 'src/shared/auth.js';
import { checkResourceAllowed } from 'src/shared/auth-utils.js';

import cors from 'cors';

// Check for OAuth flag
const useOAuth = process.argv.includes('--oauth');
const strictOAuth = process.argv.includes('--oauth-strict');

// Create an MCP server with implementation details
const getServer = () => {
  const server = new McpServer({
    name: 'simple-streamable-http-server',
    version: '1.0.0'
  }, { capabilities: { logging: {} } });

  // Register a simple tool that returns a greeting
  server.registerTool(
    'greet',
    {
      title: 'Greeting Tool',  // Display name for UI
      description: 'A simple greeting tool',
      inputSchema: {
        name: z.string().describe('Name to greet'),
      },
    },
    async ({ name }): Promise<CallToolResult> => {
      return {
        content: [
          {
            type: 'text',
            text: `Hello, ${name}!`,
          },
        ],
      };
    }
  );

  // Register a tool that sends multiple greetings with notifications (with annotations)
  server.tool(
    'multi-greet',
    'A tool that sends different greetings with delays between them',
    {
      name: z.string().describe('Name to greet'),
    },
    {
      title: 'Multiple Greeting Tool',
      readOnlyHint: true,
      openWorldHint: false
    },
    async ({ name }, { sendNotification }): Promise<CallToolResult> => {
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

      await sendNotification({
        method: "notifications/message",
        params: { level: "debug", data: `Starting multi-greet for ${name}` }
      });

      await sleep(1000); // Wait 1 second before first greeting

      await sendNotification({
        method: "notifications/message",
        params: { level: "info", data: `Sending first greeting to ${name}` }
      });

      await sleep(1000); // Wait another second before second greeting

      await sendNotification({
        method: "notifications/message",
        params: { level: "info", data: `Sending second greeting to ${name}` }
      });

      return {
        content: [
          {
            type: 'text',
            text: `Good morning, ${name}!`,
          }
        ],
      };
    }
  );
  // Register a tool that demonstrates elicitation (user input collection)
  // This creates a closure that captures the server instance
  server.tool(
    'collect-user-info',
    'A tool that collects user information through elicitation',
    {
      infoType: z.enum(['contact', 'preferences', 'feedback']).describe('Type of information to collect'),
    },
    async ({ infoType }): Promise<CallToolResult> => {
      let message: string;
      let requestedSchema: {
        type: 'object';
        properties: Record<string, PrimitiveSchemaDefinition>;
        required?: string[];
      };

      switch (infoType) {
        case 'contact':
          message = 'Please provide your contact information';
          requestedSchema = {
            type: 'object',
            properties: {
              name: {
                type: 'string',
                title: 'Full Name',
                description: 'Your full name',
              },
              email: {
                type: 'string',
                title: 'Email Address',
                description: 'Your email address',
                format: 'email',
              },
              phone: {
                type: 'string',
                title: 'Phone Number',
                description: 'Your phone number (optional)',
              },
            },
            required: ['name', 'email'],
          };
          break;
        case 'preferences':
          message = 'Please set your preferences';
          requestedSchema = {
            type: 'object',
            properties: {
              theme: {
                type: 'string',
                title: 'Theme',
                description: 'Choose your preferred theme',
                enum: ['light', 'dark', 'auto'],
                enumNames: ['Light', 'Dark', 'Auto'],
              },
              notifications: {
                type: 'boolean',
                title: 'Enable Notifications',
                description: 'Would you like to receive notifications?',
                default: true,
              },
              frequency: {
                type: 'string',
                title: 'Notification Frequency',
                description: 'How often would you like notifications?',
                enum: ['daily', 'weekly', 'monthly'],
                enumNames: ['Daily', 'Weekly', 'Monthly'],
              },
            },
            required: ['theme'],
          };
          break;
        case 'feedback':
          message = 'Please provide your feedback';
          requestedSchema = {
            type: 'object',
            properties: {
              rating: {
                type: 'integer',
                title: 'Rating',
                description: 'Rate your experience (1-5)',
                minimum: 1,
                maximum: 5,
              },
              comments: {
                type: 'string',
                title: 'Comments',
                description: 'Additional comments (optional)',
                maxLength: 500,
              },
              recommend: {
                type: 'boolean',
                title: 'Would you recommend this?',
                description: 'Would you recommend this to others?',
              },
            },
            required: ['rating', 'recommend'],
          };
          break;
        default:
          throw new Error(`Unknown info type: ${infoType}`);
      }

      try {
        // Use the underlying server instance to elicit input from the client
        const result = await server.server.elicitInput({
          message,
          requestedSchema,
        });

        if (result.action === 'accept') {
          return {
            content: [
              {
                type: 'text',
                text: `Thank you! Collected ${infoType} information: ${JSON.stringify(result.content, null, 2)}`,
              },
            ],
          };
        } else if (result.action === 'decline') {
          return {
            content: [
              {
                type: 'text',
                text: `No information was collected. User declined ${infoType} information request.`,
              },
            ],
          };
        } else {
          return {
            content: [
              {
                type: 'text',
                text: `Information collection was cancelled by the user.`,
              },
            ],
          };
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error collecting ${infoType} information: ${error}`,
            },
          ],
        };
      }
    }
  );

  // Register a simple prompt with title
  server.registerPrompt(
    'greeting-template',
    {
      title: 'Greeting Template',  // Display name for UI
      description: 'A simple greeting prompt template',
      argsSchema: {
        name: z.string().describe('Name to include in greeting'),
      },
    },
    async ({ name }): Promise<GetPromptResult> => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Please greet ${name} in a friendly manner.`,
            },
          },
        ],
      };
    }
  );

  // Register a tool specifically for testing resumability
  server.tool(
    'start-notification-stream',
    'Starts sending periodic notifications for testing resumability',
    {
      interval: z.number().describe('Interval in milliseconds between notifications').default(100),
      count: z.number().describe('Number of notifications to send (0 for 100)').default(50),
    },
    async ({ interval, count }, { sendNotification }): Promise<CallToolResult> => {
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
      let counter = 0;

      while (count === 0 || counter < count) {
        counter++;
        try {
          await sendNotification({
            method: "notifications/message",
            params: {
              level: "info",
              data: `Periodic notification #${counter} at ${new Date().toISOString()}`
            }
          });
        }
        catch (error) {
          console.error("Error sending notification:", error);
        }
        // Wait for the specified interval
        await sleep(interval);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Started sending periodic notifications every ${interval}ms`,
          }
        ],
      };
    }
  );

  // Create a simple resource at a fixed URI
  server.registerResource(
    'greeting-resource',
    'https://example.com/greetings/default',
    {
      title: 'Default Greeting',  // Display name for UI
      description: 'A simple greeting resource',
      mimeType: 'text/plain'
    },
    async (): Promise<ReadResourceResult> => {
      return {
        contents: [
          {
            uri: 'https://example.com/greetings/default',
            text: 'Hello, world!',
          },
        ],
      };
    }
  );

  // Create additional resources for ResourceLink demonstration
  server.registerResource(
    'example-file-1',
    'file:///example/file1.txt',
    {
      title: 'Example File 1',
      description: 'First example file for ResourceLink demonstration',
      mimeType: 'text/plain'
    },
    async (): Promise<ReadResourceResult> => {
      return {
        contents: [
          {
            uri: 'file:///example/file1.txt',
            text: 'This is the content of file 1',
          },
        ],
      };
    }
  );

  server.registerResource(
    'example-file-2',
    'file:///example/file2.txt',
    {
      title: 'Example File 2',
      description: 'Second example file for ResourceLink demonstration',
      mimeType: 'text/plain'
    },
    async (): Promise<ReadResourceResult> => {
      return {
        contents: [
          {
            uri: 'file:///example/file2.txt',
            text: 'This is the content of file 2',
          },
        ],
      };
    }
  );

  // Register a tool that returns ResourceLinks
  server.registerTool(
    'list-files',
    {
      title: 'List Files with ResourceLinks',
      description: 'Returns a list of files as ResourceLinks without embedding their content',
      inputSchema: {
        includeDescriptions: z.boolean().optional().describe('Whether to include descriptions in the resource links'),
      },
    },
    async ({ includeDescriptions = true }): Promise<CallToolResult> => {
      const resourceLinks: ResourceLink[] = [
        {
          type: 'resource_link',
          uri: 'https://example.com/greetings/default',
          name: 'Default Greeting',
          mimeType: 'text/plain',
          ...(includeDescriptions && { description: 'A simple greeting resource' })
        },
        {
          type: 'resource_link',
          uri: 'file:///example/file1.txt',
          name: 'Example File 1',
          mimeType: 'text/plain',
          ...(includeDescriptions && { description: 'First example file for ResourceLink demonstration' })
        },
        {
          type: 'resource_link',
          uri: 'file:///example/file2.txt',
          name: 'Example File 2',
          mimeType: 'text/plain',
          ...(includeDescriptions && { description: 'Second example file for ResourceLink demonstration' })
        }
      ];

      return {
        content: [
          {
            type: 'text',
            text: 'Here are the available files as resource links:',
          },
          ...resourceLinks,
          {
            type: 'text',
            text: '\nYou can read any of these resources using their URI.',
          }
        ],
      };
    }
  );

  return server;
};

const MCP_PORT = process.env.MCP_PORT ? parseInt(process.env.MCP_PORT, 10) : 3000;
const AUTH_PORT = process.env.MCP_AUTH_PORT ? parseInt(process.env.MCP_AUTH_PORT, 10) : 3001;

const app = express();
app.use(express.json());

// Allow CORS all domains, expose the Mcp-Session-Id header
app.use(cors({
  origin: '*', // Allow all origins
  exposedHeaders: ["Mcp-Session-Id"]
}));

// Set up OAuth if enabled
let authMiddleware = null;
if (useOAuth) {
  // Create auth middleware for MCP endpoints
  const mcpServerUrl = new URL(`http://localhost:${MCP_PORT}/mcp`);
  const authServerUrl = new URL(`http://localhost:${AUTH_PORT}`);

  const oauthMetadata: OAuthMetadata = setupAuthServer({ authServerUrl, mcpServerUrl, strictResource: strictOAuth });

  const tokenVerifier = {
    verifyAccessToken: async (token: string) => {
      const endpoint = oauthMetadata.introspection_endpoint;

      if (!endpoint) {
        throw new Error('No token verification endpoint available in metadata');
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          token: token
        }).toString()
      });


      if (!response.ok) {
        throw new Error(`Invalid or expired token: ${await response.text()}`);
      }

      const data = await response.json();

      if (strictOAuth) {
        if (!data.aud) {
          throw new Error(`Resource Indicator (RFC8707) missing`);
        }
        if (!checkResourceAllowed({ requestedResource: data.aud, configuredResource: mcpServerUrl })) {
          throw new Error(`Expected resource indicator ${mcpServerUrl}, got: ${data.aud}`);
        }
      }

      // Convert the response to AuthInfo format
      return {
        token,
        clientId: data.client_id,
        scopes: data.scope ? data.scope.split(' ') : [],
        expiresAt: data.exp,
      };
    }
  }
  // Add metadata routes to the main MCP server
  app.use(mcpAuthMetadataRouter({
    oauthMetadata,
    resourceServerUrl: mcpServerUrl,
    scopesSupported: ['mcp:tools'],
    resourceName: 'MCP Demo Server',
  }));

  authMiddleware = requireBearerAuth({
    verifier: tokenVerifier,
    requiredScopes: [],
    resourceMetadataUrl: getOAuthProtectedResourceMetadataUrl(mcpServerUrl),
  });
}

// Map to store transports by session ID
const transports: { [sessionId: string]: StreamableHTTPServerTransport } = {};

// MCP POST endpoint with optional auth
const mcpPostHandler = async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined;
  if (sessionId) {
    console.log(`Received MCP request for session: ${sessionId}`);
  } else {
    console.log('Request body:', req.body);
  }

  if (useOAuth && req.auth) {
    console.log('Authenticated user:', req.auth);
  }
  try {
    let transport: StreamableHTTPServerTransport;
    if (sessionId && transports[sessionId]) {
      // Reuse existing transport
      transport = transports[sessionId];
    } else if (!sessionId && isInitializeRequest(req.body)) {
      // New initialization request
      const eventStore = new InMemoryEventStore();
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        eventStore, // Enable resumability
        onsessioninitialized: (sessionId) => {
          // Store the transport by session ID when session is initialized
          // This avoids race conditions where requests might come in before the session is stored
          console.log(`Session initialized with ID: ${sessionId}`);
          transports[sessionId] = transport;
        }
      });

      // Set up onclose handler to clean up transport when closed
      transport.onclose = () => {
        const sid = transport.sessionId;
        if (sid && transports[sid]) {
          console.log(`Transport closed for session ${sid}, removing from transports map`);
          delete transports[sid];
        }
      };

      // Connect the transport to the MCP server BEFORE handling the request
      // so responses can flow back through the same transport
      const server = getServer();
      await server.connect(transport);

      await transport.handleRequest(req, res, req.body);
      return; // Already handled
    } else {
      // Invalid request - no session ID or not initialization request
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided',
        },
        id: null,
      });
      return;
    }

    // Handle the request with existing transport - no need to reconnect
    // The existing transport is already connected to the server
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
};

// Set up routes with conditional auth middleware
if (useOAuth && authMiddleware) {
  app.post('/mcp', authMiddleware, mcpPostHandler);
} else {
  app.post('/mcp', mcpPostHandler);
}

// Handle GET requests for SSE streams (using built-in support from StreamableHTTP)
const mcpGetHandler = async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined;
  if (!sessionId || !transports[sessionId]) {
    res.status(400).send('Invalid or missing session ID');
    return;
  }

  if (useOAuth && req.auth) {
    console.log('Authenticated SSE connection from user:', req.auth);
  }

  // Check for Last-Event-ID header for resumability
  const lastEventId = req.headers['last-event-id'] as string | undefined;
  if (lastEventId) {
    console.log(`Client reconnecting with Last-Event-ID: ${lastEventId}`);
  } else {
    console.log(`Establishing new SSE stream for session ${sessionId}`);
  }

  const transport = transports[sessionId];
  await transport.handleRequest(req, res);
};

// Set up GET route with conditional auth middleware
if (useOAuth && authMiddleware) {
  app.get('/mcp', authMiddleware, mcpGetHandler);
} else {
  app.get('/mcp', mcpGetHandler);
}

// Handle DELETE requests for session termination (according to MCP spec)
const mcpDeleteHandler = async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined;
  if (!sessionId || !transports[sessionId]) {
    res.status(400).send('Invalid or missing session ID');
    return;
  }

  console.log(`Received session termination request for session ${sessionId}`);

  try {
    const transport = transports[sessionId];
    await transport.handleRequest(req, res);
  } catch (error) {
    console.error('Error handling session termination:', error);
    if (!res.headersSent) {
      res.status(500).send('Error processing session termination');
    }
  }
};

// Set up DELETE route with conditional auth middleware
if (useOAuth && authMiddleware) {
  app.delete('/mcp', authMiddleware, mcpDeleteHandler);
} else {
  app.delete('/mcp', mcpDeleteHandler);
}

app.listen(MCP_PORT, (error) => {
  if (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
  console.log(`MCP Streamable HTTP Server listening on port ${MCP_PORT}`);
});

// Handle server shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');

  // Close all active transports to properly clean up resources
  for (const sessionId in transports) {
    try {
      console.log(`Closing transport for session ${sessionId}`);
      await transports[sessionId].close();
      delete transports[sessionId];
    } catch (error) {
      console.error(`Error closing transport for session ${sessionId}:`, error);
    }
  }
  console.log('Server shutdown complete');
  process.exit(0);
});



================================================
FILE: src/examples/server/sseAndStreamableHttpCompatibleServer.ts
================================================
import express, { Request, Response } from 'express';
import { randomUUID } from "node:crypto";
import { McpServer } from '../../server/mcp.js';
import { StreamableHTTPServerTransport } from '../../server/streamableHttp.js';
import { SSEServerTransport } from '../../server/sse.js';
import { z } from 'zod';
import { CallToolResult, isInitializeRequest } from '../../types.js';
import { InMemoryEventStore } from '../shared/inMemoryEventStore.js';
import cors from 'cors';

/**
 * This example server demonstrates backwards compatibility with both:
 * 1. The deprecated HTTP+SSE transport (protocol version 2024-11-05)
 * 2. The Streamable HTTP transport (protocol version 2025-03-26)
 * 
 * It maintains a single MCP server instance but exposes two transport options:
 * - /mcp: The new Streamable HTTP endpoint (supports GET/POST/DELETE)
 * - /sse: The deprecated SSE endpoint for older clients (GET to establish stream)
 * - /messages: The deprecated POST endpoint for older clients (POST to send messages)
 */

const getServer = () => {
  const server = new McpServer({
    name: 'backwards-compatible-server',
    version: '1.0.0',
  }, { capabilities: { logging: {} } });

  // Register a simple tool that sends notifications over time
  server.tool(
    'start-notification-stream',
    'Starts sending periodic notifications for testing resumability',
    {
      interval: z.number().describe('Interval in milliseconds between notifications').default(100),
      count: z.number().describe('Number of notifications to send (0 for 100)').default(50),
    },
    async ({ interval, count }, { sendNotification }): Promise<CallToolResult> => {
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
      let counter = 0;

      while (count === 0 || counter < count) {
        counter++;
        try {
          await sendNotification({
            method: "notifications/message",
            params: {
              level: "info",
              data: `Periodic notification #${counter} at ${new Date().toISOString()}`
            }
          });
        }
        catch (error) {
          console.error("Error sending notification:", error);
        }
        // Wait for the specified interval
        await sleep(interval);
      }

      return {
        content: [
          {
            type: 'text',
            text: `Started sending periodic notifications every ${interval}ms`,
          }
        ],
      };
    }
  );
  return server;
};

// Create Express application
const app = express();
app.use(express.json());

// Configure CORS to expose Mcp-Session-Id header for browser-based clients
app.use(cors({
  origin: '*', // Allow all origins - adjust as needed for production
  exposedHeaders: ['Mcp-Session-Id']
}));

// Store transports by session ID
const transports: Record<string, StreamableHTTPServerTransport | SSEServerTransport> = {};

//=============================================================================
// STREAMABLE HTTP TRANSPORT (PROTOCOL VERSION 2025-03-26)
//=============================================================================

// Handle all MCP Streamable HTTP requests (GET, POST, DELETE) on a single endpoint
app.all('/mcp', async (req: Request, res: Response) => {
  console.log(`Received ${req.method} request to /mcp`);

  try {
    // Check for existing session ID
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
      // Check if the transport is of the correct type
      const existingTransport = transports[sessionId];
      if (existingTransport instanceof StreamableHTTPServerTransport) {
        // Reuse existing transport
        transport = existingTransport;
      } else {
        // Transport exists but is not a StreamableHTTPServerTransport (could be SSEServerTransport)
        res.status(400).json({
          jsonrpc: '2.0',
          error: {
            code: -32000,
            message: 'Bad Request: Session exists but uses a different transport protocol',
          },
          id: null,
        });
        return;
      }
    } else if (!sessionId && req.method === 'POST' && isInitializeRequest(req.body)) {
      const eventStore = new InMemoryEventStore();
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        eventStore, // Enable resumability
        onsessioninitialized: (sessionId) => {
          // Store the transport by session ID when session is initialized
          console.log(`StreamableHTTP session initialized with ID: ${sessionId}`);
          transports[sessionId] = transport;
        }
      });

      // Set up onclose handler to clean up transport when closed
      transport.onclose = () => {
        const sid = transport.sessionId;
        if (sid && transports[sid]) {
          console.log(`Transport closed for session ${sid}, removing from transports map`);
          delete transports[sid];
        }
      };

      // Connect the transport to the MCP server
      const server = getServer();
      await server.connect(transport);
    } else {
      // Invalid request - no session ID or not initialization request
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided',
        },
        id: null,
      });
      return;
    }

    // Handle the request with the transport
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

//=============================================================================
// DEPRECATED HTTP+SSE TRANSPORT (PROTOCOL VERSION 2024-11-05)
//=============================================================================

app.get('/sse', async (req: Request, res: Response) => {
  console.log('Received GET request to /sse (deprecated SSE transport)');
  const transport = new SSEServerTransport('/messages', res);
  transports[transport.sessionId] = transport;
  res.on("close", () => {
    delete transports[transport.sessionId];
  });
  const server = getServer();
  await server.connect(transport);
});

app.post("/messages", async (req: Request, res: Response) => {
  const sessionId = req.query.sessionId as string;
  let transport: SSEServerTransport;
  const existingTransport = transports[sessionId];
  if (existingTransport instanceof SSEServerTransport) {
    // Reuse existing transport
    transport = existingTransport;
  } else {
    // Transport exists but is not a SSEServerTransport (could be StreamableHTTPServerTransport)
    res.status(400).json({
      jsonrpc: '2.0',
      error: {
        code: -32000,
        message: 'Bad Request: Session exists but uses a different transport protocol',
      },
      id: null,
    });
    return;
  }
  if (transport) {
    await transport.handlePostMessage(req, res, req.body);
  } else {
    res.status(400).send('No transport found for sessionId');
  }
});


// Start the server
const PORT = 3000;
app.listen(PORT, (error) => {
  if (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
  console.log(`Backwards compatible MCP server listening on port ${PORT}`);
  console.log(`
==============================================
SUPPORTED TRANSPORT OPTIONS:

1. Streamable Http(Protocol version: 2025-03-26)
   Endpoint: /mcp
   Methods: GET, POST, DELETE
   Usage: 
     - Initialize with POST to /mcp
     - Establish SSE stream with GET to /mcp
     - Send requests with POST to /mcp
     - Terminate session with DELETE to /mcp

2. Http + SSE (Protocol version: 2024-11-05)
   Endpoints: /sse (GET) and /messages (POST)
   Usage:
     - Establish SSE stream with GET to /sse
     - Send requests with POST to /messages?sessionId=<id>
==============================================
`);
});

// Handle server shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');

  // Close all active transports to properly clean up resources
  for (const sessionId in transports) {
    try {
      console.log(`Closing transport for session ${sessionId}`);
      await transports[sessionId].close();
      delete transports[sessionId];
    } catch (error) {
      console.error(`Error closing transport for session ${sessionId}:`, error);
    }
  }
  console.log('Server shutdown complete');
  process.exit(0);
});


================================================
FILE: src/examples/server/standaloneSseWithGetStreamableHttp.ts
================================================
import express, { Request, Response } from 'express';
import { randomUUID } from 'node:crypto';
import { McpServer } from '../../server/mcp.js';
import { StreamableHTTPServerTransport } from '../../server/streamableHttp.js';
import { isInitializeRequest, ReadResourceResult } from '../../types.js';

// Create an MCP server with implementation details
const server = new McpServer({
  name: 'resource-list-changed-notification-server',
  version: '1.0.0',
});

// Store transports by session ID to send notifications
const transports: { [sessionId: string]: StreamableHTTPServerTransport } = {};

const addResource = (name: string, content: string) => {
  const uri = `https://mcp-example.com/dynamic/${encodeURIComponent(name)}`;
  server.resource(
    name,
    uri,
    { mimeType: 'text/plain', description: `Dynamic resource: ${name}` },
    async (): Promise<ReadResourceResult> => {
      return {
        contents: [{ uri, text: content }],
      };
    }
  );

};

addResource('example-resource', 'Initial content for example-resource');

const resourceChangeInterval = setInterval(() => {
  const name = randomUUID();
  addResource(name, `Content for ${name}`);
}, 5000); // Change resources every 5 seconds for testing

const app = express();
app.use(express.json());

app.post('/mcp', async (req: Request, res: Response) => {
  console.log('Received MCP request:', req.body);
  try {
    // Check for existing session ID
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
      // Reuse existing transport
      transport = transports[sessionId];
    } else if (!sessionId && isInitializeRequest(req.body)) {
      // New initialization request
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (sessionId) => {
          // Store the transport by session ID when session is initialized
          // This avoids race conditions where requests might come in before the session is stored
          console.log(`Session initialized with ID: ${sessionId}`);
          transports[sessionId] = transport;
        }
      });

      // Connect the transport to the MCP server
      await server.connect(transport);

      // Handle the request - the onsessioninitialized callback will store the transport
      await transport.handleRequest(req, res, req.body);
      return; // Already handled
    } else {
      // Invalid request - no session ID or not initialization request
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided',
        },
        id: null,
      });
      return;
    }

    // Handle the request with existing transport
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

// Handle GET requests for SSE streams (now using built-in support from StreamableHTTP)
app.get('/mcp', async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined;
  if (!sessionId || !transports[sessionId]) {
    res.status(400).send('Invalid or missing session ID');
    return;
  }

  console.log(`Establishing SSE stream for session ${sessionId}`);
  const transport = transports[sessionId];
  await transport.handleRequest(req, res);
});


// Start the server
const PORT = 3000;
app.listen(PORT, (error) => {
  if (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
  console.log(`Server listening on port ${PORT}`);
});

// Handle server shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');
  clearInterval(resourceChangeInterval);
  await server.close();
  process.exit(0);
});


================================================
FILE: src/examples/server/toolWithSampleServer.ts
================================================

// Run with: npx tsx src/examples/server/toolWithSampleServer.ts

import { McpServer } from "../../server/mcp.js";
import { StdioServerTransport } from "../../server/stdio.js";
import { z } from "zod";

const mcpServer = new McpServer({
  name: "tools-with-sample-server",
  version: "1.0.0",
});

// Tool that uses LLM sampling to summarize any text
mcpServer.registerTool(
  "summarize",
  {
    description: "Summarize any text using an LLM",
    inputSchema: {
      text: z.string().describe("Text to summarize"),
    },
  },
  async ({ text }) => {
    // Call the LLM through MCP sampling
    const response = await mcpServer.server.createMessage({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `Please summarize the following text concisely:\n\n${text}`,
          },
        },
      ],
      maxTokens: 500,
    });

    return {
      content: [
        {
          type: "text",
          text: response.content.type === "text" ? response.content.text : "Unable to generate summary",
        },
      ],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await mcpServer.connect(transport);
  console.log("MCP server is running...");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});


================================================
FILE: src/examples/shared/inMemoryEventStore.ts
================================================
import { JSONRPCMessage } from '../../types.js';
import { EventStore } from '../../server/streamableHttp.js';

/**
 * Simple in-memory implementation of the EventStore interface for resumability
 * This is primarily intended for examples and testing, not for production use
 * where a persistent storage solution would be more appropriate.
 */
export class InMemoryEventStore implements EventStore {
  private events: Map<string, { streamId: string, message: JSONRPCMessage }> = new Map();

  /**
   * Generates a unique event ID for a given stream ID
   */
  private generateEventId(streamId: string): string {
    return `${streamId}_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
  }

  /**
   * Extracts the stream ID from an event ID
   */
  private getStreamIdFromEventId(eventId: string): string {
    const parts = eventId.split('_');
    return parts.length > 0 ? parts[0] : '';
  }

  /**
   * Stores an event with a generated event ID
   * Implements EventStore.storeEvent
   */
  async storeEvent(streamId: string, message: JSONRPCMessage): Promise<string> {
    const eventId = this.generateEventId(streamId);
    this.events.set(eventId, { streamId, message });
    return eventId;
  }

  /**
   * Replays events that occurred after a specific event ID
   * Implements EventStore.replayEventsAfter
   */
  async replayEventsAfter(lastEventId: string,
    { send }: { send: (eventId: string, message: JSONRPCMessage) => Promise<void> }
  ): Promise<string> {
    if (!lastEventId || !this.events.has(lastEventId)) {
      return '';
    }

    // Extract the stream ID from the event ID
    const streamId = this.getStreamIdFromEventId(lastEventId);
    if (!streamId) {
      return '';
    }

    let foundLastEvent = false;

    // Sort events by eventId for chronological ordering
    const sortedEvents = [...this.events.entries()].sort((a, b) => a[0].localeCompare(b[0]));

    for (const [eventId, { streamId: eventStreamId, message }] of sortedEvents) {
      // Only include events from the same stream
      if (eventStreamId !== streamId) {
        continue;
      }

      // Start sending events after we find the lastEventId
      if (eventId === lastEventId) {
        foundLastEvent = true;
        continue;
      }

      if (foundLastEvent) {
        await send(eventId, message);
      }
    }
    return streamId;
  }
}


================================================
FILE: src/integration-tests/process-cleanup.test.ts
================================================
import { Server } from "../server/index.js";
import { StdioServerTransport } from "../server/stdio.js";

describe("Process cleanup", () => {
  jest.setTimeout(5000); // 5 second timeout

  it("should exit cleanly after closing transport", async () => {
    const server = new Server(
      {
        name: "test-server",
        version: "1.0.0",
      },
      {
        capabilities: {},
      }
    );

    const transport = new StdioServerTransport();
    await server.connect(transport);

    // Close the transport
    await transport.close();

    // If we reach here without hanging, the test passes
    // The test runner will fail if the process hangs
    expect(true).toBe(true);
  });
});


================================================
FILE: src/integration-tests/stateManagementStreamableHttp.test.ts
================================================
import { createServer, type Server } from 'node:http';
import { AddressInfo } from 'node:net';
import { randomUUID } from 'node:crypto';
import { Client } from '../client/index.js';
import { StreamableHTTPClientTransport } from '../client/streamableHttp.js';
import { McpServer } from '../server/mcp.js';
import { StreamableHTTPServerTransport } from '../server/streamableHttp.js';
import { CallToolResultSchema, ListToolsResultSchema, ListResourcesResultSchema, ListPromptsResultSchema, LATEST_PROTOCOL_VERSION } from '../types.js';
import { z } from 'zod';

describe('Streamable HTTP Transport Session Management', () => {
  // Function to set up the server with optional session management
  async function setupServer(withSessionManagement: boolean) {
    const server: Server = createServer();
    const mcpServer = new McpServer(
      { name: 'test-server', version: '1.0.0' },
      {
        capabilities: {
          logging: {},
          tools: {},
          resources: {},
          prompts: {}
        }
      }
    );

    // Add a simple resource
    mcpServer.resource(
      'test-resource',
      '/test',
      { description: 'A test resource' },
      async () => ({
        contents: [{
          uri: '/test',
          text: 'This is a test resource content'
        }]
      })
    );

    mcpServer.prompt(
      'test-prompt',
      'A test prompt',
      async () => ({
        messages: [{
          role: 'user',
          content: {
            type: 'text',
            text: 'This is a test prompt'
          }
        }]
      })
    );

    mcpServer.tool(
      'greet',
      'A simple greeting tool',
      {
        name: z.string().describe('Name to greet').default('World'),
      },
      async ({ name }) => {
        return {
          content: [{ type: 'text', text: `Hello, ${name}!` }]
        };
      }
    );

    // Create transport with or without session management
    const serverTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: withSessionManagement
        ? () => randomUUID()   // With session management, generate UUID
        : undefined     // Without session management, return undefined
    });

    await mcpServer.connect(serverTransport);

    server.on('request', async (req, res) => {
      await serverTransport.handleRequest(req, res);
    });

    // Start the server on a random port
    const baseUrl = await new Promise<URL>((resolve) => {
      server.listen(0, '127.0.0.1', () => {
        const addr = server.address() as AddressInfo;
        resolve(new URL(`http://127.0.0.1:${addr.port}`));
      });
    });

    return { server, mcpServer, serverTransport, baseUrl };
  }

  describe('Stateless Mode', () => {
    let server: Server;
    let mcpServer: McpServer;
    let serverTransport: StreamableHTTPServerTransport;
    let baseUrl: URL;

    beforeEach(async () => {
      const setup = await setupServer(false);
      server = setup.server;
      mcpServer = setup.mcpServer;
      serverTransport = setup.serverTransport;
      baseUrl = setup.baseUrl;
    });

    afterEach(async () => {
      // Clean up resources
      await mcpServer.close().catch(() => { });
      await serverTransport.close().catch(() => { });
      server.close();
    });

    it('should support multiple client connections', async () => {
      // Create and connect a client
      const client1 = new Client({
        name: 'test-client',
        version: '1.0.0'
      });

      const transport1 = new StreamableHTTPClientTransport(baseUrl);
      await client1.connect(transport1);

      // Verify that no session ID was set
      expect(transport1.sessionId).toBeUndefined();

      // List available tools
      await client1.request({
        method: 'tools/list',
        params: {}
      }, ListToolsResultSchema);

      const client2 = new Client({
        name: 'test-client',
        version: '1.0.0'
      });

      const transport2 = new StreamableHTTPClientTransport(baseUrl);
      await client2.connect(transport2);

      // Verify that no session ID was set
      expect(transport2.sessionId).toBeUndefined();

      // List available tools
      await client2.request({
        method: 'tools/list',
        params: {}
      }, ListToolsResultSchema);


    });
    it('should operate without session management', async () => {
      // Create and connect a client
      const client = new Client({
        name: 'test-client',
        version: '1.0.0'
      });

      const transport = new StreamableHTTPClientTransport(baseUrl);
      await client.connect(transport);

      // Verify that no session ID was set
      expect(transport.sessionId).toBeUndefined();

      // List available tools
      const toolsResult = await client.request({
        method: 'tools/list',
        params: {}
      }, ListToolsResultSchema);

      // Verify tools are accessible
      expect(toolsResult.tools).toContainEqual(expect.objectContaining({
        name: 'greet'
      }));

      // List available resources
      const resourcesResult = await client.request({
        method: 'resources/list',
        params: {}
      }, ListResourcesResultSchema);

      // Verify resources result structure
      expect(resourcesResult).toHaveProperty('resources');

      // List available prompts
      const promptsResult = await client.request({
        method: 'prompts/list',
        params: {}
      }, ListPromptsResultSchema);

      // Verify prompts result structure
      expect(promptsResult).toHaveProperty('prompts');
      expect(promptsResult.prompts).toContainEqual(expect.objectContaining({
        name: 'test-prompt'
      }));

      // Call the greeting tool
      const greetingResult = await client.request({
        method: 'tools/call',
        params: {
          name: 'greet',
          arguments: {
            name: 'Stateless Transport'
          }
        }
      }, CallToolResultSchema);

      // Verify tool result
      expect(greetingResult.content).toEqual([
        { type: 'text', text: 'Hello, Stateless Transport!' }
      ]);

      // Clean up
      await transport.close();
    });

    it('should set protocol version after connecting', async () => {
      // Create and connect a client
      const client = new Client({
        name: 'test-client',
        version: '1.0.0'
      });

      const transport = new StreamableHTTPClientTransport(baseUrl);

      // Verify protocol version is not set before connecting
      expect(transport.protocolVersion).toBeUndefined();

      await client.connect(transport);

      // Verify protocol version is set after connecting
      expect(transport.protocolVersion).toBe(LATEST_PROTOCOL_VERSION);

      // Clean up
      await transport.close();
    });
  });

  describe('Stateful Mode', () => {
    let server: Server;
    let mcpServer: McpServer;
    let serverTransport: StreamableHTTPServerTransport;
    let baseUrl: URL;

    beforeEach(async () => {
      const setup = await setupServer(true);
      server = setup.server;
      mcpServer = setup.mcpServer;
      serverTransport = setup.serverTransport;
      baseUrl = setup.baseUrl;
    });

    afterEach(async () => {
      // Clean up resources
      await mcpServer.close().catch(() => { });
      await serverTransport.close().catch(() => { });
      server.close();
    });

    it('should operate with session management', async () => {
      // Create and connect a client
      const client = new Client({
        name: 'test-client',
        version: '1.0.0'
      });

      const transport = new StreamableHTTPClientTransport(baseUrl);
      await client.connect(transport);

      // Verify that a session ID was set
      expect(transport.sessionId).toBeDefined();
      expect(typeof transport.sessionId).toBe('string');

      // List available tools
      const toolsResult = await client.request({
        method: 'tools/list',
        params: {}
      }, ListToolsResultSchema);

      // Verify tools are accessible
      expect(toolsResult.tools).toContainEqual(expect.objectContaining({
        name: 'greet'
      }));

      // List available resources
      const resourcesResult = await client.request({
        method: 'resources/list',
        params: {}
      }, ListResourcesResultSchema);

      // Verify resources result structure
      expect(resourcesResult).toHaveProperty('resources');

      // List available prompts
      const promptsResult = await client.request({
        method: 'prompts/list',
        params: {}
      }, ListPromptsResultSchema);

      // Verify prompts result structure
      expect(promptsResult).toHaveProperty('prompts');
      expect(promptsResult.prompts).toContainEqual(expect.objectContaining({
        name: 'test-prompt'
      }));

      // Call the greeting tool
      const greetingResult = await client.request({
        method: 'tools/call',
        params: {
          name: 'greet',
          arguments: {
            name: 'Stateful Transport'
          }
        }
      }, CallToolResultSchema);

      // Verify tool result
      expect(greetingResult.content).toEqual([
        { type: 'text', text: 'Hello, Stateful Transport!' }
      ]);

      // Clean up
      await transport.close();
    });
  });
});


================================================
FILE: src/integration-tests/taskResumability.test.ts
================================================
import { createServer, type Server } from 'node:http';
import { AddressInfo } from 'node:net';
import { randomUUID } from 'node:crypto';
import { Client } from '../client/index.js';
import { StreamableHTTPClientTransport } from '../client/streamableHttp.js';
import { McpServer } from '../server/mcp.js';
import { StreamableHTTPServerTransport } from '../server/streamableHttp.js';
import { CallToolResultSchema, LoggingMessageNotificationSchema } from '../types.js';
import { z } from 'zod';
import { InMemoryEventStore } from '../examples/shared/inMemoryEventStore.js';



describe('Transport resumability', () => {
  let server: Server;
  let mcpServer: McpServer;
  let serverTransport: StreamableHTTPServerTransport;
  let baseUrl: URL;
  let eventStore: InMemoryEventStore;

  beforeEach(async () => {
    // Create event store for resumability
    eventStore = new InMemoryEventStore();

    // Create a simple MCP server
    mcpServer = new McpServer(
      { name: 'test-server', version: '1.0.0' },
      { capabilities: { logging: {} } }
    );

    // Add a simple notification tool that completes quickly
    mcpServer.tool(
      'send-notification',
      'Sends a single notification',
      {
        message: z.string().describe('Message to send').default('Test notification')
      },
      async ({ message }, { sendNotification }) => {
        // Send notification immediately
        await sendNotification({
          method: "notifications/message",
          params: {
            level: "info",
            data: message
          }
        });

        return {
          content: [{ type: 'text', text: 'Notification sent' }]
        };
      }
    );

    // Add a long-running tool that sends multiple notifications
    mcpServer.tool(
      'run-notifications',
      'Sends multiple notifications over time',
      {
        count: z.number().describe('Number of notifications to send').default(10),
        interval: z.number().describe('Interval between notifications in ms').default(50)
      },
      async ({ count, interval }, { sendNotification }) => {
        // Send notifications at specified intervals
        for (let i = 0; i < count; i++) {
          await sendNotification({
            method: "notifications/message",
            params: {
              level: "info",
              data: `Notification ${i + 1} of ${count}`
            }
          });

          // Wait for the specified interval before sending next notification
          if (i < count - 1) {
            await new Promise(resolve => setTimeout(resolve, interval));
          }
        }

        return {
          content: [{ type: 'text', text: `Sent ${count} notifications` }]
        };
      }
    );

    // Create a transport with the event store
    serverTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
      eventStore
    });

    // Connect the transport to the MCP server
    await mcpServer.connect(serverTransport);

    // Create and start an HTTP server
    server = createServer(async (req, res) => {
      await serverTransport.handleRequest(req, res);
    });

    // Start the server on a random port
    baseUrl = await new Promise<URL>((resolve) => {
      server.listen(0, '127.0.0.1', () => {
        const addr = server.address() as AddressInfo;
        resolve(new URL(`http://127.0.0.1:${addr.port}`));
      });
    });
  });

  afterEach(async () => {
    // Clean up resources
    await mcpServer.close().catch(() => { });
    await serverTransport.close().catch(() => { });
    server.close();
  });

  it('should store session ID when client connects', async () => {
    // Create and connect a client
    const client = new Client({
      name: 'test-client',
      version: '1.0.0'
    });

    const transport = new StreamableHTTPClientTransport(baseUrl);
    await client.connect(transport);

    // Verify session ID was generated
    expect(transport.sessionId).toBeDefined();

    // Clean up
    await transport.close();
  });

  it('should have session ID functionality', async () => {
    // The ability to store a session ID when connecting
    const client = new Client({
      name: 'test-client-reconnection',
      version: '1.0.0'
    });

    const transport = new StreamableHTTPClientTransport(baseUrl);

    // Make sure the client can connect and get a session ID
    await client.connect(transport);
    expect(transport.sessionId).toBeDefined();

    // Clean up
    await transport.close();
  });

  // This test demonstrates the capability to resume long-running tools
  // across client disconnection/reconnection
  it('should resume long-running notifications with lastEventId', async () => {
    // Create unique client ID for this test
    const clientId = 'test-client-long-running';
    const notifications = [];
    let lastEventId: string | undefined;

    // Create first client
    const client1 = new Client({
      id: clientId,
      name: 'test-client',
      version: '1.0.0'
    });

    // Set up notification handler for first client
    client1.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
      if (notification.method === 'notifications/message') {
        notifications.push(notification.params);
      }
    });

    // Connect first client
    const transport1 = new StreamableHTTPClientTransport(baseUrl);
    await client1.connect(transport1);
    const sessionId = transport1.sessionId;
    expect(sessionId).toBeDefined();

    // Start a long-running notification stream with tracking of lastEventId
    const onLastEventIdUpdate = jest.fn((eventId: string) => {
      lastEventId = eventId;
    });
    expect(lastEventId).toBeUndefined();
    // Start the notification tool with event tracking using request
    const toolPromise = client1.request({
      method: 'tools/call',
      params: {
        name: 'run-notifications',
        arguments: {
          count: 3,
          interval: 10
        }
      }
    }, CallToolResultSchema, {
      resumptionToken: lastEventId,
      onresumptiontoken: onLastEventIdUpdate
    });

    // Wait for some notifications to arrive (not all) - shorter wait time
    await new Promise(resolve => setTimeout(resolve, 20));

    // Verify we received some notifications and lastEventId was updated
    expect(notifications.length).toBeGreaterThan(0);
    expect(notifications.length).toBeLessThan(4);
    expect(onLastEventIdUpdate).toHaveBeenCalled();
    expect(lastEventId).toBeDefined();


    // Disconnect first client without waiting for completion
    // When we close the connection, it will cause a ConnectionClosed error for
    // any in-progress requests, which is expected behavior
    await transport1.close();
    // Save the promise so we can catch it after closing
    const catchPromise = toolPromise.catch(err => {
      // This error is expected - the connection was intentionally closed
      if (err?.code !== -32000) { // ConnectionClosed error code
        console.error("Unexpected error type during transport close:", err);
      }
    });



    // Add a short delay to ensure clean disconnect before reconnecting
    await new Promise(resolve => setTimeout(resolve, 10));

    // Wait for the rejection to be handled
    await catchPromise;


    // Create second client with same client ID
    const client2 = new Client({
      id: clientId,
      name: 'test-client',
      version: '1.0.0'
    });

    // Set up notification handler for second client
    client2.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
      if (notification.method === 'notifications/message') {
        notifications.push(notification.params);
      }
    });

    // Connect second client with same session ID
    const transport2 = new StreamableHTTPClientTransport(baseUrl, {
      sessionId
    });
    await client2.connect(transport2);

    // Resume the notification stream using lastEventId
    // This is the key part - we're resuming the same long-running tool using lastEventId
    await client2.request({
      method: 'tools/call',
      params: {
        name: 'run-notifications',
        arguments: {
          count: 1,
          interval: 5
        }
      }
    }, CallToolResultSchema, {
      resumptionToken: lastEventId,  // Pass the lastEventId from the previous session
      onresumptiontoken: onLastEventIdUpdate
    });

    // Verify we eventually received at leaset a few motifications
    expect(notifications.length).toBeGreaterThan(1);


    // Clean up
    await transport2.close();

  });
});


================================================
FILE: src/server/completable.test.ts
================================================
import { z } from "zod";
import { completable } from "./completable.js";

describe("completable", () => {
  it("preserves types and values of underlying schema", () => {
    const baseSchema = z.string();
    const schema = completable(baseSchema, () => []);

    expect(schema.parse("test")).toBe("test");
    expect(() => schema.parse(123)).toThrow();
  });

  it("provides access to completion function", async () => {
    const completions = ["foo", "bar", "baz"];
    const schema = completable(z.string(), () => completions);

    expect(await schema._def.complete("")).toEqual(completions);
  });

  it("allows async completion functions", async () => {
    const completions = ["foo", "bar", "baz"];
    const schema = completable(z.string(), async () => completions);

    expect(await schema._def.complete("")).toEqual(completions);
  });

  it("passes current value to completion function", async () => {
    const schema = completable(z.string(), (value) => [value + "!"]);

    expect(await schema._def.complete("test")).toEqual(["test!"]);
  });

  it("works with number schemas", async () => {
    const schema = completable(z.number(), () => [1, 2, 3]);

    expect(schema.parse(1)).toBe(1);
    expect(await schema._def.complete(0)).toEqual([1, 2, 3]);
  });

  it("preserves schema description", () => {
    const desc = "test description";
    const schema = completable(z.string().describe(desc), () => []);

    expect(schema.description).toBe(desc);
  });
});



================================================
FILE: src/server/completable.ts
================================================
import {
  ZodTypeAny,
  ZodTypeDef,
  ZodType,
  ParseInput,
  ParseReturnType,
  RawCreateParams,
  ZodErrorMap,
  ProcessedCreateParams,
} from "zod";

export enum McpZodTypeKind {
  Completable = "McpCompletable",
}

export type CompleteCallback<T extends ZodTypeAny = ZodTypeAny> = (
  value: T["_input"],
  context?: {
    arguments?: Record<string, string>;
  },
) => T["_input"][] | Promise<T["_input"][]>;

export interface CompletableDef<T extends ZodTypeAny = ZodTypeAny>
  extends ZodTypeDef {
  type: T;
  complete: CompleteCallback<T>;
  typeName: McpZodTypeKind.Completable;
}

export class Completable<T extends ZodTypeAny> extends ZodType<
  T["_output"],
  CompletableDef<T>,
  T["_input"]
> {
  _parse(input: ParseInput): ParseReturnType<this["_output"]> {
    const { ctx } = this._processInputParams(input);
    const data = ctx.data;
    return this._def.type._parse({
      data,
      path: ctx.path,
      parent: ctx,
    });
  }

  unwrap() {
    return this._def.type;
  }

  static create = <T extends ZodTypeAny>(
    type: T,
    params: RawCreateParams & {
      complete: CompleteCallback<T>;
    },
  ): Completable<T> => {
    return new Completable({
      type,
      typeName: McpZodTypeKind.Completable,
      complete: params.complete,
      ...processCreateParams(params),
    });
  };
}

/**
 * Wraps a Zod type to provide autocompletion capabilities. Useful for, e.g., prompt arguments in MCP.
 */
export function completable<T extends ZodTypeAny>(
  schema: T,
  complete: CompleteCallback<T>,
): Completable<T> {
  return Completable.create(schema, { ...schema._def, complete });
}

// Not sure why this isn't exported from Zod:
// https://github.com/colinhacks/zod/blob/f7ad26147ba291cb3fb257545972a8e00e767470/src/types.ts#L130
function processCreateParams(params: RawCreateParams): ProcessedCreateParams {
  if (!params) return {};
  const { errorMap, invalid_type_error, required_error, description } = params;
  if (errorMap && (invalid_type_error || required_error)) {
    throw new Error(
      `Can't use "invalid_type_error" or "required_error" in conjunction with custom error map.`,
    );
  }
  if (errorMap) return { errorMap: errorMap, description };
  const customMap: ZodErrorMap = (iss, ctx) => {
    const { message } = params;

    if (iss.code === "invalid_enum_value") {
      return { message: message ?? ctx.defaultError };
    }
    if (typeof ctx.data === "undefined") {
      return { message: message ?? required_error ?? ctx.defaultError };
    }
    if (iss.code !== "invalid_type") return { message: ctx.defaultError };
    return { message: message ?? invalid_type_error ?? ctx.defaultError };
  };
  return { errorMap: customMap, description };
}



================================================
FILE: src/server/index.test.ts
================================================
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-constant-binary-expression */
/* eslint-disable @typescript-eslint/no-unused-expressions */
import { Server } from "./index.js";
import { z } from "zod";
import {
  RequestSchema,
  NotificationSchema,
  ResultSchema,
  LATEST_PROTOCOL_VERSION,
  SUPPORTED_PROTOCOL_VERSIONS,
  CreateMessageRequestSchema,
  ElicitRequestSchema,
  ListPromptsRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  SetLevelRequestSchema,
  ErrorCode
} from "../types.js";
import { Transport } from "../shared/transport.js";
import { InMemoryTransport } from "../inMemory.js";
import { Client } from "../client/index.js";

test("should accept latest protocol version", async () => {
  let sendPromiseResolve: (value: unknown) => void;
  const sendPromise = new Promise((resolve) => {
    sendPromiseResolve = resolve;
  });

  const serverTransport: Transport = {
    start: jest.fn().mockResolvedValue(undefined),
    close: jest.fn().mockResolvedValue(undefined),
    send: jest.fn().mockImplementation((message) => {
      if (message.id === 1 && message.result) {
        expect(message.result).toEqual({
          protocolVersion: LATEST_PROTOCOL_VERSION,
          capabilities: expect.any(Object),
          serverInfo: {
            name: "test server",
            version: "1.0",
          },
          instructions: "Test instructions",
        });
        sendPromiseResolve(undefined);
      }
      return Promise.resolve();
    }),
  };

  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
      instructions: "Test instructions",
    },
  );

  await server.connect(serverTransport);

  // Simulate initialize request with latest version
  serverTransport.onmessage?.({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: LATEST_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: {
        name: "test client",
        version: "1.0",
      },
    },
  });

  await expect(sendPromise).resolves.toBeUndefined();
});

test("should accept supported older protocol version", async () => {
  const OLD_VERSION = SUPPORTED_PROTOCOL_VERSIONS[1];
  let sendPromiseResolve: (value: unknown) => void;
  const sendPromise = new Promise((resolve) => {
    sendPromiseResolve = resolve;
  });

  const serverTransport: Transport = {
    start: jest.fn().mockResolvedValue(undefined),
    close: jest.fn().mockResolvedValue(undefined),
    send: jest.fn().mockImplementation((message) => {
      if (message.id === 1 && message.result) {
        expect(message.result).toEqual({
          protocolVersion: OLD_VERSION,
          capabilities: expect.any(Object),
          serverInfo: {
            name: "test server",
            version: "1.0",
          },
        });
        sendPromiseResolve(undefined);
      }
      return Promise.resolve();
    }),
  };

  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
    },
  );

  await server.connect(serverTransport);

  // Simulate initialize request with older version
  serverTransport.onmessage?.({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: OLD_VERSION,
      capabilities: {},
      clientInfo: {
        name: "test client",
        version: "1.0",
      },
    },
  });

  await expect(sendPromise).resolves.toBeUndefined();
});

test("should handle unsupported protocol version", async () => {
  let sendPromiseResolve: (value: unknown) => void;
  const sendPromise = new Promise((resolve) => {
    sendPromiseResolve = resolve;
  });

  const serverTransport: Transport = {
    start: jest.fn().mockResolvedValue(undefined),
    close: jest.fn().mockResolvedValue(undefined),
    send: jest.fn().mockImplementation((message) => {
      if (message.id === 1 && message.result) {
        expect(message.result).toEqual({
          protocolVersion: LATEST_PROTOCOL_VERSION,
          capabilities: expect.any(Object),
          serverInfo: {
            name: "test server",
            version: "1.0",
          },
        });
        sendPromiseResolve(undefined);
      }
      return Promise.resolve();
    }),
  };

  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
    },
  );

  await server.connect(serverTransport);

  // Simulate initialize request with unsupported version
  serverTransport.onmessage?.({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "invalid-version",
      capabilities: {},
      clientInfo: {
        name: "test client",
        version: "1.0",
      },
    },
  });

  await expect(sendPromise).resolves.toBeUndefined();
});

test("should respect client capabilities", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  // Implement request handler for sampling/createMessage
  client.setRequestHandler(CreateMessageRequestSchema, async (request) => {
    // Mock implementation of createMessage
    return {
      model: "test-model",
      role: "assistant",
      content: {
        type: "text",
        text: "This is a test response",
      },
    };
  });

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  expect(server.getClientCapabilities()).toEqual({ sampling: {} });

  // This should work because sampling is supported by the client
  await expect(
    server.createMessage({
      messages: [],
      maxTokens: 10,
    }),
  ).resolves.not.toThrow();

  // This should still throw because roots are not supported by the client
  await expect(server.listRoots()).rejects.toThrow(/^Client does not support/);
});

test("should respect client elicitation capabilities", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        elicitation: {},
      },
    },
  );

  client.setRequestHandler(ElicitRequestSchema, (params) => ({
    action: "accept",
    content: {
      username: params.params.message.includes("username") ? "test-user" : undefined,
      confirmed: true,
    },
  }));

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  expect(server.getClientCapabilities()).toEqual({ elicitation: {} });

  // This should work because elicitation is supported by the client
  await expect(
    server.elicitInput({
      message: "Please provide your username",
      requestedSchema: {
        type: "object",
        properties: {
          username: {
            type: "string",
            title: "Username",
            description: "Your username",
          },
          confirmed: {
            type: "boolean",
            title: "Confirm",
            description: "Please confirm",
            default: false,
          },
        },
        required: ["username"],
      },
    }),
  ).resolves.toEqual({
    action: "accept",
    content: {
      username: "test-user",
      confirmed: true,
    },
  });

  // This should still throw because sampling is not supported by the client
  await expect(
    server.createMessage({
      messages: [],
      maxTokens: 10,
    }),
  ).rejects.toThrow(/^Client does not support/);
});

test("should validate elicitation response against requested schema", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        elicitation: {},
      },
    },
  );

  // Set up client to return valid response
  client.setRequestHandler(ElicitRequestSchema, (request) => ({
    action: "accept",
    content: {
      name: "John Doe",
      email: "john@example.com",
      age: 30,
    },
  }));

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Test with valid response
  await expect(
    server.elicitInput({
      message: "Please provide your information",
      requestedSchema: {
        type: "object",
        properties: {
          name: {
            type: "string",
            minLength: 1,
          },
          email: {
            type: "string",
            minLength: 1,
          },
          age: {
            type: "integer",
            minimum: 0,
            maximum: 150,
          },
        },
        required: ["name", "email"],
      },
    }),
  ).resolves.toEqual({
    action: "accept",
    content: {
      name: "John Doe",
      email: "john@example.com",
      age: 30,
    },
  });
});

test("should reject elicitation response with invalid data", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        elicitation: {},
      },
    },
  );

  // Set up client to return invalid response (missing required field, invalid age)
  client.setRequestHandler(ElicitRequestSchema, (request) => ({
    action: "accept",
    content: {
      email: "", // Invalid - too short
      age: -5, // Invalid age
    },
  }));

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Test with invalid response
  await expect(
    server.elicitInput({
      message: "Please provide your information",
      requestedSchema: {
        type: "object",
        properties: {
          name: {
            type: "string",
            minLength: 1,
          },
          email: {
            type: "string",
            minLength: 1,
          },
          age: {
            type: "integer",
            minimum: 0,
            maximum: 150,
          },
        },
        required: ["name", "email"],
      },
    }),
  ).rejects.toThrow(/does not match requested schema/);
});

test("should allow elicitation reject and cancel without validation", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        elicitation: {},
      },
    },
  );

  let requestCount = 0;
  client.setRequestHandler(ElicitRequestSchema, (request) => {
    requestCount++;
    if (requestCount === 1) {
      return { action: "decline" };
    } else {
      return { action: "cancel" };
    }
  });

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  const schema = {
    type: "object" as const,
    properties: {
      name: { type: "string" as const },
    },
    required: ["name"],
  };

  // Test reject - should not validate
  await expect(
    server.elicitInput({
      message: "Please provide your name",
      requestedSchema: schema,
    }),
  ).resolves.toEqual({
    action: "decline",
  });

  // Test cancel - should not validate  
  await expect(
    server.elicitInput({
      message: "Please provide your name",
      requestedSchema: schema,
    }),
  ).resolves.toEqual({
    action: "cancel",
  });
});

test("should respect server notification capabilities", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        logging: {},
      },
      enforceStrictCapabilities: true,
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  await server.connect(serverTransport);

  // This should work because logging is supported by the server
  await expect(
    server.sendLoggingMessage({
      level: "info",
      data: "Test log message",
    }),
  ).resolves.not.toThrow();

  // This should throw because resource notificaitons are not supported by the server
  await expect(
    server.sendResourceUpdated({ uri: "test://resource" }),
  ).rejects.toThrow(/^Server does not support/);
});

test("should only allow setRequestHandler for declared capabilities", () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
      },
    },
  );

  // These should work because the capabilities are declared
  expect(() => {
    server.setRequestHandler(ListPromptsRequestSchema, () => ({ prompts: [] }));
  }).not.toThrow();

  expect(() => {
    server.setRequestHandler(ListResourcesRequestSchema, () => ({
      resources: [],
    }));
  }).not.toThrow();

  // These should throw because the capabilities are not declared
  expect(() => {
    server.setRequestHandler(ListToolsRequestSchema, () => ({ tools: [] }));
  }).toThrow(/^Server does not support tools/);

  expect(() => {
    server.setRequestHandler(SetLevelRequestSchema, () => ({}));
  }).toThrow(/^Server does not support logging/);
});

/*
  Test that custom request/notification/result schemas can be used with the Server class.
  */
test("should typecheck", () => {
  const GetWeatherRequestSchema = RequestSchema.extend({
    method: z.literal("weather/get"),
    params: z.object({
      city: z.string(),
    }),
  });

  const GetForecastRequestSchema = RequestSchema.extend({
    method: z.literal("weather/forecast"),
    params: z.object({
      city: z.string(),
      days: z.number(),
    }),
  });

  const WeatherForecastNotificationSchema = NotificationSchema.extend({
    method: z.literal("weather/alert"),
    params: z.object({
      severity: z.enum(["warning", "watch"]),
      message: z.string(),
    }),
  });

  const WeatherRequestSchema = GetWeatherRequestSchema.or(
    GetForecastRequestSchema,
  );
  const WeatherNotificationSchema = WeatherForecastNotificationSchema;
  const WeatherResultSchema = ResultSchema.extend({
    temperature: z.number(),
    conditions: z.string(),
  });

  type WeatherRequest = z.infer<typeof WeatherRequestSchema>;
  type WeatherNotification = z.infer<typeof WeatherNotificationSchema>;
  type WeatherResult = z.infer<typeof WeatherResultSchema>;

  // Create a typed Server for weather data
  const weatherServer = new Server<
    WeatherRequest,
    WeatherNotification,
    WeatherResult
  >(
    {
      name: "WeatherServer",
      version: "1.0.0",
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {},
        logging: {},
      },
    },
  );

  // Typecheck that only valid weather requests/notifications/results are allowed
  weatherServer.setRequestHandler(GetWeatherRequestSchema, (request) => {
    return {
      temperature: 72,
      conditions: "sunny",
    };
  });

  weatherServer.setNotificationHandler(
    WeatherForecastNotificationSchema,
    (notification) => {
      console.log(`Weather alert: ${notification.params.message}`);
    },
  );
});

test("should handle server cancelling a request", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  // Set up client to delay responding to createMessage
  client.setRequestHandler(
    CreateMessageRequestSchema,
    async (_request, extra) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return {
        model: "test",
        role: "assistant",
        content: {
          type: "text",
          text: "Test response",
        },
      };
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Set up abort controller
  const controller = new AbortController();

  // Issue request but cancel it immediately
  const createMessagePromise = server.createMessage(
    {
      messages: [],
      maxTokens: 10,
    },
    {
      signal: controller.signal,
    },
  );
  controller.abort("Cancelled by test");

  // Request should be rejected
  await expect(createMessagePromise).rejects.toBe("Cancelled by test");
});

test("should handle request timeout", async () => {
  const server = new Server(
    {
      name: "test server",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  // Set up client that delays responses
  const client = new Client(
    {
      name: "test client",
      version: "1.0",
    },
    {
      capabilities: {
        sampling: {},
      },
    },
  );

  client.setRequestHandler(
    CreateMessageRequestSchema,
    async (_request, extra) => {
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(resolve, 100);
        extra.signal.addEventListener("abort", () => {
          clearTimeout(timeout);
          reject(extra.signal.reason);
        });
      });

      return {
        model: "test",
        role: "assistant",
        content: {
          type: "text",
          text: "Test response",
        },
      };
    },
  );

  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);

  // Request with 0 msec timeout should fail immediately
  await expect(
    server.createMessage(
      {
        messages: [],
        maxTokens: 10,
      },
      { timeout: 0 },
    ),
  ).rejects.toMatchObject({
    code: ErrorCode.RequestTimeout,
  });
});



================================================
FILE: src/server/index.ts
================================================
import {
  mergeCapabilities,
  Protocol,
  ProtocolOptions,
  RequestOptions,
} from "../shared/protocol.js";
import {
  ClientCapabilities,
  CreateMessageRequest,
  CreateMessageResultSchema,
  ElicitRequest,
  ElicitResult,
  ElicitResultSchema,
  EmptyResultSchema,
  Implementation,
  InitializedNotificationSchema,
  InitializeRequest,
  InitializeRequestSchema,
  InitializeResult,
  LATEST_PROTOCOL_VERSION,
  ListRootsRequest,
  ListRootsResultSchema,
  LoggingMessageNotification,
  McpError,
  ErrorCode,
  Notification,
  Request,
  ResourceUpdatedNotification,
  Result,
  ServerCapabilities,
  ServerNotification,
  ServerRequest,
  ServerResult,
  SUPPORTED_PROTOCOL_VERSIONS,
} from "../types.js";
import Ajv from "ajv";

export type ServerOptions = ProtocolOptions & {
  /**
   * Capabilities to advertise as being supported by this server.
   */
  capabilities?: ServerCapabilities;

  /**
   * Optional instructions describing how to use the server and its features.
   */
  instructions?: string;
};

/**
 * An MCP server on top of a pluggable transport.
 *
 * This server will automatically respond to the initialization flow as initiated from the client.
 *
 * To use with custom types, extend the base Request/Notification/Result types and pass them as type parameters:
 *
 * ```typescript
 * // Custom schemas
 * const CustomRequestSchema = RequestSchema.extend({...})
 * const CustomNotificationSchema = NotificationSchema.extend({...})
 * const CustomResultSchema = ResultSchema.extend({...})
 *
 * // Type aliases
 * type CustomRequest = z.infer<typeof CustomRequestSchema>
 * type CustomNotification = z.infer<typeof CustomNotificationSchema>
 * type CustomResult = z.infer<typeof CustomResultSchema>
 *
 * // Create typed server
 * const server = new Server<CustomRequest, CustomNotification, CustomResult>({
 *   name: "CustomServer",
 *   version: "1.0.0"
 * })
 * ```
 */
export class Server<
  RequestT extends Request = Request,
  NotificationT extends Notification = Notification,
  ResultT extends Result = Result,
> extends Protocol<
  ServerRequest | RequestT,
  ServerNotification | NotificationT,
  ServerResult | ResultT
> {
  private _clientCapabilities?: ClientCapabilities;
  private _clientVersion?: Implementation;
  private _capabilities: ServerCapabilities;
  private _instructions?: string;

  /**
   * Callback for when initialization has fully completed (i.e., the client has sent an `initialized` notification).
   */
  oninitialized?: () => void;

  /**
   * Initializes this server with the given name and version information.
   */
  constructor(
    private _serverInfo: Implementation,
    options?: ServerOptions,
  ) {
    super(options);
    this._capabilities = options?.capabilities ?? {};
    this._instructions = options?.instructions;

    this.setRequestHandler(InitializeRequestSchema, (request) =>
      this._oninitialize(request),
    );
    this.setNotificationHandler(InitializedNotificationSchema, () =>
      this.oninitialized?.(),
    );
  }

  /**
   * Registers new capabilities. This can only be called before connecting to a transport.
   *
   * The new capabilities will be merged with any existing capabilities previously given (e.g., at initialization).
   */
  public registerCapabilities(capabilities: ServerCapabilities): void {
    if (this.transport) {
      throw new Error(
        "Cannot register capabilities after connecting to transport",
      );
    }

    this._capabilities = mergeCapabilities(this._capabilities, capabilities);
  }

  protected assertCapabilityForMethod(method: RequestT["method"]): void {
    switch (method as ServerRequest["method"]) {
      case "sampling/createMessage":
        if (!this._clientCapabilities?.sampling) {
          throw new Error(
            `Client does not support sampling (required for ${method})`,
          );
        }
        break;

      case "elicitation/create":
        if (!this._clientCapabilities?.elicitation) {
          throw new Error(
            `Client does not support elicitation (required for ${method})`,
          );
        }
        break;

      case "roots/list":
        if (!this._clientCapabilities?.roots) {
          throw new Error(
            `Client does not support listing roots (required for ${method})`,
          );
        }
        break;

      case "ping":
        // No specific capability required for ping
        break;
    }
  }

  protected assertNotificationCapability(
    method: (ServerNotification | NotificationT)["method"],
  ): void {
    switch (method as ServerNotification["method"]) {
      case "notifications/message":
        if (!this._capabilities.logging) {
          throw new Error(
            `Server does not support logging (required for ${method})`,
          );
        }
        break;

      case "notifications/resources/updated":
      case "notifications/resources/list_changed":
        if (!this._capabilities.resources) {
          throw new Error(
            `Server does not support notifying about resources (required for ${method})`,
          );
        }
        break;

      case "notifications/tools/list_changed":
        if (!this._capabilities.tools) {
          throw new Error(
            `Server does not support notifying of tool list changes (required for ${method})`,
          );
        }
        break;

      case "notifications/prompts/list_changed":
        if (!this._capabilities.prompts) {
          throw new Error(
            `Server does not support notifying of prompt list changes (required for ${method})`,
          );
        }
        break;

      case "notifications/cancelled":
        // Cancellation notifications are always allowed
        break;

      case "notifications/progress":
        // Progress notifications are always allowed
        break;
    }
  }

  protected assertRequestHandlerCapability(method: string): void {
    switch (method) {
      case "sampling/createMessage":
        if (!this._capabilities.sampling) {
          throw new Error(
            `Server does not support sampling (required for ${method})`,
          );
        }
        break;

      case "logging/setLevel":
        if (!this._capabilities.logging) {
          throw new Error(
            `Server does not support logging (required for ${method})`,
          );
        }
        break;

      case "prompts/get":
      case "prompts/list":
        if (!this._capabilities.prompts) {
          throw new Error(
            `Server does not support prompts (required for ${method})`,
          );
        }
        break;

      case "resources/list":
      case "resources/templates/list":
      case "resources/read":
        if (!this._capabilities.resources) {
          throw new Error(
            `Server does not support resources (required for ${method})`,
          );
        }
        break;

      case "tools/call":
      case "tools/list":
        if (!this._capabilities.tools) {
          throw new Error(
            `Server does not support tools (required for ${method})`,
          );
        }
        break;

      case "ping":
      case "initialize":
        // No specific capability required for these methods
        break;
    }
  }

  private async _oninitialize(
    request: InitializeRequest,
  ): Promise<InitializeResult> {
    const requestedVersion = request.params.protocolVersion;

    this._clientCapabilities = request.params.capabilities;
    this._clientVersion = request.params.clientInfo;

    const protocolVersion = SUPPORTED_PROTOCOL_VERSIONS.includes(requestedVersion)
        ? requestedVersion
        : LATEST_PROTOCOL_VERSION;

    return {
      protocolVersion,
      capabilities: this.getCapabilities(),
      serverInfo: this._serverInfo,
      ...(this._instructions && { instructions: this._instructions }),
    };
  }

  /**
   * After initialization has completed, this will be populated with the client's reported capabilities.
   */
  getClientCapabilities(): ClientCapabilities | undefined {
    return this._clientCapabilities;
  }

  /**
   * After initialization has completed, this will be populated with information about the client's name and version.
   */
  getClientVersion(): Implementation | undefined {
    return this._clientVersion;
  }

  private getCapabilities(): ServerCapabilities {
    return this._capabilities;
  }

  async ping() {
    return this.request({ method: "ping" }, EmptyResultSchema);
  }

  async createMessage(
    params: CreateMessageRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "sampling/createMessage", params },
      CreateMessageResultSchema,
      options,
    );
  }

  async elicitInput(
    params: ElicitRequest["params"],
    options?: RequestOptions,
  ): Promise<ElicitResult> {
    const result = await this.request(
      { method: "elicitation/create", params },
      ElicitResultSchema,
      options,
    );

    // Validate the response content against the requested schema if action is "accept"
    if (result.action === "accept" && result.content) {
      try {
        const ajv = new Ajv();
        
        const validate = ajv.compile(params.requestedSchema);
        const isValid = validate(result.content);
        
        if (!isValid) {
          throw new McpError(
            ErrorCode.InvalidParams,
            `Elicitation response content does not match requested schema: ${ajv.errorsText(validate.errors)}`,
          );
        }
      } catch (error) {
        if (error instanceof McpError) {
          throw error;
        }
        throw new McpError(
          ErrorCode.InternalError,
          `Error validating elicitation response: ${error}`,
        );
      }
    }

    return result;
  }

  async listRoots(
    params?: ListRootsRequest["params"],
    options?: RequestOptions,
  ) {
    return this.request(
      { method: "roots/list", params },
      ListRootsResultSchema,
      options,
    );
  }

  async sendLoggingMessage(params: LoggingMessageNotification["params"]) {
    return this.notification({ method: "notifications/message", params });
  }

  async sendResourceUpdated(params: ResourceUpdatedNotification["params"]) {
    return this.notification({
      method: "notifications/resources/updated",
      params,
    });
  }

  async sendResourceListChanged() {
    return this.notification({
      method: "notifications/resources/list_changed",
    });
  }

  async sendToolListChanged() {
    return this.notification({ method: "notifications/tools/list_changed" });
  }

  async sendPromptListChanged() {
    return this.notification({ method: "notifications/prompts/list_changed" });
  }
}



================================================
FILE: src/server/mcp.ts
================================================
import { Server, ServerOptions } from "./index.js";
import { zodToJsonSchema } from "zod-to-json-schema";
import {
  z,
  ZodRawShape,
  ZodObject,
  ZodString,
  AnyZodObject,
  ZodTypeAny,
  ZodType,
  ZodTypeDef,
  ZodOptional,
} from "zod";
import {
  Implementation,
  Tool,
  ListToolsResult,
  CallToolResult,
  McpError,
  ErrorCode,
  CompleteRequest,
  CompleteResult,
  PromptReference,
  ResourceTemplateReference,
  BaseMetadata,
  Resource,
  ListResourcesResult,
  ListResourceTemplatesRequestSchema,
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
  CompleteRequestSchema,
  ListPromptsResult,
  Prompt,
  PromptArgument,
  GetPromptResult,
  ReadResourceResult,
  ServerRequest,
  ServerNotification,
  ToolAnnotations,
} from "../types.js";
import { Completable, CompletableDef } from "./completable.js";
import { UriTemplate, Variables } from "../shared/uriTemplate.js";
import { RequestHandlerExtra } from "../shared/protocol.js";
import { Transport } from "../shared/transport.js";

/**
 * High-level MCP server that provides a simpler API for working with resources, tools, and prompts.
 * For advanced usage (like sending notifications or setting custom request handlers), use the underlying
 * Server instance available via the `server` property.
 */
export class McpServer {
  /**
   * The underlying Server instance, useful for advanced operations like sending notifications.
   */
  public readonly server: Server;

  private _registeredResources: { [uri: string]: RegisteredResource } = {};
  private _registeredResourceTemplates: {
    [name: string]: RegisteredResourceTemplate;
  } = {};
  private _registeredTools: { [name: string]: RegisteredTool } = {};
  private _registeredPrompts: { [name: string]: RegisteredPrompt } = {};

  constructor(serverInfo: Implementation, options?: ServerOptions) {
    this.server = new Server(serverInfo, options);
  }

  /**
   * Attaches to the given transport, starts it, and starts listening for messages.
   *
   * The `server` object assumes ownership of the Transport, replacing any callbacks that have already been set, and expects that it is the only user of the Transport instance going forward.
   */
  async connect(transport: Transport): Promise<void> {
    return await this.server.connect(transport);
  }

  /**
   * Closes the connection.
   */
  async close(): Promise<void> {
    await this.server.close();
  }

  private _toolHandlersInitialized = false;

  private setToolRequestHandlers() {
    if (this._toolHandlersInitialized) {
      return;
    }

    this.server.assertCanSetRequestHandler(
      ListToolsRequestSchema.shape.method.value,
    );
    this.server.assertCanSetRequestHandler(
      CallToolRequestSchema.shape.method.value,
    );

    this.server.registerCapabilities({
      tools: {
        listChanged: true
      }
    })

    this.server.setRequestHandler(
      ListToolsRequestSchema,
      (): ListToolsResult => ({
        tools: Object.entries(this._registeredTools).filter(
          ([, tool]) => tool.enabled,
        ).map(
          ([name, tool]): Tool => {
            const toolDefinition: Tool = {
              name,
              title: tool.title,
              description: tool.description,
              inputSchema: tool.inputSchema
                ? (zodToJsonSchema(tool.inputSchema, {
                  strictUnions: true,
                }) as Tool["inputSchema"])
                : EMPTY_OBJECT_JSON_SCHEMA,
              annotations: tool.annotations,
            };

            if (tool.outputSchema) {
              toolDefinition.outputSchema = zodToJsonSchema(
                tool.outputSchema,
                { strictUnions: true }
              ) as Tool["outputSchema"];
            }

            return toolDefinition;
          },
        ),
      }),
    );

    this.server.setRequestHandler(
      CallToolRequestSchema,
      async (request, extra): Promise<CallToolResult> => {
        const tool = this._registeredTools[request.params.name];
        if (!tool) {
          throw new McpError(
            ErrorCode.InvalidParams,
            `Tool ${request.params.name} not found`,
          );
        }

        if (!tool.enabled) {
          throw new McpError(
            ErrorCode.InvalidParams,
            `Tool ${request.params.name} disabled`,
          );
        }

        let result: CallToolResult;

        if (tool.inputSchema) {
          const parseResult = await tool.inputSchema.safeParseAsync(
            request.params.arguments,
          );
          if (!parseResult.success) {
            throw new McpError(
              ErrorCode.InvalidParams,
              `Invalid arguments for tool ${request.params.name}: ${parseResult.error.message}`,
            );
          }

          const args = parseResult.data;
          const cb = tool.callback as ToolCallback<ZodRawShape>;
          try {
            result = await Promise.resolve(cb(args, extra));
          } catch (error) {
            result = {
              content: [
                {
                  type: "text",
                  text: error instanceof Error ? error.message : String(error),
                },
              ],
              isError: true,
            };
          }
        } else {
          const cb = tool.callback as ToolCallback<undefined>;
          try {
            result = await Promise.resolve(cb(extra));
          } catch (error) {
            result = {
              content: [
                {
                  type: "text",
                  text: error instanceof Error ? error.message : String(error),
                },
              ],
              isError: true,
            };
          }
        }

        if (tool.outputSchema && !result.isError) {
          if (!result.structuredContent) {
            throw new McpError(
              ErrorCode.InvalidParams,
              `Tool ${request.params.name} has an output schema but no structured content was provided`,
            );
          }

          // if the tool has an output schema, validate structured content
          const parseResult = await tool.outputSchema.safeParseAsync(
            result.structuredContent,
          );
          if (!parseResult.success) {
            throw new McpError(
              ErrorCode.InvalidParams,
              `Invalid structured content for tool ${request.params.name}: ${parseResult.error.message}`,
            );
          }
        }

        return result;
      },
    );

    this._toolHandlersInitialized = true;
  }

  private _completionHandlerInitialized = false;

  private setCompletionRequestHandler() {
    if (this._completionHandlerInitialized) {
      return;
    }

    this.server.assertCanSetRequestHandler(
      CompleteRequestSchema.shape.method.value,
    );

    this.server.registerCapabilities({
      completions: {},
    });

    this.server.setRequestHandler(
      CompleteRequestSchema,
      async (request): Promise<CompleteResult> => {
        switch (request.params.ref.type) {
          case "ref/prompt":
            return this.handlePromptCompletion(request, request.params.ref);

          case "ref/resource":
            return this.handleResourceCompletion(request, request.params.ref);

          default:
            throw new McpError(
              ErrorCode.InvalidParams,
              `Invalid completion reference: ${request.params.ref}`,
            );
        }
      },
    );

    this._completionHandlerInitialized = true;
  }

  private async handlePromptCompletion(
    request: CompleteRequest,
    ref: PromptReference,
  ): Promise<CompleteResult> {
    const prompt = this._registeredPrompts[ref.name];
    if (!prompt) {
      throw new McpError(
        ErrorCode.InvalidParams,
        `Prompt ${ref.name} not found`,
      );
    }

    if (!prompt.enabled) {
      throw new McpError(
        ErrorCode.InvalidParams,
        `Prompt ${ref.name} disabled`,
      );
    }

    if (!prompt.argsSchema) {
      return EMPTY_COMPLETION_RESULT;
    }

    const field = prompt.argsSchema.shape[request.params.argument.name];
    if (!(field instanceof Completable)) {
      return EMPTY_COMPLETION_RESULT;
    }

    const def: CompletableDef<ZodString> = field._def;
    const suggestions = await def.complete(request.params.argument.value, request.params.context);
    return createCompletionResult(suggestions);
  }

  private async handleResourceCompletion(
    request: CompleteRequest,
    ref: ResourceTemplateReference,
  ): Promise<CompleteResult> {
    const template = Object.values(this._registeredResourceTemplates).find(
      (t) => t.resourceTemplate.uriTemplate.toString() === ref.uri,
    );

    if (!template) {
      if (this._registeredResources[ref.uri]) {
        // Attempting to autocomplete a fixed resource URI is not an error in the spec (but probably should be).
        return EMPTY_COMPLETION_RESULT;
      }

      throw new McpError(
        ErrorCode.InvalidParams,
        `Resource template ${request.params.ref.uri} not found`,
      );
    }

    const completer = template.resourceTemplate.completeCallback(
      request.params.argument.name,
    );
    if (!completer) {
      return EMPTY_COMPLETION_RESULT;
    }

    const suggestions = await completer(request.params.argument.value, request.params.context);
    return createCompletionResult(suggestions);
  }

  private _resourceHandlersInitialized = false;

  private setResourceRequestHandlers() {
    if (this._resourceHandlersInitialized) {
      return;
    }

    this.server.assertCanSetRequestHandler(
      ListResourcesRequestSchema.shape.method.value,
    );
    this.server.assertCanSetRequestHandler(
      ListResourceTemplatesRequestSchema.shape.method.value,
    );
    this.server.assertCanSetRequestHandler(
      ReadResourceRequestSchema.shape.method.value,
    );

    this.server.registerCapabilities({
      resources: {
        listChanged: true
      }
    })

    this.server.setRequestHandler(
      ListResourcesRequestSchema,
      async (request, extra) => {
        const resources = Object.entries(this._registeredResources).filter(
          ([_, resource]) => resource.enabled,
        ).map(
          ([uri, resource]) => ({
            uri,
            name: resource.name,
            ...resource.metadata,
          }),
        );

        const templateResources: Resource[] = [];
        for (const template of Object.values(
          this._registeredResourceTemplates,
        )) {
          if (!template.resourceTemplate.listCallback) {
            continue;
          }

          const result = await template.resourceTemplate.listCallback(extra);
          for (const resource of result.resources) {
            templateResources.push({
              ...template.metadata,
              // the defined resource metadata should override the template metadata if present
              ...resource,
            });
          }
        }

        return { resources: [...resources, ...templateResources] };
      },
    );

    this.server.setRequestHandler(
      ListResourceTemplatesRequestSchema,
      async () => {
        const resourceTemplates = Object.entries(
          this._registeredResourceTemplates,
        ).map(([name, template]) => ({
          name,
          uriTemplate: template.resourceTemplate.uriTemplate.toString(),
          ...template.metadata,
        }));

        return { resourceTemplates };
      },
    );

    this.server.setRequestHandler(
      ReadResourceRequestSchema,
      async (request, extra) => {
        const uri = new URL(request.params.uri);

        // First check for exact resource match
        const resource = this._registeredResources[uri.toString()];
        if (resource) {
          if (!resource.enabled) {
            throw new McpError(
              ErrorCode.InvalidParams,
              `Resource ${uri} disabled`,
            );
          }
          return resource.readCallback(uri, extra);
        }

        // Then check templates
        for (const template of Object.values(
          this._registeredResourceTemplates,
        )) {
          const variables = template.resourceTemplate.uriTemplate.match(
            uri.toString(),
          );
          if (variables) {
            return template.readCallback(uri, variables, extra);
          }
        }

        throw new McpError(
          ErrorCode.InvalidParams,
          `Resource ${uri} not found`,
        );
      },
    );

    this.setCompletionRequestHandler();

    this._resourceHandlersInitialized = true;
  }

  private _promptHandlersInitialized = false;

  private setPromptRequestHandlers() {
    if (this._promptHandlersInitialized) {
      return;
    }

    this.server.assertCanSetRequestHandler(
      ListPromptsRequestSchema.shape.method.value,
    );
    this.server.assertCanSetRequestHandler(
      GetPromptRequestSchema.shape.method.value,
    );

    this.server.registerCapabilities({
      prompts: {
        listChanged: true
      }
    })

    this.server.setRequestHandler(
      ListPromptsRequestSchema,
      (): ListPromptsResult => ({
        prompts: Object.entries(this._registeredPrompts).filter(
          ([, prompt]) => prompt.enabled,
        ).map(
          ([name, prompt]): Prompt => {
            return {
              name,
              title: prompt.title,
              description: prompt.description,
              arguments: prompt.argsSchema
                ? promptArgumentsFromSchema(prompt.argsSchema)
                : undefined,
            };
          },
        ),
      }),
    );

    this.server.setRequestHandler(
      GetPromptRequestSchema,
      async (request, extra): Promise<GetPromptResult> => {
        const prompt = this._registeredPrompts[request.params.name];
        if (!prompt) {
          throw new McpError(
            ErrorCode.InvalidParams,
            `Prompt ${request.params.name} not found`,
          );
        }

        if (!prompt.enabled) {
          throw new McpError(
            ErrorCode.InvalidParams,
            `Prompt ${request.params.name} disabled`,
          );
        }

        if (prompt.argsSchema) {
          const parseResult = await prompt.argsSchema.safeParseAsync(
            request.params.arguments,
          );
          if (!parseResult.success) {
            throw new McpError(
              ErrorCode.InvalidParams,
              `Invalid arguments for prompt ${request.params.name}: ${parseResult.error.message}`,
            );
          }

          const args = parseResult.data;
          const cb = prompt.callback as PromptCallback<PromptArgsRawShape>;
          return await Promise.resolve(cb(args, extra));
        } else {
          const cb = prompt.callback as PromptCallback<undefined>;
          return await Promise.resolve(cb(extra));
        }
      },
    );

    this.setCompletionRequestHandler();

    this._promptHandlersInitialized = true;
  }

  /**
   * Registers a resource `name` at a fixed URI, which will use the given callback to respond to read requests.
   */
  resource(name: string, uri: string, readCallback: ReadResourceCallback): RegisteredResource;

  /**
   * Registers a resource `name` at a fixed URI with metadata, which will use the given callback to respond to read requests.
   */
  resource(
    name: string,
    uri: string,
    metadata: ResourceMetadata,
    readCallback: ReadResourceCallback,
  ): RegisteredResource;

  /**
   * Registers a resource `name` with a template pattern, which will use the given callback to respond to read requests.
   */
  resource(
    name: string,
    template: ResourceTemplate,
    readCallback: ReadResourceTemplateCallback,
  ): RegisteredResourceTemplate;

  /**
   * Registers a resource `name` with a template pattern and metadata, which will use the given callback to respond to read requests.
   */
  resource(
    name: string,
    template: ResourceTemplate,
    metadata: ResourceMetadata,
    readCallback: ReadResourceTemplateCallback,
  ): RegisteredResourceTemplate;

  resource(
    name: string,
    uriOrTemplate: string | ResourceTemplate,
    ...rest: unknown[]
  ): RegisteredResource | RegisteredResourceTemplate {
    let metadata: ResourceMetadata | undefined;
    if (typeof rest[0] === "object") {
      metadata = rest.shift() as ResourceMetadata;
    }

    const readCallback = rest[0] as
      | ReadResourceCallback
      | ReadResourceTemplateCallback;

    if (typeof uriOrTemplate === "string") {
      if (this._registeredResources[uriOrTemplate]) {
        throw new Error(`Resource ${uriOrTemplate} is already registered`);
      }

      const registeredResource = this._createRegisteredResource(
        name,
        undefined,
        uriOrTemplate,
        metadata,
        readCallback as ReadResourceCallback
      );

      this.setResourceRequestHandlers();
      this.sendResourceListChanged();
      return registeredResource;
    } else {
      if (this._registeredResourceTemplates[name]) {
        throw new Error(`Resource template ${name} is already registered`);
      }

      const registeredResourceTemplate = this._createRegisteredResourceTemplate(
        name,
        undefined,
        uriOrTemplate,
        metadata,
        readCallback as ReadResourceTemplateCallback
      );

      this.setResourceRequestHandlers();
      this.sendResourceListChanged();
      return registeredResourceTemplate;
    }
  }

  /**
   * Registers a resource with a config object and callback.
   * For static resources, use a URI string. For dynamic resources, use a ResourceTemplate.
   */
  registerResource(
    name: string,
    uriOrTemplate: string,
    config: ResourceMetadata,
    readCallback: ReadResourceCallback
  ): RegisteredResource;
  registerResource(
    name: string,
    uriOrTemplate: ResourceTemplate,
    config: ResourceMetadata,
    readCallback: ReadResourceTemplateCallback
  ): RegisteredResourceTemplate;
  registerResource(
    name: string,
    uriOrTemplate: string | ResourceTemplate,
    config: ResourceMetadata,
    readCallback: ReadResourceCallback | ReadResourceTemplateCallback
  ): RegisteredResource | RegisteredResourceTemplate {
    if (typeof uriOrTemplate === "string") {
      if (this._registeredResources[uriOrTemplate]) {
        throw new Error(`Resource ${uriOrTemplate} is already registered`);
      }

      const registeredResource = this._createRegisteredResource(
        name,
        (config as BaseMetadata).title,
        uriOrTemplate,
        config,
        readCallback as ReadResourceCallback
      );

      this.setResourceRequestHandlers();
      this.sendResourceListChanged();
      return registeredResource;
    } else {
      if (this._registeredResourceTemplates[name]) {
        throw new Error(`Resource template ${name} is already registered`);
      }

      const registeredResourceTemplate = this._createRegisteredResourceTemplate(
        name,
        (config as BaseMetadata).title,
        uriOrTemplate,
        config,
        readCallback as ReadResourceTemplateCallback
      );

      this.setResourceRequestHandlers();
      this.sendResourceListChanged();
      return registeredResourceTemplate;
    }
  }

  private _createRegisteredResource(
    name: string,
    title: string | undefined,
    uri: string,
    metadata: ResourceMetadata | undefined,
    readCallback: ReadResourceCallback
  ): RegisteredResource {
    const registeredResource: RegisteredResource = {
      name,
      title,
      metadata,
      readCallback,
      enabled: true,
      disable: () => registeredResource.update({ enabled: false }),
      enable: () => registeredResource.update({ enabled: true }),
      remove: () => registeredResource.update({ uri: null }),
      update: (updates) => {
        if (typeof updates.uri !== "undefined" && updates.uri !== uri) {
          delete this._registeredResources[uri]
          if (updates.uri) this._registeredResources[updates.uri] = registeredResource
        }
        if (typeof updates.name !== "undefined") registeredResource.name = updates.name
        if (typeof updates.title !== "undefined") registeredResource.title = updates.title
        if (typeof updates.metadata !== "undefined") registeredResource.metadata = updates.metadata
        if (typeof updates.callback !== "undefined") registeredResource.readCallback = updates.callback
        if (typeof updates.enabled !== "undefined") registeredResource.enabled = updates.enabled
        this.sendResourceListChanged()
      },
    };
    this._registeredResources[uri] = registeredResource;
    return registeredResource;
  }

  private _createRegisteredResourceTemplate(
    name: string,
    title: string | undefined,
    template: ResourceTemplate,
    metadata: ResourceMetadata | undefined,
    readCallback: ReadResourceTemplateCallback
  ): RegisteredResourceTemplate {
    const registeredResourceTemplate: RegisteredResourceTemplate = {
      resourceTemplate: template,
      title,
      metadata,
      readCallback,
      enabled: true,
      disable: () => registeredResourceTemplate.update({ enabled: false }),
      enable: () => registeredResourceTemplate.update({ enabled: true }),
      remove: () => registeredResourceTemplate.update({ name: null }),
      update: (updates) => {
        if (typeof updates.name !== "undefined" && updates.name !== name) {
          delete this._registeredResourceTemplates[name]
          if (updates.name) this._registeredResourceTemplates[updates.name] = registeredResourceTemplate
        }
        if (typeof updates.title !== "undefined") registeredResourceTemplate.title = updates.title
        if (typeof updates.template !== "undefined") registeredResourceTemplate.resourceTemplate = updates.template
        if (typeof updates.metadata !== "undefined") registeredResourceTemplate.metadata = updates.metadata
        if (typeof updates.callback !== "undefined") registeredResourceTemplate.readCallback = updates.callback
        if (typeof updates.enabled !== "undefined") registeredResourceTemplate.enabled = updates.enabled
        this.sendResourceListChanged()
      },
    };
    this._registeredResourceTemplates[name] = registeredResourceTemplate;
    return registeredResourceTemplate;
  }

  private _createRegisteredPrompt(
    name: string,
    title: string | undefined,
    description: string | undefined,
    argsSchema: PromptArgsRawShape | undefined,
    callback: PromptCallback<PromptArgsRawShape | undefined>
  ): RegisteredPrompt {
    const registeredPrompt: RegisteredPrompt = {
      title,
      description,
      argsSchema: argsSchema === undefined ? undefined : z.object(argsSchema),
      callback,
      enabled: true,
      disable: () => registeredPrompt.update({ enabled: false }),
      enable: () => registeredPrompt.update({ enabled: true }),
      remove: () => registeredPrompt.update({ name: null }),
      update: (updates) => {
        if (typeof updates.name !== "undefined" && updates.name !== name) {
          delete this._registeredPrompts[name]
          if (updates.name) this._registeredPrompts[updates.name] = registeredPrompt
        }
        if (typeof updates.title !== "undefined") registeredPrompt.title = updates.title
        if (typeof updates.description !== "undefined") registeredPrompt.description = updates.description
        if (typeof updates.argsSchema !== "undefined") registeredPrompt.argsSchema = z.object(updates.argsSchema)
        if (typeof updates.callback !== "undefined") registeredPrompt.callback = updates.callback
        if (typeof updates.enabled !== "undefined") registeredPrompt.enabled = updates.enabled
        this.sendPromptListChanged()
      },
    };
    this._registeredPrompts[name] = registeredPrompt;
    return registeredPrompt;
  }

  private _createRegisteredTool(
    name: string,
    title: string | undefined,
    description: string | undefined,
    inputSchema: ZodRawShape | undefined,
    outputSchema: ZodRawShape | undefined,
    annotations: ToolAnnotations | undefined,
    callback: ToolCallback<ZodRawShape | undefined>
  ): RegisteredTool {
    const registeredTool: RegisteredTool = {
      title,
      description,
      inputSchema:
        inputSchema === undefined ? undefined : z.object(inputSchema),
      outputSchema:
        outputSchema === undefined ? undefined : z.object(outputSchema),
      annotations,
      callback,
      enabled: true,
      disable: () => registeredTool.update({ enabled: false }),
      enable: () => registeredTool.update({ enabled: true }),
      remove: () => registeredTool.update({ name: null }),
      update: (updates) => {
        if (typeof updates.name !== "undefined" && updates.name !== name) {
          delete this._registeredTools[name]
          if (updates.name) this._registeredTools[updates.name] = registeredTool
        }
        if (typeof updates.title !== "undefined") registeredTool.title = updates.title
        if (typeof updates.description !== "undefined") registeredTool.description = updates.description
        if (typeof updates.paramsSchema !== "undefined") registeredTool.inputSchema = z.object(updates.paramsSchema)
        if (typeof updates.callback !== "undefined") registeredTool.callback = updates.callback
        if (typeof updates.annotations !== "undefined") registeredTool.annotations = updates.annotations
        if (typeof updates.enabled !== "undefined") registeredTool.enabled = updates.enabled
        this.sendToolListChanged()
      },
    };
    this._registeredTools[name] = registeredTool;

    this.setToolRequestHandlers();
    this.sendToolListChanged()

    return registeredTool
  }

  /**
   * Registers a zero-argument tool `name`, which will run the given function when the client calls it.
   */
  tool(name: string, cb: ToolCallback): RegisteredTool;

  /**
   * Registers a zero-argument tool `name` (with a description) which will run the given function when the client calls it.
   */
  tool(name: string, description: string, cb: ToolCallback): RegisteredTool;

  /**
   * Registers a tool taking either a parameter schema for validation or annotations for additional metadata.
   * This unified overload handles both `tool(name, paramsSchema, cb)` and `tool(name, annotations, cb)` cases.
   * 
   * Note: We use a union type for the second parameter because TypeScript cannot reliably disambiguate
   * between ToolAnnotations and ZodRawShape during overload resolution, as both are plain object types.
   */
  tool<Args extends ZodRawShape>(
    name: string,
    paramsSchemaOrAnnotations: Args | ToolAnnotations,
    cb: ToolCallback<Args>,
  ): RegisteredTool;

  /**
   * Registers a tool `name` (with a description) taking either parameter schema or annotations.
   * This unified overload handles both `tool(name, description, paramsSchema, cb)` and 
   * `tool(name, description, annotations, cb)` cases.
   * 
   * Note: We use a union type for the third parameter because TypeScript cannot reliably disambiguate
   * between ToolAnnotations and ZodRawShape during overload resolution, as both are plain object types.
   */
  tool<Args extends ZodRawShape>(
    name: string,
    description: string,
    paramsSchemaOrAnnotations: Args | ToolAnnotations,
    cb: ToolCallback<Args>,
  ): RegisteredTool;

  /**
   * Registers a tool with both parameter schema and annotations.
   */
  tool<Args extends ZodRawShape>(
    name: string,
    paramsSchema: Args,
    annotations: ToolAnnotations,
    cb: ToolCallback<Args>,
  ): RegisteredTool;

  /**
   * Registers a tool with description, parameter schema, and annotations.
   */
  tool<Args extends ZodRawShape>(
    name: string,
    description: string,
    paramsSchema: Args,
    annotations: ToolAnnotations,
    cb: ToolCallback<Args>,
  ): RegisteredTool;


  /**
   * tool() implementation. Parses arguments passed to overrides defined above.
   */
  tool(name: string, ...rest: unknown[]): RegisteredTool {
    if (this._registeredTools[name]) {
      throw new Error(`Tool ${name} is already registered`);
    }

    let description: string | undefined;
    let inputSchema: ZodRawShape | undefined;
    let outputSchema: ZodRawShape | undefined;
    let annotations: ToolAnnotations | undefined;

    // Tool properties are passed as separate arguments, with omissions allowed.
    // Support for this style is frozen as of protocol version 2025-03-26. Future additions
    // to tool definition should *NOT* be added.

    if (typeof rest[0] === "string") {
      description = rest.shift() as string;
    }

    // Handle the different overload combinations
    if (rest.length > 1) {
      // We have at least one more arg before the callback
      const firstArg = rest[0];

      if (isZodRawShape(firstArg)) {
        // We have a params schema as the first arg
        inputSchema = rest.shift() as ZodRawShape;

        // Check if the next arg is potentially annotations
        if (rest.length > 1 && typeof rest[0] === "object" && rest[0] !== null && !(isZodRawShape(rest[0]))) {
          // Case: tool(name, paramsSchema, annotations, cb)
          // Or: tool(name, description, paramsSchema, annotations, cb)
          annotations = rest.shift() as ToolAnnotations;
        }
      } else if (typeof firstArg === "object" && firstArg !== null) {
        // Not a ZodRawShape, so must be annotations in this position
        // Case: tool(name, annotations, cb)
        // Or: tool(name, description, annotations, cb)
        annotations = rest.shift() as ToolAnnotations;
      }
    }
    const callback = rest[0] as ToolCallback<ZodRawShape | undefined>;

    return this._createRegisteredTool(name, undefined, description, inputSchema, outputSchema, annotations, callback)
  }

  /**
   * Registers a tool with a config object and callback.
   */
  registerTool<InputArgs extends ZodRawShape, OutputArgs extends ZodRawShape>(
    name: string,
    config: {
      title?: string;
      description?: string;
      inputSchema?: InputArgs;
      outputSchema?: OutputArgs;
      annotations?: ToolAnnotations;
    },
    cb: ToolCallback<InputArgs>
  ): RegisteredTool {
    if (this._registeredTools[name]) {
      throw new Error(`Tool ${name} is already registered`);
    }

    const { title, description, inputSchema, outputSchema, annotations } = config;

    return this._createRegisteredTool(
      name,
      title,
      description,
      inputSchema,
      outputSchema,
      annotations,
      cb as ToolCallback<ZodRawShape | undefined>
    );
  }

  /**
   * Registers a zero-argument prompt `name`, which will run the given function when the client calls it.
   */
  prompt(name: string, cb: PromptCallback): RegisteredPrompt;

  /**
   * Registers a zero-argument prompt `name` (with a description) which will run the given function when the client calls it.
   */
  prompt(name: string, description: string, cb: PromptCallback): RegisteredPrompt;

  /**
   * Registers a prompt `name` accepting the given arguments, which must be an object containing named properties associated with Zod schemas. When the client calls it, the function will be run with the parsed and validated arguments.
   */
  prompt<Args extends PromptArgsRawShape>(
    name: string,
    argsSchema: Args,
    cb: PromptCallback<Args>,
  ): RegisteredPrompt;

  /**
   * Registers a prompt `name` (with a description) accepting the given arguments, which must be an object containing named properties associated with Zod schemas. When the client calls it, the function will be run with the parsed and validated arguments.
   */
  prompt<Args extends PromptArgsRawShape>(
    name: string,
    description: string,
    argsSchema: Args,
    cb: PromptCallback<Args>,
  ): RegisteredPrompt;

  prompt(name: string, ...rest: unknown[]): RegisteredPrompt {
    if (this._registeredPrompts[name]) {
      throw new Error(`Prompt ${name} is already registered`);
    }

    let description: string | undefined;
    if (typeof rest[0] === "string") {
      description = rest.shift() as string;
    }

    let argsSchema: PromptArgsRawShape | undefined;
    if (rest.length > 1) {
      argsSchema = rest.shift() as PromptArgsRawShape;
    }

    const cb = rest[0] as PromptCallback<PromptArgsRawShape | undefined>;
    const registeredPrompt = this._createRegisteredPrompt(
      name,
      undefined,
      description,
      argsSchema,
      cb
    );

    this.setPromptRequestHandlers();
    this.sendPromptListChanged()

    return registeredPrompt
  }

  /**
   * Registers a prompt with a config object and callback.
   */
  registerPrompt<Args extends PromptArgsRawShape>(
    name: string,
    config: {
      title?: string;
      description?: string;
      argsSchema?: Args;
    },
    cb: PromptCallback<Args>
  ): RegisteredPrompt {
    if (this._registeredPrompts[name]) {
      throw new Error(`Prompt ${name} is already registered`);
    }

    const { title, description, argsSchema } = config;

    const registeredPrompt = this._createRegisteredPrompt(
      name,
      title,
      description,
      argsSchema,
      cb as PromptCallback<PromptArgsRawShape | undefined>
    );

    this.setPromptRequestHandlers();
    this.sendPromptListChanged()

    return registeredPrompt;
  }

  /**
   * Checks if the server is connected to a transport.
   * @returns True if the server is connected
   */
  isConnected() {
    return this.server.transport !== undefined
  }

  /**
   * Sends a resource list changed event to the client, if connected.
   */
  sendResourceListChanged() {
    if (this.isConnected()) {
      this.server.sendResourceListChanged();
    }
  }

  /**
   * Sends a tool list changed event to the client, if connected.
   */
  sendToolListChanged() {
    if (this.isConnected()) {
      this.server.sendToolListChanged();
    }
  }

  /**
   * Sends a prompt list changed event to the client, if connected.
   */
  sendPromptListChanged() {
    if (this.isConnected()) {
      this.server.sendPromptListChanged();
    }
  }
}

/**
 * A callback to complete one variable within a resource template's URI template.
 */
export type CompleteResourceTemplateCallback = (
  value: string,
  context?: {
    arguments?: Record<string, string>;
  },
) => string[] | Promise<string[]>;

/**
 * A resource template combines a URI pattern with optional functionality to enumerate
 * all resources matching that pattern.
 */
export class ResourceTemplate {
  private _uriTemplate: UriTemplate;

  constructor(
    uriTemplate: string | UriTemplate,
    private _callbacks: {
      /**
       * A callback to list all resources matching this template. This is required to specified, even if `undefined`, to avoid accidentally forgetting resource listing.
       */
      list: ListResourcesCallback | undefined;

      /**
       * An optional callback to autocomplete variables within the URI template. Useful for clients and users to discover possible values.
       */
      complete?: {
        [variable: string]: CompleteResourceTemplateCallback;
      };
    },
  ) {
    this._uriTemplate =
      typeof uriTemplate === "string"
        ? new UriTemplate(uriTemplate)
        : uriTemplate;
  }

  /**
   * Gets the URI template pattern.
   */
  get uriTemplate(): UriTemplate {
    return this._uriTemplate;
  }

  /**
   * Gets the list callback, if one was provided.
   */
  get listCallback(): ListResourcesCallback | undefined {
    return this._callbacks.list;
  }

  /**
   * Gets the callback for completing a specific URI template variable, if one was provided.
   */
  completeCallback(
    variable: string,
  ): CompleteResourceTemplateCallback | undefined {
    return this._callbacks.complete?.[variable];
  }
}

/**
 * Callback for a tool handler registered with Server.tool().
 *
 * Parameters will include tool arguments, if applicable, as well as other request handler context.
 *
 * The callback should return:
 * - `structuredContent` if the tool has an outputSchema defined
 * - `content` if the tool does not have an outputSchema
 * - Both fields are optional but typically one should be provided
 */
export type ToolCallback<Args extends undefined | ZodRawShape = undefined> =
  Args extends ZodRawShape
  ? (
    args: z.objectOutputType<Args, ZodTypeAny>,
    extra: RequestHandlerExtra<ServerRequest, ServerNotification>,
  ) => CallToolResult | Promise<CallToolResult>
  : (extra: RequestHandlerExtra<ServerRequest, ServerNotification>) => CallToolResult | Promise<CallToolResult>;

export type RegisteredTool = {
  title?: string;
  description?: string;
  inputSchema?: AnyZodObject;
  outputSchema?: AnyZodObject;
  annotations?: ToolAnnotations;
  callback: ToolCallback<undefined | ZodRawShape>;
  enabled: boolean;
  enable(): void;
  disable(): void;
  update<InputArgs extends ZodRawShape, OutputArgs extends ZodRawShape>(
    updates: {
      name?: string | null,
      title?: string,
      description?: string,
      paramsSchema?: InputArgs,
      outputSchema?: OutputArgs,
      annotations?: ToolAnnotations,
      callback?: ToolCallback<InputArgs>,
      enabled?: boolean
    }): void
  remove(): void
};

const EMPTY_OBJECT_JSON_SCHEMA = {
  type: "object" as const,
  properties: {},
};

// Helper to check if an object is a Zod schema (ZodRawShape)
function isZodRawShape(obj: unknown): obj is ZodRawShape {
  if (typeof obj !== "object" || obj === null) return false;

  const isEmptyObject = Object.keys(obj).length === 0;

  // Check if object is empty or at least one property is a ZodType instance
  // Note: use heuristic check to avoid instanceof failure across different Zod versions
  return isEmptyObject || Object.values(obj as object).some(isZodTypeLike);
}

function isZodTypeLike(value: unknown): value is ZodType {
  return value !== null &&
    typeof value === 'object' &&
    'parse' in value && typeof value.parse === 'function' &&
    'safeParse' in value && typeof value.safeParse === 'function';
}

/**
 * Additional, optional information for annotating a resource.
 */
export type ResourceMetadata = Omit<Resource, "uri" | "name">;

/**
 * Callback to list all resources matching a given template.
 */
export type ListResourcesCallback = (
  extra: RequestHandlerExtra<ServerRequest, ServerNotification>,
) => ListResourcesResult | Promise<ListResourcesResult>;

/**
 * Callback to read a resource at a given URI.
 */
export type ReadResourceCallback = (
  uri: URL,
  extra: RequestHandlerExtra<ServerRequest, ServerNotification>,
) => ReadResourceResult | Promise<ReadResourceResult>;

export type RegisteredResource = {
  name: string;
  title?: string;
  metadata?: ResourceMetadata;
  readCallback: ReadResourceCallback;
  enabled: boolean;
  enable(): void;
  disable(): void;
  update(updates: { name?: string, title?: string, uri?: string | null, metadata?: ResourceMetadata, callback?: ReadResourceCallback, enabled?: boolean }): void
  remove(): void
};

/**
 * Callback to read a resource at a given URI, following a filled-in URI template.
 */
export type ReadResourceTemplateCallback = (
  uri: URL,
  variables: Variables,
  extra: RequestHandlerExtra<ServerRequest, ServerNotification>,
) => ReadResourceResult | Promise<ReadResourceResult>;

export type RegisteredResourceTemplate = {
  resourceTemplate: ResourceTemplate;
  title?: string;
  metadata?: ResourceMetadata;
  readCallback: ReadResourceTemplateCallback;
  enabled: boolean;
  enable(): void;
  disable(): void;
  update(updates: { name?: string | null, title?: string, template?: ResourceTemplate, metadata?: ResourceMetadata, callback?: ReadResourceTemplateCallback, enabled?: boolean }): void
  remove(): void
};

type PromptArgsRawShape = {
  [k: string]:
  | ZodType<string, ZodTypeDef, string>
  | ZodOptional<ZodType<string, ZodTypeDef, string>>;
};

export type PromptCallback<
  Args extends undefined | PromptArgsRawShape = undefined,
> = Args extends PromptArgsRawShape
  ? (
    args: z.objectOutputType<Args, ZodTypeAny>,
    extra: RequestHandlerExtra<ServerRequest, ServerNotification>,
  ) => GetPromptResult | Promise<GetPromptResult>
  : (extra: RequestHandlerExtra<ServerRequest, ServerNotification>) => GetPromptResult | Promise<GetPromptResult>;

export type RegisteredPrompt = {
  title?: string;
  description?: string;
  argsSchema?: ZodObject<PromptArgsRawShape>;
  callback: PromptCallback<undefined | PromptArgsRawShape>;
  enabled: boolean;
  enable(): void;
  disable(): void;
  update<Args extends PromptArgsRawShape>(updates: { name?: string | null, title?: string, description?: string, argsSchema?: Args, callback?: PromptCallback<Args>, enabled?: boolean }): void
  remove(): void
};

function promptArgumentsFromSchema(
  schema: ZodObject<PromptArgsRawShape>,
): PromptArgument[] {
  return Object.entries(schema.shape).map(
    ([name, field]): PromptArgument => ({
      name,
      description: field.description,
      required: !field.isOptional(),
    }),
  );
}

function createCompletionResult(suggestions: string[]): CompleteResult {
  return {
    completion: {
      values: suggestions.slice(0, 100),
      total: suggestions.length,
      hasMore: suggestions.length > 100,
    },
  };
}

const EMPTY_COMPLETION_RESULT: CompleteResult = {
  completion: {
    values: [],
    hasMore: false,
  },
};



================================================
FILE: src/server/sse.test.ts
================================================
import http from 'http'; 
import { jest } from '@jest/globals';
import { SSEServerTransport } from './sse.js'; 
import { McpServer } from './mcp.js';
import { createServer, type Server } from "node:http";
import { AddressInfo } from "node:net";
import { z } from 'zod';
import { CallToolResult, JSONRPCMessage } from 'src/types.js';

const createMockResponse = () => {
  const res = {
    writeHead: jest.fn<http.ServerResponse['writeHead']>().mockReturnThis(),
    write: jest.fn<http.ServerResponse['write']>().mockReturnThis(),
    on: jest.fn<http.ServerResponse['on']>().mockReturnThis(),
    end: jest.fn<http.ServerResponse['end']>().mockReturnThis(),
  };
  
  return res as unknown as jest.Mocked<http.ServerResponse>;
};

const createMockRequest = ({ headers = {}, body }: { headers?: Record<string, string>, body?: string } = {}) => {
  const mockReq = {
    headers,
    body: body ? body : undefined,
    auth: {
      token: 'test-token',
    },
    on: jest.fn<http.IncomingMessage['on']>().mockImplementation((event, listener) => {
      const mockListener = listener as unknown as (...args: unknown[]) => void;
      if (event === 'data') {
        mockListener(Buffer.from(body || '') as unknown as Error);
      }
      if (event === 'error') {
        mockListener(new Error('test'));
      }
      if (event === 'end') {
        mockListener();
      }
      if (event === 'close') {
        setTimeout(listener, 100);
      }
      return mockReq;
    }),
    listeners: jest.fn<http.IncomingMessage['listeners']>(),
    removeListener: jest.fn<http.IncomingMessage['removeListener']>(),
  } as unknown as http.IncomingMessage;

  return mockReq;
};

/**
 * Helper to create and start test HTTP server with MCP setup
 */
async function createTestServerWithSse(args: {
  mockRes: http.ServerResponse;
}): Promise<{
  server: Server;
  transport: SSEServerTransport;
  mcpServer: McpServer;
  baseUrl: URL;
  sessionId: string
  serverPort: number;
}> {
  const mcpServer = new McpServer(
    { name: "test-server", version: "1.0.0" },
    { capabilities: { logging: {} } }
  );

  mcpServer.tool(
    "greet",
    "A simple greeting tool",
    { name: z.string().describe("Name to greet") },
    async ({ name }): Promise<CallToolResult> => {
      return { content: [{ type: "text", text: `Hello, ${name}!` }] };
    }
  );

  const endpoint = '/messages';

  const transport = new SSEServerTransport(endpoint, args.mockRes);
  const sessionId = transport.sessionId;

  await mcpServer.connect(transport);

  const server = createServer(async (req, res) => {
    try {
        await transport.handlePostMessage(req, res);
    } catch (error) {
      console.error("Error handling request:", error);
      if (!res.headersSent) res.writeHead(500).end();
    }
  });

  const baseUrl = await new Promise<URL>((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as AddressInfo;
      resolve(new URL(`http://127.0.0.1:${addr.port}`));
    });
  });

  const port = (server.address() as AddressInfo).port;

  return { server, transport, mcpServer, baseUrl, sessionId, serverPort: port };
}

async function readAllSSEEvents(response: Response): Promise<string[]> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No readable stream');
  
  const events: string[] = [];
  const decoder = new TextDecoder();
  
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      if (value) {
        events.push(decoder.decode(value));
      }
    }
  } finally {
    reader.releaseLock();
  }
  
  return events;
}

/**
 * Helper to send JSON-RPC request
 */
async function sendSsePostRequest(baseUrl: URL, message: JSONRPCMessage | JSONRPCMessage[], sessionId?: string, extraHeaders?: Record<string, string>): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
    ...extraHeaders
  };

  if (sessionId) {
    baseUrl.searchParams.set('sessionId', sessionId);
  }

  return fetch(baseUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(message),
  });
}

describe('SSEServerTransport', () => {

  async function initializeServer(baseUrl: URL): Promise<void> {
    const response = await sendSsePostRequest(baseUrl, {
      jsonrpc: "2.0",
      method: "initialize",
      params: {
        clientInfo: { name: "test-client", version: "1.0" },
        protocolVersion: "2025-03-26",
        capabilities: {
        },
      },
  
      id: "init-1",
    } as JSONRPCMessage);

    expect(response.status).toBe(202);

    const text = await readAllSSEEvents(response);

    expect(text).toHaveLength(1);
    expect(text[0]).toBe('Accepted');
  }

  describe('start method', () => { 
    it('should correctly append sessionId to a simple relative endpoint', async () => { 
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);
      const expectedSessionId = transport.sessionId;

      await transport.start();

      expect(mockRes.writeHead).toHaveBeenCalledWith(200, expect.any(Object));
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        `event: endpoint\ndata: /messages?sessionId=${expectedSessionId}\n\n`
      );
    });

    it('should correctly append sessionId to an endpoint with existing query parameters', async () => { 
      const mockRes = createMockResponse();
      const endpoint = '/messages?foo=bar&baz=qux';
      const transport = new SSEServerTransport(endpoint, mockRes);
      const expectedSessionId = transport.sessionId;

      await transport.start();

      expect(mockRes.writeHead).toHaveBeenCalledWith(200, expect.any(Object));
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        `event: endpoint\ndata: /messages?foo=bar&baz=qux&sessionId=${expectedSessionId}\n\n`
      );
    });

    it('should correctly append sessionId to an endpoint with a hash fragment', async () => { 
      const mockRes = createMockResponse();
      const endpoint = '/messages#section1';
      const transport = new SSEServerTransport(endpoint, mockRes);
      const expectedSessionId = transport.sessionId;

      await transport.start();

      expect(mockRes.writeHead).toHaveBeenCalledWith(200, expect.any(Object));
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        `event: endpoint\ndata: /messages?sessionId=${expectedSessionId}#section1\n\n`
      );
    });

    it('should correctly append sessionId to an endpoint with query parameters and a hash fragment', async () => { 
      const mockRes = createMockResponse();
      const endpoint = '/messages?key=value#section2';
      const transport = new SSEServerTransport(endpoint, mockRes);
      const expectedSessionId = transport.sessionId;

      await transport.start();

      expect(mockRes.writeHead).toHaveBeenCalledWith(200, expect.any(Object));
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        `event: endpoint\ndata: /messages?key=value&sessionId=${expectedSessionId}#section2\n\n`
      );
    });

    it('should correctly handle the root path endpoint "/"', async () => { 
      const mockRes = createMockResponse();
      const endpoint = '/';
      const transport = new SSEServerTransport(endpoint, mockRes);
      const expectedSessionId = transport.sessionId;

      await transport.start();

      expect(mockRes.writeHead).toHaveBeenCalledWith(200, expect.any(Object));
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        `event: endpoint\ndata: /?sessionId=${expectedSessionId}\n\n`
      );
    });

    it('should correctly handle an empty string endpoint ""', async () => { 
      const mockRes = createMockResponse();
      const endpoint = ''; 
      const transport = new SSEServerTransport(endpoint, mockRes);
      const expectedSessionId = transport.sessionId;

      await transport.start();

      expect(mockRes.writeHead).toHaveBeenCalledWith(200, expect.any(Object));
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        `event: endpoint\ndata: /?sessionId=${expectedSessionId}\n\n`
      );
    });

  /**
   * Test: Tool With Request Info
   */
  it("should pass request info to tool callback", async () => {
    const mockRes = createMockResponse();
    const { mcpServer, baseUrl, sessionId, serverPort } = await createTestServerWithSse({ mockRes });
    await initializeServer(baseUrl);

    mcpServer.tool(
      "test-request-info",
      "A simple test tool with request info",
      { name: z.string().describe("Name to greet") },
      async ({ name }, { requestInfo }): Promise<CallToolResult> => {
        return { content: [{ type: "text", text: `Hello, ${name}!` }, { type: "text", text: `${JSON.stringify(requestInfo)}` }] };
      }
    );
   
    const toolCallMessage: JSONRPCMessage = {
      jsonrpc: "2.0",
      method: "tools/call",
      params: {
        name: "test-request-info",
        arguments: {
          name: "Test User",
        },
      },
      id: "call-1",
    };

    const response = await sendSsePostRequest(baseUrl, toolCallMessage, sessionId);

    expect(response.status).toBe(202);

    expect(mockRes.write).toHaveBeenCalledWith(`event: endpoint\ndata: /messages?sessionId=${sessionId}\n\n`);

    const expectedMessage = {
      result: {
        content: [
          {
            type: "text",
            text: "Hello, Test User!",
          },
          {
            type: "text",
            text: JSON.stringify({
              headers: {
                host: `127.0.0.1:${serverPort}`,
                connection: 'keep-alive',
                'content-type': 'application/json',
                accept: 'application/json, text/event-stream',
                'accept-language': '*',
                'sec-fetch-mode': 'cors',
                'user-agent': 'node',
                'accept-encoding': 'gzip, deflate',
                'content-length': '124'
              },
            })
          },
        ],
      },
      jsonrpc: "2.0",
      id: "call-1",
    };
    expect(mockRes.write).toHaveBeenCalledWith(`event: message\ndata: ${JSON.stringify(expectedMessage)}\n\n`);
  });
  });

  describe('handlePostMessage method', () => {
    it('should return 500 if server has not started', async () => {
      const mockReq = createMockRequest();
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);

      const error = 'SSE connection not established';
      await expect(transport.handlePostMessage(mockReq, mockRes))
        .rejects.toThrow(error);
      expect(mockRes.writeHead).toHaveBeenCalledWith(500);
      expect(mockRes.end).toHaveBeenCalledWith(error);
    });

    it('should return 400 if content-type is not application/json', async () => {
      const mockReq = createMockRequest({ headers: { 'content-type': 'text/plain' } });
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);
      await transport.start();

      transport.onerror = jest.fn();
      const error = 'Unsupported content-type: text/plain';
      await expect(transport.handlePostMessage(mockReq, mockRes))
        .resolves.toBe(undefined);
      expect(mockRes.writeHead).toHaveBeenCalledWith(400);
      expect(mockRes.end).toHaveBeenCalledWith(expect.stringContaining(error));
      expect(transport.onerror).toHaveBeenCalledWith(new Error(error));
    });

    it('should return 400 if message has not a valid schema', async () => {
      const invalidMessage = JSON.stringify({
        // missing jsonrpc field
        method: 'call',
        params: [1, 2, 3],
        id: 1,
      })
      const mockReq = createMockRequest({
        headers: { 'content-type': 'application/json' },
        body: invalidMessage,
      });
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);
      await transport.start();

      transport.onmessage = jest.fn();
      await transport.handlePostMessage(mockReq, mockRes);
      expect(mockRes.writeHead).toHaveBeenCalledWith(400);
      expect(transport.onmessage).not.toHaveBeenCalled();
      expect(mockRes.end).toHaveBeenCalledWith(`Invalid message: ${invalidMessage}`);
    });

    it('should return 202 if message has a valid schema', async () => {
      const validMessage = JSON.stringify({
        jsonrpc: "2.0",
        method: 'call',
        params: {
          a: 1,
          b: 2,
          c: 3,
        },
        id: 1
      })
      const mockReq = createMockRequest({
        headers: { 'content-type': 'application/json' },
        body: validMessage,
      });
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);
      await transport.start();

      transport.onmessage = jest.fn();
      await transport.handlePostMessage(mockReq, mockRes);
      expect(mockRes.writeHead).toHaveBeenCalledWith(202);
      expect(mockRes.end).toHaveBeenCalledWith('Accepted');
      expect(transport.onmessage).toHaveBeenCalledWith({
        jsonrpc: "2.0",
        method: 'call',
        params: {
          a: 1,
          b: 2,
          c: 3,
        },
        id: 1
      }, {
        authInfo: {
          token: 'test-token',
        },
        requestInfo: {
          headers: {
            'content-type': 'application/json',
          },
        },
      });
    });
  });

  describe('close method', () => {
    it('should call onclose', async () => {
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);
      await transport.start();
      transport.onclose = jest.fn();
      await transport.close();
      expect(transport.onclose).toHaveBeenCalled();
    });
  });

  describe('send method', () => {
    it('should call onsend', async () => {
      const mockRes = createMockResponse();
      const endpoint = '/messages';
      const transport = new SSEServerTransport(endpoint, mockRes);
      await transport.start();
      expect(mockRes.write).toHaveBeenCalledTimes(1);
      expect(mockRes.write).toHaveBeenCalledWith(
        expect.stringContaining('event: endpoint'));
      expect(mockRes.write).toHaveBeenCalledWith(
        expect.stringContaining(`data: /messages?sessionId=${transport.sessionId}`));
    });
  });

  describe('DNS rebinding protection', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    describe('Host header validation', () => {
      it('should accept requests with allowed host headers', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedHosts: ['localhost:3000', 'example.com'],
          enableDnsRebindingProtection: true,
        });
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            host: 'localhost:3000',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(202);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Accepted');
      });

      it('should reject requests with disallowed host headers', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedHosts: ['localhost:3000'],
          enableDnsRebindingProtection: true,
        });
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            host: 'evil.com',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(403);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Invalid Host header: evil.com');
      });

      it('should reject requests without host header when allowedHosts is configured', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedHosts: ['localhost:3000'],
          enableDnsRebindingProtection: true,
        });
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            'content-type': 'application/json',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(403);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Invalid Host header: undefined');
      });
    });

    describe('Origin header validation', () => {
      it('should accept requests with allowed origin headers', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedOrigins: ['http://localhost:3000', 'https://example.com'],
          enableDnsRebindingProtection: true,
        });
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            origin: 'http://localhost:3000',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(202);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Accepted');
      });

      it('should reject requests with disallowed origin headers', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedOrigins: ['http://localhost:3000'],
          enableDnsRebindingProtection: true,
        });
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            origin: 'http://evil.com',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(403);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Invalid Origin header: http://evil.com');
      });
    });

    describe('Content-Type validation', () => {
      it('should accept requests with application/json content-type', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes);
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            'content-type': 'application/json',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(202);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Accepted');
      });

      it('should accept requests with application/json with charset', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes);
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            'content-type': 'application/json; charset=utf-8',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(202);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Accepted');
      });

      it('should reject requests with non-application/json content-type when protection is enabled', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes);
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            'content-type': 'text/plain',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(400);
        expect(mockHandleRes.end).toHaveBeenCalledWith('Error: Unsupported content-type: text/plain');
      });
    });

    describe('enableDnsRebindingProtection option', () => {
      it('should skip all validations when enableDnsRebindingProtection is false', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedHosts: ['localhost:3000'],
          allowedOrigins: ['http://localhost:3000'],
          enableDnsRebindingProtection: false,
        });
        await transport.start();

        const mockReq = createMockRequest({
          headers: {
            host: 'evil.com',
            origin: 'http://evil.com',
            'content-type': 'text/plain',
          }
        });
        const mockHandleRes = createMockResponse();

        await transport.handlePostMessage(mockReq, mockHandleRes, { jsonrpc: '2.0', method: 'test' });

        // Should pass even with invalid headers because protection is disabled
        expect(mockHandleRes.writeHead).toHaveBeenCalledWith(400);
        // The error should be from content-type parsing, not DNS rebinding protection
        expect(mockHandleRes.end).toHaveBeenCalledWith('Error: Unsupported content-type: text/plain');
      });
    });

    describe('Combined validations', () => {
      it('should validate both host and origin when both are configured', async () => {
        const mockRes = createMockResponse();
        const transport = new SSEServerTransport('/messages', mockRes, {
          allowedHosts: ['localhost:3000'],
          allowedOrigins: ['http://localhost:3000'],
          enableDnsRebindingProtection: true,
        });
        await transport.start();

        // Valid host, invalid origin
        const mockReq1 = createMockRequest({
          headers: {
            host: 'localhost:3000',
            origin: 'http://evil.com',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes1 = createMockResponse();

        await transport.handlePostMessage(mockReq1, mockHandleRes1, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes1.writeHead).toHaveBeenCalledWith(403);
        expect(mockHandleRes1.end).toHaveBeenCalledWith('Invalid Origin header: http://evil.com');

        // Invalid host, valid origin
        const mockReq2 = createMockRequest({
          headers: {
            host: 'evil.com',
            origin: 'http://localhost:3000',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes2 = createMockResponse();

        await transport.handlePostMessage(mockReq2, mockHandleRes2, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes2.writeHead).toHaveBeenCalledWith(403);
        expect(mockHandleRes2.end).toHaveBeenCalledWith('Invalid Host header: evil.com');

        // Both valid
        const mockReq3 = createMockRequest({
          headers: {
            host: 'localhost:3000',
            origin: 'http://localhost:3000',
            'content-type': 'application/json',
          }
        });
        const mockHandleRes3 = createMockResponse();

        await transport.handlePostMessage(mockReq3, mockHandleRes3, { jsonrpc: '2.0', method: 'test' });

        expect(mockHandleRes3.writeHead).toHaveBeenCalledWith(202);
        expect(mockHandleRes3.end).toHaveBeenCalledWith('Accepted');
      });
    });
  });
});



================================================
FILE: src/server/sse.ts
================================================
import { randomUUID } from "node:crypto";
import { IncomingMessage, ServerResponse } from "node:http";
import { Transport } from "../shared/transport.js";
import { JSONRPCMessage, JSONRPCMessageSchema, MessageExtraInfo, RequestInfo } from "../types.js";
import getRawBody from "raw-body";
import contentType from "content-type";
import { AuthInfo } from "./auth/types.js";
import { URL } from 'url';

const MAXIMUM_MESSAGE_SIZE = "4mb";

/**
 * Configuration options for SSEServerTransport.
 */
export interface SSEServerTransportOptions {
  /**
   * List of allowed host header values for DNS rebinding protection.
   * If not specified, host validation is disabled.
   */
  allowedHosts?: string[];
  
  /**
   * List of allowed origin header values for DNS rebinding protection.
   * If not specified, origin validation is disabled.
   */
  allowedOrigins?: string[];
  
  /**
   * Enable DNS rebinding protection (requires allowedHosts and/or allowedOrigins to be configured).
   * Default is false for backwards compatibility.
   */
  enableDnsRebindingProtection?: boolean;
}

/**
 * Server transport for SSE: this will send messages over an SSE connection and receive messages from HTTP POST requests.
 *
 * This transport is only available in Node.js environments.
 */
export class SSEServerTransport implements Transport {
  private _sseResponse?: ServerResponse;
  private _sessionId: string;
  private _options: SSEServerTransportOptions;
  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage, extra?: MessageExtraInfo) => void;

  /**
   * Creates a new SSE server transport, which will direct the client to POST messages to the relative or absolute URL identified by `_endpoint`.
   */
  constructor(
    private _endpoint: string,
    private res: ServerResponse,
    options?: SSEServerTransportOptions,
  ) {
    this._sessionId = randomUUID();
    this._options = options || {enableDnsRebindingProtection: false};
  }

  /**
   * Validates request headers for DNS rebinding protection.
   * @returns Error message if validation fails, undefined if validation passes.
   */
  private validateRequestHeaders(req: IncomingMessage): string | undefined {
    // Skip validation if protection is not enabled
    if (!this._options.enableDnsRebindingProtection) {
      return undefined;
    }

    // Validate Host header if allowedHosts is configured
    if (this._options.allowedHosts && this._options.allowedHosts.length > 0) {
      const hostHeader = req.headers.host;
      if (!hostHeader || !this._options.allowedHosts.includes(hostHeader)) {
        return `Invalid Host header: ${hostHeader}`;
      }
    }

    // Validate Origin header if allowedOrigins is configured
    if (this._options.allowedOrigins && this._options.allowedOrigins.length > 0) {
      const originHeader = req.headers.origin;
      if (!originHeader || !this._options.allowedOrigins.includes(originHeader)) {
        return `Invalid Origin header: ${originHeader}`;
      }
    }

    return undefined;
  }

  /**
   * Handles the initial SSE connection request.
   *
   * This should be called when a GET request is made to establish the SSE stream.
   */
  async start(): Promise<void> {
    if (this._sseResponse) {
      throw new Error(
        "SSEServerTransport already started! If using Server class, note that connect() calls start() automatically.",
      );
    }

    this.res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    });

    // Send the endpoint event
    // Use a dummy base URL because this._endpoint is relative.
    // This allows using URL/URLSearchParams for robust parameter handling.
    const dummyBase = 'http://localhost'; // Any valid base works
    const endpointUrl = new URL(this._endpoint, dummyBase);
    endpointUrl.searchParams.set('sessionId', this._sessionId);

    // Reconstruct the relative URL string (pathname + search + hash)
    const relativeUrlWithSession = endpointUrl.pathname + endpointUrl.search + endpointUrl.hash;

    this.res.write(
      `event: endpoint\ndata: ${relativeUrlWithSession}\n\n`,
    );

    this._sseResponse = this.res;
    this.res.on("close", () => {
      this._sseResponse = undefined;
      this.onclose?.();
    });
  }

  /**
   * Handles incoming POST messages.
   *
   * This should be called when a POST request is made to send a message to the server.
   */
  async handlePostMessage(
    req: IncomingMessage & { auth?: AuthInfo },
    res: ServerResponse,
    parsedBody?: unknown,
  ): Promise<void> {
    if (!this._sseResponse) {
      const message = "SSE connection not established";
      res.writeHead(500).end(message);
      throw new Error(message);
    }

    // Validate request headers for DNS rebinding protection
    const validationError = this.validateRequestHeaders(req);
    if (validationError) {
      res.writeHead(403).end(validationError);
      this.onerror?.(new Error(validationError));
      return;
    }

    const authInfo: AuthInfo | undefined = req.auth;
    const requestInfo: RequestInfo = { headers: req.headers };

    let body: string | unknown;
    try {
      const ct = contentType.parse(req.headers["content-type"] ?? "");
      if (ct.type !== "application/json") {
        throw new Error(`Unsupported content-type: ${ct.type}`);
      }

      body = parsedBody ?? await getRawBody(req, {
        limit: MAXIMUM_MESSAGE_SIZE,
        encoding: ct.parameters.charset ?? "utf-8",
      });
    } catch (error) {
      res.writeHead(400).end(String(error));
      this.onerror?.(error as Error);
      return;
    }

    try {
      await this.handleMessage(typeof body === 'string' ? JSON.parse(body) : body, { requestInfo, authInfo });
    } catch {
      res.writeHead(400).end(`Invalid message: ${body}`);
      return;
    }

    res.writeHead(202).end("Accepted");
  }

  /**
   * Handle a client message, regardless of how it arrived. This can be used to inform the server of messages that arrive via a means different than HTTP POST.
   */
  async handleMessage(message: unknown, extra?: MessageExtraInfo): Promise<void> {
    let parsedMessage: JSONRPCMessage;
    try {
      parsedMessage = JSONRPCMessageSchema.parse(message);
    } catch (error) {
      this.onerror?.(error as Error);
      throw error;
    }

    this.onmessage?.(parsedMessage, extra);
  }

  async close(): Promise<void> {
    this._sseResponse?.end();
    this._sseResponse = undefined;
    this.onclose?.();
  }

  async send(message: JSONRPCMessage): Promise<void> {
    if (!this._sseResponse) {
      throw new Error("Not connected");
    }

    this._sseResponse.write(
      `event: message\ndata: ${JSON.stringify(message)}\n\n`,
    );
  }

  /**
   * Returns the session ID for this transport.
   *
   * This can be used to route incoming POST requests.
   */
  get sessionId(): string {
    return this._sessionId;
  }
}



================================================
FILE: src/server/stdio.test.ts
================================================
import { Readable, Writable } from "node:stream";
import { ReadBuffer, serializeMessage } from "../shared/stdio.js";
import { JSONRPCMessage } from "../types.js";
import { StdioServerTransport } from "./stdio.js";

let input: Readable;
let outputBuffer: ReadBuffer;
let output: Writable;

beforeEach(() => {
  input = new Readable({
    // We'll use input.push() instead.
    read: () => {},
  });

  outputBuffer = new ReadBuffer();
  output = new Writable({
    write(chunk, encoding, callback) {
      outputBuffer.append(chunk);
      callback();
    },
  });
});

test("should start then close cleanly", async () => {
  const server = new StdioServerTransport(input, output);
  server.onerror = (error) => {
    throw error;
  };

  let didClose = false;
  server.onclose = () => {
    didClose = true;
  };

  await server.start();
  expect(didClose).toBeFalsy();
  await server.close();
  expect(didClose).toBeTruthy();
});

test("should not read until started", async () => {
  const server = new StdioServerTransport(input, output);
  server.onerror = (error) => {
    throw error;
  };

  let didRead = false;
  const readMessage = new Promise((resolve) => {
    server.onmessage = (message) => {
      didRead = true;
      resolve(message);
    };
  });

  const message: JSONRPCMessage = {
    jsonrpc: "2.0",
    id: 1,
    method: "ping",
  };
  input.push(serializeMessage(message));

  expect(didRead).toBeFalsy();
  await server.start();
  expect(await readMessage).toEqual(message);
});

test("should read multiple messages", async () => {
  const server = new StdioServerTransport(input, output);
  server.onerror = (error) => {
    throw error;
  };

  const messages: JSONRPCMessage[] = [
    {
      jsonrpc: "2.0",
      id: 1,
      method: "ping",
    },
    {
      jsonrpc: "2.0",
      method: "notifications/initialized",
    },
  ];

  const readMessages: JSONRPCMessage[] = [];
  const finished = new Promise<void>((resolve) => {
    server.onmessage = (message) => {
      readMessages.push(message);
      if (JSON.stringify(message) === JSON.stringify(messages[1])) {
        resolve();
      }
    };
  });

  input.push(serializeMessage(messages[0]));
  input.push(serializeMessage(messages[1]));

  await server.start();
  await finished;
  expect(readMessages).toEqual(messages);
});



================================================
FILE: src/server/stdio.ts
================================================
import process from "node:process";
import { Readable, Writable } from "node:stream";
import { ReadBuffer, serializeMessage } from "../shared/stdio.js";
import { JSONRPCMessage } from "../types.js";
import { Transport } from "../shared/transport.js";

/**
 * Server transport for stdio: this communicates with a MCP client by reading from the current process' stdin and writing to stdout.
 *
 * This transport is only available in Node.js environments.
 */
export class StdioServerTransport implements Transport {
  private _readBuffer: ReadBuffer = new ReadBuffer();
  private _started = false;

  constructor(
    private _stdin: Readable = process.stdin,
    private _stdout: Writable = process.stdout,
  ) {}

  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;

  // Arrow functions to bind `this` properly, while maintaining function identity.
  _ondata = (chunk: Buffer) => {
    this._readBuffer.append(chunk);
    this.processReadBuffer();
  };
  _onerror = (error: Error) => {
    this.onerror?.(error);
  };

  /**
   * Starts listening for messages on stdin.
   */
  async start(): Promise<void> {
    if (this._started) {
      throw new Error(
        "StdioServerTransport already started! If using Server class, note that connect() calls start() automatically.",
      );
    }

    this._started = true;
    this._stdin.on("data", this._ondata);
    this._stdin.on("error", this._onerror);
  }

  private processReadBuffer() {
    while (true) {
      try {
        const message = this._readBuffer.readMessage();
        if (message === null) {
          break;
        }

        this.onmessage?.(message);
      } catch (error) {
        this.onerror?.(error as Error);
      }
    }
  }

  async close(): Promise<void> {
    // Remove our event listeners first
    this._stdin.off("data", this._ondata);
    this._stdin.off("error", this._onerror);

    // Check if we were the only data listener
    const remainingDataListeners = this._stdin.listenerCount('data');
    if (remainingDataListeners === 0) {
      // Only pause stdin if we were the only listener
      // This prevents interfering with other parts of the application that might be using stdin
      this._stdin.pause();
    }
    
    // Clear the buffer and notify closure
    this._readBuffer.clear();
    this.onclose?.();
  }

  send(message: JSONRPCMessage): Promise<void> {
    return new Promise((resolve) => {
      const json = serializeMessage(message);
      if (this._stdout.write(json)) {
        resolve();
      } else {
        this._stdout.once("drain", resolve);
      }
    });
  }
}



================================================
FILE: src/server/streamableHttp.ts
================================================
import { IncomingMessage, ServerResponse } from "node:http";
import { Transport } from "../shared/transport.js";
import { MessageExtraInfo, RequestInfo, isInitializeRequest, isJSONRPCError, isJSONRPCRequest, isJSONRPCResponse, JSONRPCMessage, JSONRPCMessageSchema, RequestId, SUPPORTED_PROTOCOL_VERSIONS, DEFAULT_NEGOTIATED_PROTOCOL_VERSION } from "../types.js";
import getRawBody from "raw-body";
import contentType from "content-type";
import { randomUUID } from "node:crypto";
import { AuthInfo } from "./auth/types.js";

const MAXIMUM_MESSAGE_SIZE = "4mb";

export type StreamId = string;
export type EventId = string;

/**
 * Interface for resumability support via event storage
 */
export interface EventStore {
  /**
   * Stores an event for later retrieval
   * @param streamId ID of the stream the event belongs to
   * @param message The JSON-RPC message to store
   * @returns The generated event ID for the stored event
   */
  storeEvent(streamId: StreamId, message: JSONRPCMessage): Promise<EventId>;

  replayEventsAfter(lastEventId: EventId, { send }: {
    send: (eventId: EventId, message: JSONRPCMessage) => Promise<void>
  }): Promise<StreamId>;
}

/**
 * Configuration options for StreamableHTTPServerTransport
 */
export interface StreamableHTTPServerTransportOptions {
  /**
   * Function that generates a session ID for the transport.
   * The session ID SHOULD be globally unique and cryptographically secure (e.g., a securely generated UUID, a JWT, or a cryptographic hash)
   * 
   * Return undefined to disable session management.
   */
  sessionIdGenerator: (() => string) | undefined;

  /**
   * A callback for session initialization events
   * This is called when the server initializes a new session.
   * Useful in cases when you need to register multiple mcp sessions
   * and need to keep track of them.
   * @param sessionId The generated session ID
   */
  onsessioninitialized?: (sessionId: string) => void | Promise<void>;

  /**
   * A callback for session close events
   * This is called when the server closes a session due to a DELETE request.
   * Useful in cases when you need to clean up resources associated with the session.
   * Note that this is different from the transport closing, if you are handling 
   * HTTP requests from multiple nodes you might want to close each 
   * StreamableHTTPServerTransport after a request is completed while still keeping the 
   * session open/running.
   * @param sessionId The session ID that was closed
  */
  onsessionclosed?: (sessionId: string) => void | Promise<void>;

  /**
   * If true, the server will return JSON responses instead of starting an SSE stream.
   * This can be useful for simple request/response scenarios without streaming.
   * Default is false (SSE streams are preferred).
   */
  enableJsonResponse?: boolean;

  /**
   * Event store for resumability support
   * If provided, resumability will be enabled, allowing clients to reconnect and resume messages
   */
  eventStore?: EventStore;

  /**
   * List of allowed host header values for DNS rebinding protection.
   * If not specified, host validation is disabled.
   */
  allowedHosts?: string[];
  
  /**
   * List of allowed origin header values for DNS rebinding protection.
   * If not specified, origin validation is disabled.
   */
  allowedOrigins?: string[];
  
  /**
   * Enable DNS rebinding protection (requires allowedHosts and/or allowedOrigins to be configured).
   * Default is false for backwards compatibility.
   */
  enableDnsRebindingProtection?: boolean;
}

/**
 * Server transport for Streamable HTTP: this implements the MCP Streamable HTTP transport specification.
 * It supports both SSE streaming and direct HTTP responses.
 * 
 * Usage example:
 * 
 * ```typescript
 * // Stateful mode - server sets the session ID
 * const statefulTransport = new StreamableHTTPServerTransport({
 *   sessionIdGenerator: () => randomUUID(),
 * });
 * 
 * // Stateless mode - explicitly set session ID to undefined
 * const statelessTransport = new StreamableHTTPServerTransport({
 *   sessionIdGenerator: undefined,
 * });
 * 
 * // Using with pre-parsed request body
 * app.post('/mcp', (req, res) => {
 *   transport.handleRequest(req, res, req.body);
 * });
 * ```
 * 
 * In stateful mode:
 * - Session ID is generated and included in response headers
 * - Session ID is always included in initialization responses
 * - Requests with invalid session IDs are rejected with 404 Not Found
 * - Non-initialization requests without a session ID are rejected with 400 Bad Request
 * - State is maintained in-memory (connections, message history)
 * 
 * In stateless mode:
 * - No Session ID is included in any responses
 * - No session validation is performed
 */
export class StreamableHTTPServerTransport implements Transport {
  // when sessionId is not set (undefined), it means the transport is in stateless mode
  private sessionIdGenerator: (() => string) | undefined;
  private _started: boolean = false;
  private _streamMapping: Map<string, ServerResponse> = new Map();
  private _requestToStreamMapping: Map<RequestId, string> = new Map();
  private _requestResponseMap: Map<RequestId, JSONRPCMessage> = new Map();
  private _initialized: boolean = false;
  private _enableJsonResponse: boolean = false;
  private _standaloneSseStreamId: string = '_GET_stream';
  private _eventStore?: EventStore;
  private _onsessioninitialized?: (sessionId: string) => void | Promise<void>;
  private _onsessionclosed?: (sessionId: string) => void | Promise<void>;
  private _allowedHosts?: string[];
  private _allowedOrigins?: string[];
  private _enableDnsRebindingProtection: boolean;

  sessionId?: string;
  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage, extra?: MessageExtraInfo) => void;

  constructor(options: StreamableHTTPServerTransportOptions) {
    this.sessionIdGenerator = options.sessionIdGenerator;
    this._enableJsonResponse = options.enableJsonResponse ?? false;
    this._eventStore = options.eventStore;
    this._onsessioninitialized = options.onsessioninitialized;
    this._onsessionclosed = options.onsessionclosed;
    this._allowedHosts = options.allowedHosts;
    this._allowedOrigins = options.allowedOrigins;
    this._enableDnsRebindingProtection = options.enableDnsRebindingProtection ?? false;
  }

  /**
   * Starts the transport. This is required by the Transport interface but is a no-op
   * for the Streamable HTTP transport as connections are managed per-request.
   */
  async start(): Promise<void> {
    if (this._started) {
      throw new Error("Transport already started");
    }
    this._started = true;
  }

  /**
   * Validates request headers for DNS rebinding protection.
   * @returns Error message if validation fails, undefined if validation passes.
   */
  private validateRequestHeaders(req: IncomingMessage): string | undefined {
    // Skip validation if protection is not enabled
    if (!this._enableDnsRebindingProtection) {
      return undefined;
    }

    // Validate Host header if allowedHosts is configured
    if (this._allowedHosts && this._allowedHosts.length > 0) {
      const hostHeader = req.headers.host;
      if (!hostHeader || !this._allowedHosts.includes(hostHeader)) {
        return `Invalid Host header: ${hostHeader}`;
      }
    }

    // Validate Origin header if allowedOrigins is configured
    if (this._allowedOrigins && this._allowedOrigins.length > 0) {
      const originHeader = req.headers.origin;
      if (!originHeader || !this._allowedOrigins.includes(originHeader)) {
        return `Invalid Origin header: ${originHeader}`;
      }
    }

    return undefined;
  }

  /**
   * Handles an incoming HTTP request, whether GET or POST
   */
  async handleRequest(req: IncomingMessage & { auth?: AuthInfo }, res: ServerResponse, parsedBody?: unknown): Promise<void> {
    // Validate request headers for DNS rebinding protection
    const validationError = this.validateRequestHeaders(req);
    if (validationError) {
      res.writeHead(403).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: validationError
        },
        id: null
      }));
      this.onerror?.(new Error(validationError));
      return;
    }

    if (req.method === "POST") {
      await this.handlePostRequest(req, res, parsedBody);
    } else if (req.method === "GET") {
      await this.handleGetRequest(req, res);
    } else if (req.method === "DELETE") {
      await this.handleDeleteRequest(req, res);
    } else {
      await this.handleUnsupportedRequest(res);
    }
  }

  /**
   * Handles GET requests for SSE stream
   */
  private async handleGetRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
    // The client MUST include an Accept header, listing text/event-stream as a supported content type.
    const acceptHeader = req.headers.accept;
    if (!acceptHeader?.includes("text/event-stream")) {
      res.writeHead(406).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Not Acceptable: Client must accept text/event-stream"
        },
        id: null
      }));
      return;
    }

    // If an Mcp-Session-Id is returned by the server during initialization,
    // clients using the Streamable HTTP transport MUST include it
    // in the Mcp-Session-Id header on all of their subsequent HTTP requests.
    if (!this.validateSession(req, res)) {
      return;
    }
    if (!this.validateProtocolVersion(req, res)) {
      return;
    }
    // Handle resumability: check for Last-Event-ID header
    if (this._eventStore) {
      const lastEventId = req.headers['last-event-id'] as string | undefined;
      if (lastEventId) {
        await this.replayEvents(lastEventId, res);
        return;
      }
    }

    // The server MUST either return Content-Type: text/event-stream in response to this HTTP GET,
    // or else return HTTP 405 Method Not Allowed
    const headers: Record<string, string> = {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    };

    // After initialization, always include the session ID if we have one
    if (this.sessionId !== undefined) {
      headers["mcp-session-id"] = this.sessionId;
    }

    // Check if there's already an active standalone SSE stream for this session
    if (this._streamMapping.get(this._standaloneSseStreamId) !== undefined) {
      // Only one GET SSE stream is allowed per session
      res.writeHead(409).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Conflict: Only one SSE stream is allowed per session"
        },
        id: null
      }));
      return;
    }

    // We need to send headers immediately as messages will arrive much later,
    // otherwise the client will just wait for the first message
    res.writeHead(200, headers).flushHeaders();

    // Assign the response to the standalone SSE stream
    this._streamMapping.set(this._standaloneSseStreamId, res);
    // Set up close handler for client disconnects
    res.on("close", () => {
      this._streamMapping.delete(this._standaloneSseStreamId);
    });
  }

  /**
   * Replays events that would have been sent after the specified event ID
   * Only used when resumability is enabled
   */
  private async replayEvents(lastEventId: string, res: ServerResponse): Promise<void> {
    if (!this._eventStore) {
      return;
    }
    try {
      const headers: Record<string, string> = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      };

      if (this.sessionId !== undefined) {
        headers["mcp-session-id"] = this.sessionId;
      }
      res.writeHead(200, headers).flushHeaders();

      const streamId = await this._eventStore?.replayEventsAfter(lastEventId, {
        send: async (eventId: string, message: JSONRPCMessage) => {
          if (!this.writeSSEEvent(res, message, eventId)) {
            this.onerror?.(new Error("Failed replay events"));
            res.end();
          }
        }
      });
      this._streamMapping.set(streamId, res);
    } catch (error) {
      this.onerror?.(error as Error);
    }
  }

  /**
   * Writes an event to the SSE stream with proper formatting
   */
  private writeSSEEvent(res: ServerResponse, message: JSONRPCMessage, eventId?: string): boolean {
    let eventData = `event: message\n`;
    // Include event ID if provided - this is important for resumability
    if (eventId) {
      eventData += `id: ${eventId}\n`;
    }
    eventData += `data: ${JSON.stringify(message)}\n\n`;

    return res.write(eventData);
  }

  /**
   * Handles unsupported requests (PUT, PATCH, etc.)
   */
  private async handleUnsupportedRequest(res: ServerResponse): Promise<void> {
    res.writeHead(405, {
      "Allow": "GET, POST, DELETE"
    }).end(JSON.stringify({
      jsonrpc: "2.0",
      error: {
        code: -32000,
        message: "Method not allowed."
      },
      id: null
    }));
  }

  /**
   * Handles POST requests containing JSON-RPC messages
   */
  private async handlePostRequest(req: IncomingMessage & { auth?: AuthInfo }, res: ServerResponse, parsedBody?: unknown): Promise<void> {
    try {
      // Validate the Accept header
      const acceptHeader = req.headers.accept;
      // The client MUST include an Accept header, listing both application/json and text/event-stream as supported content types.
      if (!acceptHeader?.includes("application/json") || !acceptHeader.includes("text/event-stream")) {
        res.writeHead(406).end(JSON.stringify({
          jsonrpc: "2.0",
          error: {
            code: -32000,
            message: "Not Acceptable: Client must accept both application/json and text/event-stream"
          },
          id: null
        }));
        return;
      }

      const ct = req.headers["content-type"];
      if (!ct || !ct.includes("application/json")) {
        res.writeHead(415).end(JSON.stringify({
          jsonrpc: "2.0",
          error: {
            code: -32000,
            message: "Unsupported Media Type: Content-Type must be application/json"
          },
          id: null
        }));
        return;
      }

      const authInfo: AuthInfo | undefined = req.auth;
      const requestInfo: RequestInfo = { headers: req.headers };

      let rawMessage;
      if (parsedBody !== undefined) {
        rawMessage = parsedBody;
      } else {
        const parsedCt = contentType.parse(ct);
        const body = await getRawBody(req, {
          limit: MAXIMUM_MESSAGE_SIZE,
          encoding: parsedCt.parameters.charset ?? "utf-8",
        });
        rawMessage = JSON.parse(body.toString());
      }

      let messages: JSONRPCMessage[];

      // handle batch and single messages
      if (Array.isArray(rawMessage)) {
        messages = rawMessage.map(msg => JSONRPCMessageSchema.parse(msg));
      } else {
        messages = [JSONRPCMessageSchema.parse(rawMessage)];
      }

      // Check if this is an initialization request
      // https://spec.modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle/
      const isInitializationRequest = messages.some(isInitializeRequest);
      if (isInitializationRequest) {
        // If it's a server with session management and the session ID is already set we should reject the request
        // to avoid re-initialization.
        if (this._initialized && this.sessionId !== undefined) {
          res.writeHead(400).end(JSON.stringify({
            jsonrpc: "2.0",
            error: {
              code: -32600,
              message: "Invalid Request: Server already initialized"
            },
            id: null
          }));
          return;
        }
        if (messages.length > 1) {
          res.writeHead(400).end(JSON.stringify({
            jsonrpc: "2.0",
            error: {
              code: -32600,
              message: "Invalid Request: Only one initialization request is allowed"
            },
            id: null
          }));
          return;
        }
        this.sessionId = this.sessionIdGenerator?.();
        this._initialized = true;

        // If we have a session ID and an onsessioninitialized handler, call it immediately
        // This is needed in cases where the server needs to keep track of multiple sessions
        if (this.sessionId && this._onsessioninitialized) {
          await Promise.resolve(this._onsessioninitialized(this.sessionId));
        }

      }
      if (!isInitializationRequest) {
        // If an Mcp-Session-Id is returned by the server during initialization,
        // clients using the Streamable HTTP transport MUST include it 
        // in the Mcp-Session-Id header on all of their subsequent HTTP requests.
        if (!this.validateSession(req, res)) {
          return;
        }
        // Mcp-Protocol-Version header is required for all requests after initialization.
        if (!this.validateProtocolVersion(req, res)) {
          return;
        }
      }


      // check if it contains requests
      const hasRequests = messages.some(isJSONRPCRequest);

      if (!hasRequests) {
        // if it only contains notifications or responses, return 202
        res.writeHead(202).end();

        // handle each message
        for (const message of messages) {
          this.onmessage?.(message, { authInfo, requestInfo });
        }
      } else if (hasRequests) {
        // The default behavior is to use SSE streaming
        // but in some cases server will return JSON responses
        const streamId = randomUUID();
        if (!this._enableJsonResponse) {
          const headers: Record<string, string> = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            Connection: "keep-alive",
          };

          // After initialization, always include the session ID if we have one
          if (this.sessionId !== undefined) {
            headers["mcp-session-id"] = this.sessionId;
          }

          res.writeHead(200, headers);
        }
        // Store the response for this request to send messages back through this connection
        // We need to track by request ID to maintain the connection
        for (const message of messages) {
          if (isJSONRPCRequest(message)) {
            this._streamMapping.set(streamId, res);
            this._requestToStreamMapping.set(message.id, streamId);
          }
        }
        // Set up close handler for client disconnects
        res.on("close", () => {
          this._streamMapping.delete(streamId);
        });

        // handle each message
        for (const message of messages) {
          this.onmessage?.(message, { authInfo, requestInfo });
        }
        // The server SHOULD NOT close the SSE stream before sending all JSON-RPC responses
        // This will be handled by the send() method when responses are ready
      }
    } catch (error) {
      // return JSON-RPC formatted error
      res.writeHead(400).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32700,
          message: "Parse error",
          data: String(error)
        },
        id: null
      }));
      this.onerror?.(error as Error);
    }
  }

  /**
   * Handles DELETE requests to terminate sessions
   */
  private async handleDeleteRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
    if (!this.validateSession(req, res)) {
      return;
    }
    if (!this.validateProtocolVersion(req, res)) {
      return;
    }
    await Promise.resolve(this._onsessionclosed?.(this.sessionId!));
    await this.close();
    res.writeHead(200).end();
  }

  /**
   * Validates session ID for non-initialization requests
   * Returns true if the session is valid, false otherwise
   */
  private validateSession(req: IncomingMessage, res: ServerResponse): boolean {
    if (this.sessionIdGenerator === undefined) {
      // If the sessionIdGenerator ID is not set, the session management is disabled
      // and we don't need to validate the session ID
      return true;
    }
    if (!this._initialized) {
      // If the server has not been initialized yet, reject all requests
      res.writeHead(400).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Bad Request: Server not initialized"
        },
        id: null
      }));
      return false;
    }

    const sessionId = req.headers["mcp-session-id"];

    if (!sessionId) {
      // Non-initialization requests without a session ID should return 400 Bad Request
      res.writeHead(400).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Bad Request: Mcp-Session-Id header is required"
        },
        id: null
      }));
      return false;
    } else if (Array.isArray(sessionId)) {
      res.writeHead(400).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Bad Request: Mcp-Session-Id header must be a single value"
        },
        id: null
      }));
      return false;
    }
    else if (sessionId !== this.sessionId) {
      // Reject requests with invalid session ID with 404 Not Found
      res.writeHead(404).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32001,
          message: "Session not found"
        },
        id: null
      }));
      return false;
    }

    return true;
  }

  private validateProtocolVersion(req: IncomingMessage, res: ServerResponse): boolean {
    let protocolVersion = req.headers["mcp-protocol-version"] ?? DEFAULT_NEGOTIATED_PROTOCOL_VERSION;
    if (Array.isArray(protocolVersion)) {
      protocolVersion = protocolVersion[protocolVersion.length - 1];
    }

    if (!SUPPORTED_PROTOCOL_VERSIONS.includes(protocolVersion)) {
      res.writeHead(400).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: `Bad Request: Unsupported protocol version (supported versions: ${SUPPORTED_PROTOCOL_VERSIONS.join(", ")})`
        },
        id: null
      }));
      return false;
    }
    return true;
  }

  async close(): Promise<void> {
    // Close all SSE connections
    this._streamMapping.forEach((response) => {
      response.end();
    });
    this._streamMapping.clear();

    // Clear any pending responses
    this._requestResponseMap.clear();
    this.onclose?.();
  }

  async send(message: JSONRPCMessage, options?: { relatedRequestId?: RequestId }): Promise<void> {
    let requestId = options?.relatedRequestId;
    if (isJSONRPCResponse(message) || isJSONRPCError(message)) {
      // If the message is a response, use the request ID from the message
      requestId = message.id;
    }

    // Check if this message should be sent on the standalone SSE stream (no request ID)
    // Ignore notifications from tools (which have relatedRequestId set)
    // Those will be sent via dedicated response SSE streams
    if (requestId === undefined) {
      // For standalone SSE streams, we can only send requests and notifications
      if (isJSONRPCResponse(message) || isJSONRPCError(message)) {
        throw new Error("Cannot send a response on a standalone SSE stream unless resuming a previous client request");
      }
      const standaloneSse = this._streamMapping.get(this._standaloneSseStreamId)
      if (standaloneSse === undefined) {
        // The spec says the server MAY send messages on the stream, so it's ok to discard if no stream
        return;
      }

      // Generate and store event ID if event store is provided
      let eventId: string | undefined;
      if (this._eventStore) {
        // Stores the event and gets the generated event ID
        eventId = await this._eventStore.storeEvent(this._standaloneSseStreamId, message);
      }

      // Send the message to the standalone SSE stream
      this.writeSSEEvent(standaloneSse, message, eventId);
      return;
    }

    // Get the response for this request
    const streamId = this._requestToStreamMapping.get(requestId);
    const response = this._streamMapping.get(streamId!);
    if (!streamId) {
      throw new Error(`No connection established for request ID: ${String(requestId)}`);
    }

    if (!this._enableJsonResponse) {
      // For SSE responses, generate event ID if event store is provided
      let eventId: string | undefined;

      if (this._eventStore) {
        eventId = await this._eventStore.storeEvent(streamId, message);
      }
      if (response) {
        // Write the event to the response stream
        this.writeSSEEvent(response, message, eventId);
      }
    }

    if (isJSONRPCResponse(message) || isJSONRPCError(message)) {
      this._requestResponseMap.set(requestId, message);
      const relatedIds = Array.from(this._requestToStreamMapping.entries())
        .filter(([_, streamId]) => this._streamMapping.get(streamId) === response)
        .map(([id]) => id);

      // Check if we have responses for all requests using this connection
      const allResponsesReady = relatedIds.every(id => this._requestResponseMap.has(id));

      if (allResponsesReady) {
        if (!response) {
          throw new Error(`No connection established for request ID: ${String(requestId)}`);
        }
        if (this._enableJsonResponse) {
          // All responses ready, send as JSON
          const headers: Record<string, string> = {
            'Content-Type': 'application/json',
          };
          if (this.sessionId !== undefined) {
            headers['mcp-session-id'] = this.sessionId;
          }

          const responses = relatedIds
            .map(id => this._requestResponseMap.get(id)!);

          response.writeHead(200, headers);
          if (responses.length === 1) {
            response.end(JSON.stringify(responses[0]));
          } else {
            response.end(JSON.stringify(responses));
          }
        } else {
          // End the SSE stream
          response.end();
        }
        // Clean up
        for (const id of relatedIds) {
          this._requestResponseMap.delete(id);
          this._requestToStreamMapping.delete(id);
        }
      }
    }
  }
}




================================================
FILE: src/server/title.test.ts
================================================
import { Server } from "./index.js";
import { Client } from "../client/index.js";
import { InMemoryTransport } from "../inMemory.js";
import { z } from "zod";
import { McpServer, ResourceTemplate } from "./mcp.js";

describe("Title field backwards compatibility", () => {
  it("should work with tools that have title", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new McpServer(
      { name: "test-server", version: "1.0.0" },
      { capabilities: {} }
    );

    // Register tool with title
    server.registerTool(
      "test-tool",
      {
        title: "Test Tool Display Name",
        description: "A test tool",
        inputSchema: {
          value: z.string()
        }
      },
      async () => ({ content: [{ type: "text", text: "result" }] })
    );

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.server.connect(serverTransport);
    await client.connect(clientTransport);

    const tools = await client.listTools();
    expect(tools.tools).toHaveLength(1);
    expect(tools.tools[0].name).toBe("test-tool");
    expect(tools.tools[0].title).toBe("Test Tool Display Name");
    expect(tools.tools[0].description).toBe("A test tool");
  });

  it("should work with tools without title", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new McpServer(
      { name: "test-server", version: "1.0.0" },
      { capabilities: {} }
    );

    // Register tool without title
    server.tool(
      "test-tool",
      "A test tool",
      { value: z.string() },
      async () => ({ content: [{ type: "text", text: "result" }] })
    );

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.server.connect(serverTransport);
    await client.connect(clientTransport);

    const tools = await client.listTools();
    expect(tools.tools).toHaveLength(1);
    expect(tools.tools[0].name).toBe("test-tool");
    expect(tools.tools[0].title).toBeUndefined();
    expect(tools.tools[0].description).toBe("A test tool");
  });

  it("should work with prompts that have title using update", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new McpServer(
      { name: "test-server", version: "1.0.0" },
      { capabilities: {} }
    );

    // Register prompt with title by updating after creation
    const prompt = server.prompt(
      "test-prompt",
      "A test prompt",
      async () => ({ messages: [{ role: "user", content: { type: "text", text: "test" } }] })
    );
    prompt.update({ title: "Test Prompt Display Name" });

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.server.connect(serverTransport);
    await client.connect(clientTransport);

    const prompts = await client.listPrompts();
    expect(prompts.prompts).toHaveLength(1);
    expect(prompts.prompts[0].name).toBe("test-prompt");
    expect(prompts.prompts[0].title).toBe("Test Prompt Display Name");
    expect(prompts.prompts[0].description).toBe("A test prompt");
  });

  it("should work with prompts using registerPrompt", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new McpServer(
      { name: "test-server", version: "1.0.0" },
      { capabilities: {} }
    );

    // Register prompt with title using registerPrompt
    server.registerPrompt(
      "test-prompt",
      {
        title: "Test Prompt Display Name",
        description: "A test prompt",
        argsSchema: { input: z.string() }
      },
      async ({ input }) => ({
        messages: [{
          role: "user",
          content: { type: "text", text: `test: ${input}` }
        }]
      })
    );

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.server.connect(serverTransport);
    await client.connect(clientTransport);

    const prompts = await client.listPrompts();
    expect(prompts.prompts).toHaveLength(1);
    expect(prompts.prompts[0].name).toBe("test-prompt");
    expect(prompts.prompts[0].title).toBe("Test Prompt Display Name");
    expect(prompts.prompts[0].description).toBe("A test prompt");
    expect(prompts.prompts[0].arguments).toHaveLength(1);
  });

  it("should work with resources using registerResource", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new McpServer(
      { name: "test-server", version: "1.0.0" },
      { capabilities: {} }
    );

    // Register resource with title using registerResource
    server.registerResource(
      "test-resource",
      "https://example.com/test",
      {
        title: "Test Resource Display Name",
        description: "A test resource",
        mimeType: "text/plain"
      },
      async () => ({
        contents: [{
          uri: "https://example.com/test",
          text: "test content"
        }]
      })
    );

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.server.connect(serverTransport);
    await client.connect(clientTransport);

    const resources = await client.listResources();
    expect(resources.resources).toHaveLength(1);
    expect(resources.resources[0].name).toBe("test-resource");
    expect(resources.resources[0].title).toBe("Test Resource Display Name");
    expect(resources.resources[0].description).toBe("A test resource");
    expect(resources.resources[0].mimeType).toBe("text/plain");
  });

  it("should work with dynamic resources using registerResource", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new McpServer(
      { name: "test-server", version: "1.0.0" },
      { capabilities: {} }
    );

    // Register dynamic resource with title using registerResource
    server.registerResource(
      "user-profile",
      new ResourceTemplate("users://{userId}/profile", { list: undefined }),
      {
        title: "User Profile",
        description: "User profile information"
      },
      async (uri, { userId }, _extra) => ({
        contents: [{
          uri: uri.href,
          text: `Profile data for user ${userId}`
        }]
      })
    );

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.server.connect(serverTransport);
    await client.connect(clientTransport);

    const resourceTemplates = await client.listResourceTemplates();
    expect(resourceTemplates.resourceTemplates).toHaveLength(1);
    expect(resourceTemplates.resourceTemplates[0].name).toBe("user-profile");
    expect(resourceTemplates.resourceTemplates[0].title).toBe("User Profile");
    expect(resourceTemplates.resourceTemplates[0].description).toBe("User profile information");
    expect(resourceTemplates.resourceTemplates[0].uriTemplate).toBe("users://{userId}/profile");

    // Test reading the resource
    const readResult = await client.readResource({ uri: "users://123/profile" });
    expect(readResult.contents).toHaveLength(1);
    expect(readResult.contents[0].text).toBe("Profile data for user 123");
  });

  it("should support serverInfo with title", async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

    const server = new Server(
      {
        name: "test-server",
        version: "1.0.0",
        title: "Test Server Display Name"
      },
      { capabilities: {} }
    );

    const client = new Client({ name: "test-client", version: "1.0.0" });

    await server.connect(serverTransport);
    await client.connect(clientTransport);

    const serverInfo = client.getServerVersion();
    expect(serverInfo?.name).toBe("test-server");
    expect(serverInfo?.version).toBe("1.0.0");
    expect(serverInfo?.title).toBe("Test Server Display Name");
  });
});


================================================
FILE: src/server/auth/clients.ts
================================================
import { OAuthClientInformationFull } from "../../shared/auth.js";

/**
 * Stores information about registered OAuth clients for this server.
 */
export interface OAuthRegisteredClientsStore {
  /**
   * Returns information about a registered client, based on its ID.
   */
  getClient(clientId: string): OAuthClientInformationFull | undefined | Promise<OAuthClientInformationFull | undefined>;

  /**
   * Registers a new client with the server. The client ID and secret will be automatically generated by the library. A modified version of the client information can be returned to reflect specific values enforced by the server.
   * 
   * NOTE: Implementations should NOT delete expired client secrets in-place. Auth middleware provided by this library will automatically check the `client_secret_expires_at` field and reject requests with expired secrets. Any custom logic for authenticating clients should check the `client_secret_expires_at` field as well.
   * 
   * If unimplemented, dynamic client registration is unsupported.
   */
  registerClient?(client: Omit<OAuthClientInformationFull, "client_id" | "client_id_issued_at">): OAuthClientInformationFull | Promise<OAuthClientInformationFull>;
}


================================================
FILE: src/server/auth/errors.ts
================================================
import { OAuthErrorResponse } from "../../shared/auth.js";

/**
 * Base class for all OAuth errors
 */
export class OAuthError extends Error {
  static errorCode: string;

  constructor(
    message: string,
    public readonly errorUri?: string
  ) {
    super(message);
    this.name = this.constructor.name;
  }

  /**
   * Converts the error to a standard OAuth error response object
   */
  toResponseObject(): OAuthErrorResponse {
    const response: OAuthErrorResponse = {
      error: this.errorCode,
      error_description: this.message
    };

    if (this.errorUri) {
      response.error_uri = this.errorUri;
    }

    return response;
  }

  get errorCode(): string {
    return (this.constructor as typeof OAuthError).errorCode
  }
}

/**
 * Invalid request error - The request is missing a required parameter,
 * includes an invalid parameter value, includes a parameter more than once,
 * or is otherwise malformed.
 */
export class InvalidRequestError extends OAuthError {
  static errorCode = "invalid_request";
}

/**
 * Invalid client error - Client authentication failed (e.g., unknown client, no client
 * authentication included, or unsupported authentication method).
 */
export class InvalidClientError extends OAuthError {
  static errorCode = "invalid_client";
}

/**
 * Invalid grant error - The provided authorization grant or refresh token is
 * invalid, expired, revoked, does not match the redirection URI used in the
 * authorization request, or was issued to another client.
 */
export class InvalidGrantError extends OAuthError {
  static errorCode = "invalid_grant";
}

/**
 * Unauthorized client error - The authenticated client is not authorized to use
 * this authorization grant type.
 */
export class UnauthorizedClientError extends OAuthError {
  static errorCode = "unauthorized_client";
}

/**
 * Unsupported grant type error - The authorization grant type is not supported
 * by the authorization server.
 */
export class UnsupportedGrantTypeError extends OAuthError {
  static errorCode = "unsupported_grant_type";
}

/**
 * Invalid scope error - The requested scope is invalid, unknown, malformed, or
 * exceeds the scope granted by the resource owner.
 */
export class InvalidScopeError extends OAuthError {
  static errorCode = "invalid_scope";
}

/**
 * Access denied error - The resource owner or authorization server denied the request.
 */
export class AccessDeniedError extends OAuthError {
  static errorCode = "access_denied";
}

/**
 * Server error - The authorization server encountered an unexpected condition
 * that prevented it from fulfilling the request.
 */
export class ServerError extends OAuthError {
  static errorCode = "server_error";
}

/**
 * Temporarily unavailable error - The authorization server is currently unable to
 * handle the request due to a temporary overloading or maintenance of the server.
 */
export class TemporarilyUnavailableError extends OAuthError {
  static errorCode = "temporarily_unavailable";
}

/**
 * Unsupported response type error - The authorization server does not support
 * obtaining an authorization code using this method.
 */
export class UnsupportedResponseTypeError extends OAuthError {
  static errorCode = "unsupported_response_type";
}

/**
 * Unsupported token type error - The authorization server does not support
 * the requested token type.
 */
export class UnsupportedTokenTypeError extends OAuthError {
  static errorCode = "unsupported_token_type";
}

/**
 * Invalid token error - The access token provided is expired, revoked, malformed,
 * or invalid for other reasons.
 */
export class InvalidTokenError extends OAuthError {
  static errorCode = "invalid_token";
}

/**
 * Method not allowed error - The HTTP method used is not allowed for this endpoint.
 * (Custom, non-standard error)
 */
export class MethodNotAllowedError extends OAuthError {
  static errorCode = "method_not_allowed";
}

/**
 * Too many requests error - Rate limit exceeded.
 * (Custom, non-standard error based on RFC 6585)
 */
export class TooManyRequestsError extends OAuthError {
  static errorCode = "too_many_requests";
}

/**
 * Invalid client metadata error - The client metadata is invalid.
 * (Custom error for dynamic client registration - RFC 7591)
 */
export class InvalidClientMetadataError extends OAuthError {
  static errorCode = "invalid_client_metadata";
}

/**
 * Insufficient scope error - The request requires higher privileges than provided by the access token.
 */
export class InsufficientScopeError extends OAuthError {
  static errorCode = "insufficient_scope";
}

/**
 * A utility class for defining one-off error codes
 */
export class CustomOAuthError extends OAuthError {
  constructor(private readonly customErrorCode: string, message: string, errorUri?: string) {
    super(message, errorUri);
  }

  get errorCode(): string {
    return this.customErrorCode;
  }
}

/**
 * A full list of all OAuthErrors, enabling parsing from error responses
 */
export const OAUTH_ERRORS = {
  [InvalidRequestError.errorCode]: InvalidRequestError,
  [InvalidClientError.errorCode]: InvalidClientError,
  [InvalidGrantError.errorCode]: InvalidGrantError,
  [UnauthorizedClientError.errorCode]: UnauthorizedClientError,
  [UnsupportedGrantTypeError.errorCode]: UnsupportedGrantTypeError,
  [InvalidScopeError.errorCode]: InvalidScopeError,
  [AccessDeniedError.errorCode]: AccessDeniedError,
  [ServerError.errorCode]: ServerError,
  [TemporarilyUnavailableError.errorCode]: TemporarilyUnavailableError,
  [UnsupportedResponseTypeError.errorCode]: UnsupportedResponseTypeError,
  [UnsupportedTokenTypeError.errorCode]: UnsupportedTokenTypeError,
  [InvalidTokenError.errorCode]: InvalidTokenError,
  [MethodNotAllowedError.errorCode]: MethodNotAllowedError,
  [TooManyRequestsError.errorCode]: TooManyRequestsError,
  [InvalidClientMetadataError.errorCode]: InvalidClientMetadataError,
  [InsufficientScopeError.errorCode]: InsufficientScopeError,
} as const;



================================================
FILE: src/server/auth/provider.ts
================================================
import { Response } from "express";
import { OAuthRegisteredClientsStore } from "./clients.js";
import { OAuthClientInformationFull, OAuthTokenRevocationRequest, OAuthTokens } from "../../shared/auth.js";
import { AuthInfo } from "./types.js";

export type AuthorizationParams = {
  state?: string;
  scopes?: string[];
  codeChallenge: string;
  redirectUri: string;
  resource?: URL;
};

/**
 * Implements an end-to-end OAuth server.
 */
export interface OAuthServerProvider {
  /**
   * A store used to read information about registered OAuth clients.
   */
  get clientsStore(): OAuthRegisteredClientsStore;

  /**
   * Begins the authorization flow, which can either be implemented by this server itself or via redirection to a separate authorization server.
   *
   * This server must eventually issue a redirect with an authorization response or an error response to the given redirect URI. Per OAuth 2.1:
   * - In the successful case, the redirect MUST include the `code` and `state` (if present) query parameters.
   * - In the error case, the redirect MUST include the `error` query parameter, and MAY include an optional `error_description` query parameter.
   */
  authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void>;

  /**
   * Returns the `codeChallenge` that was used when the indicated authorization began.
   */
  challengeForAuthorizationCode(client: OAuthClientInformationFull, authorizationCode: string): Promise<string>;

  /**
   * Exchanges an authorization code for an access token.
   */
  exchangeAuthorizationCode(
    client: OAuthClientInformationFull, 
    authorizationCode: string, 
    codeVerifier?: string,
    redirectUri?: string,
    resource?: URL
  ): Promise<OAuthTokens>;

  /**
   * Exchanges a refresh token for an access token.
   */
  exchangeRefreshToken(client: OAuthClientInformationFull, refreshToken: string, scopes?: string[], resource?: URL): Promise<OAuthTokens>;

  /**
   * Verifies an access token and returns information about it.
   */
  verifyAccessToken(token: string): Promise<AuthInfo>;

  /**
   * Revokes an access or refresh token. If unimplemented, token revocation is not supported (not recommended).
   *
   * If the given token is invalid or already revoked, this method should do nothing.
   */
  revokeToken?(client: OAuthClientInformationFull, request: OAuthTokenRevocationRequest): Promise<void>;

  /**
   * Whether to skip local PKCE validation.
   *
   * If true, the server will not perform PKCE validation locally and will pass the code_verifier to the upstream server.
   *
   * NOTE: This should only be true if the upstream server is performing the actual PKCE validation.
   */
  skipLocalPkceValidation?: boolean;
}


/**
 * Slim implementation useful for token verification
 */
export interface OAuthTokenVerifier {
  /**
   * Verifies an access token and returns information about it.
   */
  verifyAccessToken(token: string): Promise<AuthInfo>;
}



================================================
FILE: src/server/auth/router.test.ts
================================================
import { mcpAuthRouter, AuthRouterOptions, mcpAuthMetadataRouter, AuthMetadataOptions } from './router.js';
import { OAuthServerProvider, AuthorizationParams } from './provider.js';
import { OAuthRegisteredClientsStore } from './clients.js';
import { OAuthClientInformationFull, OAuthMetadata, OAuthTokenRevocationRequest, OAuthTokens } from '../../shared/auth.js';
import express, { Response } from 'express';
import supertest from 'supertest';
import { AuthInfo } from './types.js';
import { InvalidTokenError } from './errors.js';


describe('MCP Auth Router', () => {
  // Setup mock provider with full capabilities
  const mockClientStore: OAuthRegisteredClientsStore = {
    async getClient(clientId: string): Promise<OAuthClientInformationFull | undefined> {
      if (clientId === 'valid-client') {
        return {
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          redirect_uris: ['https://example.com/callback']
        };
      }
      return undefined;
    },

    async registerClient(client: OAuthClientInformationFull): Promise<OAuthClientInformationFull> {
      return client;
    }
  };

  const mockProvider: OAuthServerProvider = {
    clientsStore: mockClientStore,

    async authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void> {
      const redirectUrl = new URL(params.redirectUri);
      redirectUrl.searchParams.set('code', 'mock_auth_code');
      if (params.state) {
        redirectUrl.searchParams.set('state', params.state);
      }
      res.redirect(302, redirectUrl.toString());
    },

    async challengeForAuthorizationCode(): Promise<string> {
      return 'mock_challenge';
    },

    async exchangeAuthorizationCode(): Promise<OAuthTokens> {
      return {
        access_token: 'mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'mock_refresh_token'
      };
    },

    async exchangeRefreshToken(): Promise<OAuthTokens> {
      return {
        access_token: 'new_mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'new_mock_refresh_token'
      };
    },

    async verifyAccessToken(token: string): Promise<AuthInfo> {
      if (token === 'valid_token') {
        return {
          token,
          clientId: 'valid-client',
          scopes: ['read', 'write'],
          expiresAt: Date.now() / 1000 + 3600
        };
      }
      throw new InvalidTokenError('Token is invalid or expired');
    },

    async revokeToken(_client: OAuthClientInformationFull, _request: OAuthTokenRevocationRequest): Promise<void> {
      // Success - do nothing in mock
    }
  };

  // Provider without registration and revocation
  const mockProviderMinimal: OAuthServerProvider = {
    clientsStore: {
      async getClient(clientId: string): Promise<OAuthClientInformationFull | undefined> {
        if (clientId === 'valid-client') {
          return {
            client_id: 'valid-client',
            client_secret: 'valid-secret',
            redirect_uris: ['https://example.com/callback']
          };
        }
        return undefined;
      }
    },

    async authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void> {
      const redirectUrl = new URL(params.redirectUri);
      redirectUrl.searchParams.set('code', 'mock_auth_code');
      if (params.state) {
        redirectUrl.searchParams.set('state', params.state);
      }
      res.redirect(302, redirectUrl.toString());
    },

    async challengeForAuthorizationCode(): Promise<string> {
      return 'mock_challenge';
    },

    async exchangeAuthorizationCode(): Promise<OAuthTokens> {
      return {
        access_token: 'mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'mock_refresh_token'
      };
    },

    async exchangeRefreshToken(): Promise<OAuthTokens> {
      return {
        access_token: 'new_mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'new_mock_refresh_token'
      };
    },

    async verifyAccessToken(token: string): Promise<AuthInfo> {
      if (token === 'valid_token') {
        return {
          token,
          clientId: 'valid-client',
          scopes: ['read'],
          expiresAt: Date.now() / 1000 + 3600
        };
      }
      throw new InvalidTokenError('Token is invalid or expired');
    }
  };

  describe('Router creation', () => {
    it('throws error for non-HTTPS issuer URL', () => {
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('http://auth.example.com')
      };

      expect(() => mcpAuthRouter(options)).toThrow('Issuer URL must be HTTPS');
    });

    it('allows localhost HTTP for development', () => {
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('http://localhost:3000')
      };

      expect(() => mcpAuthRouter(options)).not.toThrow();
    });

    it('throws error for issuer URL with fragment', () => {
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('https://auth.example.com#fragment')
      };

      expect(() => mcpAuthRouter(options)).toThrow('Issuer URL must not have a fragment');
    });

    it('throws error for issuer URL with query string', () => {
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('https://auth.example.com?param=value')
      };

      expect(() => mcpAuthRouter(options)).toThrow('Issuer URL must not have a query string');
    });

    it('successfully creates router with valid options', () => {
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('https://auth.example.com')
      };

      expect(() => mcpAuthRouter(options)).not.toThrow();
    });
  });

  describe('Metadata endpoint', () => {
    let app: express.Express;

    beforeEach(() => {
      // Setup full-featured router
      app = express();
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('https://auth.example.com'),
        serviceDocumentationUrl: new URL('https://docs.example.com')
      };
      app.use(mcpAuthRouter(options));
    });

    it('returns complete metadata for full-featured router', async () => {
      const response = await supertest(app)
        .get('/.well-known/oauth-authorization-server');

      expect(response.status).toBe(200);

      // Verify essential fields
      expect(response.body.issuer).toBe('https://auth.example.com/');
      expect(response.body.authorization_endpoint).toBe('https://auth.example.com/authorize');
      expect(response.body.token_endpoint).toBe('https://auth.example.com/token');
      expect(response.body.registration_endpoint).toBe('https://auth.example.com/register');
      expect(response.body.revocation_endpoint).toBe('https://auth.example.com/revoke');

      // Verify supported features
      expect(response.body.response_types_supported).toEqual(['code']);
      expect(response.body.grant_types_supported).toEqual(['authorization_code', 'refresh_token']);
      expect(response.body.code_challenge_methods_supported).toEqual(['S256']);
      expect(response.body.token_endpoint_auth_methods_supported).toEqual(['client_secret_post']);
      expect(response.body.revocation_endpoint_auth_methods_supported).toEqual(['client_secret_post']);

      // Verify optional fields
      expect(response.body.service_documentation).toBe('https://docs.example.com/');
    });

    it('returns minimal metadata for minimal router', async () => {
      // Setup minimal router
      const minimalApp = express();
      const options: AuthRouterOptions = {
        provider: mockProviderMinimal,
        issuerUrl: new URL('https://auth.example.com')
      };
      minimalApp.use(mcpAuthRouter(options));

      const response = await supertest(minimalApp)
        .get('/.well-known/oauth-authorization-server');

      expect(response.status).toBe(200);

      // Verify essential endpoints
      expect(response.body.issuer).toBe('https://auth.example.com/');
      expect(response.body.authorization_endpoint).toBe('https://auth.example.com/authorize');
      expect(response.body.token_endpoint).toBe('https://auth.example.com/token');

      // Verify missing optional endpoints
      expect(response.body.registration_endpoint).toBeUndefined();
      expect(response.body.revocation_endpoint).toBeUndefined();
      expect(response.body.revocation_endpoint_auth_methods_supported).toBeUndefined();
      expect(response.body.service_documentation).toBeUndefined();
    });

    it('provides protected resource metadata', async () => {
      // Setup router with draft protocol version
      const draftApp = express();
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('https://mcp.example.com'),
        scopesSupported: ['read', 'write'],
        resourceName: 'Test API'
      };
      draftApp.use(mcpAuthRouter(options));

      const response = await supertest(draftApp)
        .get('/.well-known/oauth-protected-resource');

      expect(response.status).toBe(200);

      // Verify protected resource metadata
      expect(response.body.resource).toBe('https://mcp.example.com/');
      expect(response.body.authorization_servers).toContain('https://mcp.example.com/');
      expect(response.body.scopes_supported).toEqual(['read', 'write']);
      expect(response.body.resource_name).toBe('Test API');
    });
  });

  describe('Endpoint routing', () => {
    let app: express.Express;

    beforeEach(() => {
      // Setup full-featured router
      app = express();
      const options: AuthRouterOptions = {
        provider: mockProvider,
        issuerUrl: new URL('https://auth.example.com')
      };
      app.use(mcpAuthRouter(options));
      jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it('routes to authorization endpoint', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.has('code')).toBe(true);
    });

    it('routes to token endpoint', async () => {
      // Setup verifyChallenge mock for token handler
      jest.mock('pkce-challenge', () => ({
        verifyChallenge: jest.fn().mockResolvedValue(true)
      }));

      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          code: 'valid_code',
          code_verifier: 'valid_verifier'
        });

      // The request will fail in testing due to mocking limitations,
      // but we can verify the route was matched
      expect(response.status).not.toBe(404);
    });

    it('routes to registration endpoint', async () => {
      const response = await supertest(app)
        .post('/register')
        .send({
          redirect_uris: ['https://example.com/callback']
        });

      // The request will fail in testing due to mocking limitations,
      // but we can verify the route was matched
      expect(response.status).not.toBe(404);
    });

    it('routes to revocation endpoint', async () => {
      const response = await supertest(app)
        .post('/revoke')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          token: 'token_to_revoke'
        });

      // The request will fail in testing due to mocking limitations,
      // but we can verify the route was matched
      expect(response.status).not.toBe(404);
    });

    it('excludes endpoints for unsupported features', async () => {
      // Setup minimal router
      const minimalApp = express();
      const options: AuthRouterOptions = {
        provider: mockProviderMinimal,
        issuerUrl: new URL('https://auth.example.com')
      };
      minimalApp.use(mcpAuthRouter(options));

      // Registration should not be available
      const regResponse = await supertest(minimalApp)
        .post('/register')
        .send({
          redirect_uris: ['https://example.com/callback']
        });
      expect(regResponse.status).toBe(404);

      // Revocation should not be available
      const revokeResponse = await supertest(minimalApp)
        .post('/revoke')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          token: 'token_to_revoke'
        });
      expect(revokeResponse.status).toBe(404);
    });
  });
});

describe('MCP Auth Metadata Router', () => {

  const mockOAuthMetadata : OAuthMetadata = {
    issuer: 'https://auth.example.com/',
    authorization_endpoint: "https://auth.example.com/authorize",
    token_endpoint: "https://auth.example.com/token",
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    code_challenge_methods_supported: ["S256"],
    token_endpoint_auth_methods_supported: ["client_secret_post"],
  }

  describe('Router creation', () => {
    it('successfully creates router with valid options', () => {
      const options: AuthMetadataOptions = {
        oauthMetadata: mockOAuthMetadata,
        resourceServerUrl: new URL('https://api.example.com'),
      };

      expect(() => mcpAuthMetadataRouter(options)).not.toThrow();
    });
  });

  describe('Metadata endpoints', () => {
    let app: express.Express;

    beforeEach(() => {
      app = express();
      const options: AuthMetadataOptions = {
        oauthMetadata: mockOAuthMetadata,
        resourceServerUrl: new URL('https://api.example.com'),
        serviceDocumentationUrl: new URL('https://docs.example.com'),
        scopesSupported: ['read', 'write'],
        resourceName: 'Test API'
      };
      app.use(mcpAuthMetadataRouter(options));
    });

    it('returns OAuth authorization server metadata', async () => {
      const response = await supertest(app)
        .get('/.well-known/oauth-authorization-server');

      expect(response.status).toBe(200);

      // Verify metadata points to authorization server
      expect(response.body.issuer).toBe('https://auth.example.com/');
      expect(response.body.authorization_endpoint).toBe('https://auth.example.com/authorize');
      expect(response.body.token_endpoint).toBe('https://auth.example.com/token');
      expect(response.body.response_types_supported).toEqual(['code']);
      expect(response.body.grant_types_supported).toEqual(['authorization_code', 'refresh_token']);
      expect(response.body.code_challenge_methods_supported).toEqual(['S256']);
      expect(response.body.token_endpoint_auth_methods_supported).toEqual(['client_secret_post']);
    });

    it('returns OAuth protected resource metadata', async () => {
      const response = await supertest(app)
        .get('/.well-known/oauth-protected-resource');

      expect(response.status).toBe(200);

      // Verify protected resource metadata
      expect(response.body.resource).toBe('https://api.example.com/');
      expect(response.body.authorization_servers).toEqual(['https://auth.example.com/']);
      expect(response.body.scopes_supported).toEqual(['read', 'write']);
      expect(response.body.resource_name).toBe('Test API');
      expect(response.body.resource_documentation).toBe('https://docs.example.com/');
    });

    it('works with minimal configuration', async () => {
      const minimalApp = express();
      const options: AuthMetadataOptions = {
        oauthMetadata: mockOAuthMetadata,
        resourceServerUrl: new URL('https://api.example.com'),
      };
      minimalApp.use(mcpAuthMetadataRouter(options));

      const authResponse = await supertest(minimalApp)
        .get('/.well-known/oauth-authorization-server');

      expect(authResponse.status).toBe(200);
      expect(authResponse.body.issuer).toBe('https://auth.example.com/');
      expect(authResponse.body.service_documentation).toBeUndefined();
      expect(authResponse.body.scopes_supported).toBeUndefined();

      const resourceResponse = await supertest(minimalApp)
        .get('/.well-known/oauth-protected-resource');

      expect(resourceResponse.status).toBe(200);
      expect(resourceResponse.body.resource).toBe('https://api.example.com/');
      expect(resourceResponse.body.authorization_servers).toEqual(['https://auth.example.com/']);
      expect(resourceResponse.body.scopes_supported).toBeUndefined();
      expect(resourceResponse.body.resource_name).toBeUndefined();
      expect(resourceResponse.body.resource_documentation).toBeUndefined();
    });
  });
});



================================================
FILE: src/server/auth/router.ts
================================================
import express, { RequestHandler } from "express";
import { clientRegistrationHandler, ClientRegistrationHandlerOptions } from "./handlers/register.js";
import { tokenHandler, TokenHandlerOptions } from "./handlers/token.js";
import { authorizationHandler, AuthorizationHandlerOptions } from "./handlers/authorize.js";
import { revocationHandler, RevocationHandlerOptions } from "./handlers/revoke.js";
import { metadataHandler } from "./handlers/metadata.js";
import { OAuthServerProvider } from "./provider.js";
import { OAuthMetadata, OAuthProtectedResourceMetadata } from "../../shared/auth.js";

export type AuthRouterOptions = {
  /**
   * A provider implementing the actual authorization logic for this router.
   */
  provider: OAuthServerProvider;

  /**
   * The authorization server's issuer identifier, which is a URL that uses the "https" scheme and has no query or fragment components.
   */
  issuerUrl: URL;

  /**
   * The base URL of the authorization server to use for the metadata endpoints.
   *
   * If not provided, the issuer URL will be used as the base URL.
   */
  baseUrl?: URL;

  /**
   * An optional URL of a page containing human-readable information that developers might want or need to know when using the authorization server.
   */
  serviceDocumentationUrl?: URL;

  /**
   * An optional list of scopes supported by this authorization server
   */
  scopesSupported?: string[];


  /**
   * The resource name to be displayed in protected resource metadata
   */
  resourceName?: string;

  // Individual options per route
  authorizationOptions?: Omit<AuthorizationHandlerOptions, "provider">;
  clientRegistrationOptions?: Omit<ClientRegistrationHandlerOptions, "clientsStore">;
  revocationOptions?: Omit<RevocationHandlerOptions, "provider">;
  tokenOptions?: Omit<TokenHandlerOptions, "provider">;
};

const checkIssuerUrl = (issuer: URL): void => {
  // Technically RFC 8414 does not permit a localhost HTTPS exemption, but this will be necessary for ease of testing
  if (issuer.protocol !== "https:" && issuer.hostname !== "localhost" && issuer.hostname !== "127.0.0.1") {
    throw new Error("Issuer URL must be HTTPS");
  }
  if (issuer.hash) {
    throw new Error(`Issuer URL must not have a fragment: ${issuer}`);
  }
  if (issuer.search) {
    throw new Error(`Issuer URL must not have a query string: ${issuer}`);
  }
}

export const createOAuthMetadata = (options: {
  provider: OAuthServerProvider,
  issuerUrl: URL,
  baseUrl?: URL
  serviceDocumentationUrl?: URL,
  scopesSupported?: string[];
}): OAuthMetadata => {
  const issuer = options.issuerUrl;
  const baseUrl = options.baseUrl;

  checkIssuerUrl(issuer);

  const authorization_endpoint = "/authorize";
  const token_endpoint = "/token";
  const registration_endpoint = options.provider.clientsStore.registerClient ? "/register" : undefined;
  const revocation_endpoint = options.provider.revokeToken ? "/revoke" : undefined;

  const metadata: OAuthMetadata = {
    issuer: issuer.href,
    service_documentation: options.serviceDocumentationUrl?.href,

    authorization_endpoint: new URL(authorization_endpoint, baseUrl || issuer).href,
    response_types_supported: ["code"],
    code_challenge_methods_supported: ["S256"],

    token_endpoint: new URL(token_endpoint, baseUrl || issuer).href,
    token_endpoint_auth_methods_supported: ["client_secret_post"],
    grant_types_supported: ["authorization_code", "refresh_token"],

    scopes_supported: options.scopesSupported,

    revocation_endpoint: revocation_endpoint ? new URL(revocation_endpoint, baseUrl || issuer).href : undefined,
    revocation_endpoint_auth_methods_supported: revocation_endpoint ? ["client_secret_post"] : undefined,

    registration_endpoint: registration_endpoint ? new URL(registration_endpoint, baseUrl || issuer).href : undefined,
  };

  return metadata
}

/**
 * Installs standard MCP authorization server endpoints, including dynamic client registration and token revocation (if supported).
 * Also advertises standard authorization server metadata, for easier discovery of supported configurations by clients.
 * Note: if your MCP server is only a resource server and not an authorization server, use mcpAuthMetadataRouter instead.
 *
 * By default, rate limiting is applied to all endpoints to prevent abuse.
 *
 * This router MUST be installed at the application root, like so:
 *
 *  const app = express();
 *  app.use(mcpAuthRouter(...));
 */
export function mcpAuthRouter(options: AuthRouterOptions): RequestHandler {
  const oauthMetadata = createOAuthMetadata(options);

  const router = express.Router();

  router.use(
    new URL(oauthMetadata.authorization_endpoint).pathname,
    authorizationHandler({ provider: options.provider, ...options.authorizationOptions })
  );

  router.use(
    new URL(oauthMetadata.token_endpoint).pathname,
    tokenHandler({ provider: options.provider, ...options.tokenOptions })
  );

  router.use(mcpAuthMetadataRouter({
    oauthMetadata,
    // This router is used for AS+RS combo's, so the issuer is also the resource server
    resourceServerUrl: new URL(oauthMetadata.issuer),
    serviceDocumentationUrl: options.serviceDocumentationUrl,
    scopesSupported: options.scopesSupported,
    resourceName: options.resourceName
  }));

  if (oauthMetadata.registration_endpoint) {
    router.use(
      new URL(oauthMetadata.registration_endpoint).pathname,
      clientRegistrationHandler({
        clientsStore: options.provider.clientsStore,
        ...options.clientRegistrationOptions,
      })
    );
  }

  if (oauthMetadata.revocation_endpoint) {
    router.use(
      new URL(oauthMetadata.revocation_endpoint).pathname,
      revocationHandler({ provider: options.provider, ...options.revocationOptions })
    );
  }

  return router;
}

export type AuthMetadataOptions = {
  /**
   * OAuth Metadata as would be returned from the authorization server
   * this MCP server relies on
   */
  oauthMetadata: OAuthMetadata;

  /**
   * The url of the MCP server, for use in protected resource metadata
   */
  resourceServerUrl: URL;

  /**
   * The url for documentation for the MCP server
   */
  serviceDocumentationUrl?: URL;

  /**
   * An optional list of scopes supported by this MCP server
   */
  scopesSupported?: string[];

  /**
   * An optional resource name to display in resource metadata
   */
  resourceName?: string;
}

export function mcpAuthMetadataRouter(options: AuthMetadataOptions) {
  checkIssuerUrl(new URL(options.oauthMetadata.issuer));

  const router = express.Router();

  const protectedResourceMetadata: OAuthProtectedResourceMetadata = {
    resource: options.resourceServerUrl.href,

    authorization_servers: [
      options.oauthMetadata.issuer
    ],

    scopes_supported: options.scopesSupported,
    resource_name: options.resourceName,
    resource_documentation: options.serviceDocumentationUrl?.href,
  };

  router.use("/.well-known/oauth-protected-resource", metadataHandler(protectedResourceMetadata));

  // Always add this for backwards compatibility
  router.use("/.well-known/oauth-authorization-server", metadataHandler(options.oauthMetadata));

  return router;
}

/**
 * Helper function to construct the OAuth 2.0 Protected Resource Metadata URL
 * from a given server URL. This replaces the path with the standard metadata endpoint.
 *
 * @param serverUrl - The base URL of the protected resource server
 * @returns The URL for the OAuth protected resource metadata endpoint
 *
 * @example
 * getOAuthProtectedResourceMetadataUrl(new URL('https://api.example.com/mcp'))
 * // Returns: 'https://api.example.com/.well-known/oauth-protected-resource'
 */
export function getOAuthProtectedResourceMetadataUrl(serverUrl: URL): string {
  return new URL('/.well-known/oauth-protected-resource', serverUrl).href;
}



================================================
FILE: src/server/auth/types.ts
================================================
/**
 * Information about a validated access token, provided to request handlers.
 */
export interface AuthInfo {
  /**
   * The access token.
   */
  token: string;

  /**
   * The client ID associated with this token.
   */
  clientId: string;

  /**
   * Scopes associated with this token.
   */
  scopes: string[];

  /**
   * When the token expires (in seconds since epoch).
   */
  expiresAt?: number;

  /**
   * The RFC 8707 resource server identifier for which this token is valid.
   * If set, this MUST match the MCP server's resource identifier (minus hash fragment).
   */
  resource?: URL;

  /**
   * Additional data associated with the token.
   * This field should be used for any additional data that needs to be attached to the auth info.
  */
  extra?: Record<string, unknown>;
}


================================================
FILE: src/server/auth/handlers/authorize.test.ts
================================================
import { authorizationHandler, AuthorizationHandlerOptions } from './authorize.js';
import { OAuthServerProvider, AuthorizationParams } from '../provider.js';
import { OAuthRegisteredClientsStore } from '../clients.js';
import { OAuthClientInformationFull, OAuthTokens } from '../../../shared/auth.js';
import express, { Response } from 'express';
import supertest from 'supertest';
import { AuthInfo } from '../types.js';
import { InvalidTokenError } from '../errors.js';

describe('Authorization Handler', () => {
  // Mock client data
  const validClient: OAuthClientInformationFull = {
    client_id: 'valid-client',
    client_secret: 'valid-secret',
    redirect_uris: ['https://example.com/callback'],
    scope: 'profile email'
  };

  const multiRedirectClient: OAuthClientInformationFull = {
    client_id: 'multi-redirect-client',
    client_secret: 'valid-secret',
    redirect_uris: [
      'https://example.com/callback1',
      'https://example.com/callback2'
    ],
    scope: 'profile email'
  };

  // Mock client store
  const mockClientStore: OAuthRegisteredClientsStore = {
    async getClient(clientId: string): Promise<OAuthClientInformationFull | undefined> {
      if (clientId === 'valid-client') {
        return validClient;
      } else if (clientId === 'multi-redirect-client') {
        return multiRedirectClient;
      }
      return undefined;
    }
  };

  // Mock provider
  const mockProvider: OAuthServerProvider = {
    clientsStore: mockClientStore,

    async authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void> {
      // Mock implementation - redirects to redirectUri with code and state
      const redirectUrl = new URL(params.redirectUri);
      redirectUrl.searchParams.set('code', 'mock_auth_code');
      if (params.state) {
        redirectUrl.searchParams.set('state', params.state);
      }
      res.redirect(302, redirectUrl.toString());
    },

    async challengeForAuthorizationCode(): Promise<string> {
      return 'mock_challenge';
    },

    async exchangeAuthorizationCode(): Promise<OAuthTokens> {
      return {
        access_token: 'mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'mock_refresh_token'
      };
    },

    async exchangeRefreshToken(): Promise<OAuthTokens> {
      return {
        access_token: 'new_mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'new_mock_refresh_token'
      };
    },

    async verifyAccessToken(token: string): Promise<AuthInfo> {
      if (token === 'valid_token') {
        return {
          token,
          clientId: 'valid-client',
          scopes: ['read', 'write'],
          expiresAt: Date.now() / 1000 + 3600
        };
      }
      throw new InvalidTokenError('Token is invalid or expired');
    },

    async revokeToken(): Promise<void> {
      // Do nothing in mock
    }
  };

  // Setup express app with handler
  let app: express.Express;
  let options: AuthorizationHandlerOptions;

  beforeEach(() => {
    app = express();
    options = { provider: mockProvider };
    const handler = authorizationHandler(options);
    app.use('/authorize', handler);
  });

  describe('HTTP method validation', () => {
    it('rejects non-GET/POST methods', async () => {
      const response = await supertest(app)
        .put('/authorize')
        .query({ client_id: 'valid-client' });

      expect(response.status).toBe(405); // Method not allowed response from handler
    });
  });

  describe('Client validation', () => {
    it('requires client_id parameter', async () => {
      const response = await supertest(app)
        .get('/authorize');

      expect(response.status).toBe(400);
      expect(response.text).toContain('client_id');
    });

    it('validates that client exists', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({ client_id: 'nonexistent-client' });

      expect(response.status).toBe(400);
    });
  });

  describe('Redirect URI validation', () => {
    it('uses the only redirect_uri if client has just one and none provided', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.origin + location.pathname).toBe('https://example.com/callback');
    });

    it('requires redirect_uri if client has multiple', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'multi-redirect-client',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(400);
    });

    it('validates redirect_uri against client registered URIs', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://malicious.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(400);
    });

    it('accepts valid redirect_uri that client registered with', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.origin + location.pathname).toBe('https://example.com/callback');
    });
  });

  describe('Authorization request validation', () => {
    it('requires response_type=code', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'token', // invalid - we only support code flow
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.get('error')).toBe('invalid_request');
    });

    it('requires code_challenge parameter', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge_method: 'S256'
          // Missing code_challenge
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.get('error')).toBe('invalid_request');
    });

    it('requires code_challenge_method=S256', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'plain' // Only S256 is supported
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.get('error')).toBe('invalid_request');
    });
  });

  describe('Scope validation', () => {
    it('validates requested scopes against client registered scopes', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256',
          scope: 'profile email admin' // 'admin' not in client scopes
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.get('error')).toBe('invalid_scope');
    });

    it('accepts valid scopes subset', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256',
          scope: 'profile' // subset of client scopes
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.has('code')).toBe(true);
    });
  });

  describe('Resource parameter validation', () => {
    it('propagates resource parameter', async () => {
      const mockProviderWithResource = jest.spyOn(mockProvider, 'authorize');
      
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256',
          resource: 'https://api.example.com/resource'
        });

      expect(response.status).toBe(302);
      expect(mockProviderWithResource).toHaveBeenCalledWith(
        validClient,
        expect.objectContaining({
          resource: new URL('https://api.example.com/resource'),
          redirectUri: 'https://example.com/callback',
          codeChallenge: 'challenge123'
        }),
        expect.any(Object)
      );
    });
  });

  describe('Successful authorization', () => {
    it('handles successful authorization with all parameters', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256',
          scope: 'profile email',
          state: 'xyz789'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.origin + location.pathname).toBe('https://example.com/callback');
      expect(location.searchParams.get('code')).toBe('mock_auth_code');
      expect(location.searchParams.get('state')).toBe('xyz789');
    });

    it('preserves state parameter in response', async () => {
      const response = await supertest(app)
        .get('/authorize')
        .query({
          client_id: 'valid-client',
          redirect_uri: 'https://example.com/callback',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256',
          state: 'state-value-123'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.get('state')).toBe('state-value-123');
    });

    it('handles POST requests the same as GET', async () => {
      const response = await supertest(app)
        .post('/authorize')
        .type('form')
        .send({
          client_id: 'valid-client',
          response_type: 'code',
          code_challenge: 'challenge123',
          code_challenge_method: 'S256'
        });

      expect(response.status).toBe(302);
      const location = new URL(response.header.location);
      expect(location.searchParams.has('code')).toBe(true);
    });
  });
});


================================================
FILE: src/server/auth/handlers/authorize.ts
================================================
import { RequestHandler } from "express";
import { z } from "zod";
import express from "express";
import { OAuthServerProvider } from "../provider.js";
import { rateLimit, Options as RateLimitOptions } from "express-rate-limit";
import { allowedMethods } from "../middleware/allowedMethods.js";
import {
  InvalidRequestError,
  InvalidClientError,
  InvalidScopeError,
  ServerError,
  TooManyRequestsError,
  OAuthError
} from "../errors.js";

export type AuthorizationHandlerOptions = {
  provider: OAuthServerProvider;
  /**
   * Rate limiting configuration for the authorization endpoint.
   * Set to false to disable rate limiting for this endpoint.
   */
  rateLimit?: Partial<RateLimitOptions> | false;
};

// Parameters that must be validated in order to issue redirects.
const ClientAuthorizationParamsSchema = z.object({
  client_id: z.string(),
  redirect_uri: z.string().optional().refine((value) => value === undefined || URL.canParse(value), { message: "redirect_uri must be a valid URL" }),
});

// Parameters that must be validated for a successful authorization request. Failure can be reported to the redirect URI.
const RequestAuthorizationParamsSchema = z.object({
  response_type: z.literal("code"),
  code_challenge: z.string(),
  code_challenge_method: z.literal("S256"),
  scope: z.string().optional(),
  state: z.string().optional(),
  resource: z.string().url().optional(),
});

export function authorizationHandler({ provider, rateLimit: rateLimitConfig }: AuthorizationHandlerOptions): RequestHandler {
  // Create a router to apply middleware
  const router = express.Router();
  router.use(allowedMethods(["GET", "POST"]));
  router.use(express.urlencoded({ extended: false }));

  // Apply rate limiting unless explicitly disabled
  if (rateLimitConfig !== false) {
    router.use(rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100, // 100 requests per windowMs
      standardHeaders: true,
      legacyHeaders: false,
      message: new TooManyRequestsError('You have exceeded the rate limit for authorization requests').toResponseObject(),
      ...rateLimitConfig
    }));
  }

  router.all("/", async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');

    // In the authorization flow, errors are split into two categories:
    // 1. Pre-redirect errors (direct response with 400)
    // 2. Post-redirect errors (redirect with error parameters)

    // Phase 1: Validate client_id and redirect_uri. Any errors here must be direct responses.
    let client_id, redirect_uri, client;
    try {
      const result = ClientAuthorizationParamsSchema.safeParse(req.method === 'POST' ? req.body : req.query);
      if (!result.success) {
        throw new InvalidRequestError(result.error.message);
      }

      client_id = result.data.client_id;
      redirect_uri = result.data.redirect_uri;

      client = await provider.clientsStore.getClient(client_id);
      if (!client) {
        throw new InvalidClientError("Invalid client_id");
      }

      if (redirect_uri !== undefined) {
        if (!client.redirect_uris.includes(redirect_uri)) {
          throw new InvalidRequestError("Unregistered redirect_uri");
        }
      } else if (client.redirect_uris.length === 1) {
        redirect_uri = client.redirect_uris[0];
      } else {
        throw new InvalidRequestError("redirect_uri must be specified when client has multiple registered URIs");
      }
    } catch (error) {
      // Pre-redirect errors - return direct response
      //
      // These don't need to be JSON encoded, as they'll be displayed in a user
      // agent, but OTOH they all represent exceptional situations (arguably,
      // "programmer error"), so presenting a nice HTML page doesn't help the
      // user anyway.
      if (error instanceof OAuthError) {
        const status = error instanceof ServerError ? 500 : 400;
        res.status(status).json(error.toResponseObject());
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.status(500).json(serverError.toResponseObject());
      }

      return;
    }

    // Phase 2: Validate other parameters. Any errors here should go into redirect responses.
    let state;
    try {
      // Parse and validate authorization parameters
      const parseResult = RequestAuthorizationParamsSchema.safeParse(req.method === 'POST' ? req.body : req.query);
      if (!parseResult.success) {
        throw new InvalidRequestError(parseResult.error.message);
      }

      const { scope, code_challenge, resource } = parseResult.data;
      state = parseResult.data.state;

      // Validate scopes
      let requestedScopes: string[] = [];
      if (scope !== undefined) {
        requestedScopes = scope.split(" ");
        const allowedScopes = new Set(client.scope?.split(" "));

        // Check each requested scope against allowed scopes
        for (const scope of requestedScopes) {
          if (!allowedScopes.has(scope)) {
            throw new InvalidScopeError(`Client was not registered with scope ${scope}`);
          }
        }
      }

      // All validation passed, proceed with authorization
      await provider.authorize(client, {
        state,
        scopes: requestedScopes,
        redirectUri: redirect_uri,
        codeChallenge: code_challenge,
        resource: resource ? new URL(resource) : undefined,
      }, res);
    } catch (error) {
      // Post-redirect errors - redirect with error parameters
      if (error instanceof OAuthError) {
        res.redirect(302, createErrorRedirect(redirect_uri, error, state));
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.redirect(302, createErrorRedirect(redirect_uri, serverError, state));
      }
    }
  });

  return router;
}

/**
 * Helper function to create redirect URL with error parameters
 */
function createErrorRedirect(redirectUri: string, error: OAuthError, state?: string): string {
  const errorUrl = new URL(redirectUri);
  errorUrl.searchParams.set("error", error.errorCode);
  errorUrl.searchParams.set("error_description", error.message);
  if (error.errorUri) {
    errorUrl.searchParams.set("error_uri", error.errorUri);
  }
  if (state) {
    errorUrl.searchParams.set("state", state);
  }
  return errorUrl.href;
}


================================================
FILE: src/server/auth/handlers/metadata.test.ts
================================================
import { metadataHandler } from './metadata.js';
import { OAuthMetadata } from '../../../shared/auth.js';
import express from 'express';
import supertest from 'supertest';

describe('Metadata Handler', () => {
  const exampleMetadata: OAuthMetadata = {
    issuer: 'https://auth.example.com',
    authorization_endpoint: 'https://auth.example.com/authorize',
    token_endpoint: 'https://auth.example.com/token',
    registration_endpoint: 'https://auth.example.com/register',
    revocation_endpoint: 'https://auth.example.com/revoke',
    scopes_supported: ['profile', 'email'],
    response_types_supported: ['code'],
    grant_types_supported: ['authorization_code', 'refresh_token'],
    token_endpoint_auth_methods_supported: ['client_secret_basic'],
    code_challenge_methods_supported: ['S256']
  };

  let app: express.Express;

  beforeEach(() => {
    // Setup express app with metadata handler
    app = express();
    app.use('/.well-known/oauth-authorization-server', metadataHandler(exampleMetadata));
  });

  it('requires GET method', async () => {
    const response = await supertest(app)
      .post('/.well-known/oauth-authorization-server')
      .send({});

    expect(response.status).toBe(405);
    expect(response.headers.allow).toBe('GET');
    expect(response.body).toEqual({
      error: "method_not_allowed",
      error_description: "The method POST is not allowed for this endpoint"
    });
  });

  it('returns the metadata object', async () => {
    const response = await supertest(app)
      .get('/.well-known/oauth-authorization-server');

    expect(response.status).toBe(200);
    expect(response.body).toEqual(exampleMetadata);
  });

  it('includes CORS headers in response', async () => {
    const response = await supertest(app)
      .get('/.well-known/oauth-authorization-server')
      .set('Origin', 'https://example.com');

    expect(response.header['access-control-allow-origin']).toBe('*');
  });

  it('supports OPTIONS preflight requests', async () => {
    const response = await supertest(app)
      .options('/.well-known/oauth-authorization-server')
      .set('Origin', 'https://example.com')
      .set('Access-Control-Request-Method', 'GET');

    expect(response.status).toBe(204);
    expect(response.header['access-control-allow-origin']).toBe('*');
  });

  it('works with minimal metadata', async () => {
    // Setup a new express app with minimal metadata
    const minimalApp = express();
    const minimalMetadata: OAuthMetadata = {
      issuer: 'https://auth.example.com',
      authorization_endpoint: 'https://auth.example.com/authorize',
      token_endpoint: 'https://auth.example.com/token',
      response_types_supported: ['code']
    };
    minimalApp.use('/.well-known/oauth-authorization-server', metadataHandler(minimalMetadata));

    const response = await supertest(minimalApp)
      .get('/.well-known/oauth-authorization-server');

    expect(response.status).toBe(200);
    expect(response.body).toEqual(minimalMetadata);
  });
});


================================================
FILE: src/server/auth/handlers/metadata.ts
================================================
import express, { RequestHandler } from "express";
import { OAuthMetadata, OAuthProtectedResourceMetadata } from "../../../shared/auth.js";
import cors from 'cors';
import { allowedMethods } from "../middleware/allowedMethods.js";

export function metadataHandler(metadata: OAuthMetadata | OAuthProtectedResourceMetadata): RequestHandler {
  // Nested router so we can configure middleware and restrict HTTP method
  const router = express.Router();

  // Configure CORS to allow any origin, to make accessible to web-based MCP clients
  router.use(cors());

  router.use(allowedMethods(['GET']));
  router.get("/", (req, res) => {
    res.status(200).json(metadata);
  });

  return router;
}



================================================
FILE: src/server/auth/handlers/register.test.ts
================================================
import { clientRegistrationHandler, ClientRegistrationHandlerOptions } from './register.js';
import { OAuthRegisteredClientsStore } from '../clients.js';
import { OAuthClientInformationFull, OAuthClientMetadata } from '../../../shared/auth.js';
import express from 'express';
import supertest from 'supertest';

describe('Client Registration Handler', () => {
  // Mock client store with registration support
  const mockClientStoreWithRegistration: OAuthRegisteredClientsStore = {
    async getClient(_clientId: string): Promise<OAuthClientInformationFull | undefined> {
      return undefined;
    },

    async registerClient(client: OAuthClientInformationFull): Promise<OAuthClientInformationFull> {
      // Return the client info as-is in the mock
      return client;
    }
  };

  // Mock client store without registration support
  const mockClientStoreWithoutRegistration: OAuthRegisteredClientsStore = {
    async getClient(_clientId: string): Promise<OAuthClientInformationFull | undefined> {
      return undefined;
    }
    // No registerClient method
  };

  describe('Handler creation', () => {
    it('throws error if client store does not support registration', () => {
      const options: ClientRegistrationHandlerOptions = {
        clientsStore: mockClientStoreWithoutRegistration
      };

      expect(() => clientRegistrationHandler(options)).toThrow('does not support registering clients');
    });

    it('creates handler if client store supports registration', () => {
      const options: ClientRegistrationHandlerOptions = {
        clientsStore: mockClientStoreWithRegistration
      };

      expect(() => clientRegistrationHandler(options)).not.toThrow();
    });
  });

  describe('Request handling', () => {
    let app: express.Express;
    let spyRegisterClient: jest.SpyInstance;

    beforeEach(() => {
      // Setup express app with registration handler
      app = express();
      const options: ClientRegistrationHandlerOptions = {
        clientsStore: mockClientStoreWithRegistration,
        clientSecretExpirySeconds: 86400 // 1 day for testing
      };

      app.use('/register', clientRegistrationHandler(options));

      // Spy on the registerClient method
      spyRegisterClient = jest.spyOn(mockClientStoreWithRegistration, 'registerClient');
    });

    afterEach(() => {
      spyRegisterClient.mockRestore();
    });

    it('requires POST method', async () => {
      const response = await supertest(app)
        .get('/register')
        .send({
          redirect_uris: ['https://example.com/callback']
        });

      expect(response.status).toBe(405);
      expect(response.headers.allow).toBe('POST');
      expect(response.body).toEqual({
        error: "method_not_allowed",
        error_description: "The method GET is not allowed for this endpoint"
      });
      expect(spyRegisterClient).not.toHaveBeenCalled();
    });

    it('validates required client metadata', async () => {
      const response = await supertest(app)
        .post('/register')
        .send({
          // Missing redirect_uris (required)
          client_name: 'Test Client'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_client_metadata');
      expect(spyRegisterClient).not.toHaveBeenCalled();
    });

    it('validates redirect URIs format', async () => {
      const response = await supertest(app)
        .post('/register')
        .send({
          redirect_uris: ['invalid-url'] // Invalid URL format
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_client_metadata');
      expect(response.body.error_description).toContain('redirect_uris');
      expect(spyRegisterClient).not.toHaveBeenCalled();
    });

    it('successfully registers client with minimal metadata', async () => {
      const clientMetadata: OAuthClientMetadata = {
        redirect_uris: ['https://example.com/callback']
      };

      const response = await supertest(app)
        .post('/register')
        .send(clientMetadata);

      expect(response.status).toBe(201);

      // Verify the generated client information
      expect(response.body.client_id).toBeDefined();
      expect(response.body.client_secret).toBeDefined();
      expect(response.body.client_id_issued_at).toBeDefined();
      expect(response.body.client_secret_expires_at).toBeDefined();
      expect(response.body.redirect_uris).toEqual(['https://example.com/callback']);

      // Verify client was registered
      expect(spyRegisterClient).toHaveBeenCalledTimes(1);
    });

    it('sets client_secret to undefined for token_endpoint_auth_method=none', async () => {
      const clientMetadata: OAuthClientMetadata = {
        redirect_uris: ['https://example.com/callback'],
        token_endpoint_auth_method: 'none'
      };

      const response = await supertest(app)
        .post('/register')
        .send(clientMetadata);

      expect(response.status).toBe(201);
      expect(response.body.client_secret).toBeUndefined();
      expect(response.body.client_secret_expires_at).toBeUndefined();
    });
    
    it('sets client_secret_expires_at for public clients only', async () => {
      // Test for public client (token_endpoint_auth_method not 'none')
      const publicClientMetadata: OAuthClientMetadata = {
        redirect_uris: ['https://example.com/callback'],
        token_endpoint_auth_method: 'client_secret_basic'
      };

      const publicResponse = await supertest(app)
        .post('/register')
        .send(publicClientMetadata);

      expect(publicResponse.status).toBe(201);
      expect(publicResponse.body.client_secret).toBeDefined();
      expect(publicResponse.body.client_secret_expires_at).toBeDefined();
      
      // Test for non-public client (token_endpoint_auth_method is 'none')
      const nonPublicClientMetadata: OAuthClientMetadata = {
        redirect_uris: ['https://example.com/callback'],
        token_endpoint_auth_method: 'none'
      };

      const nonPublicResponse = await supertest(app)
        .post('/register')
        .send(nonPublicClientMetadata);

      expect(nonPublicResponse.status).toBe(201);
      expect(nonPublicResponse.body.client_secret).toBeUndefined();
      expect(nonPublicResponse.body.client_secret_expires_at).toBeUndefined();
    });

    it('sets expiry based on clientSecretExpirySeconds', async () => {
      // Create handler with custom expiry time
      const customApp = express();
      const options: ClientRegistrationHandlerOptions = {
        clientsStore: mockClientStoreWithRegistration,
        clientSecretExpirySeconds: 3600 // 1 hour
      };

      customApp.use('/register', clientRegistrationHandler(options));

      const response = await supertest(customApp)
        .post('/register')
        .send({
          redirect_uris: ['https://example.com/callback']
        });

      expect(response.status).toBe(201);

      // Verify the expiration time (~1 hour from now)
      const issuedAt = response.body.client_id_issued_at;
      const expiresAt = response.body.client_secret_expires_at;
      expect(expiresAt - issuedAt).toBe(3600);
    });

    it('sets no expiry when clientSecretExpirySeconds=0', async () => {
      // Create handler with no expiry
      const customApp = express();
      const options: ClientRegistrationHandlerOptions = {
        clientsStore: mockClientStoreWithRegistration,
        clientSecretExpirySeconds: 0 // No expiry
      };

      customApp.use('/register', clientRegistrationHandler(options));

      const response = await supertest(customApp)
        .post('/register')
        .send({
          redirect_uris: ['https://example.com/callback']
        });

      expect(response.status).toBe(201);
      expect(response.body.client_secret_expires_at).toBe(0);
    });

    it('sets no client_id when clientIdGeneration=false', async () => {
      // Create handler with no expiry
      const customApp = express();
      const options: ClientRegistrationHandlerOptions = {
        clientsStore: mockClientStoreWithRegistration,
        clientIdGeneration: false
      };

      customApp.use('/register', clientRegistrationHandler(options));

      const response = await supertest(customApp)
        .post('/register')
        .send({
          redirect_uris: ['https://example.com/callback']
        });

      expect(response.status).toBe(201);
      expect(response.body.client_id).toBeUndefined();
      expect(response.body.client_id_issued_at).toBeUndefined();
    });

    it('handles client with all metadata fields', async () => {
      const fullClientMetadata: OAuthClientMetadata = {
        redirect_uris: ['https://example.com/callback'],
        token_endpoint_auth_method: 'client_secret_basic',
        grant_types: ['authorization_code', 'refresh_token'],
        response_types: ['code'],
        client_name: 'Test Client',
        client_uri: 'https://example.com',
        logo_uri: 'https://example.com/logo.png',
        scope: 'profile email',
        contacts: ['dev@example.com'],
        tos_uri: 'https://example.com/tos',
        policy_uri: 'https://example.com/privacy',
        jwks_uri: 'https://example.com/jwks',
        software_id: 'test-software',
        software_version: '1.0.0'
      };

      const response = await supertest(app)
        .post('/register')
        .send(fullClientMetadata);

      expect(response.status).toBe(201);

      // Verify all metadata was preserved
      Object.entries(fullClientMetadata).forEach(([key, value]) => {
        expect(response.body[key]).toEqual(value);
      });
    });

    it('includes CORS headers in response', async () => {
      const response = await supertest(app)
        .post('/register')
        .set('Origin', 'https://example.com')
        .send({
          redirect_uris: ['https://example.com/callback']
        });

      expect(response.header['access-control-allow-origin']).toBe('*');
    });
  });
});


================================================
FILE: src/server/auth/handlers/register.ts
================================================
import express, { RequestHandler } from "express";
import { OAuthClientInformationFull, OAuthClientMetadataSchema } from "../../../shared/auth.js";
import crypto from 'node:crypto';
import cors from 'cors';
import { OAuthRegisteredClientsStore } from "../clients.js";
import { rateLimit, Options as RateLimitOptions } from "express-rate-limit";
import { allowedMethods } from "../middleware/allowedMethods.js";
import {
  InvalidClientMetadataError,
  ServerError,
  TooManyRequestsError,
  OAuthError
} from "../errors.js";

export type ClientRegistrationHandlerOptions = {
  /**
   * A store used to save information about dynamically registered OAuth clients.
   */
  clientsStore: OAuthRegisteredClientsStore;

  /**
   * The number of seconds after which to expire issued client secrets, or 0 to prevent expiration of client secrets (not recommended).
   * 
   * If not set, defaults to 30 days.
   */
  clientSecretExpirySeconds?: number;

  /**
   * Rate limiting configuration for the client registration endpoint.
   * Set to false to disable rate limiting for this endpoint.
   * Registration endpoints are particularly sensitive to abuse and should be rate limited.
   */
  rateLimit?: Partial<RateLimitOptions> | false;

  /**
   * Whether to generate a client ID before calling the client registration endpoint.
   *
   * If not set, defaults to true.
   */
  clientIdGeneration?: boolean;
};

const DEFAULT_CLIENT_SECRET_EXPIRY_SECONDS = 30 * 24 * 60 * 60; // 30 days

export function clientRegistrationHandler({
  clientsStore,
  clientSecretExpirySeconds = DEFAULT_CLIENT_SECRET_EXPIRY_SECONDS,
  rateLimit: rateLimitConfig,
  clientIdGeneration = true,
}: ClientRegistrationHandlerOptions): RequestHandler {
  if (!clientsStore.registerClient) {
    throw new Error("Client registration store does not support registering clients");
  }

  // Nested router so we can configure middleware and restrict HTTP method
  const router = express.Router();

  // Configure CORS to allow any origin, to make accessible to web-based MCP clients
  router.use(cors());

  router.use(allowedMethods(["POST"]));
  router.use(express.json());

  // Apply rate limiting unless explicitly disabled - stricter limits for registration
  if (rateLimitConfig !== false) {
    router.use(rateLimit({
      windowMs: 60 * 60 * 1000, // 1 hour
      max: 20, // 20 requests per hour - stricter as registration is sensitive
      standardHeaders: true,
      legacyHeaders: false,
      message: new TooManyRequestsError('You have exceeded the rate limit for client registration requests').toResponseObject(),
      ...rateLimitConfig
    }));
  }

  router.post("/", async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');

    try {
      const parseResult = OAuthClientMetadataSchema.safeParse(req.body);
      if (!parseResult.success) {
        throw new InvalidClientMetadataError(parseResult.error.message);
      }

      const clientMetadata = parseResult.data;
      const isPublicClient = clientMetadata.token_endpoint_auth_method === 'none'

      // Generate client credentials
      const clientSecret = isPublicClient
        ? undefined
        : crypto.randomBytes(32).toString('hex');
      const clientIdIssuedAt = Math.floor(Date.now() / 1000);

      // Calculate client secret expiry time
      const clientsDoExpire = clientSecretExpirySeconds > 0
      const secretExpiryTime = clientsDoExpire ? clientIdIssuedAt + clientSecretExpirySeconds : 0
      const clientSecretExpiresAt = isPublicClient ? undefined : secretExpiryTime

      let clientInfo: Omit<OAuthClientInformationFull, "client_id"> & { client_id?: string } = {
        ...clientMetadata,
        client_secret: clientSecret,
        client_secret_expires_at: clientSecretExpiresAt,
      };

      if (clientIdGeneration) {
        clientInfo.client_id = crypto.randomUUID();
        clientInfo.client_id_issued_at = clientIdIssuedAt;
      }

      clientInfo = await clientsStore.registerClient!(clientInfo);
      res.status(201).json(clientInfo);
    } catch (error) {
      if (error instanceof OAuthError) {
        const status = error instanceof ServerError ? 500 : 400;
        res.status(status).json(error.toResponseObject());
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.status(500).json(serverError.toResponseObject());
      }
    }
  });

  return router;
}


================================================
FILE: src/server/auth/handlers/revoke.test.ts
================================================
import { revocationHandler, RevocationHandlerOptions } from './revoke.js';
import { OAuthServerProvider, AuthorizationParams } from '../provider.js';
import { OAuthRegisteredClientsStore } from '../clients.js';
import { OAuthClientInformationFull, OAuthTokenRevocationRequest, OAuthTokens } from '../../../shared/auth.js';
import express, { Response } from 'express';
import supertest from 'supertest';
import { AuthInfo } from '../types.js';
import { InvalidTokenError } from '../errors.js';

describe('Revocation Handler', () => {
  // Mock client data
  const validClient: OAuthClientInformationFull = {
    client_id: 'valid-client',
    client_secret: 'valid-secret',
    redirect_uris: ['https://example.com/callback']
  };

  // Mock client store
  const mockClientStore: OAuthRegisteredClientsStore = {
    async getClient(clientId: string): Promise<OAuthClientInformationFull | undefined> {
      if (clientId === 'valid-client') {
        return validClient;
      }
      return undefined;
    }
  };

  // Mock provider with revocation capability
  const mockProviderWithRevocation: OAuthServerProvider = {
    clientsStore: mockClientStore,

    async authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void> {
      res.redirect('https://example.com/callback?code=mock_auth_code');
    },

    async challengeForAuthorizationCode(): Promise<string> {
      return 'mock_challenge';
    },

    async exchangeAuthorizationCode(): Promise<OAuthTokens> {
      return {
        access_token: 'mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'mock_refresh_token'
      };
    },

    async exchangeRefreshToken(): Promise<OAuthTokens> {
      return {
        access_token: 'new_mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'new_mock_refresh_token'
      };
    },

    async verifyAccessToken(token: string): Promise<AuthInfo> {
      if (token === 'valid_token') {
        return {
          token,
          clientId: 'valid-client',
          scopes: ['read', 'write'],
          expiresAt: Date.now() / 1000 + 3600
        };
      }
      throw new InvalidTokenError('Token is invalid or expired');
    },

    async revokeToken(_client: OAuthClientInformationFull, _request: OAuthTokenRevocationRequest): Promise<void> {
      // Success - do nothing in mock
    }
  };

  // Mock provider without revocation capability
  const mockProviderWithoutRevocation: OAuthServerProvider = {
    clientsStore: mockClientStore,

    async authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void> {
      res.redirect('https://example.com/callback?code=mock_auth_code');
    },

    async challengeForAuthorizationCode(): Promise<string> {
      return 'mock_challenge';
    },

    async exchangeAuthorizationCode(): Promise<OAuthTokens> {
      return {
        access_token: 'mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'mock_refresh_token'
      };
    },

    async exchangeRefreshToken(): Promise<OAuthTokens> {
      return {
        access_token: 'new_mock_access_token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'new_mock_refresh_token'
      };
    },

    async verifyAccessToken(token: string): Promise<AuthInfo> {
      if (token === 'valid_token') {
        return {
          token,
          clientId: 'valid-client',
          scopes: ['read', 'write'],
          expiresAt: Date.now() / 1000 + 3600
        };
      }
      throw new InvalidTokenError('Token is invalid or expired');
    }
    // No revokeToken method
  };

  describe('Handler creation', () => {
    it('throws error if provider does not support token revocation', () => {
      const options: RevocationHandlerOptions = { provider: mockProviderWithoutRevocation };
      expect(() => revocationHandler(options)).toThrow('does not support revoking tokens');
    });

    it('creates handler if provider supports token revocation', () => {
      const options: RevocationHandlerOptions = { provider: mockProviderWithRevocation };
      expect(() => revocationHandler(options)).not.toThrow();
    });
  });

  describe('Request handling', () => {
    let app: express.Express;
    let spyRevokeToken: jest.SpyInstance;

    beforeEach(() => {
      // Setup express app with revocation handler
      app = express();
      const options: RevocationHandlerOptions = { provider: mockProviderWithRevocation };
      app.use('/revoke', revocationHandler(options));

      // Spy on the revokeToken method
      spyRevokeToken = jest.spyOn(mockProviderWithRevocation, 'revokeToken');
    });

    afterEach(() => {
      spyRevokeToken.mockRestore();
    });

    it('requires POST method', async () => {
      const response = await supertest(app)
        .get('/revoke')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          token: 'token_to_revoke'
        });

      expect(response.status).toBe(405);
      expect(response.headers.allow).toBe('POST');
      expect(response.body).toEqual({
        error: "method_not_allowed",
        error_description: "The method GET is not allowed for this endpoint"
      });
      expect(spyRevokeToken).not.toHaveBeenCalled();
    });

    it('requires token parameter', async () => {
      const response = await supertest(app)
        .post('/revoke')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret'
          // Missing token
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_request');
      expect(spyRevokeToken).not.toHaveBeenCalled();
    });

    it('authenticates client before revoking token', async () => {
      const response = await supertest(app)
        .post('/revoke')
        .type('form')
        .send({
          client_id: 'invalid-client',
          client_secret: 'wrong-secret',
          token: 'token_to_revoke'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_client');
      expect(spyRevokeToken).not.toHaveBeenCalled();
    });

    it('successfully revokes token', async () => {
      const response = await supertest(app)
        .post('/revoke')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          token: 'token_to_revoke'
        });

      expect(response.status).toBe(200);
      expect(response.body).toEqual({}); // Empty response on success
      expect(spyRevokeToken).toHaveBeenCalledTimes(1);
      expect(spyRevokeToken).toHaveBeenCalledWith(validClient, {
        token: 'token_to_revoke'
      });
    });

    it('accepts optional token_type_hint', async () => {
      const response = await supertest(app)
        .post('/revoke')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          token: 'token_to_revoke',
          token_type_hint: 'refresh_token'
        });

      expect(response.status).toBe(200);
      expect(spyRevokeToken).toHaveBeenCalledWith(validClient, {
        token: 'token_to_revoke',
        token_type_hint: 'refresh_token'
      });
    });

    it('includes CORS headers in response', async () => {
      const response = await supertest(app)
        .post('/revoke')
        .type('form')
        .set('Origin', 'https://example.com')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          token: 'token_to_revoke'
        });

      expect(response.header['access-control-allow-origin']).toBe('*');
    });
  });
});


================================================
FILE: src/server/auth/handlers/revoke.ts
================================================
import { OAuthServerProvider } from "../provider.js";
import express, { RequestHandler } from "express";
import cors from "cors";
import { authenticateClient } from "../middleware/clientAuth.js";
import { OAuthTokenRevocationRequestSchema } from "../../../shared/auth.js";
import { rateLimit, Options as RateLimitOptions } from "express-rate-limit";
import { allowedMethods } from "../middleware/allowedMethods.js";
import {
  InvalidRequestError,
  ServerError,
  TooManyRequestsError,
  OAuthError,
} from "../errors.js";

export type RevocationHandlerOptions = {
  provider: OAuthServerProvider;
  /**
   * Rate limiting configuration for the token revocation endpoint.
   * Set to false to disable rate limiting for this endpoint.
   */
  rateLimit?: Partial<RateLimitOptions> | false;
};

export function revocationHandler({
  provider,
  rateLimit: rateLimitConfig,
}: RevocationHandlerOptions): RequestHandler {
  if (!provider.revokeToken) {
    throw new Error("Auth provider does not support revoking tokens");
  }

  // Nested router so we can configure middleware and restrict HTTP method
  const router = express.Router();

  // Configure CORS to allow any origin, to make accessible to web-based MCP clients
  router.use(cors());

  router.use(allowedMethods(["POST"]));
  router.use(express.urlencoded({ extended: false }));

  // Apply rate limiting unless explicitly disabled
  if (rateLimitConfig !== false) {
    router.use(
      rateLimit({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 50, // 50 requests per windowMs
        standardHeaders: true,
        legacyHeaders: false,
        message: new TooManyRequestsError(
          "You have exceeded the rate limit for token revocation requests"
        ).toResponseObject(),
        ...rateLimitConfig,
      })
    );
  }

  // Authenticate and extract client details
  router.use(authenticateClient({ clientsStore: provider.clientsStore }));

  router.post("/", async (req, res) => {
    res.setHeader("Cache-Control", "no-store");

    try {
      const parseResult = OAuthTokenRevocationRequestSchema.safeParse(req.body);
      if (!parseResult.success) {
        throw new InvalidRequestError(parseResult.error.message);
      }

      const client = req.client;
      if (!client) {
        // This should never happen
        throw new ServerError("Internal Server Error");
      }

      await provider.revokeToken!(client, parseResult.data);
      res.status(200).json({});
    } catch (error) {
      if (error instanceof OAuthError) {
        const status = error instanceof ServerError ? 500 : 400;
        res.status(status).json(error.toResponseObject());
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.status(500).json(serverError.toResponseObject());
      }
    }
  });

  return router;
}



================================================
FILE: src/server/auth/handlers/token.test.ts
================================================
import { tokenHandler, TokenHandlerOptions } from './token.js';
import { OAuthServerProvider, AuthorizationParams } from '../provider.js';
import { OAuthRegisteredClientsStore } from '../clients.js';
import { OAuthClientInformationFull, OAuthTokenRevocationRequest, OAuthTokens } from '../../../shared/auth.js';
import express, { Response } from 'express';
import supertest from 'supertest';
import * as pkceChallenge from 'pkce-challenge';
import { InvalidGrantError, InvalidTokenError } from '../errors.js';
import { AuthInfo } from '../types.js';
import { ProxyOAuthServerProvider } from '../providers/proxyProvider.js';

// Mock pkce-challenge
jest.mock('pkce-challenge', () => ({
  verifyChallenge: jest.fn().mockImplementation(async (verifier, challenge) => {
    return verifier === 'valid_verifier' && challenge === 'mock_challenge';
  })
}));

const mockTokens = {
    access_token: 'mock_access_token',
    token_type: 'bearer',
    expires_in: 3600,
    refresh_token: 'mock_refresh_token'
};

const mockTokensWithIdToken = {
    ...mockTokens,
    id_token: 'mock_id_token'
}

describe('Token Handler', () => {
  // Mock client data
  const validClient: OAuthClientInformationFull = {
    client_id: 'valid-client',
    client_secret: 'valid-secret',
    redirect_uris: ['https://example.com/callback']
  };

  // Mock client store
  const mockClientStore: OAuthRegisteredClientsStore = {
    async getClient(clientId: string): Promise<OAuthClientInformationFull | undefined> {
      if (clientId === 'valid-client') {
        return validClient;
      }
      return undefined;
    }
  };

  // Mock provider
  let mockProvider: OAuthServerProvider;
  let app: express.Express;

  beforeEach(() => {
    // Create fresh mocks for each test
    mockProvider = {
      clientsStore: mockClientStore,

      async authorize(client: OAuthClientInformationFull, params: AuthorizationParams, res: Response): Promise<void> {
        res.redirect('https://example.com/callback?code=mock_auth_code');
      },

      async challengeForAuthorizationCode(client: OAuthClientInformationFull, authorizationCode: string): Promise<string> {
        if (authorizationCode === 'valid_code') {
          return 'mock_challenge';
        } else if (authorizationCode === 'expired_code') {
          throw new InvalidGrantError('The authorization code has expired');
        }
        throw new InvalidGrantError('The authorization code is invalid');
      },

      async exchangeAuthorizationCode(client: OAuthClientInformationFull, authorizationCode: string): Promise<OAuthTokens> {
        if (authorizationCode === 'valid_code') {
          return mockTokens;
        }
        throw new InvalidGrantError('The authorization code is invalid or has expired');
      },

      async exchangeRefreshToken(client: OAuthClientInformationFull, refreshToken: string, scopes?: string[]): Promise<OAuthTokens> {
        if (refreshToken === 'valid_refresh_token') {
          const response: OAuthTokens = {
            access_token: 'new_mock_access_token',
            token_type: 'bearer',
            expires_in: 3600,
            refresh_token: 'new_mock_refresh_token'
          };

          if (scopes) {
            response.scope = scopes.join(' ');
          }

          return response;
        }
        throw new InvalidGrantError('The refresh token is invalid or has expired');
      },

      async verifyAccessToken(token: string): Promise<AuthInfo> {
        if (token === 'valid_token') {
          return {
            token,
            clientId: 'valid-client',
            scopes: ['read', 'write'],
            expiresAt: Date.now() / 1000 + 3600
          };
        }
        throw new InvalidTokenError('Token is invalid or expired');
      },

      async revokeToken(_client: OAuthClientInformationFull, _request: OAuthTokenRevocationRequest): Promise<void> {
        // Do nothing in mock
      }
    };

    // Mock PKCE verification
    (pkceChallenge.verifyChallenge as jest.Mock).mockImplementation(
      async (verifier: string, challenge: string) => {
        return verifier === 'valid_verifier' && challenge === 'mock_challenge';
      }
    );

    // Setup express app with token handler
    app = express();
    const options: TokenHandlerOptions = { provider: mockProvider };
    app.use('/token', tokenHandler(options));
  });

  describe('Basic request validation', () => {
    it('requires POST method', async () => {
      const response = await supertest(app)
        .get('/token')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code'
        });

      expect(response.status).toBe(405);
      expect(response.headers.allow).toBe('POST');
      expect(response.body).toEqual({
        error: "method_not_allowed",
        error_description: "The method GET is not allowed for this endpoint"
      });
    });

    it('requires grant_type parameter', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret'
          // Missing grant_type
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_request');
    });

    it('rejects unsupported grant types', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'password' // Unsupported grant type
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('unsupported_grant_type');
    });
  });

  describe('Client authentication', () => {
    it('requires valid client credentials', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'invalid-client',
          client_secret: 'wrong-secret',
          grant_type: 'authorization_code'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_client');
    });

    it('accepts valid client credentials', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          code: 'valid_code',
          code_verifier: 'valid_verifier'
        });

      expect(response.status).toBe(200);
    });
  });

  describe('Authorization code grant', () => {
    it('requires code parameter', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          // Missing code
          code_verifier: 'valid_verifier'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_request');
    });

    it('requires code_verifier parameter', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          code: 'valid_code'
          // Missing code_verifier
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_request');
    });

    it('verifies code_verifier against challenge', async () => {
      // Setup invalid verifier
      (pkceChallenge.verifyChallenge as jest.Mock).mockResolvedValueOnce(false);

      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          code: 'valid_code',
          code_verifier: 'invalid_verifier'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_grant');
      expect(response.body.error_description).toContain('code_verifier');
    });

    it('rejects expired or invalid authorization codes', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          code: 'expired_code',
          code_verifier: 'valid_verifier'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_grant');
    });

    it('returns tokens for valid code exchange', async () => {
      const mockExchangeCode = jest.spyOn(mockProvider, 'exchangeAuthorizationCode');
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          resource: 'https://api.example.com/resource',
          grant_type: 'authorization_code',
          code: 'valid_code',
          code_verifier: 'valid_verifier'
        });

      expect(response.status).toBe(200);
      expect(response.body.access_token).toBe('mock_access_token');
      expect(response.body.token_type).toBe('bearer');
      expect(response.body.expires_in).toBe(3600);
      expect(response.body.refresh_token).toBe('mock_refresh_token');
      expect(mockExchangeCode).toHaveBeenCalledWith(
        validClient,
        'valid_code',
        undefined, // code_verifier is undefined after PKCE validation
        undefined, // redirect_uri
        new URL('https://api.example.com/resource') // resource parameter
      );
    });

      it('returns id token in code exchange if provided', async () => {
          mockProvider.exchangeAuthorizationCode = async (client: OAuthClientInformationFull, authorizationCode: string): Promise<OAuthTokens> => {
              if (authorizationCode === 'valid_code') {
                  return mockTokensWithIdToken;
              }
              throw new InvalidGrantError('The authorization code is invalid or has expired');
          };

          const response = await supertest(app)
              .post('/token')
              .type('form')
              .send({
                  client_id: 'valid-client',
                  client_secret: 'valid-secret',
                  grant_type: 'authorization_code',
                  code: 'valid_code',
                  code_verifier: 'valid_verifier'
              });

          expect(response.status).toBe(200);
          expect(response.body.id_token).toBe('mock_id_token');
      });

    it('passes through code verifier when using proxy provider', async () => {
      const originalFetch = global.fetch;

      try {
        global.fetch = jest.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockTokens)
        });

        const proxyProvider = new ProxyOAuthServerProvider({
          endpoints: {
            authorizationUrl: 'https://example.com/authorize',
            tokenUrl: 'https://example.com/token'
          },
          verifyAccessToken: async (token) => ({
            token,
            clientId: 'valid-client',
            scopes: ['read', 'write'],
            expiresAt: Date.now() / 1000 + 3600
          }),
          getClient: async (clientId) => clientId === 'valid-client' ? validClient : undefined
        });

        const proxyApp = express();
        const options: TokenHandlerOptions = { provider: proxyProvider };
        proxyApp.use('/token', tokenHandler(options));

        const response = await supertest(proxyApp)
          .post('/token')
          .type('form')
          .send({
            client_id: 'valid-client',
            client_secret: 'valid-secret',
            grant_type: 'authorization_code',
            code: 'valid_code',
            code_verifier: 'any_verifier',
            redirect_uri: 'https://example.com/callback'
          });

        expect(response.status).toBe(200);
        expect(response.body.access_token).toBe('mock_access_token');

        expect(global.fetch).toHaveBeenCalledWith(
          'https://example.com/token',
          expect.objectContaining({
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: expect.stringContaining('code_verifier=any_verifier')
          })
        );
      } finally {
        global.fetch = originalFetch;
      }
    });

    it('passes through redirect_uri when using proxy provider', async () => {
      const originalFetch = global.fetch;

      try {
        global.fetch = jest.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockTokens)
        });

        const proxyProvider = new ProxyOAuthServerProvider({
          endpoints: {
            authorizationUrl: 'https://example.com/authorize',
            tokenUrl: 'https://example.com/token'
          },
          verifyAccessToken: async (token) => ({
            token,
            clientId: 'valid-client',
            scopes: ['read', 'write'],
            expiresAt: Date.now() / 1000 + 3600
          }),
          getClient: async (clientId) => clientId === 'valid-client' ? validClient : undefined
        });

        const proxyApp = express();
        const options: TokenHandlerOptions = { provider: proxyProvider };
        proxyApp.use('/token', tokenHandler(options));

        const redirectUri = 'https://example.com/callback';
        const response = await supertest(proxyApp)
          .post('/token')
          .type('form')
          .send({
            client_id: 'valid-client',
            client_secret: 'valid-secret',
            grant_type: 'authorization_code',
            code: 'valid_code',
            code_verifier: 'any_verifier',
            redirect_uri: redirectUri
          });

        expect(response.status).toBe(200);
        expect(response.body.access_token).toBe('mock_access_token');

        expect(global.fetch).toHaveBeenCalledWith(
          'https://example.com/token',
          expect.objectContaining({
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: expect.stringContaining(`redirect_uri=${encodeURIComponent(redirectUri)}`)
          })
        );
      } finally {
        global.fetch = originalFetch;
      }
    });
  });

  describe('Refresh token grant', () => {
    it('requires refresh_token parameter', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'refresh_token'
          // Missing refresh_token
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_request');
    });

    it('rejects invalid refresh tokens', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'refresh_token',
          refresh_token: 'invalid_refresh_token'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toBe('invalid_grant');
    });

    it('returns new tokens for valid refresh token', async () => {
      const mockExchangeRefresh = jest.spyOn(mockProvider, 'exchangeRefreshToken');
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          resource: 'https://api.example.com/resource',
          grant_type: 'refresh_token',
          refresh_token: 'valid_refresh_token'
        });

      expect(response.status).toBe(200);
      expect(response.body.access_token).toBe('new_mock_access_token');
      expect(response.body.token_type).toBe('bearer');
      expect(response.body.expires_in).toBe(3600);
      expect(response.body.refresh_token).toBe('new_mock_refresh_token');
      expect(mockExchangeRefresh).toHaveBeenCalledWith(
        validClient,
        'valid_refresh_token',
        undefined, // scopes
        new URL('https://api.example.com/resource') // resource parameter
      );
    });

    it('respects requested scopes on refresh', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'refresh_token',
          refresh_token: 'valid_refresh_token',
          scope: 'profile email'
        });

      expect(response.status).toBe(200);
      expect(response.body.scope).toBe('profile email');
    });
  });

  describe('CORS support', () => {
    it('includes CORS headers in response', async () => {
      const response = await supertest(app)
        .post('/token')
        .type('form')
        .set('Origin', 'https://example.com')
        .send({
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          grant_type: 'authorization_code',
          code: 'valid_code',
          code_verifier: 'valid_verifier'
        });

      expect(response.header['access-control-allow-origin']).toBe('*');
    });
  });
});


================================================
FILE: src/server/auth/handlers/token.ts
================================================
import { z } from "zod";
import express, { RequestHandler } from "express";
import { OAuthServerProvider } from "../provider.js";
import cors from "cors";
import { verifyChallenge } from "pkce-challenge";
import { authenticateClient } from "../middleware/clientAuth.js";
import { rateLimit, Options as RateLimitOptions } from "express-rate-limit";
import { allowedMethods } from "../middleware/allowedMethods.js";
import {
  InvalidRequestError,
  InvalidGrantError,
  UnsupportedGrantTypeError,
  ServerError,
  TooManyRequestsError,
  OAuthError
} from "../errors.js";

export type TokenHandlerOptions = {
  provider: OAuthServerProvider;
  /**
   * Rate limiting configuration for the token endpoint.
   * Set to false to disable rate limiting for this endpoint.
   */
  rateLimit?: Partial<RateLimitOptions> | false;
};

const TokenRequestSchema = z.object({
  grant_type: z.string(),
});

const AuthorizationCodeGrantSchema = z.object({
  code: z.string(),
  code_verifier: z.string(),
  redirect_uri: z.string().optional(),
  resource: z.string().url().optional(),
});

const RefreshTokenGrantSchema = z.object({
  refresh_token: z.string(),
  scope: z.string().optional(),
  resource: z.string().url().optional(),
});

export function tokenHandler({ provider, rateLimit: rateLimitConfig }: TokenHandlerOptions): RequestHandler {
  // Nested router so we can configure middleware and restrict HTTP method
  const router = express.Router();

  // Configure CORS to allow any origin, to make accessible to web-based MCP clients
  router.use(cors());

  router.use(allowedMethods(["POST"]));
  router.use(express.urlencoded({ extended: false }));

  // Apply rate limiting unless explicitly disabled
  if (rateLimitConfig !== false) {
    router.use(rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 50, // 50 requests per windowMs 
      standardHeaders: true,
      legacyHeaders: false,
      message: new TooManyRequestsError('You have exceeded the rate limit for token requests').toResponseObject(),
      ...rateLimitConfig
    }));
  }

  // Authenticate and extract client details
  router.use(authenticateClient({ clientsStore: provider.clientsStore }));

  router.post("/", async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');

    try {
      const parseResult = TokenRequestSchema.safeParse(req.body);
      if (!parseResult.success) {
        throw new InvalidRequestError(parseResult.error.message);
      }

      const { grant_type } = parseResult.data;

      const client = req.client;
      if (!client) {
        // This should never happen
        throw new ServerError("Internal Server Error");
      }

      switch (grant_type) {
        case "authorization_code": {
          const parseResult = AuthorizationCodeGrantSchema.safeParse(req.body);
          if (!parseResult.success) {
            throw new InvalidRequestError(parseResult.error.message);
          }

          const { code, code_verifier, redirect_uri, resource } = parseResult.data;

          const skipLocalPkceValidation = provider.skipLocalPkceValidation;

          // Perform local PKCE validation unless explicitly skipped 
          // (e.g. to validate code_verifier in upstream server)
          if (!skipLocalPkceValidation) {
            const codeChallenge = await provider.challengeForAuthorizationCode(client, code);
            if (!(await verifyChallenge(code_verifier, codeChallenge))) {
              throw new InvalidGrantError("code_verifier does not match the challenge");
            }
          }

          // Passes the code_verifier to the provider if PKCE validation didn't occur locally
          const tokens = await provider.exchangeAuthorizationCode(
            client, 
            code, 
            skipLocalPkceValidation ? code_verifier : undefined,
            redirect_uri,
            resource ? new URL(resource) : undefined
          );
          res.status(200).json(tokens);
          break;
        }

        case "refresh_token": {
          const parseResult = RefreshTokenGrantSchema.safeParse(req.body);
          if (!parseResult.success) {
            throw new InvalidRequestError(parseResult.error.message);
          }

          const { refresh_token, scope, resource } = parseResult.data;

          const scopes = scope?.split(" ");
          const tokens = await provider.exchangeRefreshToken(client, refresh_token, scopes, resource ? new URL(resource) : undefined);
          res.status(200).json(tokens);
          break;
        }

        // Not supported right now
        //case "client_credentials":

        default:
          throw new UnsupportedGrantTypeError(
            "The grant type is not supported by this authorization server."
          );
      }
    } catch (error) {
      if (error instanceof OAuthError) {
        const status = error instanceof ServerError ? 500 : 400;
        res.status(status).json(error.toResponseObject());
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.status(500).json(serverError.toResponseObject());
      }
    }
  });

  return router;
}


================================================
FILE: src/server/auth/middleware/allowedMethods.test.ts
================================================
import { allowedMethods } from "./allowedMethods.js";
import express, { Request, Response } from "express";
import request from "supertest";

describe("allowedMethods", () => {
  let app: express.Express;

  beforeEach(() => {
    app = express();

    // Set up a test router with a GET handler and 405 middleware
    const router = express.Router();

    router.get("/test", (req, res) => {
      res.status(200).send("GET success");
    });

    // Add method not allowed middleware for all other methods
    router.all("/test", allowedMethods(["GET"]));

    app.use(router);
  });

  test("allows specified HTTP method", async () => {
    const response = await request(app).get("/test");
    expect(response.status).toBe(200);
    expect(response.text).toBe("GET success");
  });

  test("returns 405 for unspecified HTTP methods", async () => {
    const methods = ["post", "put", "delete", "patch"];

    for (const method of methods) {
      // @ts-expect-error - dynamic method call
      const response = await request(app)[method]("/test");
      expect(response.status).toBe(405);
      expect(response.body).toEqual({
        error: "method_not_allowed",
        error_description: `The method ${method.toUpperCase()} is not allowed for this endpoint`
      });
    }
  });

  test("includes Allow header with specified methods", async () => {
    const response = await request(app).post("/test");
    expect(response.headers.allow).toBe("GET");
  });

  test("works with multiple allowed methods", async () => {
    const multiMethodApp = express();
    const router = express.Router();

    router.get("/multi", (req: Request, res: Response) => {
      res.status(200).send("GET");
    });
    router.post("/multi", (req: Request, res: Response) => {
      res.status(200).send("POST");
    });
    router.all("/multi", allowedMethods(["GET", "POST"]));

    multiMethodApp.use(router);

    // Allowed methods should work
    const getResponse = await request(multiMethodApp).get("/multi");
    expect(getResponse.status).toBe(200);

    const postResponse = await request(multiMethodApp).post("/multi");
    expect(postResponse.status).toBe(200);

    // Unallowed methods should return 405
    const putResponse = await request(multiMethodApp).put("/multi");
    expect(putResponse.status).toBe(405);
    expect(putResponse.headers.allow).toBe("GET, POST");
  });
});


================================================
FILE: src/server/auth/middleware/allowedMethods.ts
================================================
import { RequestHandler } from "express";
import { MethodNotAllowedError } from "../errors.js";

/**
 * Middleware to handle unsupported HTTP methods with a 405 Method Not Allowed response.
 * 
 * @param allowedMethods Array of allowed HTTP methods for this endpoint (e.g., ['GET', 'POST'])
 * @returns Express middleware that returns a 405 error if method not in allowed list
 */
export function allowedMethods(allowedMethods: string[]): RequestHandler {
  return (req, res, next) => {
    if (allowedMethods.includes(req.method)) {
      next();
      return;
    }

    const error = new MethodNotAllowedError(`The method ${req.method} is not allowed for this endpoint`);
    res.status(405)
      .set('Allow', allowedMethods.join(', '))
      .json(error.toResponseObject());
  };
}


================================================
FILE: src/server/auth/middleware/bearerAuth.test.ts
================================================
import { Request, Response } from "express";
import { requireBearerAuth } from "./bearerAuth.js";
import { AuthInfo } from "../types.js";
import { InsufficientScopeError, InvalidTokenError, CustomOAuthError, ServerError } from "../errors.js";
import { OAuthTokenVerifier } from "../provider.js";

// Mock verifier
const mockVerifyAccessToken = jest.fn();
const mockVerifier: OAuthTokenVerifier = {
  verifyAccessToken: mockVerifyAccessToken,
};

describe("requireBearerAuth middleware", () => {
  let mockRequest: Partial<Request>;
  let mockResponse: Partial<Response>;
  let nextFunction: jest.Mock;

  beforeEach(() => {
    mockRequest = {
      headers: {},
    };
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn(),
      set: jest.fn().mockReturnThis(),
    };
    nextFunction = jest.fn();
    jest.spyOn(console, 'error').mockImplementation(() => {});
  })

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should call next when token is valid", async () => {
    const validAuthInfo: AuthInfo = {
      token: "valid-token",
      clientId: "client-123",
      scopes: ["read", "write"],
      expiresAt: Math.floor(Date.now() / 1000) + 3600, // Token expires in an hour
    };
    mockVerifyAccessToken.mockResolvedValue(validAuthInfo);

    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockRequest.auth).toEqual(validAuthInfo);
    expect(nextFunction).toHaveBeenCalled();
    expect(mockResponse.status).not.toHaveBeenCalled();
    expect(mockResponse.json).not.toHaveBeenCalled();
  });
  
  it.each([
    [100], // Token expired 100 seconds ago
    [0], // Token expires at the same time as now
  ])("should reject expired tokens (expired %s seconds ago)", async (expiredSecondsAgo: number) => {
    const expiresAt = Math.floor(Date.now() / 1000) - expiredSecondsAgo;
    const expiredAuthInfo: AuthInfo = {
      token: "expired-token",
      clientId: "client-123",
      scopes: ["read", "write"],
      expiresAt
    };
    mockVerifyAccessToken.mockResolvedValue(expiredAuthInfo);

    mockRequest.headers = {
      authorization: "Bearer expired-token",
    };

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("expired-token");
    expect(mockResponse.status).toHaveBeenCalledWith(401);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="invalid_token"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "invalid_token", error_description: "Token has expired" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it.each([
    [undefined], // Token has no expiration time
    [NaN], // Token has no expiration time
  ])("should reject tokens with no expiration time (expiresAt: %s)", async (expiresAt: number | undefined) => {
    const noExpirationAuthInfo: AuthInfo = {
      token: "no-expiration-token",
      clientId: "client-123",
      scopes: ["read", "write"],
      expiresAt
    };
    mockVerifyAccessToken.mockResolvedValue(noExpirationAuthInfo);

    mockRequest.headers = {
      authorization: "Bearer expired-token",
    };

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("expired-token");
    expect(mockResponse.status).toHaveBeenCalledWith(401);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="invalid_token"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "invalid_token", error_description: "Token has no expiration time" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should accept non-expired tokens", async () => {
    const nonExpiredAuthInfo: AuthInfo = {
      token: "valid-token",
      clientId: "client-123",
      scopes: ["read", "write"],
      expiresAt: Math.floor(Date.now() / 1000) + 3600, // Token expires in an hour
    };
    mockVerifyAccessToken.mockResolvedValue(nonExpiredAuthInfo);

    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockRequest.auth).toEqual(nonExpiredAuthInfo);
    expect(nextFunction).toHaveBeenCalled();
    expect(mockResponse.status).not.toHaveBeenCalled();
    expect(mockResponse.json).not.toHaveBeenCalled();
  });

  it("should require specific scopes when configured", async () => {
    const authInfo: AuthInfo = {
      token: "valid-token",
      clientId: "client-123",
      scopes: ["read"],
    };
    mockVerifyAccessToken.mockResolvedValue(authInfo);

    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    const middleware = requireBearerAuth({
      verifier: mockVerifier,
      requiredScopes: ["read", "write"]
    });

    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockResponse.status).toHaveBeenCalledWith(403);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="insufficient_scope"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "insufficient_scope", error_description: "Insufficient scope" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should accept token with all required scopes", async () => {
    const authInfo: AuthInfo = {
      token: "valid-token",
      clientId: "client-123",
      scopes: ["read", "write", "admin"],
      expiresAt: Math.floor(Date.now() / 1000) + 3600, // Token expires in an hour
    };
    mockVerifyAccessToken.mockResolvedValue(authInfo);

    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    const middleware = requireBearerAuth({
      verifier: mockVerifier,
      requiredScopes: ["read", "write"]
    });

    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockRequest.auth).toEqual(authInfo);
    expect(nextFunction).toHaveBeenCalled();
    expect(mockResponse.status).not.toHaveBeenCalled();
    expect(mockResponse.json).not.toHaveBeenCalled();
  });

  it("should return 401 when no Authorization header is present", async () => {
    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).not.toHaveBeenCalled();
    expect(mockResponse.status).toHaveBeenCalledWith(401);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="invalid_token"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "invalid_token", error_description: "Missing Authorization header" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should return 401 when Authorization header format is invalid", async () => {
    mockRequest.headers = {
      authorization: "InvalidFormat",
    };

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).not.toHaveBeenCalled();
    expect(mockResponse.status).toHaveBeenCalledWith(401);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="invalid_token"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: "invalid_token",
        error_description: "Invalid Authorization header format, expected 'Bearer TOKEN'"
      })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should return 401 when token verification fails with InvalidTokenError", async () => {
    mockRequest.headers = {
      authorization: "Bearer invalid-token",
    };

    mockVerifyAccessToken.mockRejectedValue(new InvalidTokenError("Token expired"));

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("invalid-token");
    expect(mockResponse.status).toHaveBeenCalledWith(401);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="invalid_token"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "invalid_token", error_description: "Token expired" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should return 403 when access token has insufficient scopes", async () => {
    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    mockVerifyAccessToken.mockRejectedValue(new InsufficientScopeError("Required scopes: read, write"));

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockResponse.status).toHaveBeenCalledWith(403);
    expect(mockResponse.set).toHaveBeenCalledWith(
      "WWW-Authenticate",
      expect.stringContaining('Bearer error="insufficient_scope"')
    );
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "insufficient_scope", error_description: "Required scopes: read, write" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should return 500 when a ServerError occurs", async () => {
    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    mockVerifyAccessToken.mockRejectedValue(new ServerError("Internal server issue"));

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockResponse.status).toHaveBeenCalledWith(500);
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "server_error", error_description: "Internal server issue" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should return 400 for generic OAuthError", async () => {
    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    mockVerifyAccessToken.mockRejectedValue(new CustomOAuthError("custom_error", "Some OAuth error"));

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockResponse.status).toHaveBeenCalledWith(400);
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "custom_error", error_description: "Some OAuth error" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  it("should return 500 when unexpected error occurs", async () => {
    mockRequest.headers = {
      authorization: "Bearer valid-token",
    };

    mockVerifyAccessToken.mockRejectedValue(new Error("Unexpected error"));

    const middleware = requireBearerAuth({ verifier: mockVerifier });
    await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

    expect(mockVerifyAccessToken).toHaveBeenCalledWith("valid-token");
    expect(mockResponse.status).toHaveBeenCalledWith(500);
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({ error: "server_error", error_description: "Internal Server Error" })
    );
    expect(nextFunction).not.toHaveBeenCalled();
  });

  describe("with resourceMetadataUrl", () => {
    const resourceMetadataUrl = "https://api.example.com/.well-known/oauth-protected-resource";

    it("should include resource_metadata in WWW-Authenticate header for 401 responses", async () => {
      mockRequest.headers = {};

      const middleware = requireBearerAuth({ verifier: mockVerifier, resourceMetadataUrl });
      await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.status).toHaveBeenCalledWith(401);
      expect(mockResponse.set).toHaveBeenCalledWith(
        "WWW-Authenticate",
        `Bearer error="invalid_token", error_description="Missing Authorization header", resource_metadata="${resourceMetadataUrl}"`
      );
      expect(nextFunction).not.toHaveBeenCalled();
    });

    it("should include resource_metadata in WWW-Authenticate header when token verification fails", async () => {
      mockRequest.headers = {
        authorization: "Bearer invalid-token",
      };

      mockVerifyAccessToken.mockRejectedValue(new InvalidTokenError("Token expired"));

      const middleware = requireBearerAuth({ verifier: mockVerifier, resourceMetadataUrl });
      await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.status).toHaveBeenCalledWith(401);
      expect(mockResponse.set).toHaveBeenCalledWith(
        "WWW-Authenticate",
        `Bearer error="invalid_token", error_description="Token expired", resource_metadata="${resourceMetadataUrl}"`
      );
      expect(nextFunction).not.toHaveBeenCalled();
    });

    it("should include resource_metadata in WWW-Authenticate header for insufficient scope errors", async () => {
      mockRequest.headers = {
        authorization: "Bearer valid-token",
      };

      mockVerifyAccessToken.mockRejectedValue(new InsufficientScopeError("Required scopes: admin"));

      const middleware = requireBearerAuth({ verifier: mockVerifier, resourceMetadataUrl });
      await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.status).toHaveBeenCalledWith(403);
      expect(mockResponse.set).toHaveBeenCalledWith(
        "WWW-Authenticate",
        `Bearer error="insufficient_scope", error_description="Required scopes: admin", resource_metadata="${resourceMetadataUrl}"`
      );
      expect(nextFunction).not.toHaveBeenCalled();
    });

    it("should include resource_metadata when token is expired", async () => {
      const expiredAuthInfo: AuthInfo = {
        token: "expired-token",
        clientId: "client-123",
        scopes: ["read", "write"],
        expiresAt: Math.floor(Date.now() / 1000) - 100,
      };
      mockVerifyAccessToken.mockResolvedValue(expiredAuthInfo);

      mockRequest.headers = {
        authorization: "Bearer expired-token",
      };

      const middleware = requireBearerAuth({ verifier: mockVerifier, resourceMetadataUrl });
      await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.status).toHaveBeenCalledWith(401);
      expect(mockResponse.set).toHaveBeenCalledWith(
        "WWW-Authenticate",
        `Bearer error="invalid_token", error_description="Token has expired", resource_metadata="${resourceMetadataUrl}"`
      );
      expect(nextFunction).not.toHaveBeenCalled();
    });

    it("should include resource_metadata when scope check fails", async () => {
      const authInfo: AuthInfo = {
        token: "valid-token",
        clientId: "client-123",
        scopes: ["read"],
      };
      mockVerifyAccessToken.mockResolvedValue(authInfo);

      mockRequest.headers = {
        authorization: "Bearer valid-token",
      };

      const middleware = requireBearerAuth({
        verifier: mockVerifier,
        requiredScopes: ["read", "write"],
        resourceMetadataUrl
      });

      await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.status).toHaveBeenCalledWith(403);
      expect(mockResponse.set).toHaveBeenCalledWith(
        "WWW-Authenticate",
        `Bearer error="insufficient_scope", error_description="Insufficient scope", resource_metadata="${resourceMetadataUrl}"`
      );
      expect(nextFunction).not.toHaveBeenCalled();
    });

    it("should not affect server errors (no WWW-Authenticate header)", async () => {
      mockRequest.headers = {
        authorization: "Bearer valid-token",
      };

      mockVerifyAccessToken.mockRejectedValue(new ServerError("Internal server issue"));

      const middleware = requireBearerAuth({ verifier: mockVerifier, resourceMetadataUrl });
      await middleware(mockRequest as Request, mockResponse as Response, nextFunction);

      expect(mockResponse.status).toHaveBeenCalledWith(500);
      expect(mockResponse.set).not.toHaveBeenCalledWith("WWW-Authenticate", expect.anything());
      expect(nextFunction).not.toHaveBeenCalled();
    });
  });
});



================================================
FILE: src/server/auth/middleware/bearerAuth.ts
================================================
import { RequestHandler } from "express";
import { InsufficientScopeError, InvalidTokenError, OAuthError, ServerError } from "../errors.js";
import { OAuthTokenVerifier } from "../provider.js";
import { AuthInfo } from "../types.js";

export type BearerAuthMiddlewareOptions = {
  /**
   * A provider used to verify tokens.
   */
  verifier: OAuthTokenVerifier;

  /**
   * Optional scopes that the token must have.
   */
  requiredScopes?: string[];

  /**
   * Optional resource metadata URL to include in WWW-Authenticate header.
   */
  resourceMetadataUrl?: string;
};

declare module "express-serve-static-core" {
  interface Request {
    /**
     * Information about the validated access token, if the `requireBearerAuth` middleware was used.
     */
    auth?: AuthInfo;
  }
}

/**
 * Middleware that requires a valid Bearer token in the Authorization header.
 *
 * This will validate the token with the auth provider and add the resulting auth info to the request object.
 *
 * If resourceMetadataUrl is provided, it will be included in the WWW-Authenticate header
 * for 401 responses as per the OAuth 2.0 Protected Resource Metadata spec.
 */
export function requireBearerAuth({ verifier, requiredScopes = [], resourceMetadataUrl }: BearerAuthMiddlewareOptions): RequestHandler {
  return async (req, res, next) => {
    try {
      const authHeader = req.headers.authorization;
      if (!authHeader) {
        throw new InvalidTokenError("Missing Authorization header");
      }

      const [type, token] = authHeader.split(' ');
      if (type.toLowerCase() !== 'bearer' || !token) {
        throw new InvalidTokenError("Invalid Authorization header format, expected 'Bearer TOKEN'");
      }

      const authInfo = await verifier.verifyAccessToken(token);

      // Check if token has the required scopes (if any)
      if (requiredScopes.length > 0) {
        const hasAllScopes = requiredScopes.every(scope =>
          authInfo.scopes.includes(scope)
        );

        if (!hasAllScopes) {
          throw new InsufficientScopeError("Insufficient scope");
        }
      }

      // Check if the token is set to expire or if it is expired
      if (typeof authInfo.expiresAt !== 'number' || isNaN(authInfo.expiresAt)) {
        throw new InvalidTokenError("Token has no expiration time");
      } else if (authInfo.expiresAt < Date.now() / 1000) {
        throw new InvalidTokenError("Token has expired");
      }

      req.auth = authInfo;
      next();
    } catch (error) {
      if (error instanceof InvalidTokenError) {
        const wwwAuthValue = resourceMetadataUrl
          ? `Bearer error="${error.errorCode}", error_description="${error.message}", resource_metadata="${resourceMetadataUrl}"`
          : `Bearer error="${error.errorCode}", error_description="${error.message}"`;
        res.set("WWW-Authenticate", wwwAuthValue);
        res.status(401).json(error.toResponseObject());
      } else if (error instanceof InsufficientScopeError) {
        const wwwAuthValue = resourceMetadataUrl
          ? `Bearer error="${error.errorCode}", error_description="${error.message}", resource_metadata="${resourceMetadataUrl}"`
          : `Bearer error="${error.errorCode}", error_description="${error.message}"`;
        res.set("WWW-Authenticate", wwwAuthValue);
        res.status(403).json(error.toResponseObject());
      } else if (error instanceof ServerError) {
        res.status(500).json(error.toResponseObject());
      } else if (error instanceof OAuthError) {
        res.status(400).json(error.toResponseObject());
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.status(500).json(serverError.toResponseObject());
      }
    }
  };
}



================================================
FILE: src/server/auth/middleware/clientAuth.test.ts
================================================
import { authenticateClient, ClientAuthenticationMiddlewareOptions } from './clientAuth.js';
import { OAuthRegisteredClientsStore } from '../clients.js';
import { OAuthClientInformationFull } from '../../../shared/auth.js';
import express from 'express';
import supertest from 'supertest';

describe('clientAuth middleware', () => {
  // Mock client store
  const mockClientStore: OAuthRegisteredClientsStore = {
    async getClient(clientId: string): Promise<OAuthClientInformationFull | undefined> {
      if (clientId === 'valid-client') {
        return {
          client_id: 'valid-client',
          client_secret: 'valid-secret',
          redirect_uris: ['https://example.com/callback']
        };
      } else if (clientId === 'expired-client') {
        // Client with no secret
        return {
          client_id: 'expired-client',
          redirect_uris: ['https://example.com/callback']
        };
      } else if (clientId === 'client-with-expired-secret') {
        // Client with an expired secret
        return {
          client_id: 'client-with-expired-secret',
          client_secret: 'expired-secret',
          client_secret_expires_at: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
          redirect_uris: ['https://example.com/callback']
        };
      }
      return undefined;
    }
  };

  // Setup Express app with middleware
  let app: express.Express;
  let options: ClientAuthenticationMiddlewareOptions;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    
    options = {
      clientsStore: mockClientStore
    };

    // Setup route with client auth
    app.post('/protected', authenticateClient(options), (req, res) => {
      res.status(200).json({ success: true, client: req.client });
    });
  });

  it('authenticates valid client credentials', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_id: 'valid-client',
        client_secret: 'valid-secret'
      });

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.client.client_id).toBe('valid-client');
  });

  it('rejects invalid client_id', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_id: 'non-existent-client',
        client_secret: 'some-secret'
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('invalid_client');
    expect(response.body.error_description).toBe('Invalid client_id');
  });

  it('rejects invalid client_secret', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_id: 'valid-client',
        client_secret: 'wrong-secret'
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('invalid_client');
    expect(response.body.error_description).toBe('Invalid client_secret');
  });

  it('rejects missing client_id', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_secret: 'valid-secret'
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('invalid_request');
  });

  it('allows missing client_secret if client has none', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_id: 'expired-client'
      });

    // Since the client has no secret, this should pass without providing one
    expect(response.status).toBe(200);
  });
  
  it('rejects request when client secret has expired', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_id: 'client-with-expired-secret',
        client_secret: 'expired-secret'
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('invalid_client');
    expect(response.body.error_description).toBe('Client secret has expired');
  });

  it('handles malformed request body', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send('not-json-format');

    expect(response.status).toBe(400);
  });

  // Testing request with extra fields to ensure they're ignored
  it('ignores extra fields in request', async () => {
    const response = await supertest(app)
      .post('/protected')
      .send({
        client_id: 'valid-client',
        client_secret: 'valid-secret',
        extra_field: 'should be ignored'
      });

    expect(response.status).toBe(200);
  });
});


================================================
FILE: src/server/auth/middleware/clientAuth.ts
================================================
import { z } from "zod";
import { RequestHandler } from "express";
import { OAuthRegisteredClientsStore } from "../clients.js";
import { OAuthClientInformationFull } from "../../../shared/auth.js";
import { InvalidRequestError, InvalidClientError, ServerError, OAuthError } from "../errors.js";

export type ClientAuthenticationMiddlewareOptions = {
  /**
   * A store used to read information about registered OAuth clients.
   */
  clientsStore: OAuthRegisteredClientsStore;
}

const ClientAuthenticatedRequestSchema = z.object({
  client_id: z.string(),
  client_secret: z.string().optional(),
});

declare module "express-serve-static-core" {
  interface Request {
    /**
     * The authenticated client for this request, if the `authenticateClient` middleware was used.
     */
    client?: OAuthClientInformationFull;
  }
}

export function authenticateClient({ clientsStore }: ClientAuthenticationMiddlewareOptions): RequestHandler {
  return async (req, res, next) => {
    try {
      const result = ClientAuthenticatedRequestSchema.safeParse(req.body);
      if (!result.success) {
        throw new InvalidRequestError(String(result.error));
      }

      const { client_id, client_secret } = result.data;
      const client = await clientsStore.getClient(client_id);
      if (!client) {
        throw new InvalidClientError("Invalid client_id");
      }

      // If client has a secret, validate it
      if (client.client_secret) {
        // Check if client_secret is required but not provided
        if (!client_secret) {
          throw new InvalidClientError("Client secret is required");
        }

        // Check if client_secret matches
        if (client.client_secret !== client_secret) {
          throw new InvalidClientError("Invalid client_secret");
        }

        // Check if client_secret has expired
        if (client.client_secret_expires_at && client.client_secret_expires_at < Math.floor(Date.now() / 1000)) {
          throw new InvalidClientError("Client secret has expired");
        }
      }

      req.client = client;
      next();
    } catch (error) {
      if (error instanceof OAuthError) {
        const status = error instanceof ServerError ? 500 : 400;
        res.status(status).json(error.toResponseObject());
      } else {
        const serverError = new ServerError("Internal Server Error");
        res.status(500).json(serverError.toResponseObject());
      }
    }
  }
}


================================================
FILE: src/server/auth/providers/proxyProvider.test.ts
================================================
import { Response } from "express";
import { ProxyOAuthServerProvider, ProxyOptions } from "./proxyProvider.js";
import { AuthInfo } from "../types.js";
import { OAuthClientInformationFull, OAuthTokens } from "../../../shared/auth.js";
import { ServerError } from "../errors.js";
import { InvalidTokenError } from "../errors.js";
import { InsufficientScopeError } from "../errors.js";

describe("Proxy OAuth Server Provider", () => {
  // Mock client data
  const validClient: OAuthClientInformationFull = {
    client_id: "test-client",
    client_secret: "test-secret",
    redirect_uris: ["https://example.com/callback"],
  };

  // Mock response object
  const mockResponse = {
    redirect: jest.fn(),
  } as unknown as Response;

  // Mock provider functions
  const mockVerifyToken = jest.fn();
  const mockGetClient = jest.fn();

  // Base provider options
  const baseOptions: ProxyOptions = {
    endpoints: {
      authorizationUrl: "https://auth.example.com/authorize",
      tokenUrl: "https://auth.example.com/token",
      revocationUrl: "https://auth.example.com/revoke",
      registrationUrl: "https://auth.example.com/register",
    },
    verifyAccessToken: mockVerifyToken,
    getClient: mockGetClient,
  };

  let provider: ProxyOAuthServerProvider;
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    provider = new ProxyOAuthServerProvider(baseOptions);
    originalFetch = global.fetch;
    global.fetch = jest.fn();

    // Setup mock implementations
    mockVerifyToken.mockImplementation(async (token: string) => {
      if (token === "valid-token") {
        return {
          token,
          clientId: "test-client",
          scopes: ["read", "write"],
          expiresAt: Date.now() / 1000 + 3600,
        } as AuthInfo;
      }
      throw new InvalidTokenError("Invalid token");
    });

    mockGetClient.mockImplementation(async (clientId: string) => {
      if (clientId === "test-client") {
        return validClient;
      }
      return undefined;
    });
  });

  // Add helper function for failed responses
  const mockFailedResponse = () => {
    (global.fetch as jest.Mock).mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 400,
      })
    );
  };

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  describe("authorization", () => {
    it("redirects to authorization endpoint with correct parameters", async () => {
      await provider.authorize(
        validClient,
        {
          redirectUri: "https://example.com/callback",
          codeChallenge: "test-challenge",
          state: "test-state",
          scopes: ["read", "write"],
          resource: new URL('https://api.example.com/resource'),
        },
        mockResponse
      );

      const expectedUrl = new URL("https://auth.example.com/authorize");
      expectedUrl.searchParams.set("client_id", "test-client");
      expectedUrl.searchParams.set("response_type", "code");
      expectedUrl.searchParams.set("redirect_uri", "https://example.com/callback");
      expectedUrl.searchParams.set("code_challenge", "test-challenge");
      expectedUrl.searchParams.set("code_challenge_method", "S256");
      expectedUrl.searchParams.set("state", "test-state");
      expectedUrl.searchParams.set("scope", "read write");
      expectedUrl.searchParams.set('resource', 'https://api.example.com/resource');

      expect(mockResponse.redirect).toHaveBeenCalledWith(expectedUrl.toString());
    });
  });

  describe("token exchange", () => {
    const mockTokenResponse: OAuthTokens = {
      access_token: "new-access-token",
      token_type: "Bearer",
      expires_in: 3600,
      refresh_token: "new-refresh-token",
    };

    beforeEach(() => {
      (global.fetch as jest.Mock).mockImplementation(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTokenResponse),
        })
      );
    });

    it("exchanges authorization code for tokens", async () => {
      const tokens = await provider.exchangeAuthorizationCode(
        validClient,
        "test-code",
        "test-verifier"
      );

      expect(global.fetch).toHaveBeenCalledWith(
        "https://auth.example.com/token",
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: expect.stringContaining("grant_type=authorization_code")
        })
      );
      expect(tokens).toEqual(mockTokenResponse);
    });

    it("includes redirect_uri in token request when provided", async () => {
      const redirectUri = "https://example.com/callback";
      const tokens = await provider.exchangeAuthorizationCode(
        validClient,
        "test-code",
        "test-verifier",
        redirectUri
      );

      expect(global.fetch).toHaveBeenCalledWith(
        "https://auth.example.com/token",
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: expect.stringContaining(`redirect_uri=${encodeURIComponent(redirectUri)}`)
        })
      );
      expect(tokens).toEqual(mockTokenResponse);
    });

    it('includes resource parameter in authorization code exchange', async () => {
      const tokens = await provider.exchangeAuthorizationCode(
        validClient,
        'test-code',
        'test-verifier',
        'https://example.com/callback',
        new URL('https://api.example.com/resource')
      );

      expect(global.fetch).toHaveBeenCalledWith(
        'https://auth.example.com/token',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: expect.stringContaining('resource=' + encodeURIComponent('https://api.example.com/resource'))
        })
      );
      expect(tokens).toEqual(mockTokenResponse);
    });

    it('handles authorization code exchange without resource parameter', async () => {
      const tokens = await provider.exchangeAuthorizationCode(
        validClient,
        'test-code',
        'test-verifier'
      );

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      const body = fetchCall[1].body as string;
      expect(body).not.toContain('resource=');
      expect(tokens).toEqual(mockTokenResponse);
    });

    it("exchanges refresh token for new tokens", async () => {
      const tokens = await provider.exchangeRefreshToken(
        validClient,
        "test-refresh-token",
        ["read", "write"]
      );

      expect(global.fetch).toHaveBeenCalledWith(
        "https://auth.example.com/token",
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: expect.stringContaining("grant_type=refresh_token")
        })
      );
      expect(tokens).toEqual(mockTokenResponse);
    });

    it('includes resource parameter in refresh token exchange', async () => {
      const tokens = await provider.exchangeRefreshToken(
        validClient,
        'test-refresh-token',
        ['read', 'write'],
        new URL('https://api.example.com/resource')
      );

      expect(global.fetch).toHaveBeenCalledWith(
        'https://auth.example.com/token',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: expect.stringContaining('resource=' + encodeURIComponent('https://api.example.com/resource'))
        })
      );
      expect(tokens).toEqual(mockTokenResponse);
    });
  });

  describe("client registration", () => {
    it("registers new client", async () => {
      const newClient: OAuthClientInformationFull = {
        client_id: "new-client",
        redirect_uris: ["https://new-client.com/callback"],
      };

      (global.fetch as jest.Mock).mockImplementation(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(newClient),
        })
      );

      const result = await provider.clientsStore.registerClient!(newClient);

      expect(global.fetch).toHaveBeenCalledWith(
        "https://auth.example.com/register",
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(newClient),
        })
      );
      expect(result).toEqual(newClient);
    });

    it("handles registration failure", async () => {
      mockFailedResponse();
      const newClient: OAuthClientInformationFull = {
        client_id: "new-client",
        redirect_uris: ["https://new-client.com/callback"],
      };

      await expect(
        provider.clientsStore.registerClient!(newClient)
      ).rejects.toThrow(ServerError);
    });
  });

  describe("token revocation", () => {
    it("revokes token", async () => {
      (global.fetch as jest.Mock).mockImplementation(() =>
        Promise.resolve({
          ok: true,
        })
      );

      await provider.revokeToken!(validClient, {
        token: "token-to-revoke",
        token_type_hint: "access_token",
      });

      expect(global.fetch).toHaveBeenCalledWith(
        "https://auth.example.com/revoke",
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: expect.stringContaining("token=token-to-revoke"),
        })
      );
    });

    it("handles revocation failure", async () => {
      mockFailedResponse();
      await expect(
        provider.revokeToken!(validClient, {
          token: "invalid-token",
        })
      ).rejects.toThrow(ServerError);
    });
  });

  describe("token verification", () => {
    it("verifies valid token", async () => {
      const validAuthInfo: AuthInfo = {
        token: "valid-token",
        clientId: "test-client",
        scopes: ["read", "write"],
        expiresAt: Date.now() / 1000 + 3600,
      };
      mockVerifyToken.mockResolvedValue(validAuthInfo);

      const authInfo = await provider.verifyAccessToken("valid-token");
      expect(authInfo).toEqual(validAuthInfo);
      expect(mockVerifyToken).toHaveBeenCalledWith("valid-token");
    });

    it("passes through InvalidTokenError", async () => {
      const error = new InvalidTokenError("Token expired");
      mockVerifyToken.mockRejectedValue(error);

      await expect(provider.verifyAccessToken("invalid-token"))
        .rejects.toBe(error);
      expect(mockVerifyToken).toHaveBeenCalledWith("invalid-token");
    });

    it("passes through InsufficientScopeError", async () => {
      const error = new InsufficientScopeError("Required scopes: read, write");
      mockVerifyToken.mockRejectedValue(error);

      await expect(provider.verifyAccessToken("token-with-insufficient-scope"))
        .rejects.toBe(error);
      expect(mockVerifyToken).toHaveBeenCalledWith("token-with-insufficient-scope");
    });

    it("passes through unexpected errors", async () => {
      const error = new Error("Unexpected error");
      mockVerifyToken.mockRejectedValue(error);

      await expect(provider.verifyAccessToken("valid-token"))
        .rejects.toBe(error);
      expect(mockVerifyToken).toHaveBeenCalledWith("valid-token");
    });
  });
}); 


================================================
FILE: src/server/auth/providers/proxyProvider.ts
================================================
import { Response } from "express";
import { OAuthRegisteredClientsStore } from "../clients.js";
import {
  OAuthClientInformationFull,
  OAuthClientInformationFullSchema,
  OAuthTokenRevocationRequest,
  OAuthTokens,
  OAuthTokensSchema,
} from "../../../shared/auth.js";
import { AuthInfo } from "../types.js";
import { AuthorizationParams, OAuthServerProvider } from "../provider.js";
import { ServerError } from "../errors.js";
import { FetchLike } from "../../../shared/transport.js";

export type ProxyEndpoints = {
  authorizationUrl: string;
  tokenUrl: string;
  revocationUrl?: string;
  registrationUrl?: string;
};

export type ProxyOptions = {
  /**
   * Individual endpoint URLs for proxying specific OAuth operations
   */
  endpoints: ProxyEndpoints;

  /**
  * Function to verify access tokens and return auth info
  */
  verifyAccessToken: (token: string) => Promise<AuthInfo>;

  /**
  * Function to fetch client information from the upstream server
  */
  getClient: (clientId: string) => Promise<OAuthClientInformationFull | undefined>;

  /**
   * Custom fetch implementation used for all network requests.
   */
  fetch?: FetchLike;
};

/**
 * Implements an OAuth server that proxies requests to another OAuth server.
 */
export class ProxyOAuthServerProvider implements OAuthServerProvider {
  protected readonly _endpoints: ProxyEndpoints;
  protected readonly _verifyAccessToken: (token: string) => Promise<AuthInfo>;
  protected readonly _getClient: (clientId: string) => Promise<OAuthClientInformationFull | undefined>;
  protected readonly _fetch?: FetchLike;
  
  skipLocalPkceValidation = true;

  revokeToken?: (
    client: OAuthClientInformationFull,
    request: OAuthTokenRevocationRequest
  ) => Promise<void>;

  constructor(options: ProxyOptions) {
    this._endpoints = options.endpoints;
    this._verifyAccessToken = options.verifyAccessToken;
    this._getClient = options.getClient;
    this._fetch = options.fetch;
    if (options.endpoints?.revocationUrl) {
      this.revokeToken = async (
        client: OAuthClientInformationFull,
        request: OAuthTokenRevocationRequest
      ) => {
        const revocationUrl = this._endpoints.revocationUrl;

        if (!revocationUrl) {
          throw new Error("No revocation endpoint configured");
        }

        const params = new URLSearchParams();
        params.set("token", request.token);
        params.set("client_id", client.client_id);
        if (client.client_secret) {
          params.set("client_secret", client.client_secret);
        }
        if (request.token_type_hint) {
          params.set("token_type_hint", request.token_type_hint);
        }

        const response = await (this._fetch ?? fetch)(revocationUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: params.toString(),
        });

        if (!response.ok) {
          throw new ServerError(`Token revocation failed: ${response.status}`);
        }
      }
    }
  }

  get clientsStore(): OAuthRegisteredClientsStore {
    const registrationUrl = this._endpoints.registrationUrl;
    return {
      getClient: this._getClient,
      ...(registrationUrl && {
        registerClient: async (client: OAuthClientInformationFull) => {
          const response = await (this._fetch ?? fetch)(registrationUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(client),
          });

          if (!response.ok) {
            throw new ServerError(`Client registration failed: ${response.status}`);
          }

          const data = await response.json();
          return OAuthClientInformationFullSchema.parse(data);
        }
      })
    }
  }

  async authorize(
    client: OAuthClientInformationFull,
    params: AuthorizationParams,
    res: Response
  ): Promise<void> {
    // Start with required OAuth parameters
    const targetUrl = new URL(this._endpoints.authorizationUrl);
    const searchParams = new URLSearchParams({
      client_id: client.client_id,
      response_type: "code",
      redirect_uri: params.redirectUri,
      code_challenge: params.codeChallenge,
      code_challenge_method: "S256"
    });

    // Add optional standard OAuth parameters
    if (params.state) searchParams.set("state", params.state);
    if (params.scopes?.length) searchParams.set("scope", params.scopes.join(" "));
    if (params.resource) searchParams.set("resource", params.resource.href);

    targetUrl.search = searchParams.toString();
    res.redirect(targetUrl.toString());
  }

  async challengeForAuthorizationCode(
    _client: OAuthClientInformationFull,
    _authorizationCode: string
  ): Promise<string> {
    // In a proxy setup, we don't store the code challenge ourselves
    // Instead, we proxy the token request and let the upstream server validate it
    return "";
  }

  async exchangeAuthorizationCode(
    client: OAuthClientInformationFull,
    authorizationCode: string,
    codeVerifier?: string,
    redirectUri?: string,
    resource?: URL
  ): Promise<OAuthTokens> {
    const params = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: client.client_id,
      code: authorizationCode,
    });

    if (client.client_secret) {
      params.append("client_secret", client.client_secret);
    }

    if (codeVerifier) {
      params.append("code_verifier", codeVerifier);
    }

    if (redirectUri) {
      params.append("redirect_uri", redirectUri);
    }

    if (resource) {
      params.append("resource", resource.href);
    }

    const response = await (this._fetch ?? fetch)(this._endpoints.tokenUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });


    if (!response.ok) {
      throw new ServerError(`Token exchange failed: ${response.status}`);
    }

    const data = await response.json();
    return OAuthTokensSchema.parse(data);
  }

  async exchangeRefreshToken(
    client: OAuthClientInformationFull,
    refreshToken: string,
    scopes?: string[],
    resource?: URL
  ): Promise<OAuthTokens> {

    const params = new URLSearchParams({
      grant_type: "refresh_token",
      client_id: client.client_id,
      refresh_token: refreshToken,
    });

    if (client.client_secret) {
      params.set("client_secret", client.client_secret);
    }

    if (scopes?.length) {
      params.set("scope", scopes.join(" "));
    }

    if (resource) {
      params.set("resource", resource.href);
    }

    const response = await (this._fetch ?? fetch)(this._endpoints.tokenUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    if (!response.ok) {
      throw new ServerError(`Token refresh failed: ${response.status}`);
    }

    const data = await response.json();
    return OAuthTokensSchema.parse(data);
  }

  async verifyAccessToken(token: string): Promise<AuthInfo> {
    return this._verifyAccessToken(token);
  }
} 


================================================
FILE: src/shared/auth-utils.test.ts
================================================
import { resourceUrlFromServerUrl, checkResourceAllowed } from './auth-utils.js';

describe('auth-utils', () => {
  describe('resourceUrlFromServerUrl', () => {
    it('should remove fragments', () => {
      expect(resourceUrlFromServerUrl(new URL('https://example.com/path#fragment')).href).toBe('https://example.com/path');
      expect(resourceUrlFromServerUrl(new URL('https://example.com#fragment')).href).toBe('https://example.com/');
      expect(resourceUrlFromServerUrl(new URL('https://example.com/path?query=1#fragment')).href).toBe('https://example.com/path?query=1');
    });

    it('should return URL unchanged if no fragment', () => {
      expect(resourceUrlFromServerUrl(new URL('https://example.com')).href).toBe('https://example.com/');
      expect(resourceUrlFromServerUrl(new URL('https://example.com/path')).href).toBe('https://example.com/path');
      expect(resourceUrlFromServerUrl(new URL('https://example.com/path?query=1')).href).toBe('https://example.com/path?query=1');
    });

    it('should keep everything else unchanged', () => {
      // Case sensitivity preserved
      expect(resourceUrlFromServerUrl(new URL('https://EXAMPLE.COM/PATH')).href).toBe('https://example.com/PATH');
      // Ports preserved
      expect(resourceUrlFromServerUrl(new URL('https://example.com:443/path')).href).toBe('https://example.com/path');
      expect(resourceUrlFromServerUrl(new URL('https://example.com:8080/path')).href).toBe('https://example.com:8080/path');
      // Query parameters preserved
      expect(resourceUrlFromServerUrl(new URL('https://example.com?foo=bar&baz=qux')).href).toBe('https://example.com/?foo=bar&baz=qux');
      // Trailing slashes preserved
      expect(resourceUrlFromServerUrl(new URL('https://example.com/')).href).toBe('https://example.com/');
      expect(resourceUrlFromServerUrl(new URL('https://example.com/path/')).href).toBe('https://example.com/path/');
    });
  });

  describe('resourceMatches', () => {
    it('should match identical URLs', () => {
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/path', configuredResource: 'https://example.com/path' })).toBe(true);
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/', configuredResource: 'https://example.com/' })).toBe(true);
    });

    it('should not match URLs with different paths', () => {
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/path1', configuredResource: 'https://example.com/path2' })).toBe(false);
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/', configuredResource: 'https://example.com/path' })).toBe(false);
    });

    it('should not match URLs with different domains', () => {
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/path', configuredResource: 'https://example.org/path' })).toBe(false);
    });

    it('should not match URLs with different ports', () => {
      expect(checkResourceAllowed({ requestedResource: 'https://example.com:8080/path', configuredResource: 'https://example.com/path' })).toBe(false);
    });

    it('should not match URLs where one path is a sub-path of another', () => {
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/mcpxxxx', configuredResource: 'https://example.com/mcp' })).toBe(false);
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/folder', configuredResource: 'https://example.com/folder/subfolder' })).toBe(false);
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/api/v1', configuredResource: 'https://example.com/api' })).toBe(true);
    });

    it('should handle trailing slashes vs no trailing slashes', () => {
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/mcp/', configuredResource: 'https://example.com/mcp' })).toBe(true);
      expect(checkResourceAllowed({ requestedResource: 'https://example.com/folder', configuredResource: 'https://example.com/folder/' })).toBe(false);
    });
  });
});



================================================
FILE: src/shared/auth-utils.ts
================================================
/**
 * Utilities for handling OAuth resource URIs.
 */

/**
 * Converts a server URL to a resource URL by removing the fragment.
 * RFC 8707 section 2 states that resource URIs "MUST NOT include a fragment component".
 * Keeps everything else unchanged (scheme, domain, port, path, query).
 */
export function resourceUrlFromServerUrl(url: URL | string ): URL {
  const resourceURL = typeof url === "string" ? new URL(url) : new URL(url.href);
  resourceURL.hash = ''; // Remove fragment
  return resourceURL;
}

/**
 * Checks if a requested resource URL matches a configured resource URL.
 * A requested resource matches if it has the same scheme, domain, port,
 * and its path starts with the configured resource's path.
 *
 * @param requestedResource The resource URL being requested
 * @param configuredResource The resource URL that has been configured
 * @returns true if the requested resource matches the configured resource, false otherwise
 */
 export function checkResourceAllowed(
   { requestedResource, configuredResource }: {
     requestedResource: URL | string;
     configuredResource: URL | string
   }
 ): boolean {
   const requested = typeof requestedResource === "string" ? new URL(requestedResource) : new URL(requestedResource.href);
   const configured = typeof configuredResource === "string" ? new URL(configuredResource) : new URL(configuredResource.href);

   // Compare the origin (scheme, domain, and port)
   if (requested.origin !== configured.origin) {
     return false;
   }

   // Handle cases like requested=/foo and configured=/foo/
   if (requested.pathname.length < configured.pathname.length) {
     return false
   }

   // Check if the requested path starts with the configured path
   // Ensure both paths end with / for proper comparison
   // This ensures that if we have paths like "/api" and "/api/users",
   // we properly detect that "/api/users" is a subpath of "/api"
   // By adding a trailing slash if missing, we avoid false positives
   // where paths like "/api123" would incorrectly match "/api"
   const requestedPath = requested.pathname.endsWith('/') ? requested.pathname : requested.pathname + '/';
   const configuredPath = configured.pathname.endsWith('/') ? configured.pathname : configured.pathname + '/';

   return requestedPath.startsWith(configuredPath);
 }



================================================
FILE: src/shared/auth.test.ts
================================================
import { describe, it, expect } from '@jest/globals';
import {
  SafeUrlSchema,
  OAuthMetadataSchema,
  OpenIdProviderMetadataSchema,
  OAuthClientMetadataSchema,
} from './auth.js';

describe('SafeUrlSchema', () => {
  it('accepts valid HTTPS URLs', () => {
    expect(SafeUrlSchema.parse('https://example.com')).toBe('https://example.com');
    expect(SafeUrlSchema.parse('https://auth.example.com/oauth/authorize')).toBe('https://auth.example.com/oauth/authorize');
  });

  it('accepts valid HTTP URLs', () => {
    expect(SafeUrlSchema.parse('http://localhost:3000')).toBe('http://localhost:3000');
  });

  it('rejects javascript: scheme URLs', () => {
    expect(() => SafeUrlSchema.parse('javascript:alert(1)')).toThrow('URL cannot use javascript:, data:, or vbscript: scheme');
    expect(() => SafeUrlSchema.parse('JAVASCRIPT:alert(1)')).toThrow('URL cannot use javascript:, data:, or vbscript: scheme');
  });

  it('rejects invalid URLs', () => {
    expect(() => SafeUrlSchema.parse('not-a-url')).toThrow();
    expect(() => SafeUrlSchema.parse('')).toThrow();
  });

  it('works with safeParse', () => {
    expect(() => SafeUrlSchema.safeParse('not-a-url')).not.toThrow();
  });
});

describe('OAuthMetadataSchema', () => {
  it('validates complete OAuth metadata', () => {
    const metadata = {
      issuer: 'https://auth.example.com',
      authorization_endpoint: 'https://auth.example.com/oauth/authorize',
      token_endpoint: 'https://auth.example.com/oauth/token',
      response_types_supported: ['code'],
      scopes_supported: ['read', 'write'],
    };

    expect(() => OAuthMetadataSchema.parse(metadata)).not.toThrow();
  });

  it('rejects metadata with javascript: URLs', () => {
    const metadata = {
      issuer: 'https://auth.example.com',
      authorization_endpoint: 'javascript:alert(1)',
      token_endpoint: 'https://auth.example.com/oauth/token',
      response_types_supported: ['code'],
    };

    expect(() => OAuthMetadataSchema.parse(metadata)).toThrow('URL cannot use javascript:, data:, or vbscript: scheme');
  });

  it('requires mandatory fields', () => {
    const incompleteMetadata = {
      issuer: 'https://auth.example.com',
    };

    expect(() => OAuthMetadataSchema.parse(incompleteMetadata)).toThrow();
  });
});

describe('OpenIdProviderMetadataSchema', () => {
  it('validates complete OpenID Provider metadata', () => {
    const metadata = {
      issuer: 'https://auth.example.com',
      authorization_endpoint: 'https://auth.example.com/oauth/authorize',
      token_endpoint: 'https://auth.example.com/oauth/token',
      jwks_uri: 'https://auth.example.com/.well-known/jwks.json',
      response_types_supported: ['code'],
      subject_types_supported: ['public'],
      id_token_signing_alg_values_supported: ['RS256'],
    };

    expect(() => OpenIdProviderMetadataSchema.parse(metadata)).not.toThrow();
  });

  it('rejects metadata with javascript: in jwks_uri', () => {
    const metadata = {
      issuer: 'https://auth.example.com',
      authorization_endpoint: 'https://auth.example.com/oauth/authorize',
      token_endpoint: 'https://auth.example.com/oauth/token',
      jwks_uri: 'javascript:alert(1)',
      response_types_supported: ['code'],
      subject_types_supported: ['public'],
      id_token_signing_alg_values_supported: ['RS256'],
    };

    expect(() => OpenIdProviderMetadataSchema.parse(metadata)).toThrow('URL cannot use javascript:, data:, or vbscript: scheme');
  });
});

describe('OAuthClientMetadataSchema', () => {
  it('validates client metadata with safe URLs', () => {
    const metadata = {
      redirect_uris: ['https://app.example.com/callback'],
      client_name: 'Test App',
      client_uri: 'https://app.example.com',
    };

    expect(() => OAuthClientMetadataSchema.parse(metadata)).not.toThrow();
  });

  it('rejects client metadata with javascript: redirect URIs', () => {
    const metadata = {
      redirect_uris: ['javascript:alert(1)'],
      client_name: 'Test App',
    };

    expect(() => OAuthClientMetadataSchema.parse(metadata)).toThrow('URL cannot use javascript:, data:, or vbscript: scheme');
  });
});



================================================
FILE: src/shared/auth.ts
================================================
import { z } from "zod";

/**
 * Reusable URL validation that disallows javascript: scheme
 */
export const SafeUrlSchema = z.string().url()
  .superRefine((val, ctx) => {
    if (!URL.canParse(val)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "URL must be parseable",
        fatal: true,
      });

      return z.NEVER;
    }
  }).refine(
    (url) => {
      const u = new URL(url);
      return u.protocol !== 'javascript:' && u.protocol !== 'data:' && u.protocol !== 'vbscript:';
    },
    { message: "URL cannot use javascript:, data:, or vbscript: scheme" }
);


/**
 * RFC 9728 OAuth Protected Resource Metadata
 */
export const OAuthProtectedResourceMetadataSchema = z
  .object({
    resource: z.string().url(),
    authorization_servers: z.array(SafeUrlSchema).optional(),
    jwks_uri: z.string().url().optional(),
    scopes_supported: z.array(z.string()).optional(),
    bearer_methods_supported: z.array(z.string()).optional(),
    resource_signing_alg_values_supported: z.array(z.string()).optional(),
    resource_name: z.string().optional(),
    resource_documentation: z.string().optional(),
    resource_policy_uri: z.string().url().optional(),
    resource_tos_uri: z.string().url().optional(),
    tls_client_certificate_bound_access_tokens: z.boolean().optional(),
    authorization_details_types_supported: z.array(z.string()).optional(),
    dpop_signing_alg_values_supported: z.array(z.string()).optional(),
    dpop_bound_access_tokens_required: z.boolean().optional(),
  })
  .passthrough();

/**
 * RFC 8414 OAuth 2.0 Authorization Server Metadata
 */
export const OAuthMetadataSchema = z
  .object({
    issuer: z.string(),
    authorization_endpoint: SafeUrlSchema,
    token_endpoint: SafeUrlSchema,
    registration_endpoint: SafeUrlSchema.optional(),
    scopes_supported: z.array(z.string()).optional(),
    response_types_supported: z.array(z.string()),
    response_modes_supported: z.array(z.string()).optional(),
    grant_types_supported: z.array(z.string()).optional(),
    token_endpoint_auth_methods_supported: z.array(z.string()).optional(),
    token_endpoint_auth_signing_alg_values_supported: z
      .array(z.string())
      .optional(),
    service_documentation: SafeUrlSchema.optional(),
    revocation_endpoint: SafeUrlSchema.optional(),
    revocation_endpoint_auth_methods_supported: z.array(z.string()).optional(),
    revocation_endpoint_auth_signing_alg_values_supported: z
      .array(z.string())
      .optional(),
    introspection_endpoint: z.string().optional(),
    introspection_endpoint_auth_methods_supported: z
      .array(z.string())
      .optional(),
    introspection_endpoint_auth_signing_alg_values_supported: z
      .array(z.string())
      .optional(),
    code_challenge_methods_supported: z.array(z.string()).optional(),
  })
  .passthrough();

/**
 * OpenID Connect Discovery 1.0 Provider Metadata
 * see: https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata
 */
export const OpenIdProviderMetadataSchema = z
  .object({
    issuer: z.string(),
    authorization_endpoint: SafeUrlSchema,
    token_endpoint: SafeUrlSchema,
    userinfo_endpoint: SafeUrlSchema.optional(),
    jwks_uri: SafeUrlSchema,
    registration_endpoint: SafeUrlSchema.optional(),
    scopes_supported: z.array(z.string()).optional(),
    response_types_supported: z.array(z.string()),
    response_modes_supported: z.array(z.string()).optional(),
    grant_types_supported: z.array(z.string()).optional(),
    acr_values_supported: z.array(z.string()).optional(),
    subject_types_supported: z.array(z.string()),
    id_token_signing_alg_values_supported: z.array(z.string()),
    id_token_encryption_alg_values_supported: z.array(z.string()).optional(),
    id_token_encryption_enc_values_supported: z.array(z.string()).optional(),
    userinfo_signing_alg_values_supported: z.array(z.string()).optional(),
    userinfo_encryption_alg_values_supported: z.array(z.string()).optional(),
    userinfo_encryption_enc_values_supported: z.array(z.string()).optional(),
    request_object_signing_alg_values_supported: z.array(z.string()).optional(),
    request_object_encryption_alg_values_supported: z
      .array(z.string())
      .optional(),
    request_object_encryption_enc_values_supported: z
      .array(z.string())
      .optional(),
    token_endpoint_auth_methods_supported: z.array(z.string()).optional(),
    token_endpoint_auth_signing_alg_values_supported: z
      .array(z.string())
      .optional(),
    display_values_supported: z.array(z.string()).optional(),
    claim_types_supported: z.array(z.string()).optional(),
    claims_supported: z.array(z.string()).optional(),
    service_documentation: z.string().optional(),
    claims_locales_supported: z.array(z.string()).optional(),
    ui_locales_supported: z.array(z.string()).optional(),
    claims_parameter_supported: z.boolean().optional(),
    request_parameter_supported: z.boolean().optional(),
    request_uri_parameter_supported: z.boolean().optional(),
    require_request_uri_registration: z.boolean().optional(),
    op_policy_uri: SafeUrlSchema.optional(),
    op_tos_uri: SafeUrlSchema.optional(),
  })
  .passthrough();

/**
 * OpenID Connect Discovery metadata that may include OAuth 2.0 fields
 * This schema represents the real-world scenario where OIDC providers
 * return a mix of OpenID Connect and OAuth 2.0 metadata fields
 */
export const OpenIdProviderDiscoveryMetadataSchema =
  OpenIdProviderMetadataSchema.merge(
    OAuthMetadataSchema.pick({
      code_challenge_methods_supported: true,
    })
  );

/**
 * OAuth 2.1 token response
 */
export const OAuthTokensSchema = z
  .object({
    access_token: z.string(),
    id_token: z.string().optional(), // Optional for OAuth 2.1, but necessary in OpenID Connect
    token_type: z.string(),
    expires_in: z.number().optional(),
    scope: z.string().optional(),
    refresh_token: z.string().optional(),
  })
  .strip();

/**
 * OAuth 2.1 error response
 */
export const OAuthErrorResponseSchema = z
  .object({
    error: z.string(),
    error_description: z.string().optional(),
    error_uri: z.string().optional(),
  });

/**
 * RFC 7591 OAuth 2.0 Dynamic Client Registration metadata
 */
export const OAuthClientMetadataSchema = z.object({
  redirect_uris: z.array(SafeUrlSchema),
  token_endpoint_auth_method: z.string().optional(),
  grant_types: z.array(z.string()).optional(),
  response_types: z.array(z.string()).optional(),
  client_name: z.string().optional(),
  client_uri: SafeUrlSchema.optional(),
  logo_uri: SafeUrlSchema.optional(),
  scope: z.string().optional(),
  contacts: z.array(z.string()).optional(),
  tos_uri: SafeUrlSchema.optional(),
  policy_uri: z.string().optional(),
  jwks_uri: SafeUrlSchema.optional(),
  jwks: z.any().optional(),
  software_id: z.string().optional(),
  software_version: z.string().optional(),
  software_statement: z.string().optional(),
}).strip();

/**
 * RFC 7591 OAuth 2.0 Dynamic Client Registration client information
 */
export const OAuthClientInformationSchema = z.object({
  client_id: z.string(),
  client_secret: z.string().optional(),
  client_id_issued_at: z.number().optional(),
  client_secret_expires_at: z.number().optional(),
}).strip();

/**
 * RFC 7591 OAuth 2.0 Dynamic Client Registration full response (client information plus metadata)
 */
export const OAuthClientInformationFullSchema = OAuthClientMetadataSchema.merge(OAuthClientInformationSchema);

/**
 * RFC 7591 OAuth 2.0 Dynamic Client Registration error response
 */
export const OAuthClientRegistrationErrorSchema = z.object({
  error: z.string(),
  error_description: z.string().optional(),
}).strip();

/**
 * RFC 7009 OAuth 2.0 Token Revocation request
 */
export const OAuthTokenRevocationRequestSchema = z.object({
  token: z.string(),
  token_type_hint: z.string().optional(),
}).strip();

export type OAuthMetadata = z.infer<typeof OAuthMetadataSchema>;
export type OpenIdProviderMetadata = z.infer<typeof OpenIdProviderMetadataSchema>;
export type OpenIdProviderDiscoveryMetadata = z.infer<typeof OpenIdProviderDiscoveryMetadataSchema>;

export type OAuthTokens = z.infer<typeof OAuthTokensSchema>;
export type OAuthErrorResponse = z.infer<typeof OAuthErrorResponseSchema>;
export type OAuthClientMetadata = z.infer<typeof OAuthClientMetadataSchema>;
export type OAuthClientInformation = z.infer<typeof OAuthClientInformationSchema>;
export type OAuthClientInformationFull = z.infer<typeof OAuthClientInformationFullSchema>;
export type OAuthClientRegistrationError = z.infer<typeof OAuthClientRegistrationErrorSchema>;
export type OAuthTokenRevocationRequest = z.infer<typeof OAuthTokenRevocationRequestSchema>;
export type OAuthProtectedResourceMetadata = z.infer<typeof OAuthProtectedResourceMetadataSchema>;

// Unified type for authorization server metadata
export type AuthorizationServerMetadata = OAuthMetadata | OpenIdProviderDiscoveryMetadata;



================================================
FILE: src/shared/metadataUtils.ts
================================================
import { BaseMetadata } from "../types.js";

/**
 * Utilities for working with BaseMetadata objects.
 */

/**
 * Gets the display name for an object with BaseMetadata.
 * For tools, the precedence is: title → annotations.title → name
 * For other objects: title → name
 * This implements the spec requirement: "if no title is provided, name should be used for display purposes"
 */
export function getDisplayName(metadata: BaseMetadata): string {
  // First check for title (not undefined and not empty string)
  if (metadata.title !== undefined && metadata.title !== '') {
    return metadata.title;
  }

  // Then check for annotations.title (only present in Tool objects)
  if ('annotations' in metadata) {
    const metadataWithAnnotations = metadata as BaseMetadata & { annotations?: { title?: string } };
    if (metadataWithAnnotations.annotations?.title) {
      return metadataWithAnnotations.annotations.title;
    }
  }

  // Finally fall back to name
  return metadata.name;
}



================================================
FILE: src/shared/protocol-transport-handling.test.ts
================================================
import { describe, expect, test, beforeEach } from "@jest/globals";
import { Protocol } from "./protocol.js";
import { Transport } from "./transport.js";
import { Request, Notification, Result, JSONRPCMessage } from "../types.js";
import { z } from "zod";

// Mock Transport class
class MockTransport implements Transport {
  id: string;
  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: unknown) => void;
  sentMessages: JSONRPCMessage[] = [];

  constructor(id: string) {
    this.id = id;
  }

  async start(): Promise<void> {}
  
  async close(): Promise<void> {
    this.onclose?.();
  }
  
  async send(message: JSONRPCMessage): Promise<void> {
    this.sentMessages.push(message);
  }
}

describe("Protocol transport handling bug", () => {
  let protocol: Protocol<Request, Notification, Result>;
  let transportA: MockTransport;
  let transportB: MockTransport;

  beforeEach(() => {
    protocol = new (class extends Protocol<Request, Notification, Result> {
      protected assertCapabilityForMethod(): void {}
      protected assertNotificationCapability(): void {}
      protected assertRequestHandlerCapability(): void {}
    })();
    
    transportA = new MockTransport("A");
    transportB = new MockTransport("B");
  });

  test("should send response to the correct transport when multiple clients are connected", async () => {
    // Set up a request handler that simulates processing time
    let resolveHandler: (value: Result) => void;
    const handlerPromise = new Promise<Result>((resolve) => {
      resolveHandler = resolve;
    });

    const TestRequestSchema = z.object({
      method: z.literal("test/method"),
      params: z.object({
        from: z.string()
      }).optional()
    });

    protocol.setRequestHandler(
      TestRequestSchema,
      async (request) => {
        console.log(`Processing request from ${request.params?.from}`);
        return handlerPromise;
      }
    );

    // Client A connects and sends a request
    await protocol.connect(transportA);
    
    const requestFromA = {
      jsonrpc: "2.0" as const,
      method: "test/method",
      params: { from: "clientA" },
      id: 1
    };
    
    // Simulate client A sending a request
    transportA.onmessage?.(requestFromA);
    
    // While A's request is being processed, client B connects
    // This overwrites the transport reference in the protocol
    await protocol.connect(transportB);
    
    const requestFromB = {
      jsonrpc: "2.0" as const,
      method: "test/method", 
      params: { from: "clientB" },
      id: 2
    };
    
    // Client B sends its own request
    transportB.onmessage?.(requestFromB);
    
    // Now complete A's request
    resolveHandler!({ data: "responseForA" } as Result);
    
    // Wait for async operations to complete
    await new Promise(resolve => setTimeout(resolve, 10));
    
    // Check where the responses went
    console.log("Transport A received:", transportA.sentMessages);
    console.log("Transport B received:", transportB.sentMessages);
    
    // FIXED: Each transport now receives its own response
    
    // Transport A should receive response for request ID 1
    expect(transportA.sentMessages.length).toBe(1);
    expect(transportA.sentMessages[0]).toMatchObject({
      jsonrpc: "2.0",
      id: 1,
      result: { data: "responseForA" }
    });
    
    // Transport B should only receive its own response (when implemented)
    expect(transportB.sentMessages.length).toBe(1);
    expect(transportB.sentMessages[0]).toMatchObject({
      jsonrpc: "2.0",
      id: 2,
      result: { data: "responseForA" } // Same handler result in this test
    });
  });

  test("demonstrates the timing issue with multiple rapid connections", async () => {
    const delays: number[] = [];
    const results: { transport: string; response: JSONRPCMessage[] }[] = [];
    
    const DelayedRequestSchema = z.object({
      method: z.literal("test/delayed"),
      params: z.object({
        delay: z.number(),
        client: z.string()
      }).optional()
    });

    // Set up handler with variable delay
    protocol.setRequestHandler(
      DelayedRequestSchema,
      async (request, extra) => {
        const delay = request.params?.delay || 0;
        delays.push(delay);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        
        return { 
          processedBy: `handler-${extra.requestId}`,
          delay: delay
        } as Result;
      }
    );

    // Rapid succession of connections and requests
    await protocol.connect(transportA);
    transportA.onmessage?.({
      jsonrpc: "2.0" as const,
      method: "test/delayed",
      params: { delay: 50, client: "A" },
      id: 1
    });

    // Connect B while A is processing
    setTimeout(async () => {
      await protocol.connect(transportB);
      transportB.onmessage?.({
        jsonrpc: "2.0" as const,
        method: "test/delayed", 
        params: { delay: 10, client: "B" },
        id: 2
      });
    }, 10);

    // Wait for all processing
    await new Promise(resolve => setTimeout(resolve, 100));

    // Collect results
    if (transportA.sentMessages.length > 0) {
      results.push({ transport: "A", response: transportA.sentMessages });
    }
    if (transportB.sentMessages.length > 0) {
      results.push({ transport: "B", response: transportB.sentMessages });
    }

    console.log("Timing test results:", results);
    
    // FIXED: Each transport receives its own responses
    expect(transportA.sentMessages.length).toBe(1);
    expect(transportB.sentMessages.length).toBe(1);
  });
});


================================================
FILE: src/shared/protocol.test.ts
================================================
import { ZodType, z } from "zod";
import {
  ClientCapabilities,
  ErrorCode,
  McpError,
  Notification,
  Request,
  Result,
  ServerCapabilities,
} from "../types.js";
import { Protocol, mergeCapabilities } from "./protocol.js";
import { Transport } from "./transport.js";

// Mock Transport class
class MockTransport implements Transport {
  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: unknown) => void;

  async start(): Promise<void> {}
  async close(): Promise<void> {
    this.onclose?.();
  }
  async send(_message: unknown): Promise<void> {}
}

describe("protocol tests", () => {
  let protocol: Protocol<Request, Notification, Result>;
  let transport: MockTransport;
  let sendSpy: jest.SpyInstance;

  beforeEach(() => {
    transport = new MockTransport();
    sendSpy = jest.spyOn(transport, 'send');
    protocol = new (class extends Protocol<Request, Notification, Result> {
      protected assertCapabilityForMethod(): void {}
      protected assertNotificationCapability(): void {}
      protected assertRequestHandlerCapability(): void {}
    })();
  });

  test("should throw a timeout error if the request exceeds the timeout", async () => {
    await protocol.connect(transport);
    const request = { method: "example", params: {} };
    try {
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      await protocol.request(request, mockSchema, {
        timeout: 0,
      });
    } catch (error) {
      expect(error).toBeInstanceOf(McpError);
      if (error instanceof McpError) {
        expect(error.code).toBe(ErrorCode.RequestTimeout);
      }
    }
  });

  test("should invoke onclose when the connection is closed", async () => {
    const oncloseMock = jest.fn();
    protocol.onclose = oncloseMock;
    await protocol.connect(transport);
    await transport.close();
    expect(oncloseMock).toHaveBeenCalled();
  });

  test("should not overwrite existing hooks when connecting transports", async () => {
    const oncloseMock = jest.fn();
    const onerrorMock = jest.fn();
    const onmessageMock = jest.fn();
    transport.onclose = oncloseMock;
    transport.onerror = onerrorMock;
    transport.onmessage = onmessageMock;
    await protocol.connect(transport);
    transport.onclose();
    transport.onerror(new Error());
    transport.onmessage("");
    expect(oncloseMock).toHaveBeenCalled();
    expect(onerrorMock).toHaveBeenCalled();
    expect(onmessageMock).toHaveBeenCalled();
  });

  describe("_meta preservation with onprogress", () => {
    test("should preserve existing _meta when adding progressToken", async () => {
      await protocol.connect(transport);
      const request = { 
        method: "example", 
        params: {
          data: "test",
          _meta: {
            customField: "customValue",
            anotherField: 123
          }
        }
      };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      
      protocol.request(request, mockSchema, {
        onprogress: onProgressMock,
      });
      
      expect(sendSpy).toHaveBeenCalledWith(expect.objectContaining({
        method: "example",
        params: {
          data: "test",
          _meta: {
            customField: "customValue",
            anotherField: 123,
            progressToken: expect.any(Number)
          }
        },
        jsonrpc: "2.0",
        id: expect.any(Number)
      }), expect.any(Object));
    });

    test("should create _meta with progressToken when no _meta exists", async () => {
      await protocol.connect(transport);
      const request = { 
        method: "example", 
        params: {
          data: "test"
        }
      };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      
      protocol.request(request, mockSchema, {
        onprogress: onProgressMock,
      });
      
      expect(sendSpy).toHaveBeenCalledWith(expect.objectContaining({
        method: "example",
        params: {
          data: "test",
          _meta: {
            progressToken: expect.any(Number)
          }
        },
        jsonrpc: "2.0",
        id: expect.any(Number)
      }), expect.any(Object));
    });

    test("should not modify _meta when onprogress is not provided", async () => {
      await protocol.connect(transport);
      const request = { 
        method: "example", 
        params: {
          data: "test",
          _meta: {
            customField: "customValue"
          }
        }
      };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      
      protocol.request(request, mockSchema);
      
      expect(sendSpy).toHaveBeenCalledWith(expect.objectContaining({
        method: "example",
        params: {
          data: "test",
          _meta: {
            customField: "customValue"
          }
        },
        jsonrpc: "2.0",
        id: expect.any(Number)
      }), expect.any(Object));
    });

    test("should handle params being undefined with onprogress", async () => {
      await protocol.connect(transport);
      const request = { 
        method: "example"
      };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      
      protocol.request(request, mockSchema, {
        onprogress: onProgressMock,
      });
      
      expect(sendSpy).toHaveBeenCalledWith(expect.objectContaining({
        method: "example",
        params: {
          _meta: {
            progressToken: expect.any(Number)
          }
        },
        jsonrpc: "2.0",
        id: expect.any(Number)
      }), expect.any(Object));
    });
  });

  describe("progress notification timeout behavior", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });
    afterEach(() => {
      jest.useRealTimers();
    });

    test("should not reset timeout when resetTimeoutOnProgress is false", async () => {
      await protocol.connect(transport);
      const request = { method: "example", params: {} };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      const requestPromise = protocol.request(request, mockSchema, {
        timeout: 1000,
        resetTimeoutOnProgress: false,
        onprogress: onProgressMock,
      });
      
      jest.advanceTimersByTime(800);
      
      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          method: "notifications/progress",
          params: {
            progressToken: 0,
            progress: 50,
            total: 100,
          },
        });
      }
      await Promise.resolve();
      
      expect(onProgressMock).toHaveBeenCalledWith({
        progress: 50,
        total: 100,
      });
      
      jest.advanceTimersByTime(201);
      
      await expect(requestPromise).rejects.toThrow("Request timed out");
    });

    test("should reset timeout when progress notification is received", async () => {
      await protocol.connect(transport);
      const request = { method: "example", params: {} };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      const requestPromise = protocol.request(request, mockSchema, {
        timeout: 1000,
        resetTimeoutOnProgress: true,
        onprogress: onProgressMock,
      });
      jest.advanceTimersByTime(800);
      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          method: "notifications/progress",
          params: {
            progressToken: 0,
            progress: 50,
            total: 100,
          },
        });
      }
      await Promise.resolve();
      expect(onProgressMock).toHaveBeenCalledWith({
        progress: 50,
        total: 100,
      });
      jest.advanceTimersByTime(800);
      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          id: 0,
          result: { result: "success" },
        });
      }
      await Promise.resolve();
      await expect(requestPromise).resolves.toEqual({ result: "success" });
    });

    test("should respect maxTotalTimeout", async () => {
      await protocol.connect(transport);
      const request = { method: "example", params: {} };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      const requestPromise = protocol.request(request, mockSchema, {
        timeout: 1000,
        maxTotalTimeout: 150,
        resetTimeoutOnProgress: true,
        onprogress: onProgressMock,
      });

      // First progress notification should work
      jest.advanceTimersByTime(80);
      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          method: "notifications/progress",
          params: {
            progressToken: 0,
            progress: 50,
            total: 100,
          },
        });
      }
      await Promise.resolve();
      expect(onProgressMock).toHaveBeenCalledWith({
        progress: 50,
        total: 100,
      });
      jest.advanceTimersByTime(80);
      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          method: "notifications/progress",
          params: {
            progressToken: 0,
            progress: 75,
            total: 100,
          },
        });
      }
      await expect(requestPromise).rejects.toThrow("Maximum total timeout exceeded");
      expect(onProgressMock).toHaveBeenCalledTimes(1);
    });

    test("should timeout if no progress received within timeout period", async () => {
      await protocol.connect(transport);
      const request = { method: "example", params: {} };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const requestPromise = protocol.request(request, mockSchema, {
        timeout: 100,
        resetTimeoutOnProgress: true,
      });
      jest.advanceTimersByTime(101);
      await expect(requestPromise).rejects.toThrow("Request timed out");
    });

    test("should handle multiple progress notifications correctly", async () => {
      await protocol.connect(transport);
      const request = { method: "example", params: {} };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();
      const requestPromise = protocol.request(request, mockSchema, {
        timeout: 1000,
        resetTimeoutOnProgress: true,
        onprogress: onProgressMock,
      });

      // Simulate multiple progress updates
      for (let i = 1; i <= 3; i++) {
        jest.advanceTimersByTime(800);
        if (transport.onmessage) {
          transport.onmessage({
            jsonrpc: "2.0",
            method: "notifications/progress",
            params: {
              progressToken: 0,
              progress: i * 25,
              total: 100,
            },
          });
        }
        await Promise.resolve();
        expect(onProgressMock).toHaveBeenNthCalledWith(i, {
          progress: i * 25,
          total: 100,
        });
      }
      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          id: 0,
          result: { result: "success" },
        });
      }
      await Promise.resolve();
      await expect(requestPromise).resolves.toEqual({ result: "success" });
    });

    test("should handle progress notifications with message field", async () => {
      await protocol.connect(transport);
      const request = { method: "example", params: {} };
      const mockSchema: ZodType<{ result: string }> = z.object({
        result: z.string(),
      });
      const onProgressMock = jest.fn();

      const requestPromise = protocol.request(request, mockSchema, {
        timeout: 1000,
        onprogress: onProgressMock,
      });

      jest.advanceTimersByTime(200);

      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          method: "notifications/progress",
          params: {
            progressToken: 0,
            progress: 25,
            total: 100,
            message: "Initializing process...",
          },
        });
      }
      await Promise.resolve();

      expect(onProgressMock).toHaveBeenCalledWith({
        progress: 25,
        total: 100,
        message: "Initializing process...",
      });

      jest.advanceTimersByTime(200);

      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          method: "notifications/progress",
          params: {
            progressToken: 0,
            progress: 75,
            total: 100,
            message: "Processing data...",
          },
        });
      }
      await Promise.resolve();

      expect(onProgressMock).toHaveBeenCalledWith({
        progress: 75,
        total: 100,
        message: "Processing data...",
      });

      if (transport.onmessage) {
        transport.onmessage({
          jsonrpc: "2.0",
          id: 0,
          result: { result: "success" },
        });
      }
      await Promise.resolve();
      await expect(requestPromise).resolves.toEqual({ result: "success" });
    });
  });

  describe("Debounced Notifications", () => {
    // We need to flush the microtask queue to test the debouncing logic.
    // This helper function does that.
    const flushMicrotasks = () => new Promise(resolve => setImmediate(resolve));

      it("should NOT debounce a notification that has parameters", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced_with_params'] });
      await protocol.connect(transport);

      // ACT
      // These notifications are configured for debouncing but contain params, so they should be sent immediately.
      await protocol.notification({ method: 'test/debounced_with_params', params: { data: 1 } });
      await protocol.notification({ method: 'test/debounced_with_params', params: { data: 2 } });

      // ASSERT
      // Both should have been sent immediately to avoid data loss.
      expect(sendSpy).toHaveBeenCalledTimes(2);
      expect(sendSpy).toHaveBeenCalledWith(expect.objectContaining({ params: { data: 1 } }), undefined);
      expect(sendSpy).toHaveBeenCalledWith(expect.objectContaining({ params: { data: 2 } }), undefined);
    });

    it("should NOT debounce a notification that has a relatedRequestId", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced_with_options'] });
      await protocol.connect(transport);

      // ACT
      await protocol.notification({ method: 'test/debounced_with_options' }, { relatedRequestId: 'req-1' });
      await protocol.notification({ method: 'test/debounced_with_options' }, { relatedRequestId: 'req-2' });

      // ASSERT
      expect(sendSpy).toHaveBeenCalledTimes(2);
      expect(sendSpy).toHaveBeenCalledWith(expect.any(Object), { relatedRequestId: 'req-1' });
      expect(sendSpy).toHaveBeenCalledWith(expect.any(Object), { relatedRequestId: 'req-2' });
    });

    it("should clear pending debounced notifications on connection close", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced'] });
      await protocol.connect(transport);

      // ACT
      // Schedule a notification but don't flush the microtask queue.
      protocol.notification({ method: 'test/debounced' });

      // Close the connection. This should clear the pending set.
      await protocol.close();

      // Now, flush the microtask queue.
      await flushMicrotasks();

      // ASSERT
      // The send should never have happened because the transport was cleared.
      expect(sendSpy).not.toHaveBeenCalled();
    });

    it("should debounce multiple synchronous calls when params property is omitted", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced'] });
      await protocol.connect(transport);

      // ACT
      // This is the more idiomatic way to write a notification with no params.
      protocol.notification({ method: 'test/debounced' });
      protocol.notification({ method: 'test/debounced' });
      protocol.notification({ method: 'test/debounced' });

      expect(sendSpy).not.toHaveBeenCalled();
      await flushMicrotasks();

      // ASSERT
      expect(sendSpy).toHaveBeenCalledTimes(1);
      // The final sent object might not even have the `params` key, which is fine.
      // We can check that it was called and that the params are "falsy".
      const sentNotification = sendSpy.mock.calls[0][0];
      expect(sentNotification.method).toBe('test/debounced');
      expect(sentNotification.params).toBeUndefined();
    });

    it("should debounce calls when params is explicitly undefined", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced'] });
      await protocol.connect(transport);

      // ACT
      protocol.notification({ method: 'test/debounced', params: undefined });
      protocol.notification({ method: 'test/debounced', params: undefined });
      await flushMicrotasks();

      // ASSERT
      expect(sendSpy).toHaveBeenCalledTimes(1);
      expect(sendSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'test/debounced',
          params: undefined
        }),
        undefined
      );
    });

    it("should send non-debounced notifications immediately and multiple times", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced'] }); // Configure for a different method
      await protocol.connect(transport);

      // ACT
      // Call a non-debounced notification method multiple times.
      await protocol.notification({ method: 'test/immediate' });
      await protocol.notification({ method: 'test/immediate' });

      // ASSERT
      // Since this method is not in the debounce list, it should be sent every time.
      expect(sendSpy).toHaveBeenCalledTimes(2);
    });

    it("should not debounce any notifications if the option is not provided", async () => {
      // ARRANGE
      // Use the default protocol from beforeEach, which has no debounce options.
      await protocol.connect(transport);

      // ACT
      await protocol.notification({ method: 'any/method' });
      await protocol.notification({ method: 'any/method' });

      // ASSERT
      // Without the config, behavior should be immediate sending.
      expect(sendSpy).toHaveBeenCalledTimes(2);
    });

    it("should handle sequential batches of debounced notifications correctly", async () => {
      // ARRANGE
      protocol = new (class extends Protocol<Request, Notification, Result> {
        protected assertCapabilityForMethod(): void {}
        protected assertNotificationCapability(): void {}
        protected assertRequestHandlerCapability(): void {}
      })({ debouncedNotificationMethods: ['test/debounced'] });
      await protocol.connect(transport);

      // ACT (Batch 1)
      protocol.notification({ method: 'test/debounced' });
      protocol.notification({ method: 'test/debounced' });
      await flushMicrotasks();

      // ASSERT (Batch 1)
      expect(sendSpy).toHaveBeenCalledTimes(1);

      // ACT (Batch 2)
      // After the first batch has been sent, a new batch should be possible.
      protocol.notification({ method: 'test/debounced' });
      protocol.notification({ method: 'test/debounced' });
      await flushMicrotasks();

      // ASSERT (Batch 2)
      // The total number of sends should now be 2.
      expect(sendSpy).toHaveBeenCalledTimes(2);
    });
  });
});

describe("mergeCapabilities", () => {
  it("should merge client capabilities", () => {
    const base: ClientCapabilities = {
      sampling: {},
      roots: {
        listChanged: true,
      },
    };

    const additional: ClientCapabilities = {
      experimental: {
        feature: true,
      },
      elicitation: {},
      roots: {
        newProp: true,
      },
    };

    const merged = mergeCapabilities(base, additional);
    expect(merged).toEqual({
      sampling: {},
      elicitation: {},
      roots: {
        listChanged: true,
        newProp: true,
      },
      experimental: {
        feature: true,
      },
    });
  });

  it("should merge server capabilities", () => {
    const base: ServerCapabilities = {
      logging: {},
      prompts: {
        listChanged: true,
      },
    };

    const additional: ServerCapabilities = {
      resources: {
        subscribe: true,
      },
      prompts: {
        newProp: true,
      },
    };

    const merged = mergeCapabilities(base, additional);
    expect(merged).toEqual({
      logging: {},
      prompts: {
        listChanged: true,
        newProp: true,
      },
      resources: {
        subscribe: true,
      },
    });
  });

  it("should override existing values with additional values", () => {
    const base: ServerCapabilities = {
      prompts: {
        listChanged: false,
      },
    };

    const additional: ServerCapabilities = {
      prompts: {
        listChanged: true,
      },
    };

    const merged = mergeCapabilities(base, additional);
    expect(merged.prompts!.listChanged).toBe(true);
  });

  it("should handle empty objects", () => {
    const base = {};
    const additional = {};
    const merged = mergeCapabilities(base, additional);
    expect(merged).toEqual({});
  });
});



================================================
FILE: src/shared/protocol.ts
================================================
import { ZodLiteral, ZodObject, ZodType, z } from "zod";
import {
  CancelledNotificationSchema,
  ClientCapabilities,
  ErrorCode,
  isJSONRPCError,
  isJSONRPCRequest,
  isJSONRPCResponse,
  isJSONRPCNotification,
  JSONRPCError,
  JSONRPCNotification,
  JSONRPCRequest,
  JSONRPCResponse,
  McpError,
  Notification,
  PingRequestSchema,
  Progress,
  ProgressNotification,
  ProgressNotificationSchema,
  Request,
  RequestId,
  Result,
  ServerCapabilities,
  RequestMeta,
  MessageExtraInfo,
  RequestInfo,
} from "../types.js";
import { Transport, TransportSendOptions } from "./transport.js";
import { AuthInfo } from "../server/auth/types.js";

/**
 * Callback for progress notifications.
 */
export type ProgressCallback = (progress: Progress) => void;

/**
 * Additional initialization options.
 */
export type ProtocolOptions = {
  /**
   * Whether to restrict emitted requests to only those that the remote side has indicated that they can handle, through their advertised capabilities.
   *
   * Note that this DOES NOT affect checking of _local_ side capabilities, as it is considered a logic error to mis-specify those.
   *
   * Currently this defaults to false, for backwards compatibility with SDK versions that did not advertise capabilities correctly. In future, this will default to true.
   */
  enforceStrictCapabilities?: boolean;
  /**
   * An array of notification method names that should be automatically debounced.
   * Any notifications with a method in this list will be coalesced if they
   * occur in the same tick of the event loop.
   * e.g., ['notifications/tools/list_changed']
   */
  debouncedNotificationMethods?: string[];
};

/**
 * The default request timeout, in miliseconds.
 */
export const DEFAULT_REQUEST_TIMEOUT_MSEC = 60000;

/**
 * Options that can be given per request.
 */
export type RequestOptions = {
  /**
   * If set, requests progress notifications from the remote end (if supported). When progress notifications are received, this callback will be invoked.
   */
  onprogress?: ProgressCallback;

  /**
   * Can be used to cancel an in-flight request. This will cause an AbortError to be raised from request().
   */
  signal?: AbortSignal;

  /**
   * A timeout (in milliseconds) for this request. If exceeded, an McpError with code `RequestTimeout` will be raised from request().
   *
   * If not specified, `DEFAULT_REQUEST_TIMEOUT_MSEC` will be used as the timeout.
   */
  timeout?: number;

  /**
   * If true, receiving a progress notification will reset the request timeout.
   * This is useful for long-running operations that send periodic progress updates.
   * Default: false
   */
  resetTimeoutOnProgress?: boolean;

  /**
   * Maximum total time (in milliseconds) to wait for a response.
   * If exceeded, an McpError with code `RequestTimeout` will be raised, regardless of progress notifications.
   * If not specified, there is no maximum total timeout.
   */
  maxTotalTimeout?: number;
} & TransportSendOptions;

/**
 * Options that can be given per notification.
 */
export type NotificationOptions = {
  /**
   * May be used to indicate to the transport which incoming request to associate this outgoing notification with.
   */
  relatedRequestId?: RequestId;
}

/**
 * Extra data given to request handlers.
 */
export type RequestHandlerExtra<SendRequestT extends Request,
  SendNotificationT extends Notification> = {
    /**
     * An abort signal used to communicate if the request was cancelled from the sender's side.
     */
    signal: AbortSignal;

    /**
     * Information about a validated access token, provided to request handlers.
     */
    authInfo?: AuthInfo;

    /**
     * The session ID from the transport, if available.
     */
    sessionId?: string;

    /**
     * Metadata from the original request.
     */
    _meta?: RequestMeta;

    /**
     * The JSON-RPC ID of the request being handled.
     * This can be useful for tracking or logging purposes.
     */
    requestId: RequestId;

    /**
     * The original HTTP request.
     */
    requestInfo?: RequestInfo;

    /**
     * Sends a notification that relates to the current request being handled.
     * 
     * This is used by certain transports to correctly associate related messages.
     */
    sendNotification: (notification: SendNotificationT) => Promise<void>;

    /**
     * Sends a request that relates to the current request being handled.
     * 
     * This is used by certain transports to correctly associate related messages.
     */
    sendRequest: <U extends ZodType<object>>(request: SendRequestT, resultSchema: U, options?: RequestOptions) => Promise<z.infer<U>>;
  };

/**
 * Information about a request's timeout state
 */
type TimeoutInfo = {
  timeoutId: ReturnType<typeof setTimeout>;
  startTime: number;
  timeout: number;
  maxTotalTimeout?: number;
  resetTimeoutOnProgress: boolean;
  onTimeout: () => void;
};

/**
 * Implements MCP protocol framing on top of a pluggable transport, including
 * features like request/response linking, notifications, and progress.
 */
export abstract class Protocol<
  SendRequestT extends Request,
  SendNotificationT extends Notification,
  SendResultT extends Result,
> {
  private _transport?: Transport;
  private _requestMessageId = 0;
  private _requestHandlers: Map<
    string,
    (
      request: JSONRPCRequest,
      extra: RequestHandlerExtra<SendRequestT, SendNotificationT>,
    ) => Promise<SendResultT>
  > = new Map();
  private _requestHandlerAbortControllers: Map<RequestId, AbortController> =
    new Map();
  private _notificationHandlers: Map<
    string,
    (notification: JSONRPCNotification) => Promise<void>
  > = new Map();
  private _responseHandlers: Map<
    number,
    (response: JSONRPCResponse | Error) => void
  > = new Map();
  private _progressHandlers: Map<number, ProgressCallback> = new Map();
  private _timeoutInfo: Map<number, TimeoutInfo> = new Map();
  private _pendingDebouncedNotifications = new Set<string>();

  /**
   * Callback for when the connection is closed for any reason.
   *
   * This is invoked when close() is called as well.
   */
  onclose?: () => void;

  /**
   * Callback for when an error occurs.
   *
   * Note that errors are not necessarily fatal; they are used for reporting any kind of exceptional condition out of band.
   */
  onerror?: (error: Error) => void;

  /**
   * A handler to invoke for any request types that do not have their own handler installed.
   */
  fallbackRequestHandler?: (
    request: JSONRPCRequest,
    extra: RequestHandlerExtra<SendRequestT, SendNotificationT>
  ) => Promise<SendResultT>;

  /**
   * A handler to invoke for any notification types that do not have their own handler installed.
   */
  fallbackNotificationHandler?: (notification: Notification) => Promise<void>;

  constructor(private _options?: ProtocolOptions) {
    this.setNotificationHandler(CancelledNotificationSchema, (notification) => {
      const controller = this._requestHandlerAbortControllers.get(
        notification.params.requestId,
      );
      controller?.abort(notification.params.reason);
    });

    this.setNotificationHandler(ProgressNotificationSchema, (notification) => {
      this._onprogress(notification as unknown as ProgressNotification);
    });

    this.setRequestHandler(
      PingRequestSchema,
      // Automatic pong by default.
      (_request) => ({}) as SendResultT,
    );
  }

  private _setupTimeout(
    messageId: number,
    timeout: number,
    maxTotalTimeout: number | undefined,
    onTimeout: () => void,
    resetTimeoutOnProgress: boolean = false
  ) {
    this._timeoutInfo.set(messageId, {
      timeoutId: setTimeout(onTimeout, timeout),
      startTime: Date.now(),
      timeout,
      maxTotalTimeout,
      resetTimeoutOnProgress,
      onTimeout
    });
  }

  private _resetTimeout(messageId: number): boolean {
    const info = this._timeoutInfo.get(messageId);
    if (!info) return false;

    const totalElapsed = Date.now() - info.startTime;
    if (info.maxTotalTimeout && totalElapsed >= info.maxTotalTimeout) {
      this._timeoutInfo.delete(messageId);
      throw new McpError(
        ErrorCode.RequestTimeout,
        "Maximum total timeout exceeded",
        { maxTotalTimeout: info.maxTotalTimeout, totalElapsed }
      );
    }

    clearTimeout(info.timeoutId);
    info.timeoutId = setTimeout(info.onTimeout, info.timeout);
    return true;
  }

  private _cleanupTimeout(messageId: number) {
    const info = this._timeoutInfo.get(messageId);
    if (info) {
      clearTimeout(info.timeoutId);
      this._timeoutInfo.delete(messageId);
    }
  }

  /**
   * Attaches to the given transport, starts it, and starts listening for messages.
   *
   * The Protocol object assumes ownership of the Transport, replacing any callbacks that have already been set, and expects that it is the only user of the Transport instance going forward.
   */
  async connect(transport: Transport): Promise<void> {
    this._transport = transport;
    const _onclose = this.transport?.onclose;
    this._transport.onclose = () => {
      _onclose?.();
      this._onclose();
    };

    const _onerror = this.transport?.onerror;
    this._transport.onerror = (error: Error) => {
      _onerror?.(error);
      this._onerror(error);
    };

    const _onmessage = this._transport?.onmessage;
    this._transport.onmessage = (message, extra) => {
      _onmessage?.(message, extra);
      if (isJSONRPCResponse(message) || isJSONRPCError(message)) {
        this._onresponse(message);
      } else if (isJSONRPCRequest(message)) {
        this._onrequest(message, extra);
      } else if (isJSONRPCNotification(message)) {
        this._onnotification(message);
      } else {
        this._onerror(
          new Error(`Unknown message type: ${JSON.stringify(message)}`),
        );
      }
    };

    await this._transport.start();
  }

  private _onclose(): void {
    const responseHandlers = this._responseHandlers;
    this._responseHandlers = new Map();
    this._progressHandlers.clear();
    this._pendingDebouncedNotifications.clear();
    this._transport = undefined;
    this.onclose?.();

    const error = new McpError(ErrorCode.ConnectionClosed, "Connection closed");
    for (const handler of responseHandlers.values()) {
      handler(error);
    }
  }

  private _onerror(error: Error): void {
    this.onerror?.(error);
  }

  private _onnotification(notification: JSONRPCNotification): void {
    const handler =
      this._notificationHandlers.get(notification.method) ??
      this.fallbackNotificationHandler;

    // Ignore notifications not being subscribed to.
    if (handler === undefined) {
      return;
    }

    // Starting with Promise.resolve() puts any synchronous errors into the monad as well.
    Promise.resolve()
      .then(() => handler(notification))
      .catch((error) =>
        this._onerror(
          new Error(`Uncaught error in notification handler: ${error}`),
        ),
      );
  }

  private _onrequest(request: JSONRPCRequest, extra?: MessageExtraInfo): void {
    const handler =
      this._requestHandlers.get(request.method) ?? this.fallbackRequestHandler;

    // Capture the current transport at request time to ensure responses go to the correct client
    const capturedTransport = this._transport;

    if (handler === undefined) {
      capturedTransport
        ?.send({
          jsonrpc: "2.0",
          id: request.id,
          error: {
            code: ErrorCode.MethodNotFound,
            message: "Method not found",
          },
        })
        .catch((error) =>
          this._onerror(
            new Error(`Failed to send an error response: ${error}`),
          ),
        );
      return;
    }

    const abortController = new AbortController();
    this._requestHandlerAbortControllers.set(request.id, abortController);

    const fullExtra: RequestHandlerExtra<SendRequestT, SendNotificationT> = {
      signal: abortController.signal,
      sessionId: capturedTransport?.sessionId,
      _meta: request.params?._meta,
      sendNotification:
        (notification) =>
          this.notification(notification, { relatedRequestId: request.id }),
      sendRequest: (r, resultSchema, options?) =>
        this.request(r, resultSchema, { ...options, relatedRequestId: request.id }),
      authInfo: extra?.authInfo,
      requestId: request.id,
      requestInfo: extra?.requestInfo
    };

    // Starting with Promise.resolve() puts any synchronous errors into the monad as well.
    Promise.resolve()
      .then(() => handler(request, fullExtra))
      .then(
        (result) => {
          if (abortController.signal.aborted) {
            return;
          }

          return capturedTransport?.send({
            result,
            jsonrpc: "2.0",
            id: request.id,
          });
        },
        (error) => {
          if (abortController.signal.aborted) {
            return;
          }

          return capturedTransport?.send({
            jsonrpc: "2.0",
            id: request.id,
            error: {
              code: Number.isSafeInteger(error["code"])
                ? error["code"]
                : ErrorCode.InternalError,
              message: error.message ?? "Internal error",
            },
          });
        },
      )
      .catch((error) =>
        this._onerror(new Error(`Failed to send response: ${error}`)),
      )
      .finally(() => {
        this._requestHandlerAbortControllers.delete(request.id);
      });
  }

  private _onprogress(notification: ProgressNotification): void {
    const { progressToken, ...params } = notification.params;
    const messageId = Number(progressToken);

    const handler = this._progressHandlers.get(messageId);
    if (!handler) {
      this._onerror(new Error(`Received a progress notification for an unknown token: ${JSON.stringify(notification)}`));
      return;
    }

    const responseHandler = this._responseHandlers.get(messageId);
    const timeoutInfo = this._timeoutInfo.get(messageId);

    if (timeoutInfo && responseHandler && timeoutInfo.resetTimeoutOnProgress) {
      try {
        this._resetTimeout(messageId);
      } catch (error) {
        responseHandler(error as Error);
        return;
      }
    }

    handler(params);
  }

  private _onresponse(response: JSONRPCResponse | JSONRPCError): void {
    const messageId = Number(response.id);
    const handler = this._responseHandlers.get(messageId);
    if (handler === undefined) {
      this._onerror(
        new Error(
          `Received a response for an unknown message ID: ${JSON.stringify(response)}`,
        ),
      );
      return;
    }

    this._responseHandlers.delete(messageId);
    this._progressHandlers.delete(messageId);
    this._cleanupTimeout(messageId);

    if (isJSONRPCResponse(response)) {
      handler(response);
    } else {
      const error = new McpError(
        response.error.code,
        response.error.message,
        response.error.data,
      );
      handler(error);
    }
  }

  get transport(): Transport | undefined {
    return this._transport;
  }

  /**
   * Closes the connection.
   */
  async close(): Promise<void> {
    await this._transport?.close();
  }

  /**
   * A method to check if a capability is supported by the remote side, for the given method to be called.
   *
   * This should be implemented by subclasses.
   */
  protected abstract assertCapabilityForMethod(
    method: SendRequestT["method"],
  ): void;

  /**
   * A method to check if a notification is supported by the local side, for the given method to be sent.
   *
   * This should be implemented by subclasses.
   */
  protected abstract assertNotificationCapability(
    method: SendNotificationT["method"],
  ): void;

  /**
   * A method to check if a request handler is supported by the local side, for the given method to be handled.
   *
   * This should be implemented by subclasses.
   */
  protected abstract assertRequestHandlerCapability(method: string): void;

  /**
   * Sends a request and wait for a response.
   *
   * Do not use this method to emit notifications! Use notification() instead.
   */
  request<T extends ZodType<object>>(
    request: SendRequestT,
    resultSchema: T,
    options?: RequestOptions,
  ): Promise<z.infer<T>> {
    const { relatedRequestId, resumptionToken, onresumptiontoken } = options ?? {};

    return new Promise((resolve, reject) => {
      if (!this._transport) {
        reject(new Error("Not connected"));
        return;
      }

      if (this._options?.enforceStrictCapabilities === true) {
        this.assertCapabilityForMethod(request.method);
      }

      options?.signal?.throwIfAborted();

      const messageId = this._requestMessageId++;
      const jsonrpcRequest: JSONRPCRequest = {
        ...request,
        jsonrpc: "2.0",
        id: messageId,
      };

      if (options?.onprogress) {
        this._progressHandlers.set(messageId, options.onprogress);
        jsonrpcRequest.params = {
          ...request.params,
          _meta: {
            ...(request.params?._meta || {}),
            progressToken: messageId
          },
        };
      }

      const cancel = (reason: unknown) => {
        this._responseHandlers.delete(messageId);
        this._progressHandlers.delete(messageId);
        this._cleanupTimeout(messageId);

        this._transport
          ?.send({
            jsonrpc: "2.0",
            method: "notifications/cancelled",
            params: {
              requestId: messageId,
              reason: String(reason),
            },
          }, { relatedRequestId, resumptionToken, onresumptiontoken })
          .catch((error) =>
            this._onerror(new Error(`Failed to send cancellation: ${error}`)),
          );

        reject(reason);
      };

      this._responseHandlers.set(messageId, (response) => {
        if (options?.signal?.aborted) {
          return;
        }

        if (response instanceof Error) {
          return reject(response);
        }

        try {
          const result = resultSchema.parse(response.result);
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });

      options?.signal?.addEventListener("abort", () => {
        cancel(options?.signal?.reason);
      });

      const timeout = options?.timeout ?? DEFAULT_REQUEST_TIMEOUT_MSEC;
      const timeoutHandler = () => cancel(new McpError(
        ErrorCode.RequestTimeout,
        "Request timed out",
        { timeout }
      ));

      this._setupTimeout(messageId, timeout, options?.maxTotalTimeout, timeoutHandler, options?.resetTimeoutOnProgress ?? false);

      this._transport.send(jsonrpcRequest, { relatedRequestId, resumptionToken, onresumptiontoken }).catch((error) => {
        this._cleanupTimeout(messageId);
        reject(error);
      });
    });
  }

  /**
   * Emits a notification, which is a one-way message that does not expect a response.
   */
  async notification(notification: SendNotificationT, options?: NotificationOptions): Promise<void> {
    if (!this._transport) {
      throw new Error("Not connected");
    }

    this.assertNotificationCapability(notification.method);

    const debouncedMethods = this._options?.debouncedNotificationMethods ?? [];
    // A notification can only be debounced if it's in the list AND it's "simple"
    // (i.e., has no parameters and no related request ID that could be lost).
    const canDebounce = debouncedMethods.includes(notification.method)
      && !notification.params
      && !(options?.relatedRequestId);

    if (canDebounce) {
      // If a notification of this type is already scheduled, do nothing.
      if (this._pendingDebouncedNotifications.has(notification.method)) {
        return;
      }

      // Mark this notification type as pending.
      this._pendingDebouncedNotifications.add(notification.method);

      // Schedule the actual send to happen in the next microtask.
      // This allows all synchronous calls in the current event loop tick to be coalesced.
      Promise.resolve().then(() => {
        // Un-mark the notification so the next one can be scheduled.
        this._pendingDebouncedNotifications.delete(notification.method);

        // SAFETY CHECK: If the connection was closed while this was pending, abort.
        if (!this._transport) {
          return;
        }

        const jsonrpcNotification: JSONRPCNotification = {
          ...notification,
          jsonrpc: "2.0",
        };
        // Send the notification, but don't await it here to avoid blocking.
        // Handle potential errors with a .catch().
        this._transport?.send(jsonrpcNotification, options).catch(error => this._onerror(error));
      });

      // Return immediately.
      return;
    }

    const jsonrpcNotification: JSONRPCNotification = {
      ...notification,
      jsonrpc: "2.0",
    };

    await this._transport.send(jsonrpcNotification, options);
  }

  /**
   * Registers a handler to invoke when this protocol object receives a request with the given method.
   *
   * Note that this will replace any previous request handler for the same method.
   */
  setRequestHandler<
    T extends ZodObject<{
      method: ZodLiteral<string>;
    }>,
  >(
    requestSchema: T,
    handler: (
      request: z.infer<T>,
      extra: RequestHandlerExtra<SendRequestT, SendNotificationT>,
    ) => SendResultT | Promise<SendResultT>,
  ): void {
    const method = requestSchema.shape.method.value;
    this.assertRequestHandlerCapability(method);

    this._requestHandlers.set(method, (request, extra) => {
      return Promise.resolve(handler(requestSchema.parse(request), extra));
    });
  }

  /**
   * Removes the request handler for the given method.
   */
  removeRequestHandler(method: string): void {
    this._requestHandlers.delete(method);
  }

  /**
   * Asserts that a request handler has not already been set for the given method, in preparation for a new one being automatically installed.
   */
  assertCanSetRequestHandler(method: string): void {
    if (this._requestHandlers.has(method)) {
      throw new Error(
        `A request handler for ${method} already exists, which would be overridden`,
      );
    }
  }

  /**
   * Registers a handler to invoke when this protocol object receives a notification with the given method.
   *
   * Note that this will replace any previous notification handler for the same method.
   */
  setNotificationHandler<
    T extends ZodObject<{
      method: ZodLiteral<string>;
    }>,
  >(
    notificationSchema: T,
    handler: (notification: z.infer<T>) => void | Promise<void>,
  ): void {
    this._notificationHandlers.set(
      notificationSchema.shape.method.value,
      (notification) =>
        Promise.resolve(handler(notificationSchema.parse(notification))),
    );
  }

  /**
   * Removes the notification handler for the given method.
   */
  removeNotificationHandler(method: string): void {
    this._notificationHandlers.delete(method);
  }
}

export function mergeCapabilities<
  T extends ServerCapabilities | ClientCapabilities,
>(base: T, additional: T): T {
  return Object.entries(additional).reduce(
    (acc, [key, value]) => {
      if (value && typeof value === "object") {
        acc[key] = acc[key] ? { ...acc[key], ...value } : value;
      } else {
        acc[key] = value;
      }
      return acc;
    },
    { ...base },
  );
}



================================================
FILE: src/shared/stdio.test.ts
================================================
import { JSONRPCMessage } from "../types.js";
import { ReadBuffer } from "./stdio.js";

const testMessage: JSONRPCMessage = {
  jsonrpc: "2.0",
  method: "foobar",
};

test("should have no messages after initialization", () => {
  const readBuffer = new ReadBuffer();
  expect(readBuffer.readMessage()).toBeNull();
});

test("should only yield a message after a newline", () => {
  const readBuffer = new ReadBuffer();

  readBuffer.append(Buffer.from(JSON.stringify(testMessage)));
  expect(readBuffer.readMessage()).toBeNull();

  readBuffer.append(Buffer.from("\n"));
  expect(readBuffer.readMessage()).toEqual(testMessage);
  expect(readBuffer.readMessage()).toBeNull();
});

test("should be reusable after clearing", () => {
  const readBuffer = new ReadBuffer();

  readBuffer.append(Buffer.from("foobar"));
  readBuffer.clear();
  expect(readBuffer.readMessage()).toBeNull();

  readBuffer.append(Buffer.from(JSON.stringify(testMessage)));
  readBuffer.append(Buffer.from("\n"));
  expect(readBuffer.readMessage()).toEqual(testMessage);
});



================================================
FILE: src/shared/stdio.ts
================================================
import { JSONRPCMessage, JSONRPCMessageSchema } from "../types.js";

/**
 * Buffers a continuous stdio stream into discrete JSON-RPC messages.
 */
export class ReadBuffer {
  private _buffer?: Buffer;

  append(chunk: Buffer): void {
    this._buffer = this._buffer ? Buffer.concat([this._buffer, chunk]) : chunk;
  }

  readMessage(): JSONRPCMessage | null {
    if (!this._buffer) {
      return null;
    }

    const index = this._buffer.indexOf("\n");
    if (index === -1) {
      return null;
    }

    const line = this._buffer.toString("utf8", 0, index).replace(/\r$/, '');
    this._buffer = this._buffer.subarray(index + 1);
    return deserializeMessage(line);
  }

  clear(): void {
    this._buffer = undefined;
  }
}

export function deserializeMessage(line: string): JSONRPCMessage {
  return JSONRPCMessageSchema.parse(JSON.parse(line));
}

export function serializeMessage(message: JSONRPCMessage): string {
  return JSON.stringify(message) + "\n";
}



================================================
FILE: src/shared/transport.ts
================================================
import { JSONRPCMessage, MessageExtraInfo, RequestId } from "../types.js";

export type FetchLike = (url: string | URL, init?: RequestInit) => Promise<Response>;

/**
 * Options for sending a JSON-RPC message.
 */
export type TransportSendOptions = {
  /**
   * If present, `relatedRequestId` is used to indicate to the transport which incoming request to associate this outgoing message with.
   */
  relatedRequestId?: RequestId;

  /**
   * The resumption token used to continue long-running requests that were interrupted.
   *
   * This allows clients to reconnect and continue from where they left off, if supported by the transport.
   */
  resumptionToken?: string;

  /**
   * A callback that is invoked when the resumption token changes, if supported by the transport.
   *
   * This allows clients to persist the latest token for potential reconnection.
   */
  onresumptiontoken?: (token: string) => void;
}
/**
 * Describes the minimal contract for a MCP transport that a client or server can communicate over.
 */
export interface Transport {
  /**
   * Starts processing messages on the transport, including any connection steps that might need to be taken.
   *
   * This method should only be called after callbacks are installed, or else messages may be lost.
   *
   * NOTE: This method should not be called explicitly when using Client, Server, or Protocol classes, as they will implicitly call start().
   */
  start(): Promise<void>;

  /**
   * Sends a JSON-RPC message (request or response).
   *
   * If present, `relatedRequestId` is used to indicate to the transport which incoming request to associate this outgoing message with.
   */
  send(message: JSONRPCMessage, options?: TransportSendOptions): Promise<void>;

  /**
   * Closes the connection.
   */
  close(): Promise<void>;

  /**
   * Callback for when the connection is closed for any reason.
   *
   * This should be invoked when close() is called as well.
   */
  onclose?: () => void;

  /**
   * Callback for when an error occurs.
   *
   * Note that errors are not necessarily fatal; they are used for reporting any kind of exceptional condition out of band.
   */
  onerror?: (error: Error) => void;

  /**
   * Callback for when a message (request or response) is received over the connection.
   *
   * Includes the requestInfo and authInfo if the transport is authenticated.
   *
   * The requestInfo can be used to get the original request information (headers, etc.)
   */
  onmessage?: (message: JSONRPCMessage, extra?: MessageExtraInfo) => void;

  /**
   * The session ID generated for this connection.
   */
  sessionId?: string;

  /**
   * Sets the protocol version used for the connection (called when the initialize response is received).
   */
  setProtocolVersion?: (version: string) => void;
}



================================================
FILE: src/shared/uriTemplate.test.ts
================================================
import { UriTemplate } from "./uriTemplate.js";

describe("UriTemplate", () => {
  describe("isTemplate", () => {
    it("should return true for strings containing template expressions", () => {
      expect(UriTemplate.isTemplate("{foo}")).toBe(true);
      expect(UriTemplate.isTemplate("/users/{id}")).toBe(true);
      expect(UriTemplate.isTemplate("http://example.com/{path}/{file}")).toBe(true);
      expect(UriTemplate.isTemplate("/search{?q,limit}")).toBe(true);
    });

    it("should return false for strings without template expressions", () => {
      expect(UriTemplate.isTemplate("")).toBe(false);
      expect(UriTemplate.isTemplate("plain string")).toBe(false);
      expect(UriTemplate.isTemplate("http://example.com/foo/bar")).toBe(false);
      expect(UriTemplate.isTemplate("{}")).toBe(false); // Empty braces don't count
      expect(UriTemplate.isTemplate("{ }")).toBe(false); // Just whitespace doesn't count
    });
  });

  describe("simple string expansion", () => {
    it("should expand simple string variables", () => {
      const template = new UriTemplate("http://example.com/users/{username}");
      expect(template.expand({ username: "fred" })).toBe(
        "http://example.com/users/fred",
      );
      expect(template.variableNames).toEqual(['username'])
    });

    it("should handle multiple variables", () => {
      const template = new UriTemplate("{x,y}");
      expect(template.expand({ x: "1024", y: "768" })).toBe("1024,768");
      expect(template.variableNames).toEqual(['x', 'y'])
    });

    it("should encode reserved characters", () => {
      const template = new UriTemplate("{var}");
      expect(template.expand({ var: "value with spaces" })).toBe(
        "value%20with%20spaces",
      );
    });
  });

  describe("reserved expansion", () => {
    it("should not encode reserved characters with + operator", () => {
      const template = new UriTemplate("{+path}/here");
      expect(template.expand({ path: "/foo/bar" })).toBe("/foo/bar/here");
      expect(template.variableNames).toEqual(['path'])
    });
  });

  describe("fragment expansion", () => {
    it("should add # prefix and not encode reserved chars", () => {
      const template = new UriTemplate("X{#var}");
      expect(template.expand({ var: "/test" })).toBe("X#/test");
      expect(template.variableNames).toEqual(['var'])
    });
  });

  describe("label expansion", () => {
    it("should add . prefix", () => {
      const template = new UriTemplate("X{.var}");
      expect(template.expand({ var: "test" })).toBe("X.test");
      expect(template.variableNames).toEqual(['var'])
    });
  });

  describe("path expansion", () => {
    it("should add / prefix", () => {
      const template = new UriTemplate("X{/var}");
      expect(template.expand({ var: "test" })).toBe("X/test");
      expect(template.variableNames).toEqual(['var'])
    });
  });

  describe("query expansion", () => {
    it("should add ? prefix and name=value format", () => {
      const template = new UriTemplate("X{?var}");
      expect(template.expand({ var: "test" })).toBe("X?var=test");
      expect(template.variableNames).toEqual(['var'])
    });
  });

  describe("form continuation expansion", () => {
    it("should add & prefix and name=value format", () => {
      const template = new UriTemplate("X{&var}");
      expect(template.expand({ var: "test" })).toBe("X&var=test");
      expect(template.variableNames).toEqual(['var'])
    });
  });

  describe("matching", () => {
    it("should match simple strings and extract variables", () => {
      const template = new UriTemplate("http://example.com/users/{username}");
      const match = template.match("http://example.com/users/fred");
      expect(match).toEqual({ username: "fred" });
    });

    it("should match multiple variables", () => {
      const template = new UriTemplate("/users/{username}/posts/{postId}");
      const match = template.match("/users/fred/posts/123");
      expect(match).toEqual({ username: "fred", postId: "123" });
    });

    it("should return null for non-matching URIs", () => {
      const template = new UriTemplate("/users/{username}");
      const match = template.match("/posts/123");
      expect(match).toBeNull();
    });

    it("should handle exploded arrays", () => {
      const template = new UriTemplate("{/list*}");
      const match = template.match("/red,green,blue");
      expect(match).toEqual({ list: ["red", "green", "blue"] });
    });
  });

  describe("edge cases", () => {
    it("should handle empty variables", () => {
      const template = new UriTemplate("{empty}");
      expect(template.expand({})).toBe("");
      expect(template.expand({ empty: "" })).toBe("");
    });

    it("should handle undefined variables", () => {
      const template = new UriTemplate("{a}{b}{c}");
      expect(template.expand({ b: "2" })).toBe("2");
    });

    it("should handle special characters in variable names", () => {
      const template = new UriTemplate("{$var_name}");
      expect(template.expand({ "$var_name": "value" })).toBe("value");
    });
  });

  describe("complex patterns", () => {
    it("should handle nested path segments", () => {
      const template = new UriTemplate("/api/{version}/{resource}/{id}");
      expect(template.expand({
        version: "v1",
        resource: "users",
        id: "123"
      })).toBe("/api/v1/users/123");
      expect(template.variableNames).toEqual(['version', 'resource', 'id'])
    });

    it("should handle query parameters with arrays", () => {
      const template = new UriTemplate("/search{?tags*}");
      expect(template.expand({
        tags: ["nodejs", "typescript", "testing"]
      })).toBe("/search?tags=nodejs,typescript,testing");
      expect(template.variableNames).toEqual(['tags'])
    });

    it("should handle multiple query parameters", () => {
      const template = new UriTemplate("/search{?q,page,limit}");
      expect(template.expand({
        q: "test",
        page: "1",
        limit: "10"
      })).toBe("/search?q=test&page=1&limit=10");
      expect(template.variableNames).toEqual(['q', 'page', 'limit'])
    });
  });

  describe("matching complex patterns", () => {
    it("should match nested path segments", () => {
      const template = new UriTemplate("/api/{version}/{resource}/{id}");
      const match = template.match("/api/v1/users/123");
      expect(match).toEqual({
        version: "v1",
        resource: "users",
        id: "123"
      });
      expect(template.variableNames).toEqual(['version', 'resource', 'id'])
    });

    it("should match query parameters", () => {
      const template = new UriTemplate("/search{?q}");
      const match = template.match("/search?q=test");
      expect(match).toEqual({ q: "test" });
      expect(template.variableNames).toEqual(['q'])
    });

    it("should match multiple query parameters", () => {
      const template = new UriTemplate("/search{?q,page}");
      const match = template.match("/search?q=test&page=1");
      expect(match).toEqual({ q: "test", page: "1" });
      expect(template.variableNames).toEqual(['q', 'page'])
    });

    it("should handle partial matches correctly", () => {
      const template = new UriTemplate("/users/{id}");
      expect(template.match("/users/123/extra")).toBeNull();
      expect(template.match("/users")).toBeNull();
    });
  });

  describe("security and edge cases", () => {
    it("should handle extremely long input strings", () => {
      const longString = "x".repeat(100000);
      const template = new UriTemplate(`/api/{param}`);
      expect(template.expand({ param: longString })).toBe(`/api/${longString}`);
      expect(template.match(`/api/${longString}`)).toEqual({ param: longString });
    });

    it("should handle deeply nested template expressions", () => {
      const template = new UriTemplate("{a}{b}{c}{d}{e}{f}{g}{h}{i}{j}".repeat(1000));
      expect(() => template.expand({
        a: "1", b: "2", c: "3", d: "4", e: "5",
        f: "6", g: "7", h: "8", i: "9", j: "0"
      })).not.toThrow();
    });

    it("should handle malformed template expressions", () => {
      expect(() => new UriTemplate("{unclosed")).toThrow();
      expect(() => new UriTemplate("{}")).not.toThrow();
      expect(() => new UriTemplate("{,}")).not.toThrow();
      expect(() => new UriTemplate("{a}{")).toThrow();
    });

    it("should handle pathological regex patterns", () => {
      const template = new UriTemplate("/api/{param}");
      // Create a string that could cause catastrophic backtracking
      const input = "/api/" + "a".repeat(100000);
      expect(() => template.match(input)).not.toThrow();
    });

    it("should handle invalid UTF-8 sequences", () => {
      const template = new UriTemplate("/api/{param}");
      const invalidUtf8 = "���";
      expect(() => template.expand({ param: invalidUtf8 })).not.toThrow();
      expect(() => template.match(`/api/${invalidUtf8}`)).not.toThrow();
    });

    it("should handle template/URI length mismatches", () => {
      const template = new UriTemplate("/api/{param}");
      expect(template.match("/api/")).toBeNull();
      expect(template.match("/api")).toBeNull();
      expect(template.match("/api/value/extra")).toBeNull();
    });

    it("should handle repeated operators", () => {
      const template = new UriTemplate("{?a}{?b}{?c}");
      expect(template.expand({ a: "1", b: "2", c: "3" })).toBe("?a=1&b=2&c=3");
      expect(template.variableNames).toEqual(['a', 'b', 'c'])
    });

    it("should handle overlapping variable names", () => {
      const template = new UriTemplate("{var}{vara}");
      expect(template.expand({ var: "1", vara: "2" })).toBe("12");
      expect(template.variableNames).toEqual(['var', 'vara'])
    });

    it("should handle empty segments", () => {
      const template = new UriTemplate("///{a}////{b}////");
      expect(template.expand({ a: "1", b: "2" })).toBe("///1////2////");
      expect(template.match("///1////2////")).toEqual({ a: "1", b: "2" });
      expect(template.variableNames).toEqual(['a', 'b'])
    });

    it("should handle maximum template expression limit", () => {
      // Create a template with many expressions
      const expressions = Array(10000).fill("{param}").join("");
      expect(() => new UriTemplate(expressions)).not.toThrow();
    });

    it("should handle maximum variable name length", () => {
      const longName = "a".repeat(10000);
      const template = new UriTemplate(`{${longName}}`);
      const vars: Record<string, string> = {};
      vars[longName] = "value";
      expect(() => template.expand(vars)).not.toThrow();
    });
  });
});



================================================
FILE: src/shared/uriTemplate.ts
================================================
// Claude-authored implementation of RFC 6570 URI Templates

export type Variables = Record<string, string | string[]>;

const MAX_TEMPLATE_LENGTH = 1000000; // 1MB
const MAX_VARIABLE_LENGTH = 1000000; // 1MB
const MAX_TEMPLATE_EXPRESSIONS = 10000;
const MAX_REGEX_LENGTH = 1000000; // 1MB

export class UriTemplate {
  /**
   * Returns true if the given string contains any URI template expressions.
   * A template expression is a sequence of characters enclosed in curly braces,
   * like {foo} or {?bar}.
   */
  static isTemplate(str: string): boolean {
    // Look for any sequence of characters between curly braces
    // that isn't just whitespace
    return /\{[^}\s]+\}/.test(str);
  }

  private static validateLength(
    str: string,
    max: number,
    context: string,
  ): void {
    if (str.length > max) {
      throw new Error(
        `${context} exceeds maximum length of ${max} characters (got ${str.length})`,
      );
    }
  }
  private readonly template: string;
  private readonly parts: Array<
    | string
    | { name: string; operator: string; names: string[]; exploded: boolean }
  >;

  get variableNames(): string[] {
    return this.parts.flatMap((part) => typeof part === 'string' ? [] : part.names);
  }

  constructor(template: string) {
    UriTemplate.validateLength(template, MAX_TEMPLATE_LENGTH, "Template");
    this.template = template;
    this.parts = this.parse(template);
  }

  toString(): string {
    return this.template;
  }

  private parse(
    template: string,
  ): Array<
    | string
    | { name: string; operator: string; names: string[]; exploded: boolean }
  > {
    const parts: Array<
      | string
      | { name: string; operator: string; names: string[]; exploded: boolean }
    > = [];
    let currentText = "";
    let i = 0;
    let expressionCount = 0;

    while (i < template.length) {
      if (template[i] === "{") {
        if (currentText) {
          parts.push(currentText);
          currentText = "";
        }
        const end = template.indexOf("}", i);
        if (end === -1) throw new Error("Unclosed template expression");

        expressionCount++;
        if (expressionCount > MAX_TEMPLATE_EXPRESSIONS) {
          throw new Error(
            `Template contains too many expressions (max ${MAX_TEMPLATE_EXPRESSIONS})`,
          );
        }

        const expr = template.slice(i + 1, end);
        const operator = this.getOperator(expr);
        const exploded = expr.includes("*");
        const names = this.getNames(expr);
        const name = names[0];

        // Validate variable name length
        for (const name of names) {
          UriTemplate.validateLength(
            name,
            MAX_VARIABLE_LENGTH,
            "Variable name",
          );
        }

        parts.push({ name, operator, names, exploded });
        i = end + 1;
      } else {
        currentText += template[i];
        i++;
      }
    }

    if (currentText) {
      parts.push(currentText);
    }

    return parts;
  }

  private getOperator(expr: string): string {
    const operators = ["+", "#", ".", "/", "?", "&"];
    return operators.find((op) => expr.startsWith(op)) || "";
  }

  private getNames(expr: string): string[] {
    const operator = this.getOperator(expr);
    return expr
      .slice(operator.length)
      .split(",")
      .map((name) => name.replace("*", "").trim())
      .filter((name) => name.length > 0);
  }

  private encodeValue(value: string, operator: string): string {
    UriTemplate.validateLength(value, MAX_VARIABLE_LENGTH, "Variable value");
    if (operator === "+" || operator === "#") {
      return encodeURI(value);
    }
    return encodeURIComponent(value);
  }

  private expandPart(
    part: {
      name: string;
      operator: string;
      names: string[];
      exploded: boolean;
    },
    variables: Variables,
  ): string {
    if (part.operator === "?" || part.operator === "&") {
      const pairs = part.names
        .map((name) => {
          const value = variables[name];
          if (value === undefined) return "";
          const encoded = Array.isArray(value)
            ? value.map((v) => this.encodeValue(v, part.operator)).join(",")
            : this.encodeValue(value.toString(), part.operator);
          return `${name}=${encoded}`;
        })
        .filter((pair) => pair.length > 0);

      if (pairs.length === 0) return "";
      const separator = part.operator === "?" ? "?" : "&";
      return separator + pairs.join("&");
    }

    if (part.names.length > 1) {
      const values = part.names
        .map((name) => variables[name])
        .filter((v) => v !== undefined);
      if (values.length === 0) return "";
      return values.map((v) => (Array.isArray(v) ? v[0] : v)).join(",");
    }

    const value = variables[part.name];
    if (value === undefined) return "";

    const values = Array.isArray(value) ? value : [value];
    const encoded = values.map((v) => this.encodeValue(v, part.operator));

    switch (part.operator) {
      case "":
        return encoded.join(",");
      case "+":
        return encoded.join(",");
      case "#":
        return "#" + encoded.join(",");
      case ".":
        return "." + encoded.join(".");
      case "/":
        return "/" + encoded.join("/");
      default:
        return encoded.join(",");
    }
  }

  expand(variables: Variables): string {
    let result = "";
    let hasQueryParam = false;

    for (const part of this.parts) {
      if (typeof part === "string") {
        result += part;
        continue;
      }

      const expanded = this.expandPart(part, variables);
      if (!expanded) continue;

      // Convert ? to & if we already have a query parameter
      if ((part.operator === "?" || part.operator === "&") && hasQueryParam) {
        result += expanded.replace("?", "&");
      } else {
        result += expanded;
      }

      if (part.operator === "?" || part.operator === "&") {
        hasQueryParam = true;
      }
    }

    return result;
  }

  private escapeRegExp(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  private partToRegExp(part: {
    name: string;
    operator: string;
    names: string[];
    exploded: boolean;
  }): Array<{ pattern: string; name: string }> {
    const patterns: Array<{ pattern: string; name: string }> = [];

    // Validate variable name length for matching
    for (const name of part.names) {
      UriTemplate.validateLength(name, MAX_VARIABLE_LENGTH, "Variable name");
    }

    if (part.operator === "?" || part.operator === "&") {
      for (let i = 0; i < part.names.length; i++) {
        const name = part.names[i];
        const prefix = i === 0 ? "\\" + part.operator : "&";
        patterns.push({
          pattern: prefix + this.escapeRegExp(name) + "=([^&]+)",
          name,
        });
      }
      return patterns;
    }

    let pattern: string;
    const name = part.name;

    switch (part.operator) {
      case "":
        pattern = part.exploded ? "([^/]+(?:,[^/]+)*)" : "([^/,]+)";
        break;
      case "+":
      case "#":
        pattern = "(.+)";
        break;
      case ".":
        pattern = "\\.([^/,]+)";
        break;
      case "/":
        pattern = "/" + (part.exploded ? "([^/]+(?:,[^/]+)*)" : "([^/,]+)");
        break;
      default:
        pattern = "([^/]+)";
    }

    patterns.push({ pattern, name });
    return patterns;
  }

  match(uri: string): Variables | null {
    UriTemplate.validateLength(uri, MAX_TEMPLATE_LENGTH, "URI");
    let pattern = "^";
    const names: Array<{ name: string; exploded: boolean }> = [];

    for (const part of this.parts) {
      if (typeof part === "string") {
        pattern += this.escapeRegExp(part);
      } else {
        const patterns = this.partToRegExp(part);
        for (const { pattern: partPattern, name } of patterns) {
          pattern += partPattern;
          names.push({ name, exploded: part.exploded });
        }
      }
    }

    pattern += "$";
    UriTemplate.validateLength(
      pattern,
      MAX_REGEX_LENGTH,
      "Generated regex pattern",
    );
    const regex = new RegExp(pattern);
    const match = uri.match(regex);

    if (!match) return null;

    const result: Variables = {};
    for (let i = 0; i < names.length; i++) {
      const { name, exploded } = names[i];
      const value = match[i + 1];
      const cleanName = name.replace("*", "");

      if (exploded && value.includes(",")) {
        result[cleanName] = value.split(",");
      } else {
        result[cleanName] = value;
      }
    }

    return result;
  }
}



================================================
FILE: .github/CODEOWNERS
================================================
# TypeScript SDK Code Owners

# Default owners for everything in the repo
* @modelcontextprotocol/typescript-sdk

# Auth team owns all auth-related code
/src/server/auth/ @modelcontextprotocol/typescript-sdk-auth
/src/client/auth* @modelcontextprotocol/typescript-sdk-auth
/src/shared/auth* @modelcontextprotocol/typescript-sdk-auth
/src/examples/client/simpleOAuthClient.ts @modelcontextprotocol/typescript-sdk-auth
/src/examples/server/demoInMemoryOAuthProvider.ts @modelcontextprotocol/typescript-sdk-auth


================================================
FILE: .github/workflows/main.yml
================================================
on:
  push:
    branches:
      - main
  pull_request:
  release:
    types: [published]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
          cache: npm

      - run: npm ci
      - run: npm run build
      - run: npm test
      - run: npm run lint

  publish:
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    environment: release
    needs: build

    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
          cache: npm
          registry-url: 'https://registry.npmjs.org'

      - run: npm ci

      - run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}


