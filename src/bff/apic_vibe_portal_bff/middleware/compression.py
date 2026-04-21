"""GZip response compression middleware.

Compresses all responses that are above a minimum size threshold using GZip
encoding.  Brotli is preferred by browsers but is not available in the
standard-library; GZip provides a good balance of compression ratio and
compatibility.

The middleware honours the ``Accept-Encoding`` request header and only
applies compression when the client signals support.
"""

from __future__ import annotations

from starlette.middleware.gzip import GZipMiddleware

__all__ = ["GZipMiddleware"]
