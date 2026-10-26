# 🧰 Checking Connection Security: Behind a Reverse Proxy

This page is for running LibreFolio **behind a reverse proxy** such as Nginx, Caddy, Traefik or
Tailscale Serve: the headers the proxy must send for the connection to count as secure, which proxy
LibreFolio trusts, and how it learns each visitor's address.

To see what your users get, with the indicator, the server's view and the session cookie, start from
[Checking Connection Security](connection_checks.md).

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
([Failed Sign-ins](configuration_accounts.md#login-limit)), the registration emails, **Send the link again**
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
[Forgotten Passwords](email_flows.md#forgot-password), in the email guide, explains how to list your proxy there.

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
  [The Server's View](connection_checks.md#server-view) explains.

#### 🕵️ When LibreFolio Does Not Trust Your Proxy {: #untrusted-proxy }

LibreFolio does not trust your proxy when it learns the visitor's address neither through
`FORWARDED_ALLOW_IPS` nor through `LIBREFOLIO_CLIENT_IP_HEADER`: it cannot tell the visitors
behind the proxy apart, and neither can its limits per visitor's address. It recognises such a
proxy by its requests: they come from a local address (`loopback`, `lan` or `vpn` in
[The Server's View](connection_checks.md#server-view), such as `172.18.0.2` on a Docker network) and carry a forwarding
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
  request comes again, so it never appears among the [startup checks](configuration_security.md#startup-checks).
- **To fix it**, list your proxy in `FORWARDED_ALLOW_IPS`, as [Forgotten Passwords](email_flows.md#forgot-password)
  in the email guide explains, or name the header it sets itself in
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
  IPv6 visitor that Docker's proxy passes on ([Limits](connection_checks.md#limits)): list nothing.

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
[Exposing Securely](service_exposure.md), on the server and in
[sidecar containers](service_exposure_funnel.md#level-4-multi-funnel-with-docker-sidecars), reach its container through Docker, so their requests come
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
  ([Limits](connection_checks.md#limits)): trusting it lets them choose the address the limits count.
    - If you reach LibreFolio **only** through `tailscale serve` or `tailscale funnel` on the
      server, publish the port on the loopback only, so that nothing outside the server can reach
      it: in `docker-compose.yml`, under `ports:`, change `"${PORT:-6040}:6040"` to
      `"127.0.0.1:${PORT:-6040}:6040"`, then run `docker compose up -d`.
    - Not with Level 4, nor with the plain-HTTP addresses of Levels 1 and 2: they reach the port
      through the server's LAN or Tailscale address.

---

## 🔗 Related

- 📄 **[Checking Connection Security](connection_checks.md)** — Checklist, What the Indicator Shows, The Server's View, …
