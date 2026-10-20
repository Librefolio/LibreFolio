# 🔍 Checking Connection Security

Every user sees, at the bottom of LibreFolio's sidebar, how safely their browser talks to the
server: **Connection: secure**, **Connection: local network** or **Connection: not secure**. The
user guide, [Connection Security](../user/connection-security.md), explains the three levels to
them. This page is for whoever runs the server: how to check that your deployment gives its users
**Connection: secure**, and how to fix it when it does not.

The goal is an HTTPS address, from Tailscale Serve or Funnel
([Exposing Securely](service_exposure.md)) or from a reverse proxy with a certificate
([Behind a reverse proxy](#reverse-proxy)), and a session cookie marked `Secure`.

---

## ✅ Checklist {: #checklist }

Go through it once your HTTPS address works, and again after any change to the proxy or to `.env`.
You need an administrator account and, for the last two checks, a phone on mobile data.

1. **Open the HTTPS address and sign in.** The indicator shows 🟢 **Connection: secure**, and its
   details say that the connection is encrypted with HTTPS.
2. **Look for the cookie line.** Signed in as an administrator, the details show only that reason
   and the **How to connect securely** link. One more line, about the session cookie, means that
   LibreFolio does not know about the HTTPS: see [Behind a reverse proxy](#reverse-proxy).
3. **Ask the server.** In a new tab, open `https://<your address>/api/v1/system/connection`: the
   answer contains `"cookie_secure":true` ([The server's view](#server-view)).
4. **Look at the cookie.** In the browser's developer tools, the `session` cookie is
   marked `Secure` ([The session cookie](#session-cookie)).
5. **From outside, open the HTTPS address.** On the phone, with Wi-Fi off, the page loads and, once
   you sign in, the indicator shows 🟢 **Connection: secure**. Keep Tailscale off on the phone for a
   Funnel or reverse-proxy address; switch it on for a Tailscale Serve address, which only your
   tailnet can open.
6. **From outside, try plain HTTP.** On the same phone, `http://<your public IP or name>:6040`, or
   your own `PORT`, does not load. If the login page appears, plain HTTP is open to the internet:
   do not sign in there, since the password would travel in clear text, and close the port
   ([When a check fails](#when-a-check-fails)). Whoever signs in over that address sees
   🔴 **Connection: not secure**, or 🏠 **Connection: local network** with an *Unclear* reason when
   the server cannot see where visitors come from ([Limits](#limits)).

Every check passed? Ask your users to use the HTTPS address on every device and to update their old
bookmarks ([How to connect securely](../user/connection-security.md#https-address)).

!!! note "📶 No HTTPS address yet?"

    With Level 1 or 2 of [Exposing Securely](service_exposure.md), users reach LibreFolio over plain
    HTTP. Check the level each address gets ([What the indicator shows](#indicator)) and that plain
    HTTP does not load from outside (check 6). The cookie checks do not apply: over plain HTTP the
    session cookie is not `Secure`, and `"cookie_secure":false` is expected.

---

## 🚦 What the Indicator Shows {: #indicator }

The browser judges the address it opened; the server then reports where it sees the request coming
from, and can confirm that verdict or make it uncertain, but never make it secure. What your users
see, by the way they reach LibreFolio:

| How users reach LibreFolio | Example | Level |
| --- | --- | --- |
| Tailscale Serve or Funnel, or a reverse proxy with a certificate | `https://librefolio.your-tailnet.ts.net` | 🟢 **secure**: HTTPS |
| On the server itself | `http://localhost:6040` | 🟢 **secure**: `localhost` |
| Tailscale IP or full MagicDNS name, plain HTTP (Level 1) | `http://100.a.b.c:6040` | 🟢 **secure**: VPN (Tailscale) |
| Short MagicDNS name, plain HTTP: a name without a dot counts as local | `http://your-server:6040` | 🏠 **local network** |
| Local address, also through a subnet router (Level 2) | `http://192.168.1.100:6040` | 🏠 **local network** |
| A port opened on the router, plain HTTP | `http://myhome.duckdns.org:6040` | 🔴 **not secure** |

When the server cannot see your visitors' addresses, the last row shows 🏠 **local network** with
an *Unclear* reason instead ([Limits](#limits)). The user guide gives the exact rules under each
level: address ranges, names and the *Unclear* cases
([Connection Security](../user/connection-security.md#connection-secure)).

---

## 🔎 The Server's View {: #server-view }

The indicator asks the server how it sees the connection, once per page load:
`GET /api/v1/system/connection`. You can read the same answer: signed in, open this address in a
new tab of the same browser, with your own LibreFolio address in place of the example's:

```text
https://librefolio.your-tailnet.ts.net/api/v1/system/connection
```

The browser shows a one-line answer, for example:

```json
{"client_class":"public","cookie_secure":true}
```

Any account works, not only an administrator. An answer such as `{"detail":"Not authenticated"}`
means that there is no session at that address: sessions belong to an address, so signing in at
`http://192.168.1.100:6040` does not sign you in at the HTTPS address. And since the indicator asks
only once per page load, reload LibreFolio after a change to see its new verdict.

**`cookie_secure`** tells whether a session cookie set on this request would be `Secure`, following
[`SESSION_COOKIE_SECURE`](#session-cookie). On the HTTPS address it must be `true`: `false` is what
shows the administrator line about the cookie ([Behind a reverse proxy](#reverse-proxy)). Over plain
HTTP, `false` is expected.

**`client_class`** is where the server sees the request coming from. It reads the last
`X-Forwarded-For` value, the one the nearest proxy added, when it is an IP address, and otherwise
the address of the connection itself. Only the class leaves the server: the address is never
returned or logged.

| `client_class` | The request comes from |
| --- | --- |
| `loopback` | The server itself: `127.0.0.0/8` or `::1` |
| `vpn` | Tailscale or Headscale: `100.64.0.0/10` or `fd7a:115c:a1e0::/48` |
| `lan` | A local network: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` or `fc00::/7` |
| `public` | Any other address: the internet |
| `unknown` | No address, or one that cannot be read |

The class counts only over plain HTTP, and not on the server itself (`localhost`):

- with a public address in the browser, `public` or `unknown` confirms **Connection: not secure**,
  while `loopback`, `vpn` or `lan` turn it into **Connection: local network**, as unclear;
- with a local or Tailscale address in the browser, `public` makes the verdict unclear, and any other
  class leaves it as it is.

On the HTTPS address the class changes nothing, but it tells you whether the server can see your
visitors' addresses: from the phone on mobile data, with Tailscale off, `public` means it can, and
`lan` or `loopback` mean it cannot ([Limits](#limits)).

---

## 🍪 The Session Cookie {: #session-cookie }

The cookie that keeps a user signed in is called `session`. LibreFolio sets it at sign-in, always
`HttpOnly`, so scripts in the page cannot read it, and `SameSite=Lax`. Whether it is also `Secure`,
sent over HTTPS only, depends on `SESSION_COOKIE_SECURE` in `.env`:

- **`auto`**, the default: `Secure` when the request is HTTPS, seen directly or because the first
  `X-Forwarded-Proto` value sent by a reverse proxy is `https`;
- **`always`**: always `Secure`;
- **`never`**: never `Secure`.

Case and spaces around the value do not matter; any other value stops LibreFolio at startup. When
`always` or `never` is the right choice: [Configuration](configuration.md#session-cookie-secure).

The flag is decided at sign-in: the cookie a browser already holds keeps the flag it got then. After
fixing the proxy or the option, sign out and sign in again.

To see the flag in the browser:

1. Sign in at the HTTPS address.
2. Open the developer tools: `F12`, or right-click the page and choose **Inspect**. Safari shows
   them only once its developer features are turned on in its settings.
3. Open the cookies of your LibreFolio address: **Application** → **Cookies** in Chrome and Edge,
   **Storage** → **Cookies** in Firefox and Safari.
4. In the `session` row, **Secure** is ticked (`true` in Firefox), and so is **HttpOnly**;
   **SameSite** reads `Lax`.

The console cannot show it: `document.cookie` leaves out `HttpOnly` cookies.

---

## 🧰 Behind a Reverse Proxy {: #reverse-proxy }

A reverse proxy receives the HTTPS connection and passes it to LibreFolio over plain HTTP, so
LibreFolio learns about the HTTPS, and about the visitor, only from the proxy's headers:

- `X-Forwarded-Proto: https` says that the browser uses HTTPS: with `SESSION_COOKIE_SECURE=auto`,
  the default, LibreFolio then marks the session cookie `Secure`;
- `X-Forwarded-For` carries the visitor's address, which lets the indicator see where users connect
  from.

Tailscale Serve and Funnel, Caddy and Traefik send both on their own. Nginx needs both lines in the
`location` block that passes requests to LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

If the browser uses HTTPS but the session cookie is not marked `Secure`, because the proxy does not
send `X-Forwarded-Proto` or because `SESSION_COOKIE_SECURE` is `never`, administrators see one more
line in the indicator's details. The level stays **Connection: secure**, because the connection is
encrypted; only the cookie lacks `Secure`:

> Your browser uses HTTPS, but the session cookie is not marked Secure. Make the reverse proxy send
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), or set
> SESSION_COOKIE_SECURE back to auto if it is never.

Once the proxy is fixed, reload LibreFolio: the line disappears. Then sign out and sign in again,
so that the browser gets a `Secure` cookie.

??? tip "⚙️ Set `SESSION_COOKIE_SECURE` instead"

    Sending the header is the better fix. If you only ever reach LibreFolio over HTTPS, you can
    instead add this line to `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Then restart LibreFolio: with Docker, run `docker compose up -d` (a plain
    `docker compose restart` keeps the old environment); on a host installation, restart
    `./dev.py server`, which reads `.env` too. Then sign out and sign in again.

    Use `never` only for the rare proxy that claims HTTPS while the browser is on plain HTTP. See
    [Configuration](configuration.md#session-cookie-secure) for every option.

### 🧭 The Visitor's Address {: #client-address }

LibreFolio limits some requests per visitor's address: the failed sign-ins
([Failed Sign-ins](configuration.md#login-limit)), the registration emails, **Send the link again**
and the forgotten passwords ([Email](email.md)). Behind a reverse proxy, the connections come from
the proxy: unless LibreFolio learns each visitor's address, all of them share the proxy's, and a
single count. For the sign-ins it matters most: 50 failed sign-ins through the proxy, from anyone,
would refuse every sign-in through it, the right passwords included, for up to 15 minutes. That
remains true behind a proxy on a public address. Behind one on a local address, such as a proxy
container in front of the Docker image, LibreFolio leaves the sign-ins through it out of the count
per address instead, and only the limit per username or email address counts them: see
[When LibreFolio does not trust your proxy](#untrusted-proxy), below. Either way, the cure is to
let LibreFolio learn each visitor's address, in one of the two ways that follow.

Out of the box, the address that counts is the connection's, as uvicorn, LibreFolio's web server,
gives it. uvicorn takes the visitor's address from `X-Forwarded-For` only when the connection comes
from an address listed in `FORWARDED_ALLOW_IPS`, `127.0.0.1` when that variable is not set:
«Forgotten Passwords» in [Email](email.md#forgot-password) explains how to list your proxy there.

If your proxy writes the visitor's address in a header of its own instead, name that header in
`LIBREFOLIO_CLIENT_IP_HEADER`, in `.env` or in the container's environment:

```bash
LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP
```

| Your proxy | The header | What to set up |
| --- | --- | --- |
| Fly.io | `Fly-Client-IP` | Nothing: Fly's proxy sets it. |
| Nginx | `X-Real-IP` | Add `proxy_set_header X-Real-IP $remote_addr;` to the `location` block that passes requests to LibreFolio. |

!!! warning "🚧 Only when every request crosses the proxy"

    LibreFolio believes the header whoever sends it. Set the variable only if your visitors can
    reach LibreFolio through that proxy alone: a visitor who reaches it directly, on its own port
    (`PORT`, 6040 by default) or by any other path, can send the header and choose any address, to
    get around the limits or to use up someone else's.

- **Restart after a change**: LibreFolio reads the variable once per server process. With Docker,
  run `docker compose up -d` (a plain `docker compose restart` keeps the old environment); on a
  host installation, restart `./dev.py server`.
- **The header must hold one address, written by the proxy itself**: never a value the proxy passes
  on from the visitor. `X-Forwarded-For` and `Forwarded` are refused: they hold a list whose first
  address the visitor chooses. For `X-Forwarded-For`, list your proxy in `FORWARDED_ALLOW_IPS`
  instead.
- **A wrong value stops the server at startup**, with an error that names the variable: one of
  those two headers, or a value that is not the name of one header, such as a name with a space or
  a `:` in it. Case and spaces around the name do not matter; an empty value is the same as not
  setting it.
- **A request without the header** counts with the connection's address.
- **A header LibreFolio cannot use**, because the request carries it twice or it holds a list, an
  address with a port or anything other than one IP address, counts with the connection's address
  too. The log then has one warning per server process,
  `Client address header unusable: using the connection's address`, with the header's name in
  `header`, how many times the request carried it in `lines` and their total length in `length`,
  never the value itself: check how your proxy sets the header.
- **Another proxy in front of Fly.io**, such as Cloudflare: `Fly-Client-IP` then holds that proxy's
  address, not the visitor's.
- **No profile sets it**, the [managed profile](hosting_providers.md#managed-profile) included: the
  header depends on the proxy in front of each instance.
- **The indicator does not use it**: it keeps reading `X-Forwarded-For`, as
  [The Server's View](#server-view) explains.

#### 🕵️ When LibreFolio Does Not Trust Your Proxy {: #untrusted-proxy }

LibreFolio does not trust your proxy when it learns the visitor's address neither through
`FORWARDED_ALLOW_IPS` nor through `LIBREFOLIO_CLIENT_IP_HEADER`: it cannot tell the visitors
behind the proxy apart, and neither can its limits per visitor's address. It recognises such a
proxy by its requests: they come from a local address (`loopback`, `lan` or `vpn` in
[The Server's View](#server-view), such as `172.18.0.2` on a Docker network) and carry a forwarding
header (`X-Forwarded-For`, `Forwarded` or `X-Real-IP`) that gave LibreFolio no visitor's address.
Then:

- **The limits per visitor's address leave those requests out**, so that one visitor cannot lock
  everyone out. The limits per account or per email address still count them.
- **The log has one warning per server process**, the first time such a request meets a limit per
  visitor's address:
  `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`,
  with the names of the headers in `headers`, such as `X-Forwarded-For, X-Real-IP`, never an
  address.
- **The security checks** report it too, as a warning of `platform.client_address`. This check
  tells what the server has met since its last start: after a restart it reads `ok` until such a
  request comes again, so it never appears among the [startup checks](configuration.md#startup-checks).
- **To fix it**, list your proxy in `FORWARDED_ALLOW_IPS`, as «Forgotten Passwords» in
  [Email](email.md#forgot-password) explains, or name the header it sets itself in
  `LIBREFOLIO_CLIENT_IP_HEADER`, as above, if every request crosses it. Behind Tailscale Serve or
  Funnel with the Docker image, follow [Tailscale Serve and Funnel with Docker](#tailscale). In
  `FORWARDED_ALLOW_IPS`, give the proxy's address as LibreFolio sees it: with Docker, the proxy
  container's address, or its Docker network, such as `FORWARDED_ALLOW_IPS=172.18.0.0/16`
  (`docker network inspect`, with the network's name, shows both), though a whole network includes
  its gateway, which is also the address of the connections made on the server itself
  ([see below](#tailscale)). Trust only addresses your proxy alone uses. Set either variable
  in `.env` or in the container's environment, then restart, as above: with Docker,
  `docker compose up -d`. No proxy of yours in front of LibreFolio? Then a visitor on your own
  network or VPN sent the header, or, with Docker Desktop exposed directly, any visitor, or any
  IPv6 visitor that Docker's proxy passes on ([Limits](#limits)): list nothing.

**Forwarding headers from a public address** only get an `info`, in the log once per server process,
`Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS`,
with `headers` too, and in the security checks, where `platform.client_address` stays a warning if
a proxy as above was met too. Those requests keep counting with the connection's address. They are
harmless when no proxy of yours has a public address: a visitor, or a proxy of their own, may add
such headers.

#### 🐳 Tailscale Serve and Funnel with Docker {: #tailscale }

Tailscale Serve and Funnel pass the visitor's address in `X-Forwarded-For`: the Tailscale address
of the device, `100.x.y.z`, or, through Funnel, the address of the visitor on the internet. They
write the header themselves, in place of any the visitor sent. Over HTTPS, the default of Serve and
the only way of Funnel, they also send `X-Forwarded-Proto: https`; with `tailscale serve --http=…`
they send none, rightly, since the browser is on plain HTTP too.

With the Docker image, LibreFolio cannot use that address out of the box. Both Tailscale setups of
[Exposing Securely](service_exposure.md) reach its container through Docker, so their requests come
from the gateway of the container's Docker network, such as `172.28.0.1`, which uvicorn does not
trust:

- **On the server**, `tailscale serve --bg 6040` (the HTTPS address of Level 1) or
  `tailscale funnel --bg 6040` (Level 3) passes the requests to `http://127.0.0.1:6040`, and
  Docker's own proxy hands them to the container;
- **In sidecar containers** (Level 4), socat passes them to the server's LAN address and
  LibreFolio's published port.

So LibreFolio warns about a proxy it does not trust, [as above](#untrusted-proxy), and its limits
per visitor's address leave all those requests out. Installed on the host instead, without Docker,
LibreFolio needs nothing for `tailscale serve` or `tailscale funnel` on the same server: it sees
their requests come from `127.0.0.1`, which uvicorn trusts by default.

To let LibreFolio see each visitor, work on the server, in the folder that holds
`docker-compose.yml` and `.env`:

1. **Find the gateway** of LibreFolio's Docker network:

    ```bash
    docker inspect --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' librefolio
    ```

    It prints an address such as `172.28.0.1`; `librefolio` is the name `docker-compose.yml` gives
    the container (`container_name`). `docker network inspect <network>` shows the same gateway
    under `IPAM` → `Config` → `Gateway`, next to the network's `Subnet`: `docker network ls` lists
    the networks, and a Compose project's own is `<project>_default`.

    To make sure that Tailscale's requests come from it, open LibreFolio at its Tailscale address,
    then read the last lines of its log:

    ```bash
    docker compose logs --tail 20 librefolio
    ```

    uvicorn logs each request on a line that gives the address it sees, then the request. Through
    Tailscale, that address is the gateway's:

    ```text
    172.28.0.1:<port> - "GET … HTTP/1.1" 200 OK
    ```

    The lines for `/api/v1/system/health` are Docker's health check, made inside the container:
    leave them aside.

2. **List the gateway in `FORWARDED_ALLOW_IPS`.** Add this line to `.env`, with your own gateway:

    ```bash
    FORWARDED_ALLOW_IPS=172.28.0.1
    ```

    If `.env` already sets the variable, for another proxy, add the gateway at the end of its list,
    after a comma.

3. **Restart LibreFolio**, so that its container gets the new environment:

    ```bash
    docker compose up -d
    ```

    A plain `docker compose restart` keeps the old environment.

4. **Check.** Open LibreFolio at its Tailscale address again, then read the log as in step 1. The
   lines of your requests now show the address of the device in place of the gateway's (through
   Funnel, the visitor's public address), followed by port `0`:

    ```text
    100.x.y.z:0 - "GET … HTTP/1.1" 200 OK
    ```

    The warning of `platform.client_address` stops coming back. That check tells what the server
    has met since its last start, though, so it reads `ok` after the restart either way: the log
    line is the real proof.

Three things to keep in mind about trusting the gateway:

- **The exact gateway is the narrowest choice**, but Compose may give the network another subnet
  when it creates it again (`docker compose down`, then `docker compose up -d`): check the gateway
  again after such a change.
- **`FORWARDED_ALLOW_IPS=172.16.0.0/12` survives that**, since it covers every Docker network from
  `172.16` to `172.31`. But it trusts every Docker network on the server, and it does not cover the
  `192.168.x.x` networks that Docker hands out once those run out.
- **The gateway is not Tailscale alone.** It is also the address of every connection made on the
  server itself through the published port, and of the IPv6 visitors that Docker's proxy passes on
  ([Limits](#limits)): trusting it lets them choose the address the limits count.
    - If you reach LibreFolio **only** through `tailscale serve` or `tailscale funnel` on the
      server, publish the port on the loopback only, so that nothing outside the server can reach
      it: in `docker-compose.yml`, under `ports:`, change `"${PORT:-6040}:6040"` to
      `"127.0.0.1:${PORT:-6040}:6040"`, then run `docker compose up -d`.
    - Not with Level 4, nor with the plain-HTTP addresses of Levels 1 and 2: they reach the port
      through the server's LAN or Tailscale address.

---

## 🛠️ When a Check Fails {: #when-a-check-fails }

| What you see | Why | What to do |
| --- | --- | --- |
| The HTTPS address does not show **Connection: secure** | The page is not on HTTPS: the address bar shows `http://` | Open the `https://` address, and have the proxy redirect `http://` to it |
| The line about the session cookie, or `"cookie_secure":false` on the HTTPS address | The proxy does not send `X-Forwarded-Proto: https`, or `SESSION_COOKIE_SECURE` is `never` | Fix the proxy ([Behind a reverse proxy](#reverse-proxy)) or set the option back to `auto`, then reload |
| `"cookie_secure":true`, but the `session` cookie is not `Secure` | The cookie was set before the fix | Sign out and sign in again |
| `{"detail":"Not authenticated"}` | No session at this address | Sign in at this address, in the same browser |
| Every sign-in ends on the login page again | The cookie is `Secure`, but the browser uses plain HTTP: `SESSION_COOKIE_SECURE=always`, or a proxy that sends `X-Forwarded-Proto: https` to a plain-HTTP browser | Use the HTTPS address, or fix the proxy: see [Configuration](configuration.md#session-cookie-secure) |
| From outside, the HTTPS address does not load | A Tailscale Serve address is private; a new Funnel needs approval and a few minutes | Switch Tailscale on on the phone, or use Funnel; approve the Funnel and wait ([Exposing Securely](service_exposure.md)) |
| From outside, plain `http://…:6040` loads | LibreFolio's port is open to the internet: a port forward on the router, or a server with a public address | Close it: remove the port forward, or block the port in the server's firewall. Tailscale needs no open port, and a reverse proxy only its own |
| `client_class` reads `lan` or `loopback` from mobile data, or plain HTTP from the internet shows **Connection: local network**, *Unclear* | The server cannot see where visitors come from | See [Limits](#limits); with Nginx, add the `X-Forwarded-For` line |
| A Tailscale address shows **Connection: local network** | A short MagicDNS name has no dot, so it counts as local | Use the Tailscale IP, the full `.ts.net` name or, better, the HTTPS address |

---

## ⚠️ Limits {: #limits }

The indicator is advice, not a check: it blocks nothing. Two limits matter when you check a
deployment.

**It cannot always see where visitors are.** With Docker Desktop exposed directly, or behind a
proxy that does not pass the visitor's address in `X-Forwarded-For`, the server sees every visitor
as local: `lan`, or `loopback` for a proxy on the same machine. Plain HTTP from the internet then
shows **Connection: local network**, as unclear, instead of **Connection: not secure**. HTTPS
addresses are not affected: they show **Connection: secure** either way. Docker Engine on Linux
keeps the visitor's address over IPv4; over IPv6, unless the container has an IPv6 address of its
own, IPv6 visitors arrive through Docker's proxy, from the gateway of the container's network, so
all of them share that one local address, for the indicator and for the limits per visitor's
address, which then count them together. Docker's proxy adds no forwarding header, so LibreFolio
cannot notice it: its warning about a proxy it does not trust needs one. A reverse proxy in front
that sees each visitor's own address, set up as [The Visitor's Address](#client-address) explains,
avoids it.

**It does not check certificates.** A self-signed certificate that a user accepted in the browser
shows **Connection: secure**: the traffic is encrypted, but nobody vouches that the server is really
yours.

Neither the indicator nor the session cookie needs a list of trusted proxies: a forged
`X-Forwarded-For` misleads only the indicator of whoever sent it, and since `X-Forwarded-Proto` can
only turn `Secure` on, a forged `https` breaks only the sender's own sign-in. The limits per
visitor's address are another matter: see [The Visitor's Address](#client-address).

---

## 🔗 Related

- 🔐 **[Connection Security](../user/connection-security.md)** — The user guide: the three levels
  and what to do at each
- 🌐 **[Exposing Securely](service_exposure.md)** — Tailscale, from a private VPN to a public HTTPS
  address
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, environment variables, reverse proxy
- 📝 **[Configuration](configuration.md)** — `SESSION_COOKIE_SECURE` and every other `.env` option
