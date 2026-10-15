# 🔐 Connection Security

The connection security indicator in LibreFolio's sidebar tells you whether what you type — your
password, your figures — travels encrypted between your device and your server. It shows one of
three levels, **secure**, **local network** or **not secure**, depending on the address you opened
and the network you are on.

For maximum security, give LibreFolio an HTTPS address and use it everywhere, even on your home
network.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="The connection security indicator at the bottom of the sidebar, open on Connection: local network: its reason, that anyone on the same network can read the traffic, and the How to connect securely link" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 The Three Levels

### 🟢 Connection: secure {: #connection-secure }

What you type is encrypted, or it never leaves the server.

<div class="lf-pros-cons" markdown>

| ✅ Pro | ⚠️ Con |
|:--|:--|
| Nobody along the way can read or change it, not even on a public Wi-Fi. | Nothing, as far as risk goes. |

</div>

!!! warning "📱 Tailscale over plain HTTP and the app"

    Through Tailscale with a plain `http://` address, such as `http://100.110.x.x:6040`, your
    browser will not [install LibreFolio as an app](pwa.md). That is why an HTTPS address is still
    better: as a risk the two are the same, since Tailscale encrypts the traffic too.

👉 **What to do:** nothing, keep using this address. For the app, switch to an
[HTTPS address](#https-address).

??? info "🔍 When a connection counts as secure"

    The details give one of three reasons:

    - **HTTPS**: any `https://` address. Your browser decides alone, whatever the server sees.
    - **On the server itself**: `localhost`, names ending in `.localhost`, and loopback addresses
      such as `127.0.0.1` and `::1`. Your browser decides alone: the traffic does not leave that
      computer.
    - **VPN (Tailscale)**: a plain `http://` address in Tailscale's ranges, `100.64.0.0/10` and
      `fd7a:115c:a1e0::/48`, or a name ending in `.ts.net`. Tailscale encrypts the traffic between
      your device and the server. If the server sees the request coming from the internet instead,
      the level is [local network](#connection-local-network), as unclear.

### 🏠 Connection: local network {: #connection-local-network }

You opened LibreFolio over plain `http://` inside your home or office network, for example at
`http://192.168.1.100:6040`, the address other devices use after a standard
[installation](installation.md).

<div class="lf-pros-cons" markdown>

| 🤷 You settle for | ⚠️ Con |
|:--|:--|
| A connection that needs no setup, and whose traffic stays inside your network. | Nothing is encrypted: anyone on the same network, such as a guest on your Wi-Fi, could read the traffic, password included. |

</div>

👉 **What to do:** use the [HTTPS address](#https-address) at home too.

The same level appears with a reason starting with *Unclear* when LibreFolio cannot tell where you
really are: the advice does not change.

??? info "🔍 When a connection counts as local network"

    **A local address over plain `http://`**: an address in `10.x`, `172.16.x` to `172.31.x`,
    `192.168.x` or `169.254.x`, an IPv6 link-local or unique local address, or a name ending in
    `.local`, `.lan`, `.home.arpa` or `.internal`, or with no dot at all, such as
    `http://nas:6040`. A short Tailscale MagicDNS name, such as `http://my-server:6040`, has no dot
    either, so it counts here: the Tailscale IP or the full name ending in `.ts.net` counts as
    [secure](#connection-secure).

    **Unclear**: your browser judges the address you opened, and the server then reports where it
    sees the request coming from, only the kind of address and never your IP address. The server
    can confirm the browser's verdict or make it uncertain, but never make a connection count as
    secure; until it answers, the browser's verdict stands. When the two disagree, the level is
    local network and the reason starts with *Unclear*:

    - a public-looking address that the server sees coming from your local network, from Tailscale
      or from the server itself, for example through split DNS or a local proxy;
    - a local or Tailscale address that the server sees coming from the internet.

    The traffic is not encrypted, and LibreFolio cannot tell where you really are.

### 🔴 Connection: not secure {: #connection-not-secure }

You reached LibreFolio over plain `http://` from the internet, for example through a port opened on
your router. On a phone, a red dot on the menu button warns you even while the sidebar is closed.

<div class="lf-pros-cons" markdown>

| ✅ Pro | ⚠️ Con |
|:--|:--|
| None. | Passwords and data travel in clear text over networks you do not control: anyone along the way could read them, or even change them. |

</div>

👉 **What to do:** avoid this address. If you run the server, give LibreFolio an
[HTTPS address](#https-address) and stop exposing plain HTTP. Then change your password:
**Settings** → [**Profile**](settings/profile.md) → **Change Password**. This also signs out every other device
signed in to your account.

??? info "🔍 When a connection counts as not secure"

    **A public address over plain `http://`**: an address or name that is not local, not Tailscale
    and not the server itself, such as a public IP or a domain name like
    `http://myhome.duckdns.org:6040`. The level holds when the server also sees the request coming
    from the internet, or cannot tell. If it sees the request coming from your local network, from
    Tailscale or from the server itself, the level is [local network](#connection-local-network),
    as unclear.

---

## 🔒 How to Connect Securely {: #https-address }

Give LibreFolio an HTTPS address, then use only that one. Whoever runs the server sets it up, in
one of two ways:

- **Tailscale**, with no port opened on your router: Tailscale Serve gives an HTTPS address to the
  devices of your tailnet, and Funnel a public one that needs no Tailscale on your devices. See
  [Exposing Securely](../admin/service_exposure.md).
- **A reverse proxy** with a TLS certificate, such as Caddy, Traefik or Nginx: see
  [Advanced Docker](../admin/docker_advanced.md).

Then follow a few good habits:

- use the `https://` address on every device, at home too;
- bookmark it, and update the old bookmarks and home-screen shortcuts that still point to
  `http://`;
- if you do not run the server, ask whoever runs it for the address;
- check the indicator: it should show **Connection: secure**.

If you run the server, [Checking Connection Security](../admin/connection_checks.md) shows how to
verify the result.

---

## 🧭 What the Indicator Does Not Do

The indicator describes the connection you are using right now, and gives advice. Three things are
beyond it.

**It blocks nothing.** It is advice, not a check. And since it describes the connection of the
device you are on, the same LibreFolio can show **Connection: secure** on your laptop and
**Connection: not secure** on your phone.

**It does not check certificates.** A self-signed certificate that you accepted in the browser
shows **Connection: secure**. The traffic is encrypted, but nobody vouches that the server is
really yours.

**It cannot always see where you are.** When LibreFolio runs in Docker Desktop and is exposed
directly, or sits behind a proxy that does not pass your address in `X-Forwarded-For`, the server
sees every visitor as local. Plain HTTP from the internet then shows
**Connection: local network**, as unclear, instead of **Connection: not secure**. Docker Engine on
Linux keeps your address.

Whatever the indicator shows, the advice stays the same: use the HTTPS address.

---

## 🔗 Related

- 🌐 **[Exposing Securely](../admin/service_exposure.md)** — Tailscale, from a private VPN to a
  public HTTPS address
- 🔍 **[Checking Connection Security](../admin/connection_checks.md)** — For administrators: the
  HTTPS address, the session cookie and the reverse proxy
- 🐳 **[Advanced Docker](../admin/docker_advanced.md)** — Compose file, environment variables,
  reverse proxy
- 📝 **[Configuration](../admin/configuration.md)** — Every option of the `.env` file
- 📦 **[Installation with Docker](installation.md)** — Local and remote access after installing
- 📱 **[Install as App (PWA)](pwa.md)** — Needs an HTTPS address
