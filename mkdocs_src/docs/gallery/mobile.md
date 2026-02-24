# 📱 Mobile Gallery

Experience LibreFolio's responsive mobile interface. Screenshots automatically adapt to your selected theme and language.

!!! tip "Theme & Language"
Use the **theme toggle** in the header (☀️/🌙) to switch between light and dark mode.
Use the **language selector** (🇬🇧) in the header to view screenshots in different languages.

!!! info "Mobile Optimized"
LibreFolio is fully responsive and works great on smartphones and tablets. The interface automatically adapts to smaller screens with a collapsible navigation menu.

---

## 🔐 Authentication

### Login Page

Clean and accessible login on mobile devices.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page">
</div>

### Registration

Easy account creation with password strength feedback.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Register Modal">
</div>

---

## 📊 Dashboard

### Main Dashboard

Your portfolio overview optimized for mobile viewing.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard">
</div>

### Navigation Menu

Full navigation accessible via the hamburger menu.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="dashboard" data-name="menu-open" alt="Mobile Menu">
</div>

---

## ⚙️ Settings

### User Preferences

All settings accessible on mobile with the same functionality.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="User Preferences">
</div>

### Global Settings (Admin)

System-wide configuration on mobile.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings">
</div>

### About

System information at your fingertips.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

### Password Change

Secure password changes on the go.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Password Change Modal">
</div>

### Profile

Your profile, avatar, and account settings on mobile.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="settings" data-name="profile" alt="Profile Tab">
</div>

---

## 📁 Files

### Static Resources

Manage your uploaded files on mobile.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab">
</div>

### Static Resources - Grid View

Visual file browsing with image previews on mobile.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View">
</div>

### Broker Reports (BRIM)

Import and manage broker reports.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="BRIM Tab">
</div>

---

## 🏦 Brokers

### Broker List

Your brokerage accounts with touch-friendly cards.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List">
</div>

### Broker Detail

Detailed broker view optimized for mobile.

<div class="screenshot-container mobile">
    <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Detail">
</div>

### Import Modal

Import transactions directly from your phone.

<div class="screenshot-container mobile">
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
