# Network plan for the Jetson (read from pfSense on 2026-10-03)

## What was checked

Read-only. Nothing on pfSense was changed.

- From the laptop on Trusted (192.168.20.104): gateway, 192.168.10.1, Home Assistant
  (ping and port 8123), 8.8.8.8 and DNS for google.com all respond.
- Outbound NAT is automatic and covers 192.168.10.0/24, 192.168.20.0/24 and 192.168.30.0/24.
- IOT rules, in order: mDNS to the reflector; three device-specific cloud rules;
  block IoT to the pfSense web interface; block IoT to other internal networks; allow DNS
  to pfSense; allow NTP; allow Home Assistant cloud ports; allow TCP 80 and 443 out for all
  IoT devices; Aosu hub rule; log and block everything else.
- The IOT rule counters show traffic passing (for example 229 MiB on the 80/443 rule),
  so IoT devices do reach the internet today.
- TRUSTED rules allow Trusted to reach all of 192.168.10.0/24.
- IOT DHCP pool is 192.168.10.100 to .200. Static mappings exist for .10 to .13.

Conclusion: the old "packets do not pass" problem is gone. The Jetson needs no new firewall
rule. A device plugged into VLAN 10 already gets DNS, time and outbound 80/443.

## What the Jetson needs, and whether it is already there

| Need | Route | Status |
|---|---|---|
| MQTT to Home Assistant (192.168.10.10:1883) | same subnet, does not cross pfSense | ready |
| Claude API (api.anthropic.com, TCP 443) | IOT rule "basic internet access", 80/443 | ready |
| Container pulls, apt, pip, GitHub over HTTPS | same rule | ready |
| DNS | pfSense at 192.168.10.1 only | ready, see Docker note |
| Time sync | NTP rule | ready |
| SSH and setup from the laptop | TRUSTED rule to 192.168.10.0/24 | ready |
| Fixed address | DHCP static mapping | needs the Jetson's MAC address |

## To do when the Jetson arrives

1. Static mapping: Services, DHCP Server, IOT, add static mapping with the Jetson's
   Ethernet MAC, address 192.168.10.20, hostname REDGrow. Suggested for the four ESPHome
   nodes: 192.168.10.21 to .24.
2. Switch: the small PoE switch for the greenhouse goes on a GS308E port set as an
   untagged VLAN 10 access port (PVID 10). Not checked yet.
3. Docker DNS: the IOT rules only allow DNS to pfSense. Containers that fall back to
   8.8.8.8 will fail to resolve names. Put this in /etc/docker/daemon.json on the Jetson:
   `{"dns": ["192.168.10.1"]}`
4. Mosquitto: create the two broker users (gh_core, gh_module) in the Mosquitto add-on.

## Things that will look broken but are by design

- `ping 8.8.8.8` from the Jetson fails. ICMP out is not allowed for IoT. Test with
  `curl -sS -o /dev/null -w '%{http_code}\n' https://api.anthropic.com` instead; any HTTP
  code means the path works.
- Git over SSH (port 22) to the internet is blocked. Use HTTPS remotes.
- The Jetson cannot open the pfSense web interface or reach Trusted devices. Connections
  started from Trusted to the Jetson work.

## Tidy-up found, optional

- The last IOT rule (TCP 853, DNS over TLS, no description) sits below "Log and block all
  other IoT traffic", so it never matches. It can be deleted, or moved above the block rule
  if DNS over TLS for IoT was intended. Leaving it has no effect.
