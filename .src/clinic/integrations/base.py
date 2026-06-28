"""Base integration adapter — all integrations follow this pattern.

External API → adapter (normalize) → canonical store → detectors
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IntegrationStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    EXPIRED = "expired"  # token expired, needs re-auth


@dataclass
class IntegrationConfig:
    """Stored config for a connected integration."""
    provider: str                    # "withings", "whoop", "oura", "apple_health"
    user_id: str = "default"
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    last_sync: datetime | None = None
    webhook_id: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    provider: str
    success: bool
    records_synced: int = 0
    metrics_updated: list[str] = field(default_factory=list)
    error: str | None = None
    last_data_date: str | None = None


class IntegrationAdapter(ABC):
    """Base class for all integration adapters."""

    provider: str = ""
    display_name: str = ""
    description: str = ""
    metrics_provided: list[str] = []
    oauth_url: str = ""
    icon: str = ""  # SVG or emoji for UI

    @abstractmethod
    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate the OAuth authorization URL."""
        ...

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> IntegrationConfig:
        """Exchange auth code for tokens."""
        ...

    @abstractmethod
    def refresh_tokens(self, config: IntegrationConfig) -> IntegrationConfig:
        """Refresh expired tokens."""
        ...

    @abstractmethod
    def sync(self, conn: sqlite3.Connection, config: IntegrationConfig) -> SyncResult:
        """Pull data from the integration and store it."""
        ...


# Integration registry
INTEGRATION_REGISTRY: dict[str, type[IntegrationAdapter]] = {}


def register_integration(cls: type[IntegrationAdapter]) -> type[IntegrationAdapter]:
    """Decorator to register an integration adapter."""
    INTEGRATION_REGISTRY[cls.provider] = cls
    return cls
