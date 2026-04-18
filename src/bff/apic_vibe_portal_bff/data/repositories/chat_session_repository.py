"""Repository for chat session documents.

Container: ``chat-sessions``, partition key: ``/userId``.
"""

from __future__ import annotations

from azure.cosmos.container import ContainerProxy

from apic_vibe_portal_bff.data.models.chat_session import CURRENT_SCHEMA_VERSION
from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository, PaginatedResult


class ChatSessionRepository(BaseRepository):
    """Data access for the ``chat-sessions`` container."""

    # No migrations registered yet — current version is 1.
    _MIGRATIONS: dict = {}

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container, partition_key_field="userId")

    # ------------------------------------------------------------------
    # Migrations hook
    # ------------------------------------------------------------------

    def _apply_migrations(self, document: dict) -> dict:
        from apic_vibe_portal_bff.data.migrations.lazy_migration import apply_migrations

        return apply_migrations(document, target_version=CURRENT_SCHEMA_VERSION, migrations=self._MIGRATIONS)

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def find_sessions_for_user(
        self,
        user_id: str,
        *,
        max_items: int = 25,
        continuation_token: str | None = None,
    ) -> PaginatedResult:
        """Return a user's chat sessions, newest first."""
        return self.find_by_partition_key(
            user_id,
            max_items=max_items,
            continuation_token=continuation_token,
            order_by="c.createdAt DESC",
        )
