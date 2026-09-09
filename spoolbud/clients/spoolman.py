"""HTTP boundary for Spoolman."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from spoolbud.parsing.extra_fields import decode_text_extra, encode_text_extra
from spoolbud.parsing.tag_uids import normalize_uid


class TagScanRequest(BaseModel):
    """Compatibility request accepted by SpoolBud's reader-oriented API."""

    model_config = ConfigDict(extra="forbid")
    uid: str = Field(min_length=1, max_length=128)
    reader_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:-]{1,64}$")
    name: str | None = Field(default=None, max_length=64)
    format: str | None = Field(default=None, max_length=32)
    payload_b64: str | None = Field(default=None, max_length=8192)

    @field_validator("uid")
    @classmethod
    def canonicalize_uid(cls, value: str) -> str:
        return normalize_uid(value)


class TagAssignmentRequest(BaseModel):
    """An explicit request to associate an existing spool with a UID."""

    model_config = ConfigDict(extra="forbid")
    spool_id: int = Field(gt=0, strict=True)
    replace_existing: bool = Field(default=False, strict=True)


class TagLookupError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class DuplicateTagUIDError(TagLookupError):
    def __init__(self, spool_ids: list[int]):
        super().__init__(409, "Multiple spools have the same NFC ID. Check the nfc_id extra fields in Spoolman.")
        self.spool_ids = spool_ids


class TagAssignmentError(TagLookupError):
    """An actionable failure while writing a UID to a Spoolman spool."""


# Compatibility name for integrations importing the original exception.
TagScanError = TagLookupError


