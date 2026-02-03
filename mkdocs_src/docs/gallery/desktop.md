# 🖥️ Desktop Gallery

Experience LibreFolio's full desktop interface. Screenshots automatically adapt to your selected theme and language.

!!! tip "Theme & Language"
    Use the **theme toggle** in the header (☀️/🌙) to switch between light and dark mode.
    Use the **language selector** (🇬🇧) in the header to view screenshots in different languages.

---

## 🔐 Authentication

### Login Page

The welcoming login page with our signature animated background.

<div class="screenshot-container">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page">
</div>

### Registration - Empty Form

New users can easily create an account.

<div class="screenshot-container">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Register Modal">
</div>

### Registration - With Password Strength

Real-time password strength feedback helps users create secure passwords.

<div class="screenshot-container">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Register with Password Strength">
</div>

---

## 📊 Dashboard

### Main Dashboard

Your portfolio at a glance with quick stats and navigation.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard">
</div>

---

## ⚙️ Settings

### User Preferences

Customize language, currency, and theme to your liking.

<div class="screenshot-container">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="User Preferences">
</div>

### Global Settings (Admin)

Administrators can configure system-wide settings.

<div class="screenshot-container">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings">
</div>

### About

System information and version details.

<div class="screenshot-container">
    <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

### Password Change

Securely change your password with strength validation.

<div class="screenshot-container">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Password Change Modal">
</div>

---

## 📁 Files

### Static Resources

Upload and manage images, logos, and other static files.

<div class="screenshot-container">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab">
</div>

### Broker Reports (BRIM)

Import and manage broker transaction reports.

<div class="screenshot-container">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="BRIM Tab">
</div>

---

## 🏦 Brokers

### Broker List

All your brokerage accounts in one view.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List">
</div>

### Broker Detail

Detailed view of a single broker with cash balances and transactions.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Detail">
</div>

### Import Modal

Easily import transactions from your broker's export files.

<div class="screenshot-container">
    <img class="gallery-img" data-category="brokers" data-name="import-modal" alt="Import Modal">
</div>

---

<script>
document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('.gallery-img');
    
    // Get language from localStorage (shared with header selector)
    function getCurrentLang() {
        return localStorage.getItem('gallery-lang') || 'en';
    }
    
    // Detect MkDocs Material theme
    function getMkDocsTheme() {
        const scheme = document.body.getAttribute('data-md-color-scheme');
        return scheme === 'slate' ? 'dark' : 'light';
    }
    
    function updateImages() {
        const lang = getCurrentLang();
        const theme = getMkDocsTheme();
        
        images.forEach(img => {
            const category = img.dataset.category;
            const name = img.dataset.name;
            if (category && name) {
                img.src = `${lang}/${theme}/${category}/${name}.png`;
            }
        });
    }
    
    // Initial update
    updateImages();
    
    // Listen for language changes from header selector
    window.addEventListener('gallery-lang-change', updateImages);
    
    // Watch for MkDocs theme changes
    const observer = new MutationObserver(updateImages);
    observer.observe(document.body, { attributes: true, attributeFilter: ['data-md-color-scheme'] });
});
</script>

<style>
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
