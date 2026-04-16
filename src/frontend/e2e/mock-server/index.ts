/**
 * Mock BFF API server for Playwright e2e testing.
 *
 * This is a lightweight Express-like HTTP server that serves mock responses
 * for BFF API endpoints. It enables full end-to-end testing of the frontend
 * without requiring a running BFF or Azure services.
 *
 * ## Usage
 *
 * In Playwright tests, use `page.route()` for request interception (preferred),
 * or start this server as a standalone process for integration testing.
 *
 * ## Updating
 *
 * As the BFF API evolves, update the mock data and route handlers here to
 * match the latest endpoint contracts. The mock data shapes should mirror
 * the actual BFF response envelopes exactly.
 */

import http from 'node:http';

export interface MockApiDefinition {
  id: string;
  name: string;
  title: string;
  description: string;
  kind: string;
  lifecycleStage: string;
  termsOfService?: string;
  license?: string;
  contacts?: { name: string; email?: string; url?: string }[];
  externalDocs?: { title: string; url: string; description?: string }[];
  customProperties?: Record<string, unknown>;
  versions: {
    id: string;
    name: string;
    title: string;
    lifecycleStage: string;
    createdAt: string;
    updatedAt: string;
  }[];
  deployments: {
    id: string;
    title: string;
    description?: string;
    environment: {
      id: string;
      name: string;
      title: string;
      kind: string;
    };
    server: { runtimeUri: string[] };
    createdAt: string;
    updatedAt: string;
  }[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Generate mock API definitions for testing.
 */
export function generateMockApis(count: number, overrides: Partial<MockApiDefinition> = {}): MockApiDefinition[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `api-${i + 1}`,
    name: `api-${i + 1}`,
    title: `Test API ${i + 1}`,
    description: `Description for API ${i + 1}. This API provides various endpoints for testing purposes.`,
    kind: i % 2 === 0 ? 'rest' : 'graphql',
    lifecycleStage: i % 3 === 0 ? 'production' : i % 3 === 1 ? 'development' : 'deprecated',
    termsOfService: 'https://example.com/tos',
    license: 'MIT',
    contacts: [
      { name: 'API Team', email: 'api-team@example.com', url: 'https://team.example.com' },
    ],
    externalDocs: [
      { title: 'Getting Started', url: 'https://docs.example.com', description: 'Full guide for API usage' },
    ],
    customProperties: { team: 'Platform', region: 'US-East' },
    versions: Array.from({ length: Math.min(i + 1, 3) }, (__, vi) => ({
      id: `v${vi + 1}`,
      name: `v${vi + 1}`,
      title: `Version ${vi + 1}.0`,
      lifecycleStage: vi === 0 ? 'production' : 'development',
      createdAt: new Date(2026, 2, 15 - vi).toISOString(),
      updatedAt: new Date(2026, 2, 15 - vi).toISOString(),
    })),
    deployments: [
      {
        id: `dep-${i + 1}-prod`,
        title: `Production Deployment`,
        description: 'Production environment deployment',
        environment: { id: 'env-prod', name: 'production', title: 'Production', kind: 'production' },
        server: { runtimeUri: [`https://api-${i + 1}.prod.example.com`] },
        createdAt: new Date(2026, 2, 15 - i).toISOString(),
        updatedAt: new Date(2026, 2, 15 - i).toISOString(),
      },
      {
        id: `dep-${i + 1}-staging`,
        title: `Staging Deployment`,
        description: 'Staging environment deployment',
        environment: { id: 'env-staging', name: 'staging', title: 'Staging', kind: 'staging' },
        server: { runtimeUri: [`https://api-${i + 1}.staging.example.com`] },
        createdAt: new Date(2026, 2, 10 - i).toISOString(),
        updatedAt: new Date(2026, 2, 10 - i).toISOString(),
      },
    ],
    createdAt: new Date(2026, 1, 1).toISOString(),
    updatedAt: new Date(2026, 2, 15 - i).toISOString(),
    ...overrides,
  }));
}

/**
 * Generate a mock OpenAPI spec for testing.
 */
export function generateMockSpec(apiName: string, version: string): string {
  return JSON.stringify({
    openapi: '3.0.3',
    info: {
      title: apiName,
      version,
      description: `OpenAPI specification for ${apiName}`,
    },
    paths: {
      '/items': {
        get: {
          summary: 'List items',
          operationId: 'listItems',
          responses: {
            '200': {
              description: 'Successful response',
              content: {
                'application/json': {
                  schema: {
                    type: 'array',
                    items: { type: 'object', properties: { id: { type: 'string' }, name: { type: 'string' } } },
                  },
                },
              },
            },
          },
        },
      },
    },
  });
}

