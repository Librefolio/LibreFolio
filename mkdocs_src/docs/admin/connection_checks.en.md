# 🔍 Checking Connection Security

At the bottom of the sidebar, every user sees how safely the browser talks to the server:
**Connection: secure**, **Connection: local network** or **Connection: not secure**.
The three levels, explained to users: [Connection Security](../user/connection-security.md).

This page is for whoever runs the server: how to check that your deployment shows **Connection: secure**, and how to fix it when it does not.

The goal:

- an HTTPS address, from Tailscale Serve or Funnel ([Exposing Securely](service_exposure.md)) or from a reverse proxy with a certificate ([Behind a reverse proxy](connection_proxy.md#reverse-proxy));
- a session cookie marked `Secure`.

!!! info "📚 This guide is in several pages"

    This page is the checklist: what the indicator shows, how to look at the server's view and the session cookie, what to do when a check fails.
    If you run LibreFolio behind a reverse proxy, [Checking Connection Security: Behind a Reverse Proxy](connection_proxy.md) explains the headers it must send and how LibreFolio learns the visitor's address.

---

## ✅ Checklist {: #checklist }

Go through it once your HTTPS address works, and again after any change to the proxy or to `.env`.
You need an administrator account and, for the last two checks, a phone with mobile data on.

1. **Open the HTTPS address and sign in.**

    The indicator shows 🟢 **Connection: secure**; the details say that the connection is encrypted with HTTPS.

2. **Look for the cookie line.** As an administrator, the details show:

    - that reason and the **How to connect securely** link;
    - a link to the [security checks](settings.md#security-tab) when they list errors or warnings, for example **2 security warnings**.

    One more line about the session cookie means that LibreFolio does not know about the HTTPS: see [Behind a reverse proxy](connection_proxy.md#reverse-proxy).

3. **Ask the server.** In a new tab, open:

    ```text
    https://<your address>/api/v1/system/connection
    ```

    The answer contains `"cookie_secure":true` ([The server's view](#server-view)).

4. **Look at the cookie.** Open the browser's developer tools.

    The `session` cookie is marked `Secure` ([The session cookie](#session-cookie)).

5. **From outside, open the HTTPS address.** On the phone, with Wi-Fi off.

    The page loads and, after signing in, the indicator shows 🟢 **Connection: secure**.

    | Address | Tailscale on the phone |
    | --- | --- |
    | Funnel or reverse proxy | Off |
    | Tailscale Serve (only your tailnet opens it) | On |

6. **From outside, try plain HTTP.** On the same phone, open:

    ```text
    http://<your public IP or name>:6040
    ```

    Or your own `PORT`. The page does **not** load.

    If the login page appears, plain HTTP is open to the internet:

    - do not sign in there: the password would travel in clear text;
    - close the port ([When a check fails](#when-a-check-fails)).

    Whoever signs in from that address sees 🔴 **Connection: not secure**, or 🏠 **Connection: local network** with an *Unclear* reason when the server cannot see where visitors come from ([Limits](#limits)).

Every check passed? Ask your users to use the HTTPS address on every device and to update their old bookmarks ([How to connect securely](../user/connection-security.md#https-address)).

!!! note "📶 No HTTPS address yet?"

    With Level 1 or 2 of [Exposing Securely](service_exposure.md), users reach LibreFolio over plain HTTP.
    Check the level each address gets ([What the indicator shows](#indicator)) and that plain HTTP does not load from outside (check 6).
    The cookie checks do not apply: over plain HTTP the session cookie is not `Secure`, and `"cookie_secure":false` is expected.

---

## 🚦 What the Indicator Shows {: #indicator }

The browser judges the address it opened.
The server then reports where it sees the request coming from: it can confirm the verdict or make it uncertain, never make it secure.

| How users reach LibreFolio | Example | Level |
| --- | --- | --- |
| Tailscale Serve or Funnel, or a reverse proxy with a certificate | `https://librefolio.your-tailnet.ts.net` | 🟢 **secure**: HTTPS |
| On the server itself | `http://localhost:6040` | 🟢 **secure**: `localhost` |
| Tailscale IP or full MagicDNS name, plain HTTP (Level 1) | `http://100.a.b.c:6040` | 🟢 **secure**: VPN (Tailscale) |
| Short MagicDNS name, plain HTTP: a name without dots counts as local | `http://your-server:6040` | 🏠 **local network** |
| Local address, also through a subnet router (Level 2) | `http://192.168.1.100:6040` | 🏠 **local network** |
| A port opened on the router, plain HTTP | `http://myhome.duckdns.org:6040` | 🔴 **not secure** |

When the server cannot see the visitors' addresses, the last row shows 🏠 **local network** with an *Unclear* reason instead ([Limits](#limits)).
The exact rules of each level (address ranges, names, *Unclear* cases): [Connection Security](../user/connection-security.md#connection-secure).

---

## 🔎 The Server's View {: #server-view }

At every page load, the indicator asks the server how it sees the connection: `GET /api/v1/system/connection`.

To read the same answer:

1. **Sign in to LibreFolio.**

2. **Open this address in a new tab of the same browser**, with your LibreFolio address in place of the example:

    ```text
    https://librefolio.your-tailnet.ts.net/api/v1/system/connection
    ```

    The browser shows a one-line answer:

    ```json
    {"client_class":"public","cookie_secure":true}
    ```

Good to know:

- any account works, not only an administrator;
- `{"detail":"Not authenticated"}` means that there is no session at that address: sessions belong to an address, so signing in at `http://192.168.1.100:6040` does not sign you in at the HTTPS address;
- the indicator asks only once per page load: reload LibreFolio after a change to see the new verdict.

**`cookie_secure`**: whether a session cookie set on this request would be `Secure`, following [`SESSION_COOKIE_SECURE`](#session-cookie).

| Address | Expected value |
| --- | --- |
| HTTPS | `true`. `false` shows the administrator line about the cookie ([Behind a reverse proxy](connection_proxy.md#reverse-proxy)) |
| Plain HTTP | `false` |

**`client_class`**: where the server sees the request coming from.
It reads the last `X-Forwarded-For` value, the one added by the nearest proxy, if it is an IP address; otherwise the address of the connection itself.
Only the class leaves the server: the address is never returned or logged.

| `client_class` | The request comes from |
| --- | --- |
| `loopback` | The server itself: `127.0.0.0/8` or `::1` |
| `vpn` | Tailscale or Headscale: `100.64.0.0/10` or `fd7a:115c:a1e0::/48` |
| `lan` | A local network: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` or `fc00::/7` |
| `public` | Any other address: the internet |
| `unknown` | No address, or one that cannot be read |

The class counts only over plain HTTP, and not on the server itself (`localhost`):

| Address in the browser | `client_class` | Effect on the verdict |
| --- | --- | --- |
| Public | `public` or `unknown` | Confirms **Connection: not secure** |
| Public | `loopback`, `vpn` or `lan` | Becomes **Connection: local network**: uncertain verdict |
| Local or Tailscale | `public` | Uncertain verdict |
| Local or Tailscale | Any other | None |

On the HTTPS address the class changes nothing, but it tells you whether the server sees the visitors' addresses.
From the phone on mobile data, with Tailscale off:

- `public`: the server sees them;
- `lan` or `loopback`: it does not ([Limits](#limits)).

---

## 🍪 The Session Cookie {: #session-cookie }

The cookie that keeps you signed in is called `session`.
LibreFolio sets it at sign-in, always with `HttpOnly` (scripts in the page cannot read it) and `SameSite=Lax`.

Whether it is also `Secure`, that is, sent over HTTPS only, depends on `SESSION_COOKIE_SECURE` in `.env`:

| Value | `Secure` |
| --- | --- |
| `auto` (default) | When the request is HTTPS: seen directly, or because the first `X-Forwarded-Proto` value sent by a reverse proxy is `https` |
| `always` | Always |
| `never` | Never |

Case and spaces around the value do not matter.
Any other value stops LibreFolio at startup.
When `always` or `never` is the right choice: [Configuration](configuration.md#session-cookie-secure).

The flag is decided at sign-in: a cookie already in the browser keeps the flag it got then.
After fixing the proxy or the option, sign out and sign in again.

To see the flag in the browser:

1. **Sign in at the HTTPS address.**

2. **Open the developer tools**: `F12`, or right-click the page → **Inspect**.

    Safari shows them only once the developer features are turned on in its settings.

3. **Open the cookies of your LibreFolio address.**

    | Browser | Path |
    | --- | --- |
    | Chrome, Edge | **Application** → **Cookies** |
    | Firefox, Safari | **Storage** → **Cookies** |

4. **Read the `session` row.**

    **Secure** is ticked (`true` in Firefox), as is **HttpOnly**; **SameSite** reads `Lax`.

The console cannot show it: `document.cookie` leaves out `HttpOnly` cookies.

---

## 🛠️ When a Check Fails {: #when-a-check-fails }

| What you see | Why | What to do |
| --- | --- | --- |
| The HTTPS address does not show **Connection: secure** | The page is not on HTTPS: the address bar shows `http://` | Open the `https://` address and have the proxy redirect `http://` to it |
| The line about the session cookie, or `"cookie_secure":false` on the HTTPS address | The proxy does not send `X-Forwarded-Proto: https`, or `SESSION_COOKIE_SECURE` is `never` | Fix the proxy ([Behind a reverse proxy](connection_proxy.md#reverse-proxy)) or set the option back to `auto`, then reload |
| `"cookie_secure":true`, but the `session` cookie is not `Secure` | The cookie was set before the fix | Sign out and sign in again |
| `{"detail":"Not authenticated"}` | No session at this address | Sign in at this address, in the same browser |
| Every sign-in ends on the login page again | The cookie is `Secure`, but the browser uses plain HTTP: `SESSION_COOKIE_SECURE=always`, or a proxy that sends `X-Forwarded-Proto: https` to a plain-HTTP browser | Use the HTTPS address or fix the proxy: [Configuration](configuration.md#session-cookie-secure) |
| From outside, the HTTPS address does not load | A Tailscale Serve address is private; a new Funnel needs approval and a few minutes | Switch Tailscale on on the phone, or use Funnel; approve the Funnel and wait ([Exposing Securely: Public Access with Funnel](service_exposure_funnel.md#step-2-approve-and-wait-for-propagation)) |
| From outside, plain `http://…:6040` loads | LibreFolio's port is open to the internet: a port forward on the router, or a server with a public address | Close it: remove the port forward or block the port in the server's firewall. Tailscale needs no open port, a reverse proxy only its own |
| `client_class` shows `lan` or `loopback` from mobile data, or plain HTTP from the internet shows **Connection: local network**, *Unclear* | The server cannot see where visitors come from | See [Limits](#limits); with Nginx, add the `X-Forwarded-For` line |
| A Tailscale address shows **Connection: local network** | A short MagicDNS name has no dots, so it counts as local | Use the Tailscale IP, the full `.ts.net` name or, better, the HTTPS address |

---

## ⚠️ Limits {: #limits }

The indicator is advice, not a check: it blocks nothing.
Two limits matter when you check a deployment.

**It does not always see where visitors come from.**

- With Docker Desktop exposed directly, or behind a proxy that does not pass the visitor's address in `X-Forwarded-For`, the server sees every visitor as local: `lan`, or `loopback` for a proxy on the same machine.
- Plain HTTP from the internet then shows **Connection: local network**, with an uncertain verdict, instead of **Connection: not secure**.
- HTTPS addresses are not affected: they show **Connection: secure** either way.
- Docker Engine on Linux keeps the visitor's address over IPv4.
- Over IPv6, unless the container has an IPv6 address of its own, IPv6 visitors arrive through Docker's proxy, from the gateway of the container's network: all of them share that one local address, for the indicator and for the limits per visitor's address, which therefore count them together.
- Docker's proxy adds no forwarding header, so LibreFolio cannot notice it: its warning about a proxy it does not trust needs a header of that kind.
- A reverse proxy in front that sees each visitor's address, set up as [The Visitor's Address](connection_proxy.md#client-address) explains, avoids it.

**It does not check certificates.**

- A self-signed certificate that a user accepted in the browser shows **Connection: secure**: the traffic is encrypted, but nobody vouches that the server is really yours.

Neither the indicator nor the session cookie needs a list of trusted proxies:

- a forged `X-Forwarded-For` misleads only the indicator of whoever sent it;
- `X-Forwarded-Proto` can only turn `Secure` on, so a forged `https` breaks only the sender's own sign-in.

The limits per visitor's address are another matter: [The Visitor's Address](connection_proxy.md#client-address).

---

## 🔗 Related

- 📄 **[Checking Connection Security: Behind a Reverse Proxy](connection_proxy.md)** — Which proxies LibreFolio trusts, the visitor's address, Tailscale with Docker
- 🔐 **[Connection Security](../user/connection-security.md)** — The user guide: the three levels and what to do at each
- 🌐 **[Exposing Securely](service_exposure.md)** — Tailscale, from a private VPN to a public HTTPS address
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, environment variables, reverse proxy
- 📝 **[Configuration](configuration.md)** — `SESSION_COOKIE_SECURE` and every other `.env` option
