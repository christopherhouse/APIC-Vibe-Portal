/**
 * Catch-all BFF proxy route.
 *
 * Every `/api/*` request that does NOT match an explicit Next.js API route
 * (e.g. `/api/health`) is forwarded to the BFF service.  The BFF URL is read
 * from the `BFF_URL` environment variable at runtime — no `NEXT_PUBLIC_`
 * prefix needed because this code runs on the server only.
 */

import { type NextRequest, NextResponse } from 'next/server';

const getBffBaseUrl = () => process.env.BFF_URL ?? 'http://localhost:8000';

async function proxyToBff(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  const target = new URL(`/api/${path.join('/')}`, getBffBaseUrl());

  // Preserve query parameters from the incoming request
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.set(key, value);
  });

  // Forward headers, stripping hop-by-hop headers that should not be proxied
  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('connection');

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  // Forward body for methods that carry one
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = request.body;
    // @ts-expect-error duplex is required for streaming request bodies in undici/Node
    init.duplex = 'half';
  }

  const upstream = await fetch(target.toString(), init);

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}

export const GET = proxyToBff;
export const POST = proxyToBff;
export const PUT = proxyToBff;
export const PATCH = proxyToBff;
export const DELETE = proxyToBff;
