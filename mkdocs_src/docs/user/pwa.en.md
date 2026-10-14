# 📱 Install as App (PWA)

LibreFolio can be installed as a **Progressive Web App (PWA)** on your phone, tablet or computer:
it opens like a native app, from its own icon, without an app store.

---

## ✅ What You Get

- 🖥️ **Full screen** — no address bar and no browser toolbar.
- 🏠 **Home-screen icon** — launch LibreFolio like any other app.
- 👆 **No accidental gestures** — swipe-back and double-tap zoom are turned off.
- 🔐 **Stay signed in** between launches, until your session expires.

!!! note "Online Only"

    The app needs a connection to your LibreFolio server: there is no offline mode — your data
    lives on your server. If you open the app while the server cannot be reached, a
    **Server Unreachable** page appears and tries again by itself.

---

## 📲 How to Install

### 🤖 Android (Chrome / Edge)

1. Open LibreFolio in Chrome or Edge.
2. Open the **Help & Support** menu (❓, top right) and tap **Install App**.
3. Confirm with **Install**: LibreFolio appears on your home screen.

No install dialog? Use the browser's **⋮** menu → **Install app** or **Add to Home screen**.

### 🍎 iOS (Safari)

1. Open LibreFolio in **Safari**.
2. Tap the **Share** button (square with arrow).
3. Scroll down, tap **Add to Home Screen**, then **Add**.

iOS has no install dialog: on an iPhone or iPad, **Install App** in the Help & Support menu shows
these instructions instead.

### 💻 Desktop (Chrome / Edge)

1. Open LibreFolio in Chrome or Edge.
2. Click **Install App** in the **Help & Support** menu, or the install icon (⊕) in the address bar.
3. LibreFolio opens in its own window.

---

## 🌐 HTTP vs HTTPS

| Address | Install as an app | Install dialog from **Install App** |
|---|---|---|
| `https://…` (Tailscale, reverse proxy) | ✅ | ✅ |
| `http://localhost` | ✅ | ✅ |
| `http://192.168.x.x` (LAN) | ❌ HTTPS required | ❌ a hint only |

!!! warning "HTTPS Connection Requirement for PWA"

    Browsers install an app only from a secure **HTTPS** address — `localhost` and `127.0.0.1` are
    the only exceptions. Over plain HTTP on your network (for example `http://192.168.1.100:6040`)
    LibreFolio still works in the browser, but it cannot be installed.

    Any HTTPS setup will do. The simplest, free option is our
    **[Tailscale Exposure Guide](../admin/service_exposure.md)**: a secure HTTPS address without
    SSL certificates to manage or router ports to open.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| **Install App** is not in the menu | You are already in the installed app: the item is hidden there |
| **Install App** shows a hint instead of installing | The browser offered no install: check that you use HTTPS (or `localhost`), or that the app is not installed already, then follow the hint |
| iOS: no **Add to Home Screen** | Open the page in **Safari** and look in its **Share** menu |
| App doesn't update | Close and reopen the app — it always loads the latest version from your server |
| Signed out after an update | Log in again — a server restart can end every session |

---

## 🔗 Related

- 🌐 **[Tailscale Exposure Guide](../admin/service_exposure.md)** — A free HTTPS address for your instance
- 🛠️ **[PWA & Mobile Optimizations](../developer/frontend/pwa.md)** — How the app side is built (for developers)
