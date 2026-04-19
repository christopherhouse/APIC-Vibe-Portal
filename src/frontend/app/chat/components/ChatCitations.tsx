'use client';

/**
 * ChatCitations — renders citation chips below an assistant message.
 *
 * Each citation links to the referenced API detail page.
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
 * Extract a catalog API id from a citation URL if it follows the pattern
 * `/catalog/<id>` or contains the API id as the last path segment.
 */
function extractApiId(url: string): string | null {
  try {
    const parsed = new URL(url, 'http://localhost');
    const match = parsed.pathname.match(/\/catalog\/([^/]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
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
          const apiId = citation.url ? extractApiId(citation.url) : null;
          const href = apiId ? `/catalog/${apiId}` : (citation.url ?? '#');

          const handleClick = () => {
            if (href !== '#') {
              router.push(href);
            }
          };

          return (
            <Tooltip key={idx} title={citation.content ?? citation.title} placement="top" arrow>
              <Chip
                icon={<LinkIcon />}
                label={citation.title}
                size="small"
                variant="outlined"
                color="primary"
                clickable={href !== '#'}
                onClick={handleClick}
                data-testid={`citation-chip-${idx}`}
              />
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
}
