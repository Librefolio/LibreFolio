# 🔐 Connection Security

The connection security indicator in LibreFolio's sidebar tells you whether what you type — your
password, your figures — travels encrypted between your device and your server. It shows one of
three levels, depending on the address you opened and the network you are on. Click its row to open
or close its details: the reason for the level and the **How to connect securely** link, which
opens this page.
With the sidebar collapsed, the shield shows the level when you hover it, and a click opens the
sidebar with the details.

For maximum security, give LibreFolio an HTTPS address and use it everywhere, even on your home
network.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="The connection security indicator at the bottom of the sidebar, open on Connection: local network: its reason, that anyone on the same network can read the traffic, and the How to connect securely link" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 The Three Levels

### 🟢 Connection: secure {: #connection-secure }

Green: what you type is encrypted, or it never leaves the server. The details give the reason:

- HTTPS: the connection is encrypted, and your browser considers it secure.
- On the server itself (`localhost`): the traffic does not leave that computer.
- VPN (Tailscale): Tailscale encrypts the traffic between your device and the server, even though
  the address starts with `http://`, for example `http://100.110.x.x:6040`.

With the VPN reason the address is still plain `http://`, so your browser will not
[install LibreFolio as an app](pwa.md) from it: [step 1](#https-address) adds HTTPS.

### 🏠 Connection: local network {: #connection-local-network }

Light green: you opened LibreFolio over plain `http://` inside your home or office network, for
example `http://192.168.1.100:6040`, the address other devices use after a standard
[installation](installation.md). The traffic is not encrypted: anyone on the same network, such as
a guest on your Wi-Fi, could read it, password included. For the best security, use the HTTPS
address at home too.

**Connection: local network** also appears, with a reason starting with *Unclear* in the details, when
the address you opened and the source the server sees disagree: a public-looking address that the
server sees coming from your local network (split DNS, or a local proxy), or a local or Tailscale
address that the server sees coming from the internet. The traffic is not encrypted, and
LibreFolio cannot tell where you really are: use the HTTPS address.

### 🔴 Connection: not secure {: #connection-not-secure }

Red: you reached LibreFolio over plain `http://` from the internet, for example through a port
opened on your router. Passwords and data travel in clear text over networks you do not control:
anyone along the way could read them, or even change them. On a phone, a red dot on the menu button
warns you even while the sidebar is closed.

Avoid this address. If you run the server, give LibreFolio an HTTPS address
([step 1](#https-address)) and stop exposing plain HTTP. Then change your password:
**Settings** → [**Profile**](settings/profile.md) → **Change Password**.

??? info "🔍 How the level is chosen"

    Your browser sorts the address you typed into one of four kinds:

    - this computer: `localhost` and loopback addresses;
    - Tailscale: `100.64.0.0/10`, `fd7a:115c:a1e0::/48` and names ending in `.ts.net`;
    - local network: `10.x`, `172.16.x` to `172.31.x`, `192.168.x` and `169.254.x` addresses, IPv6
      link-local and unique local addresses, and names ending in `.local`, `.lan`, `.home.arpa` or
      `.internal`, or with no dot at all;
    - internet: everything else.

    HTTPS is always secure. Plain HTTP counts as secure to `localhost`, and to a Tailscale address
    unless the server sees the request coming from the internet.

    The server sorts the address each request comes from into the same kinds and reports only the
    kind, never your IP address. It can confirm the browser's verdict or make it uncertain, but
    never make a connection count as secure. Until it answers, the browser's verdict stands.

---

## 🔒 How to Connect Securely

### 🌐 1. Give LibreFolio an HTTPS address {: #https-address }

This is a job for whoever runs the server: if that is not you, ask them for the HTTPS address. Two
ways:

- Tailscale: follow [Exposing Securely](../admin/service_exposure.md). With its Level 1 (private
  VPN) in place, run `tailscale serve --bg 6040` on the server (or your own `PORT`), then open
  `https://<server-name>.your-tailnet.ts.net`. For a public HTTPS address that needs no Tailscale
  on your devices, use Funnel (Levels 3 and 4).
- A reverse proxy with a TLS certificate, such as Caddy, Traefik or Nginx: see
  [Advanced Docker](../admin/docker_advanced.md).

Tailscale, Caddy and Traefik tell LibreFolio about HTTPS on their own; Nginx needs two lines: see
[Behind a reverse proxy](#reverse-proxy).

### 🔖 2. Use the HTTPS address everywhere

Use it on every device, at home too:

- Bookmark `https://…`, not `http://192.168.x.x:6040`.
- Update old bookmarks and home-screen shortcuts that still point to `http://`.
- Open LibreFolio from the new address: the indicator shows **Connection: secure**.

---

## 🧰 Behind a Reverse Proxy {: #reverse-proxy }

*For administrators.* A reverse proxy receives the HTTPS connection and passes it to LibreFolio
over plain HTTP. What matters there is the session cookie that keeps you signed in: with
`SESSION_COOKIE_SECURE=auto`, the default, LibreFolio marks it `Secure` (sent over HTTPS only) when
the request is HTTPS, either directly or because the proxy sends `X-Forwarded-Proto: https`.

Tailscale Serve and Funnel, Caddy and Traefik send that header on their own. Caddy and Traefik also
pass your address in `X-Forwarded-For`, which lets the indicator see where you connect from. Nginx
needs both lines in the `location` block that passes requests to LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

If your browser uses HTTPS but the session cookie is not marked `Secure`, because the proxy does not
send `X-Forwarded-Proto` or because `SESSION_COOKIE_SECURE` is `never`, administrators see one more
line in the indicator's details. The level stays **Connection: secure**, because the connection is
encrypted; only the cookie lacks `Secure`:

> Your browser uses HTTPS, but the session cookie is not marked Secure. Make the reverse proxy send
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), or set
> SESSION_COOKIE_SECURE back to auto if it is never.

??? tip "⚙️ Set `SESSION_COOKIE_SECURE` instead"

    Sending the header is the better fix. If you only ever reach LibreFolio over HTTPS, you can
    instead add this line to `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Then restart LibreFolio: with Docker, run `docker compose up -d` (a plain
    `docker compose restart` keeps the old environment); on a host installation, restart
    `./dev.py server`, which reads `.env` too.

    The option takes `auto` (the default), `always` or `never`; case and spaces do not matter, and
    any other value stops LibreFolio at startup. Use `never` only for the rare proxy that claims
    HTTPS while the browser is on plain HTTP. See [Configuration](../admin/configuration.md) for
    every option.

---

## 🧭 What the Indicator Does Not Do

- It blocks nothing: it is advice, not a check.
- It describes the connection you are using right now: the same LibreFolio can show
  **Connection: secure** on your laptop and **Connection: not secure** on your phone.
- It does not check certificates: a self-signed certificate that you accepted in the browser shows
  **Connection: secure**. The traffic is encrypted, but nobody vouches that the server is really
  yours.
- It cannot always see where you are. With Docker Desktop exposed directly, or behind a proxy that
  does not pass your address in `X-Forwarded-For`, the server sees every visitor as local: plain
  HTTP from the internet then shows **Connection: local network**, as unclear, instead of
  **Connection: not secure**. Docker Engine on Linux keeps your address. The advice does not
  change: use the HTTPS address.

---

## 🔗 Related

- 🌐 **[Exposing Securely](../admin/service_exposure.md)** — Tailscale, from a private VPN to a
  public HTTPS address
- 🐳 **[Advanced Docker](../admin/docker_advanced.md)** — Compose file, environment variables,
  reverse proxy
- 📝 **[Configuration](../admin/configuration.md)** — Every option of the `.env` file
- 📦 **[Installation with Docker](installation.md)** — Local and remote access after installing
- 📱 **[Install as App (PWA)](pwa.md)** — Needs an HTTPS address