class SpoolmanClient:
    """Small async client that owns Spoolman URLs, credentials, and timeouts."""

    def __init__(
        self,
        base_url: str,
        api_token: str = "",
        *,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.client_factory = client_factory

    def auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def get_spools(self) -> list[dict[str, Any]]:
        async with self.client_factory(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(f"{self.base_url}/api/v1/spool", headers=self.auth_headers())
            response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    async def get_spool(self, spool_id: int) -> dict[str, Any]:
        async with self.client_factory(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(f"{self.base_url}/api/v1/spool/{spool_id}", headers=self.auth_headers())
            response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    async def update_spool_location(self, spool_id: int, location: str) -> httpx.Response:
        async with self.client_factory(timeout=15.0, follow_redirects=True) as client:
            return await client.patch(
                f"{self.base_url}/api/v1/spool/{spool_id}",
                headers=self.auth_headers(),
                json={"location": location},
            )

    async def assign_tag_uid(
        self,
        spool_id: int,
        uid: str,
        *,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        """Merge a canonical UID into a spool's extra fields and verify the write."""
        canonical_uid = normalize_uid(uid)
        existing_match = await self.get_spool_by_tag_uid(canonical_uid)
        if existing_match is not None:
            if existing_match.get("id") == spool_id:
                return existing_match
            raise TagAssignmentError(
                409,
                f"This NFC tag was associated with spool {existing_match['id']} while this page was open. Scan it again.",
            )

        headers = self.auth_headers()
        try:
            async with self.client_factory(timeout=15.0, follow_redirects=False) as client:
                response = await client.get(f"{self.base_url}/api/v1/spool/{spool_id}", headers=headers)
                if response.status_code == 404:
                    raise TagAssignmentError(404, "The selected spool no longer exists in Spoolman. Choose another spool.")
                if response.status_code in {401, 403}:
                    raise TagAssignmentError(502, "Spoolman denied access to the selected spool. Check the configured API credentials.")
                if response.status_code != 200:
                    raise TagAssignmentError(502, "Spoolman could not load the selected spool. Try again when the service is available.")

                try:
                    spool = response.json()
                except ValueError:
                    raise TagAssignmentError(502, "Spoolman returned an invalid spool response. The NFC tag was not associated.") from None
                if not isinstance(spool, dict) or spool.get("id") != spool_id:
                    raise TagAssignmentError(502, "Spoolman returned an invalid spool response. The NFC tag was not associated.")

                extra = spool.get("extra")
                if extra is None:
                    extra = {}
                if not isinstance(extra, dict):
                    raise TagAssignmentError(502, "The selected spool has invalid extra fields. The NFC tag was not associated.")

                stored_uid = decode_text_extra(extra.get("nfc_id"))
                if stored_uid is not None:
                    try:
                        same_uid = normalize_uid(stored_uid) == canonical_uid
                    except ValueError:
                        same_uid = False
                    if same_uid:
                        return spool
                    if not replace_existing:
                        raise TagAssignmentError(
                            409,
                            "The selected spool already has a different NFC ID. Confirm replacement and try again.",
                        )

                response = await client.patch(
                    f"{self.base_url}/api/v1/spool/{spool_id}",
                    headers=headers,
                    json={"extra": {"nfc_id": encode_text_extra(canonical_uid)}},
                )
                if response.status_code in {401, 403}:
                    raise TagAssignmentError(502, "Spoolman denied the NFC update. Check the configured API credentials.")
                if response.status_code == 404:
                    raise TagAssignmentError(404, "The selected spool no longer exists in Spoolman. Choose another spool.")
                if response.status_code in {400, 422}:
                    raise TagAssignmentError(
                        502,
                        "Spoolman rejected the NFC update. Ensure the spool nfc_id extra field exists and the API token can edit spools.",
                    )
                if response.status_code != 200:
                    raise TagAssignmentError(502, "Spoolman could not save the NFC association. Try again when the service is available.")

                try:
                    updated_spool = response.json()
                except ValueError:
                    raise TagAssignmentError(502, "Spoolman did not confirm the NFC association. Check the spool before retrying.") from None
                updated_extra_payload = updated_spool.get("extra") if isinstance(updated_spool, dict) else None
                updated_uid = (
                    decode_text_extra(updated_extra_payload.get("nfc_id"))
                    if isinstance(updated_extra_payload, dict)
                    else None
                )
                try:
                    write_confirmed = (
                        isinstance(updated_spool, dict)
                        and updated_spool.get("id") == spool_id
                        and updated_uid is not None
                        and normalize_uid(updated_uid) == canonical_uid
                    )
                except ValueError:
                    write_confirmed = False
                if not write_confirmed:
                    raise TagAssignmentError(502, "Spoolman did not confirm the NFC association. Check the spool before retrying.")
                return updated_spool
        except TagAssignmentError:
            raise
        except httpx.RequestError:
            raise TagAssignmentError(502, "Could not reach Spoolman. The NFC tag was not associated; check the connection and try again.") from None

    @staticmethod
    def _server_supports_native_tags(payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        version = payload.get("version")
        if not isinstance(version, str):
            return False
        match = re.search(r"(?:^|\D)(\d+)\.(\d+)(?:\.|\D|$)", version)
        return bool(match and (int(match.group(1)), int(match.group(2))) >= (0, 27))

    async def _supports_native_tag_lookup(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
    ) -> bool:
        """Use Spoolman's own info endpoint rather than a configured version guess."""
        try:
            response = await client.get(f"{self.base_url}/api/v1/info", headers=headers)
        except httpx.RequestError:
            return False
        if response.status_code != 200:
            return False
        try:
            return self._server_supports_native_tags(response.json())
        except ValueError:
            return False

    @staticmethod
    def _payload_spools(response: httpx.Response) -> list[dict[str, Any]]:
        try:
            payload = response.json()
        except ValueError:
            raise TagLookupError(502, "Spoolman returned an invalid spool lookup response. No spool was selected.") from None
        if not isinstance(payload, list):
            raise TagLookupError(502, "Spoolman returned an invalid spool lookup response. No spool was selected.")
        if any(not isinstance(spool, dict) for spool in payload):
            raise TagLookupError(502, "Spoolman returned an invalid spool lookup response. No spool was selected.")
        return payload

    @staticmethod
    def _one_spool(spools: list[dict[str, Any]]) -> dict[str, Any] | None:
        by_id: dict[int, dict[str, Any]] = {}
        for spool in spools:
            spool_id = spool.get("id")
            if type(spool_id) is int and spool_id > 0:
                by_id[spool_id] = spool
        if len(by_id) > 1:
            raise DuplicateTagUIDError(sorted(by_id))
        if spools and not by_id:
            raise TagLookupError(502, "Spoolman returned an invalid spool identity. No spool was selected.")
        return next(iter(by_id.values()), None)

    async def _native_tag_lookup(
        self,
        client: httpx.AsyncClient,
        uid: str,
        headers: dict[str, str],
    ) -> dict[str, Any] | None:
        response = await client.get(
            f"{self.base_url}/api/v1/spool",
            headers=headers,
            params={"tag": uid},
        )
        if response.status_code in {400, 404, 405, 422, 501}:
            return None
        if response.status_code in {401, 403}:
            raise TagLookupError(502, "Spoolman denied NFC tag lookup. Check the configured API credentials.")
        if response.status_code != 200:
            raise TagLookupError(502, "Spoolman could not resolve this NFC tag. Try again when the service is available.")
        return self._one_spool(self._payload_spools(response))

    async def _legacy_nfc_id_lookup(
        self,
        client: httpx.AsyncClient,
        uid: str,
        headers: dict[str, str],
    ) -> dict[str, Any] | None:
        response = await client.get(
            f"{self.base_url}/api/v1/spool",
            headers=headers,
            params={"extra.nfc_id": uid},
        )
        if response.status_code in {400, 422}:
            return None
        if response.status_code in {401, 403}:
            raise TagLookupError(502, "Spoolman denied NFC tag lookup. Check the configured API credentials.")
        if response.status_code != 200:
            raise TagLookupError(502, "Spoolman could not resolve this NFC tag. Check its connection, then try again.")

        matches: list[dict[str, Any]] = []
        for spool in self._payload_spools(response):
            extra = spool.get("extra")
            stored_uid = decode_text_extra(extra.get("nfc_id")) if isinstance(extra, dict) else None
            if stored_uid is None:
                continue
            try:
                if normalize_uid(stored_uid) == uid:
                    matches.append(spool)
            except ValueError:
                continue
        return self._one_spool(matches)

    async def get_spool_by_tag_uid(
        self,
        uid: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Resolve a UID through native tags when available, then extra.nfc_id."""
        canonical_uid = normalize_uid(uid)
        request_headers = headers or self.auth_headers()
        try:
            async with self.client_factory(timeout=10.0, follow_redirects=False) as client:
                if await self._supports_native_tag_lookup(client, request_headers):
                    spool = await self._native_tag_lookup(client, canonical_uid, request_headers)
                    if spool is not None:
                        return spool
                return await self._legacy_nfc_id_lookup(client, canonical_uid, request_headers)
        except TagLookupError:
            raise
        except httpx.RequestError:
            raise TagLookupError(502, "Could not reach Spoolman. Check its connection, then try again.") from None

    async def scan_tag(
        self,
        scan: TagScanRequest,
        *,
        headers: dict[str, str] | None = None,
    ) -> int | None:
        spool = await self.get_spool_by_tag_uid(scan.uid, headers=headers)
        return spool["id"] if spool is not None else None
