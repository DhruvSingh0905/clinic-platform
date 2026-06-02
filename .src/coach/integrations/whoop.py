"""Whoop integration — recovery, HRV, resting HR, sleep, strain.

API docs: developer.whoop.com (V2 API)
Auth: OAuth 2.0
Webhooks: available
Rate limit: standard

Data we pull:
- Recovery: HRV (ms), resting HR (bpm), SpO2, skin temp
- Sleep: duration, efficiency, stages
- Strain: day strain score
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, date, timedelta
from urllib.parse import urlencode

import httpx

from coach.integrations.base import (
    IntegrationAdapter, IntegrationConfig, IntegrationStatus, SyncResult,
    register_integration,
)


WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v1"


@register_integration
class WhoopAdapter(IntegrationAdapter):
    provider = "whoop"
    display_name = "WHOOP"
    description = "Recovery, HRV, heart rate, sleep tracking"
    metrics_provided = ["resting_hr", "hrv_sdnn", "sleep_duration", "strain"]
    icon = "🟢"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:recovery read:sleep read:workout read:cycles read:body_measurement",
            "state": state,
        }
        return f"{WHOOP_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> IntegrationConfig:
        with httpx.Client() as client:
            resp = client.post(WHOOP_TOKEN_URL, data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            })
            data = resp.json()

        return IntegrationConfig(
            provider="whoop",
            status=IntegrationStatus.CONNECTED,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_expires_at=datetime.fromtimestamp(
                datetime.now().timestamp() + data.get("expires_in", 86400)
            ),
        )

    def refresh_tokens(self, config: IntegrationConfig) -> IntegrationConfig:
        with httpx.Client() as client:
            resp = client.post(WHOOP_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": config.refresh_token,
            })
            data = resp.json()

        if "access_token" not in data:
            config.status = IntegrationStatus.EXPIRED
            return config

        config.access_token = data["access_token"]
        config.refresh_token = data.get("refresh_token", config.refresh_token)
        config.token_expires_at = datetime.fromtimestamp(
            datetime.now().timestamp() + data.get("expires_in", 86400)
        )
        config.status = IntegrationStatus.CONNECTED
        return config

    def sync(self, conn: sqlite3.Connection, config: IntegrationConfig) -> SyncResult:
        """Pull recovery and sleep data since last sync."""
        if not config.access_token:
            return SyncResult(provider="whoop", success=False, error="No access token")

        headers = {"Authorization": f"Bearer {config.access_token}"}
        records = 0
        metrics_updated = set()
        last_date = None

        # Determine date range
        start = config.last_sync or (datetime.now() - timedelta(days=90))
        start_str = start.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = datetime.now().strftime("%Y-%m-%dT23:59:59.999Z")

        try:
            with httpx.Client() as client:
                # === RECOVERY DATA ===
                resp = client.get(
                    f"{WHOOP_API_BASE}/recovery",
                    params={"start": start_str, "end": end_str, "limit": 100},
                    headers=headers,
                )
                recovery_data = resp.json()

                for record in recovery_data.get("records", []):
                    score = record.get("score", {})
                    cycle = record.get("cycle", {})

                    # Extract date from cycle
                    cycle_start = cycle.get("start")
                    if not cycle_start:
                        continue
                    obs_date = cycle_start[:10]  # YYYY-MM-DD
                    last_date = obs_date

                    # Resting HR
                    rhr = score.get("resting_heart_rate")
                    if rhr:
                        conn.execute("""
                            INSERT OR REPLACE INTO wearable_observation
                            (user_id, metric, observation_date, value_mean, value_min, value_max,
                             reading_count, unit, source)
                            VALUES ('default', 'resting_hr', ?, ?, ?, ?, 1, 'bpm', 'WHOOP')
                        """, (obs_date, rhr, rhr, rhr))
                        records += 1
                        metrics_updated.add("resting_hr")

                    # HRV
                    hrv = score.get("hrv_rmssd_milli")  # V2 API returns in milliseconds
                    if hrv:
                        hrv_ms = hrv  # already in ms
                        conn.execute("""
                            INSERT OR REPLACE INTO wearable_observation
                            (user_id, metric, observation_date, value_mean, value_min, value_max,
                             reading_count, unit, source)
                            VALUES ('default', 'hrv_sdnn', ?, ?, ?, ?, 1, 'ms', 'WHOOP')
                        """, (obs_date, hrv_ms, hrv_ms, hrv_ms))
                        records += 1
                        metrics_updated.add("hrv_sdnn")

                    # SpO2
                    spo2 = score.get("spo2_percentage")
                    if spo2:
                        conn.execute("""
                            INSERT OR REPLACE INTO wearable_observation
                            (user_id, metric, observation_date, value_mean, value_min, value_max,
                             reading_count, unit, source)
                            VALUES ('default', 'spo2', ?, ?, ?, ?, 1, '%', 'WHOOP')
                        """, (obs_date, spo2, spo2, spo2))
                        records += 1
                        metrics_updated.add("spo2")

                # === SLEEP DATA ===
                resp = client.get(
                    f"{WHOOP_API_BASE}/activity/sleep",
                    params={"start": start_str, "end": end_str, "limit": 100},
                    headers=headers,
                )
                sleep_data = resp.json()

                for record in sleep_data.get("records", []):
                    score = record.get("score", {})
                    start_time = record.get("start")
                    if not start_time:
                        continue
                    obs_date = start_time[:10]

                    # Sleep duration (hours)
                    total_ms = score.get("stage_summary", {}).get("total_in_bed_time_milli")
                    if total_ms:
                        hours = round(total_ms / 3600000, 1)
                        conn.execute("""
                            INSERT OR REPLACE INTO wearable_observation
                            (user_id, metric, observation_date, value_mean, value_min, value_max,
                             reading_count, unit, source)
                            VALUES ('default', 'sleep_duration', ?, ?, ?, ?, 1, 'hours', 'WHOOP')
                        """, (obs_date, hours, hours, hours))
                        records += 1
                        metrics_updated.add("sleep_duration")

                    # Sleep efficiency
                    efficiency = score.get("sleep_efficiency_percentage")
                    if efficiency:
                        conn.execute("""
                            INSERT OR REPLACE INTO wearable_observation
                            (user_id, metric, observation_date, value_mean, value_min, value_max,
                             reading_count, unit, source)
                            VALUES ('default', 'sleep_efficiency', ?, ?, ?, ?, 1, '%', 'WHOOP')
                        """, (obs_date, efficiency, efficiency, efficiency))
                        records += 1
                        metrics_updated.add("sleep_efficiency")

            conn.commit()
            return SyncResult(
                provider="whoop",
                success=True,
                records_synced=records,
                metrics_updated=list(metrics_updated),
                last_data_date=last_date,
            )

        except Exception as e:
            return SyncResult(provider="whoop", success=False, error=str(e))
