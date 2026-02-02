# 🖥️ Desktop Gallery

Experience LibreFolio's full desktop interface. Use the language selector below to view screenshots in your preferred language.

<div class="language-selector" id="lang-selector">
    <span class="lang-label">Language:</span>
    <div class="lang-grid">
        <button class="lang-btn active" data-lang="en">🇬🇧 English</button>
        <button class="lang-btn" data-lang="it">🇮🇹 Italiano</button>
        <button class="lang-btn" data-lang="fr">🇫🇷 Français</button>
        <button class="lang-btn" data-lang="es">🇪🇸 Español</button>
    </div>
</div>

---

## 🔐 Authentication

### Login Page

The welcoming login page with our signature animated background.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/auth/01-login.png" data-it="it/auth/01-login.png" data-fr="fr/auth/01-login.png" data-es="es/auth/01-login.png" alt="Login Page" src="en/auth/01-login.png">
</div>

### Registration - Empty Form

New users can easily create an account.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/auth/02-register-empty.png" data-it="it/auth/02-register-empty.png" data-fr="fr/auth/02-register-empty.png" data-es="es/auth/02-register-empty.png" alt="Register Modal" src="en/auth/02-register-empty.png">
</div>

### Registration - With Password Strength

Real-time password strength feedback helps users create secure passwords.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/auth/03-register-filled.png" data-it="it/auth/03-register-filled.png" data-fr="fr/auth/03-register-filled.png" data-es="es/auth/03-register-filled.png" alt="Register with Password Strength" src="en/auth/03-register-filled.png">
</div>

---

## 📊 Dashboard

### Main Dashboard

Your portfolio at a glance with quick stats and navigation.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/dashboard/main.png" data-it="it/dashboard/main.png" data-fr="fr/dashboard/main.png" data-es="es/dashboard/main.png" alt="Dashboard" src="en/dashboard/main.png">
</div>

---

## ⚙️ Settings

### User Preferences

Customize language, currency, and theme to your liking.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/settings/user-preferences.png" data-it="it/settings/user-preferences.png" data-fr="fr/settings/user-preferences.png" data-es="es/settings/user-preferences.png" alt="User Preferences" src="en/settings/user-preferences.png">
</div>

### Global Settings (Admin)

Administrators can configure system-wide settings.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/settings/global-settings.png" data-it="it/settings/global-settings.png" data-fr="fr/settings/global-settings.png" data-es="es/settings/global-settings.png" alt="Global Settings" src="en/settings/global-settings.png">
</div>

---

## 📁 Files

### Static Resources

Upload and manage images, logos, and other static files.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/files/static-tab.png" data-it="it/files/static-tab.png" data-fr="fr/files/static-tab.png" data-es="es/files/static-tab.png" alt="Static Files Tab" src="en/files/static-tab.png">
</div>

### Broker Reports (BRIM)

Import and manage broker transaction reports.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/files/brim-tab.png" data-it="it/files/brim-tab.png" data-fr="fr/files/brim-tab.png" data-es="es/files/brim-tab.png" alt="BRIM Tab" src="en/files/brim-tab.png">
</div>

---

## 🏦 Brokers

### Broker List

All your brokerage accounts in one view.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/brokers/list.png" data-it="it/brokers/list.png" data-fr="fr/brokers/list.png" data-es="es/brokers/list.png" alt="Broker List" src="en/brokers/list.png">
</div>

### Broker Detail

Detailed view of a single broker with cash balances and transactions.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/brokers/detail.png" data-it="it/brokers/detail.png" data-fr="fr/brokers/detail.png" data-es="es/brokers/detail.png" alt="Broker Detail" src="en/brokers/detail.png">
</div>

### Import Modal

Easily import transactions from your broker's export files.

<div class="screenshot-container">
    <img class="gallery-img" data-en="en/brokers/import-modal.png" data-it="it/brokers/import-modal.png" data-fr="fr/brokers/import-modal.png" data-es="es/brokers/import-modal.png" alt="Import Modal" src="en/brokers/import-modal.png">
</div>

---

<script>
document.addEventListener('DOMContentLoaded', function() {
    const langBtns = document.querySelectorAll('.lang-btn');
    const images = document.querySelectorAll('.gallery-img');
    
    // Get stored language or default to 'en'
    let currentLang = localStorage.getItem('gallery-lang') || 'en';
    
    // Apply initial language
    updateLanguage(currentLang);
    
    langBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            currentLang = this.dataset.lang;
            localStorage.setItem('gallery-lang', currentLang);
            updateLanguage(currentLang);
        });
    });
    
    function updateLanguage(lang) {
        // Update button states
        langBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });
        
        // Update images
        images.forEach(img => {
            const newSrc = img.dataset[lang];
            if (newSrc) {
                img.src = newSrc;
            }
        });
    }
});
</script>

<style>
.language-selector {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--md-code-bg-color);
    border-radius: 8px;
    margin-bottom: 1.5rem;
}

.lang-label {
    font-weight: bold;
    font-size: 1.1rem;
}

.lang-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
}

@media (min-width: 600px) {
    .lang-grid {
        grid-template-columns: repeat(4, 1fr);
    }
}

.lang-btn {
    padding: 0.6rem 1rem;
    border: 2px solid var(--md-primary-fg-color);
    background: transparent;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.95rem;
    text-align: center;
}

.lang-btn:hover {
    background: var(--md-primary-fg-color);
    color: white;
}

.lang-btn.active {
    background: var(--md-primary-fg-color);
    color: white;
}

.screenshot-container {
    margin: 1rem 0 2rem 0;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

.gallery-img {
    width: 100%;
    display: block;
    transition: opacity 0.3s;
}

.gallery-img:hover {
    opacity: 0.95;
}
</style>
