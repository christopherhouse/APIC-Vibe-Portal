'use client';

import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Divider from '@mui/material/Divider';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';
import type { ApiDefinition } from '@apic-vibe-portal/shared';

export interface ApiMetadataProps {
  api: ApiDefinition;
}

export default function ApiMetadata({ api }: ApiMetadataProps) {
  const hasContacts = api.contacts && api.contacts.length > 0;
  const hasExternalDocs = api.externalDocs && api.externalDocs.length > 0;
  const hasCustomProperties =
    api.customProperties && Object.keys(api.customProperties).length > 0;

  return (
    <Box data-testid="api-metadata">
      {/* Description */}
      <Typography variant="h6" gutterBottom>
        Description
      </Typography>
      <Typography variant="body1" sx={{ mb: 2 }}>
        {api.description || 'No description available.'}
      </Typography>

      {/* General Info */}
      <Table size="small" sx={{ mb: 3 }}>
        <TableBody>
          {api.license && (
            <TableRow>
              <TableCell component="th" sx={{ fontWeight: 600, width: 160 }}>
                License
              </TableCell>
              <TableCell>{api.license}</TableCell>
            </TableRow>
          )}
          {api.termsOfService && (
            <TableRow>
              <TableCell component="th" sx={{ fontWeight: 600, width: 160 }}>
                Terms of Service
              </TableCell>
              <TableCell>
                <Link href={api.termsOfService} target="_blank" rel="noopener">
                  {api.termsOfService}
                </Link>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Contacts */}
      {hasContacts && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="h6" gutterBottom>
            Contacts
          </Typography>
          <Table size="small" sx={{ mb: 3 }}>
            <TableBody>
              {api.contacts!.map((contact, idx) => (
                <TableRow key={idx}>
                  <TableCell component="th" sx={{ fontWeight: 600, width: 160 }}>
                    {contact.name}
                  </TableCell>
                  <TableCell>
                    {contact.email && (
                      <Link href={`mailto:${contact.email}`}>{contact.email}</Link>
                    )}
                    {contact.email && contact.url && ' · '}
                    {contact.url && (
                      <Link href={contact.url} target="_blank" rel="noopener">
                        {contact.url}
                      </Link>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}

      {/* External Docs */}
      {hasExternalDocs && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="h6" gutterBottom>
            External Documentation
          </Typography>
          <Table size="small" sx={{ mb: 3 }}>
            <TableBody>
              {api.externalDocs!.map((doc, idx) => (
                <TableRow key={idx}>
                  <TableCell component="th" sx={{ fontWeight: 600, width: 160 }}>
                    {doc.title}
                  </TableCell>
                  <TableCell>
                    <Link href={doc.url} target="_blank" rel="noopener">
                      {doc.url}
                    </Link>
                    {doc.description && (
                      <Typography variant="body2" color="text.secondary">
                        {doc.description}
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}

      {/* Custom Properties */}
      {hasCustomProperties && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="h6" gutterBottom>
            Custom Properties
          </Typography>
          <Table size="small" sx={{ mb: 3 }}>
            <TableBody>
              {Object.entries(api.customProperties!).map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell component="th" sx={{ fontWeight: 600, width: 160 }}>
                    {key}
                  </TableCell>
                  <TableCell>{String(value)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </Box>
  );
}
