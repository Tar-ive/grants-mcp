# Grants Search MCP Server

This project is an MCP (Model Context Protocol) server that provides a tool to search for government grants based on keywords.

# Video Introduction
![Video Introduction](grants-mcp/mcp-grants.mp4)

## Overview

The Grants Search MCP Server is built using the `@modelcontextprotocol/sdk` package. It exposes a single tool called "search-grants" that allows users to search for available government grants based on a search query.

The server interacts with the Simpler Grants API to fetch the grant data and formats the results for display.

## Features

- Search for government grants by keyword
- Paginate the search results
- Display detailed information about each grant, including:
  - Opportunity title, number, and status
  - Funding information (award floor, award ceiling, category)
  - Dates and deadlines
  - Contact information
  - Eligibility requirements
  - Additional information URL

## Setup

1. Clone the repository and navigate to the project directory.
2. Install the required dependencies:
   - Node.js 16 or higher
   - `npm install`
3. Set the `API_KEY` environment variable with your Simpler Grants API key.
4. Start the MCP server:
   ```
   npm start
   ```

The server will start running and listen for incoming MCP client connections.

## Usage

Once the server is running, you can connect to it using an MCP client (e.g., Claude Desktop).

To use the "search-grants" tool, simply send a request with the following parameters:

- `query`: The search query (e.g., "Artificial intelligence", "Climate change")
- `page`: The page number for pagination (default: 1)
- `grantsPerPage`: The number of grants to display per page (default: 3)

The server will respond with a formatted summary of the search results, including the grant details.

## Customization

You can customize the server by modifying the following:

- `formatGrantDetails`: The function that formats the grant information for display
- `createSummary`: The function that generates the search results summary
- `API_KEY`: The Simpler Grants API key used to authenticate the requests

## Troubleshooting

If you encounter any issues, please check the server logs for more information. You can also reach out to the project maintainers for assistance.

## Contributing

If you'd like to contribute to this project, please fork the repository and submit a pull request with your changes.