"""Fusioo API Client for BookSpring data access."""
import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Module version for cache busting
__version__ = "1.1.0"


class FusiooClient:
    """Client for interacting with the Fusioo API."""

    BASE_URL = "https://api.fusioo.com/v3"

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("FUSIOO_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("Access token is required")
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request."""
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def get_apps(self) -> list:
        """Get all apps in the workspace."""
        result = self._request("GET", "apps")
        return result.get("data", [])

    def get_app(self, app_id: str) -> dict:
        """Get a specific app's schema."""
        result = self._request("GET", f"apps/{app_id}")
        return result.get("data", {})

    def get_records(self, app_id: str, limit: int = 200, offset: int = 0,
                    sort_by: Optional[str] = None, order: str = "asc") -> list:
        """Get records from an app with pagination."""
        params = {"limit": limit, "offset": offset, "order": order}
        if sort_by:
            params["sort_by"] = sort_by
        result = self._request("GET", f"records/apps/{app_id}", params=params)
        return result.get("data", [])

    def get_all_records(self, app_id: str, sort_by: Optional[str] = None) -> list:
        """Get all records from an app (handles pagination)."""
        all_records = []
        offset = 0
        limit = 200

        while True:
            records = self.get_records(app_id, limit=limit, offset=offset, sort_by=sort_by)
            if not records:
                break
            all_records.extend(records)
            if len(records) < limit:
                break
            offset += limit

        return all_records

    def filter_records(self, app_id: str, filters: dict, limit: int = 200,
                       offset: int = 0) -> list:
        """Get filtered records from an app."""
        params = {"limit": limit, "offset": offset}
        result = self._request("POST", f"records/apps/{app_id}/filter",
                               json=filters, params=params)
        return result.get("data", [])

    def count_active_enrollments(self, app_id: str) -> int:
        """Count records where active_enrollment is True using filter API.

        Only reads the active_enrollment field value for counting.
        Other fields are not accessed or stored.
        """
        # Use count/filter endpoint
        filters = {
            "active_enrollment": {"equal": True}
        }
        result = self._request("POST", f"records/apps/{app_id}/count/filter", json=filters)
        return result.get("data", {}).get("count", 0)


# Pre-configured app IDs
ACTIVITY_REPORT_APP_ID = os.getenv("ACTIVITY_REPORT_APP_ID", "i71d7fa767e2546aaa40fdd007b608719")
PROGRAM_PARTNERS_APP_ID = os.getenv("PROGRAM_PARTNERS_APP_ID", "i6972b09e40f745d9a8a8bf6e41a6e840")
LEGACY_DATA_APP_ID = os.getenv("LEGACY_DATA_APP_ID", "i6972b09e40f745d9a8a8bf6e41a6e840")
B3_CHILD_FAMILY_APP_ID = os.getenv("B3_CHILD_FAMILY_APP_ID", "i8e6d5204817042dc8d9e02598538a7f4")
EVENTS_APP_ID = os.getenv("EVENTS_APP_ID", "i654f04e79285466ca2670c04b851de40")
PARTNERS_APP_ID = os.getenv("PARTNERS_APP_ID", "i6d06a2ef45f44718a1d33e971fc03f46")
