"""Azure API Center data-plane client — shared package.

This package provides a typed REST client that communicates with the API Center
**data-plane** endpoint instead of the ARM management plane.  Both the BFF and
indexer depend on this package so they share the same client, exceptions, and
data access patterns.
"""

from apic_client.client import ApiCenterDataPlaneClient
from apic_client.exceptions import (
    ApiCenterAuthError,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)

__all__ = [
    "ApiCenterAuthError",
    "ApiCenterClientError",
    "ApiCenterDataPlaneClient",
    "ApiCenterNotFoundError",
    "ApiCenterUnavailableError",
]
