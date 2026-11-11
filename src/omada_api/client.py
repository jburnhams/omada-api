"""A logged-in session on the controller, calling the Open API paths through `tplink-omada-client`'s own login and session handling."""

import json

from tplink_omada_client.omadaclient import OmadaClient

from .config import Target
from .spec import Op


class Session:
    def __init__(self, target: Target):
        self.target = target

    async def __aenter__(self):
        self._client = OmadaClient(
            self.target.url,
            username=self.target.username,
            password=self.target.password,
            verify_ssl=self.target.verify_ssl,
        )
        await self._client.__aenter__()
        site = await self._client.get_site_client(self.target.site)
        self._api, self.site_id = (
            site._api,
            site._site_id,
        )  # private attributes of tplink-omada-client (hence the pinned version range)
        return self

    async def __aexit__(self, *exc):
        return await self._client.__aexit__(*exc)

    def url(self, op: Op) -> str:
        return self._api.format_openapi_url(op.path, version=op.version, site=self.site_id)

    async def call(self, op: Op, path: str, params: dict | None = None, body=None):
        """Send the request. `path` is `op.path` with its {placeholders} filled in. A paged GET is read to the end."""
        url = self._api.format_openapi_url(path, version=op.version, site=self.site_id)
        method = op.method.lower()
        if method == "get" and op.paged:
            return await self._all_pages(url, dict(params or {}))
        return await self._api.request(method, url, params=params or None, json=body)

    async def _all_pages(self, url: str, params: dict):
        params.setdefault("page", 1)
        params.setdefault("pageSize", 100)
        first = await self._api.request("get", url, params=params)
        if not (isinstance(first, dict) and isinstance(first.get("data"), list) and "totalRows" in first):
            return first
        rows = list(first["data"])
        while len(rows) < first["totalRows"]:
            params["page"] = int(params["page"]) + 1
            more = await self._api.request("get", url, params=params)
            if not more.get("data"):
                break
            rows += more["data"]
        return {**first, "data": rows}


def pretty(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
