# 📱 Install as App (PWA)

LibreFolio can be installed as a **Progressive Web App (PWA)** on your device. This gives you an app-like experience: full-screen mode, no browser address bar, and a home screen icon — without downloading from an app store.

---

## ✅ What You Get

| Feature | Description |
|---------|-------------|
| **Full-screen mode** | No address bar or browser UI clutter |
| **Home screen icon** | Launch LibreFolio like a native app |
| **No gestures interference** | Swipe-back and double-tap zoom disabled |
| **Persistent session** | Stays logged in between launches |

!!! note "Online Only"

    LibreFolio PWA requires an active network connection. There is no offline mode — your data lives on your server.

---

## 📲 How to Install

### Android (Chrome / Edge)

1. Open LibreFolio in Chrome or Edge
2. Look for the **"Install App"** button in the **Help & Support** menu (top-right ❓ icon)
3. Tap **Install** when prompted
4. LibreFolio appears on your home screen

!!! tip "Alternative method"

    If the Install button doesn't appear, tap the browser's **⋮ menu → "Add to Home screen"** or **"Install app"**.

### iOS (Safari)

1. Open LibreFolio in **Safari** (required — other browsers don't support PWA on iOS)
2. Tap the **Share** button (square with arrow)
3. Scroll down and tap **"Add to Home Screen"**
4. Tap **Add**

!!! warning "iOS Limitation"

    The automatic install prompt is not available on iOS. Use the Share menu as described above. The Help menu will show instructions if you're on an iOS device.

### Desktop (Chrome / Edge)

1. Open LibreFolio in Chrome or Edge
2. Click the **"Install App"** button in the Help & Support menu
3. Or click the install icon (⊕) in the browser's address bar
4. LibreFolio opens in its own window

---

## 🌐 HTTP vs HTTPS

| Setup | PWA Install | Auto-prompt |
|-------|-------------|-------------|
| `https://` (Tailscale, reverse proxy) | ✅ Full support | ✅ Chrome shows banner |
| `http://localhost` | ✅ Works | ✅ Works |
| `http://192.168.x.x` (LAN) | ⚠️ Manual only | ❌ No auto-prompt |

!!! info "Self-hosted on LAN"

    If you access LibreFolio via HTTP on your local network (e.g., `http://192.168.1.100:8000`), the automatic install prompt won't appear. You can still install manually:

    - **Android**: Browser menu → "Add to Home screen"
    - **iOS**: Share → "Add to Home Screen"
    - **Desktop**: Not available on HTTP (use Tailscale for HTTPS)

    For full PWA support, expose your instance via [Tailscale](../../../admin/tailscale_exposure/) (free, easy HTTPS).

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Install button not showing | You may already have it installed, or you're on HTTP LAN |
| iOS: no install option | Must use **Safari** — Chrome/Firefox on iOS don't support PWA |
| App doesn't update | Close and reopen the app — it always fetches the latest version |
| Lost session after update | Re-login — this is expected after server restarts |
