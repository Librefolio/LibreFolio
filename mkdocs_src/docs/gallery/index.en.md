# 🖼️ LibreFolio Gallery

Welcome to the LibreFolio visual gallery! Here you can explore all the features of our portfolio management platform through screenshots.

## 👁️ Choose Your View

<div class="gallery-cards">
    <a href="desktop/" class="gallery-card">
        <span class="gallery-icon">🖥️</span>
        <h3>Desktop View</h3>
        <p>Full-featured experience with all controls visible</p>
    </a>
    <a href="mobile/" class="gallery-card">
        <span class="gallery-icon">📱</span>
        <h3>Mobile View</h3>
        <p>Responsive design optimized for touch screens</p>
    </a>
</div>

## ✨ Features Highlighted

!!! tip "What You'll See"

    - **Authentication**: Secure login with password strength meter
    - **Dashboard**: Quick overview of your portfolio
    - **Brokers**: Manage multiple brokerage accounts
    - **Files**: Upload and manage broker reports with grid & table views
    - **Settings**: Customize your experience in 4 languages
    - **Profile**: Avatar management and account settings
    - **Media & Upload**: Image crop/edit, asset picker, file renaming
    - **FX Rates**: Currency pairs, charts, sync, data editor, CSV import
    - **Assets**: Track stocks, ETFs, bonds, crypto with charts, signals, measures & classification

## 🌍 Language Support

LibreFolio is available in:

| Language | Flag | Status     |
|----------|------|------------|
| English  | 🇬🇧 | ✅ Complete |
| Italiano | 🇮🇹 | ✅ Complete |
| Français | 🇫🇷 | ✅ Complete |
| Español  | 🇪🇸 | ✅ Complete |

---

<style>

.gallery-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
}

.gallery-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem;
    background: var(--md-code-bg-color);
    border-radius: 12px;
    text-decoration: none !important;
    color: inherit !important;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 2px solid transparent;
}

.gallery-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    border-color: var(--md-primary-fg-color);
}

.gallery-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.gallery-card h3 {
    margin: 0.5rem 0;
    color: var(--md-primary-fg-color);
}

.gallery-card p {
    margin: 0;
    text-align: center;
    opacity: 0.8;
}
</style>
