#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import axios from 'axios';

const API_KEY = process.env.API_KEY;

// Update interface to match actual API response
interface Grant {
  agency: string;
  agency_code: string;
  agency_name: string;
  opportunity_id: number;
  opportunity_number: string;
  opportunity_title: string;
  opportunity_status: string;
  summary: {
    award_ceiling?: number;
    award_floor?: number;
    post_date?: string;
    close_date?: string;
    summary_description?: string;
    additional_info_url?: string;
    agency_contact_description?: string;
    agency_email_address?: string;
    agency_phone_number?: string;
    applicant_eligibility_description?: string;
  };
  category: string;
  top_level_agency_name?: string;
}

interface GrantsAPIResponse {
  data: Grant[];
  pagination_info: {
    total_records: number;
  };
  facet_counts: {
    agency: Record<string, number>;
  };
}

const server = new Server({
  name: "grantmanship",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});

const formatGrantDetails = (grant: Grant) => {
  return `
OPPORTUNITY DETAILS
------------------
Title: ${grant.opportunity_title}
Opportunity Number: ${grant.opportunity_number}
Agency: ${grant.agency_name} (${grant.agency_code})
Status: ${grant.opportunity_status}

FUNDING INFORMATION
------------------
Award Floor: ${grant.summary.award_floor ? `$${grant.summary.award_floor.toLocaleString()}` : 'Not specified'}
Award Ceiling: ${grant.summary.award_ceiling ? `$${grant.summary.award_ceiling.toLocaleString()}` : 'Not specified'}
Category: ${grant.category}

DATES AND DEADLINES
------------------
Posted Date: ${grant.summary.post_date || 'N/A'}
Close Date: ${grant.summary.close_date || 'N/A'}

CONTACT INFORMATION
------------------
Agency Contact: ${grant.summary.agency_contact_description || 'Not provided'}
Email: ${grant.summary.agency_email_address || 'Not provided'}
Phone: ${grant.summary.agency_phone_number || 'Not provided'}

ELIGIBILITY
------------------
${grant.summary.applicant_eligibility_description ? 
  grant.summary.applicant_eligibility_description.replace(/<[^>]*>/g, '').trim() : 
  'Eligibility information not provided'}

ADDITIONAL INFORMATION
------------------
More Details URL: ${grant.summary.additional_info_url || 'Not available'}

Description:
${grant.summary.summary_description ? 
  grant.summary.summary_description.replace(/<[^>]*>/g, '').trim() : 
  'No description available'}

==========================================================================
`;
};

const createSummary = (grants: Grant[], searchQuery: string, page: number = 1, grantsPerPage: number = 3) => {
  const startIdx = (page - 1) * grantsPerPage;
  const endIdx = startIdx + grantsPerPage;
  const displayedGrants = grants.slice(startIdx, endIdx);
  const totalPages = Math.ceil(grants.length / grantsPerPage);

  return `Search Results for "${searchQuery}":

OVERVIEW
--------
Total Grants Found: ${grants.length}
Showing grants ${startIdx + 1} to ${Math.min(endIdx, grants.length)} of ${grants.length}
Page ${page} of ${totalPages}

DETAILED GRANT LISTINGS
----------------------
${displayedGrants.map(formatGrantDetails).join("\n")}

Note: Showing ${grantsPerPage} grants per page. Total grants available: ${grants.length}
`;
};

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [{
      name: "search-grants",
      description: "Search for government grants based on keywords",
      inputSchema: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Search query for grants (e.g., 'Artificial intelligence', 'Climate change')"
          },
          page: {
            type: "number",
            description: "Page number for pagination (default: 1)"
          },
          grantsPerPage: {
            type: "number",
            description: "Number of grants per page (default: 3)"
          }
        },
        required: ["query"]
      }
    }]
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "search-grants") {
    try {
      const args = request.params.arguments as { query?: string; page?: number; grantsPerPage?: number } | undefined;
      const searchQuery = args?.query ? String(args.query).trim() : "Artificial intelligence";
      const page = args?.page || 1;
      const grantsPerPage = args?.grantsPerPage || 3;
      
      console.error(`Debug: Starting search with query: ${searchQuery}, page: ${page}, grantsPerPage: ${grantsPerPage}`);

      const url = 'https://api.simpler.grants.gov/v1/opportunities/search';
      const searchData = {
        filters: {
          opportunity_status: {
            one_of: ["forecasted", "posted"]
          }
        },
        pagination: {
          order_by: "opportunity_id",
          page_offset: page,
          page_size: grantsPerPage,
          sort_direction: "descending"
        },
        query: searchQuery
      };

      const response = await axios.post<GrantsAPIResponse>(url, searchData, {
        headers: {
          'accept': 'application/json',
          'X-Auth': API_KEY,
          'Content-Type': 'application/json'
        }
      });

      if (!response.data?.data) {
        return {
          content: [{
            type: "text",
            text: "No results found or invalid response format"
          }]
        };
      }

      const grants = response.data.data;
      if (grants.length === 0) {
        return {
          content: [{
            type: "text",
            text: `No grants found matching "${searchQuery}"`
          }]
        };
      }

      const summaryText = createSummary(grants, searchQuery, page, grantsPerPage);

      return {
        content: [{
          type: "text",
          text: summaryText
        }]
      };

    } catch (error) {
      console.error('Debug: Error occurred:', error);
      if (axios.isAxiosError(error)) {
        console.error('Debug: Axios error response:', error.response?.data);
        return {
          content: [{
            type: "text",
            text: `API Error: ${error.response?.data?.message || error.message}`
          }]
        };
      }
      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`
        }]
      };
    }
  }
  
  throw new Error(`Unknown tool: ${request.params.name}`);
});

async function run() {
  try {
    console.error('Debug: Starting server with API key:', API_KEY ? 'Present' : 'Missing');
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Grants Search MCP server running on stdio");
  } catch (error) {
    console.error('Debug: Server startup error:', error);
    throw error;
  }
}

run().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});