'use client';

/**
 * ChatCitations — renders citation chips below an assistant message.
 *
 * - Relative `/catalog/<id>` URLs → in-app router navigation
 * - Absolute http/https URLs → `<a target="_blank" rel="noopener noreferrer">`
 * - All other schemes (javascript:, data:, etc.) → rendered as non-clickable chips
 */

import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import LinkIcon from '@mui/icons-material/Link';
import { useRouter } from 'next/navigation';
import type { Citation } from '@apic-vibe-portal/shared';

export interface ChatCitationsProps {
  citations: Citation[];
}

/**
 * Extract a catalog API id from a citation URL **only** when the URL is
 * relative (starts with `/`).  Absolute URLs that happen to contain
 * `/catalog/` are treated as external — not as in-app links — to prevent
 * spoofing.
 */
function extractInternalApiId(url: string): string | null {
  // Only treat as internal if it's a relative path (starts with `/` but NOT `//`).
  // Protocol-relative URLs (//host/path) would bypass the scheme guard, so reject them too.
  if (!url.startsWith('/') || url.startsWith('//')) return null;
  const match = url.match(/\/catalog\/([^/?#]+)/);
  return match ? match[1] : null;
}

/**
 * Return `true` only for safe absolute http / https URLs.
 * Any other scheme (javascript:, data:, etc.) is rejected.
 */
function isSafeExternalUrl(url: string): boolean {
  try {
    const { protocol } = new URL(url);
    return protocol === 'http:' || protocol === 'https:';
  } catch {
    return false;
  }
}

export default function ChatCitations({ citations }: ChatCitationsProps) {
  const router = useRouter();

  if (!citations.length) return null;

  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
        Sources
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {citations.map((citation, idx) => {
          const url = citation.url ?? '';
          const internalApiId = extractInternalApiId(url);
          const isExternal = !internalApiId && isSafeExternalUrl(url);

          if (internalApiId) {
            // Internal catalog link — navigate within the SPA
            return (
              <Tooltip key={idx} title={citation.content ?? citation.title} placement="top" arrow>
                <Chip
                  icon={<LinkIcon />}
                  label={citation.title}
                  size="small"
                  variant="outlined"
                  color="primary"
                  clickable
                  onClick={() => router.push(`/catalog/${internalApiId}`)}
                  data-testid={`citation-chip-${idx}`}
                />
              </Tooltip>
            );
          }

          if (isExternal) {
            // External link — open in a new tab safely
            return (
              <Tooltip key={idx} title={citation.content ?? citation.title} placement="top" arrow>
                <Chip
                  icon={<LinkIcon />}
                  label={citation.title}
                  size="small"
                  variant="outlined"
                  color="primary"
                  clickable
                  component="a"
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid={`citation-chip-${idx}`}
                />
              </Tooltip>
            );
          }

          // No valid URL or unsafe scheme — render as non-clickable chip
          return (
            <Tooltip key={idx} title={citation.content ?? citation.title} placement="top" arrow>
              <Chip
                icon={<LinkIcon />}
                label={citation.title}
                size="small"
                variant="outlined"
                data-testid={`citation-chip-${idx}`}
              />
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
}
