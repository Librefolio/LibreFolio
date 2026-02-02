# 📱 Mobile Gallery

Experience LibreFolio's responsive mobile interface. Use the language selector below to view screenshots in your preferred language.

<div class="language-selector" id="lang-selector">
    <span class="lang-label">Language:</span>
    <button class="lang-btn active" data-lang="en">🇬🇧 English</button>
    <button class="lang-btn" data-lang="it">🇮🇹 Italiano</button>
    <button class="lang-btn" data-lang="fr">🇫🇷 Français</button>
    <button class="lang-btn" data-lang="es">🇪🇸 Español</button>
</div>

!!! info "Mobile Optimized"
    LibreFolio is fully responsive and works great on smartphones and tablets. The interface automatically adapts to smaller screens with a collapsible navigation menu.

---

## 🔐 Authentication

### Login Page

Clean and accessible login on mobile devices.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-en="en/auth/01-login.png" data-it="it/auth/01-login.png" data-fr="fr/auth/01-login.png" data-es="es/auth/01-login.png" alt="Login Page" src="en/auth/01-login.png">
</div>

### Registration

Easy account creation with password strength feedback.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-en="en/auth/03-register-filled.png" data-it="it/auth/03-register-filled.png" data-fr="fr/auth/03-register-filled.png" data-es="es/auth/03-register-filled.png" alt="Register Modal" src="en/auth/03-register-filled.png">
</div>

---

## 📊 Dashboard

### Main Dashboard

Your portfolio overview optimized for mobile viewing.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-en="en/dashboard/main.png" data-it="it/dashboard/main.png" data-fr="fr/dashboard/main.png" data-es="es/dashboard/main.png" alt="Dashboard" src="en/dashboard/main.png">
</div>

### Navigation Menu

Full navigation accessible via the hamburger menu.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-en="en/dashboard/menu-open.png" data-it="it/dashboard/menu-open.png" data-fr="fr/dashboard/menu-open.png" data-es="es/dashboard/menu-open.png" alt="Mobile Menu" src="en/dashboard/menu-open.png">
</div>

---

## ⚙️ Settings

### User Preferences

All settings accessible on mobile with the same functionality.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-en="en/settings/user-preferences.png" data-it="it/settings/user-preferences.png" data-fr="fr/settings/user-preferences.png" data-es="es/settings/user-preferences.png" alt="User Preferences" src="en/settings/user-preferences.png">
</div>

---

## 🏦 Brokers

### Broker List

Your brokerage accounts with touch-friendly cards.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-en="en/brokers/list.png" data-it="it/brokers/list.png" data-fr="fr/brokers/list.png" data-es="es/brokers/list.png" alt="Broker List" src="en/brokers/list.png">
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
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    padding: 1rem;
    background: var(--md-code-bg-color);
    border-radius: 8px;
    margin-bottom: 1.5rem;
}

.lang-label {
    font-weight: bold;
    margin-right: 0.5rem;
}

.lang-btn {
    padding: 0.5rem 1rem;
    border: 2px solid var(--md-primary-fg-color);
    background: transparent;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.9rem;
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

.screenshot-container.mobile {
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
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
