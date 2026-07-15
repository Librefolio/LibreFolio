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

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
  <thead>
    <tr style="background-color: #f3f4f6;">
      <th style="width: 45%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Setup</th>
      <th style="width: 25%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">PWA Install</th>
      <th style="width: 30%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Auto-prompt</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, reverse proxy)</td>
      <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Full support</td>
      <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Chrome shows the banner</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>http://localhost</code></td>
      <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Works</td>
      <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Works</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap; background-color: rgba(244, 67, 54, 0.04);"><code>http://192.168.x.x</code> (LAN)</td>
      <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Not available (HTTPS required)</td>
      <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ No auto-prompt</td>
    </tr>
  </tbody>
</table>

!!! warning "HTTPS Connection Requirement for PWA"

    To install LibreFolio as a PWA, **modern browsers strictly require a secure HTTPS connection** (except when accessing it through `localhost` or `127.0.0.1` for local development).

    If you open LibreFolio over plain HTTP on your local network (for example, `http://192.168.1.100:6040`), PWA installation will not be available and the app cannot run in standalone mode.

    You can choose any method you prefer to enable HTTPS on your instance, but we strongly recommend our simple, free guide: **[Tailscale Exposure Guide](../admin/service_exposure.md)**. It gives you a secure HTTPS URL without configuring SSL certificates or opening router ports.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Install button not showing | You may already have it installed, or you're on HTTP LAN |
| iOS: no install option | Must use **Safari** — Chrome/Firefox on iOS don't support PWA |
| App doesn't update | Close and reopen the app — it always fetches the latest version |
| Lost session after update | Re-login — this is expected after server restarts |