/**
 * Create and start a mock BFF server on the specified port.
 * Returns a cleanup function to close the server.
 */
export function startMockServer(port: number, apis: MockApiDefinition[] = generateMockApis(6)): Promise<() => void> {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url ?? '/', `http://localhost:${port}`);
      const pathname = url.pathname;

      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Headers', '*');

      if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
      }

      // GET /api/catalog - List APIs
      if (pathname === '/api/catalog' && req.method === 'GET') {
        const page = Number(url.searchParams.get('page') ?? '1');
        const pageSize = Number(url.searchParams.get('pageSize') ?? '20');
        const lifecycle = url.searchParams.get('lifecycle');
        const kind = url.searchParams.get('kind');

        let filtered = [...apis];
        if (lifecycle) filtered = filtered.filter((a) => a.lifecycleStage === lifecycle);
        if (kind) filtered = filtered.filter((a) => a.kind === kind);

        const totalCount = filtered.length;
        const totalPages = Math.ceil(totalCount / pageSize);
        const start = (page - 1) * pageSize;
        const pageItems = filtered.slice(start, start + pageSize);

        res.writeHead(200);
        res.end(JSON.stringify({
          data: pageItems,
          meta: { page, pageSize, totalCount, totalPages },
        }));
        return;
      }

      // GET /api/catalog/:apiId - API Detail
      const detailMatch = pathname.match(/^\/api\/catalog\/([^/]+)$/);
      if (detailMatch && req.method === 'GET') {
        const api = apis.find((a) => a.id === detailMatch[1]);
        if (!api) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'API not found' } }));
          return;
        }
        res.writeHead(200);
        res.end(JSON.stringify({ data: api }));
        return;
      }

      // GET /api/catalog/:apiId/versions
      const versionsMatch = pathname.match(/^\/api\/catalog\/([^/]+)\/versions$/);
      if (versionsMatch && req.method === 'GET') {
        const api = apis.find((a) => a.id === versionsMatch[1]);
        if (!api) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'API not found' } }));
          return;
        }
        res.writeHead(200);
        res.end(JSON.stringify({ data: api.versions }));
        return;
      }

      // GET /api/catalog/:apiId/versions/:versionId/definition
      const definitionMatch = pathname.match(/^\/api\/catalog\/([^/]+)\/versions\/([^/]+)\/definition$/);
      if (definitionMatch && req.method === 'GET') {
        const api = apis.find((a) => a.id === definitionMatch[1]);
        if (!api) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'API not found' } }));
          return;
        }
        const version = api.versions.find((v) => v.id === definitionMatch[2]);
        if (!version) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Version not found' } }));
          return;
        }
        res.writeHead(200);
        res.end(JSON.stringify({ data: generateMockSpec(api.title, version.title) }));
        return;
      }

      // GET /api/catalog/:apiId/deployments
      const deploymentsMatch = pathname.match(/^\/api\/catalog\/([^/]+)\/deployments$/);
      if (deploymentsMatch && req.method === 'GET') {
        const api = apis.find((a) => a.id === deploymentsMatch[1]);
        if (!api) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'API not found' } }));
          return;
        }
        res.writeHead(200);
        res.end(JSON.stringify({ data: api.deployments }));
        return;
      }

      // GET /api/environments
      if (pathname === '/api/environments' && req.method === 'GET') {
        res.writeHead(200);
        res.end(JSON.stringify({
          data: [
            { id: 'env-prod', name: 'production', title: 'Production', kind: 'production' },
            { id: 'env-staging', name: 'staging', title: 'Staging', kind: 'staging' },
            { id: 'env-dev', name: 'development', title: 'Development', kind: 'development' },
          ],
        }));
        return;
      }

      // GET /health
      if (pathname === '/health' && req.method === 'GET') {
        res.writeHead(200);
        res.end(JSON.stringify({ status: 'ok' }));
        return;
      }

      res.writeHead(404);
      res.end(JSON.stringify({ error: { code: 'NOT_FOUND', message: `Route not found: ${pathname}` } }));
    });

    server.listen(port, () => {
      console.log(`Mock BFF server running on http://localhost:${port}`);
      resolve(() => {
        server.close();
      });
    });
  });
}

// Allow running as a standalone script
if (process.argv[1] && process.argv[1].includes('mock-server')) {
  const port = Number(process.env.MOCK_PORT ?? '8000');
  startMockServer(port).then(() => {
    console.log(`Press Ctrl+C to stop`);
  });
}
