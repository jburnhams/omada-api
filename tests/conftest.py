import pytest

SPEC = {
    "paths": {
        "/openapi/v1/{omadacId}/sites/{siteId}/remote-logging": {
            "get": {"summary": "Get site remote logging setting"},
            "patch": {"summary": "Modify site remote logging setting",
                      "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/RL"}}}}},
        },
        "/openapi/v1/{omadacId}/sites/{siteId}/setting/lan/dns": {
            "get": {"summary": "Get LAN DNS list", "parameters": [{"name": "page", "in": "query", "schema": {"type": "integer"}}, {"name": "pageSize", "in": "query", "schema": {"type": "integer"}}]},
            "post": {"summary": "Create a LAN DNS rule"},
        },
        "/openapi/v1/{omadacId}/sites/{siteId}/setting/lan/dns/{dnsId}": {
            "delete": {"summary": "Delete an existing LAN DNS rule", "parameters": [{"name": "dnsId", "in": "path", "required": True, "schema": {"type": "string"}}]},
        },
        "/openapi/v2/{omadacId}/sites/{siteId}/remote-logging": {"get": {"summary": "Get site remote logging setting v2"}},
        "/openapi/v1/{omadacId}/logs/events": {"get": {"summary": "global, not site level"}},
    },
    "components": {"schemas": {
        "RL": {"type": "object", "properties": {"remoteLog": {"$ref": "#/components/schemas/RLInner"}}},
        "RLInner": {"type": "object", "properties": {"enable": {"type": "boolean", "description": "on"}, "host": {"type": "string"}, "password": {"type": "string"}}},
    }},
}


@pytest.fixture
def spec():
    return SPEC
