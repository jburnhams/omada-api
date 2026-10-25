# Recipes

Worked examples from a real network (an ER605 v2 gateway, software controller 6.3.0.111). Replace the IDs with yours. Run each write without `--yes` first.

## Find the LAN network ID
```
omada-api get lan-networks            # the "id" of each network, e.g. Default
```

## DHCP reservation (keep a machine's address)
```
omada-api schema post setting/service/dhcp
omada-api post setting/service/dhcp --json '{"netId": "<network id>", "mac": "AA-BB-CC-11-22-33", "ip": "192.168.0.50", "description": "my machine", "status": true}' --yes
omada-api get setting/service/dhcp
```
(`tplink-omada-client`'s own `omada dhcp create` does the same but reports a `KeyError: 'mac'` after the controller has created the entry; the reservation is there anyway.)

## Upstream DNS servers for the whole LAN (plain, unencrypted)
The gateway's DNS proxy has four modes (`type`: 0 DNSSEC, 1 DoH, 2 DoT, 3 override). Override with two upstream servers, applied to a network:
```
omada-api get setting/service/dns-proxy
omada-api patch setting/service/dns-proxy --json '{"enable": true, "type": 3, "dnsOverrideSetting": {"primaryDnsServer": "1.1.1.2", "secondaryDnsServer": "9.9.9.9", "applyNetwork": ["<network id>"]}}' --yes
```
Check it took effect by asking the router directly. With `1.1.1.2` (Cloudflare, malware blocking) as upstream, `malware.testcategory.com` should resolve to `0.0.0.0`, while ordinary names resolve normally. To undo: `--json '{"enable": false}'`.

The WAN port's own DNS fields are not in the open-API WAN settings (`internet/ports-config`); the DNS proxy is where upstream servers are set.

## Static names on the LAN
```
omada-api schema post setting/lan/dns
omada-api post setting/lan/dns --json '{"enable": true, "name": "unlock", "domain": "unlock.lan", "type": 0, "ipAddresses": ["192.168.0.50"], "lanNetworkIds": ["<network id>"]}' --yes
```
Clients must use the router for DNS for these names to resolve.

## Remote logging (syslog)
```
omada-api get remote-logging
omada-api patch remote-logging --json '{"remoteLog": {"enable": true, "host": "192.168.0.50", "port": 5514, "moreClientLog": true, "resource": 0}}' --yes
```
Needs a syslog receiver at that address and port (UDP), and any firewall there to allow it. `omada-api syslog` is one (see the README).

## Quirks
- List endpoints need `page` and `pageSize`; this tool adds them (100 per page) and reads every page.
- Only the site-level endpoints are searched. The global ones (`/openapi/v1/<omadacId>/...` without `/sites/`) are not reachable from here yet.
- The API description lives at `https://CONTROLLER:8043/v3/api-docs` (about 4 MB, no login needed).
