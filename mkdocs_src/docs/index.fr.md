---
hide:
 - navigation
 - toc
description: Libre à comprendre, libre d'agir. LibreFolio regroupe tous vos investissements dans un tableau de bord privé, sécurisé et doté d'outils d'analyse puissants.
---

<!-- Animated Background -->
<div class="animated-bg">
 <div class="wave wave-1"></div>
 <div class="wave wave-2"></div>
 <div class="wave wave-3"></div>
 <svg class="chart-svg" preserveAspectRatio="none" viewBox="0 0 1200 200">
 <path class="chart-line line-1" d="M0,150 L100,130 L200,140 L300,100 L400,120 L500,80 L600,90 L700,60 L800,70 L900,40 L1000,55 L1100,30 L1200,45" />
 <path class="chart-line line-2" d="M0,120 L100,140 L200,100 L300,130 L400,90 L500,110 L600,70 L700,95 L800,55 L900,80 L1000,45 L1100,65 L1200,35" />
 <path class="chart-line line-3" d="M0,140 L100,110 L200,130 L300,85 L400,115 L500,75 L600,100 L700,50 L800,85 L900,60 L1000,75 L1100,40 L1200,55" />
 </svg>
</div>

<div class="premium-landing">

 <!-- Hero Section -->
 <div class="premium-hero">
 <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-bottom: 0; margin-top: 2rem;">
 <img id="home-logo-img" alt="Logo LibreFolio" class="premium-logo-img" />
 <script>
 (function() {
 var p = window.location.pathname.replace(/\/+$/, '');
 var base = p.replace(/\/(it|fr|es)$/, '');
 document.getElementById('home-logo-img').src = base + '/static/logo.png';
 })();
 </script>
 <h1>LibreFolio</h1>
 </div>
 
 <h2>Libre à comprendre,<span class="desktop-space"> </span><span class="mobile-break"></span>libre d'agir.</h2>
 
 <p class="hero-subtitle" style="margin-top: 2rem;">
 Regroupez tous vos investissements dans un tableau de bord sécurisé.<br><br>
 Vos données prennent vie grâce à des outils d'analyse conçus pour vous.<br>
 Une clarté totale, un contrôle absolu — car les bonnes décisions commencent par une bonne information.
 </p>

 <div class="premium-badges">
 <span class="badge badge-open-source">100% OPEN SOURCE</span>
 <span class="badge badge-expandable">HAUTEMENT EXTENSIBLE</span>
 <span class="badge badge-self-hosted">AUTO-HÉBERGÉ OU CLOUD</span>
 </div>
 </div>

 <!-- Video Section: Temporaneamente rimosso (Work in Progress) -->

 <!-- Quick Install -->
 <section class="lf-quick-install-section" id="get-started-quick">
 <div class="lf-quick-install-card">
 <h2 class="lf-quick-install-title">Prêt à essayer<br><img id="quick-install-logo" alt="Logo LibreFolio" style="height: 1em; width: auto; vertical-align: text-bottom; margin-right: 0.2em; border-radius: 4px;"><script>(function(){var p=window.location.pathname.replace(/\/+$/,"");var base=p.replace(/\/(it|fr|es)$/,"");document.getElementById("quick-install-logo").src=base+"/static/logo.png";})();</script>LibreFolio ?</h2>
 
  <div class="lf-quick-install-docker" style="display: block; padding: 2rem;">
  <span class="lf-quick-install-eyebrow">Recommandé</span>
  <div class="lf-quick-install-docker-body">
  <div class="lf-quick-install-heading">
  <span class="lf-quick-install-icon lf-quick-install-icon-primary">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
  </span>
  <h3>Installer avec Docker</h3>
  </div>
  <p>La méthode standard pour faire fonctionner LibreFolio de manière privée et fiable.</p>
  </div>
  <div style="display: flex; justify-content: flex-end; margin-top: 1.25rem;">
    <a href="user/installation/" class="lf-btn-primary">Lire le guide Docker &rarr;</a>
  </div>
  </div>
  
  <div class="lf-quick-install-dev" style="display: block; padding: 1.5rem 2rem;">
  <div class="lf-quick-install-dev-body">
  <div class="lf-quick-install-heading">
  <span class="lf-quick-install-icon lf-quick-install-icon-secondary">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
  </span>
  <h4>Exécuter sur l'Hôte ?</h4>
  </div>
  <p>Configurez l'environnement Python + Pipenv pour exécuter LibreFolio directement sur votre machine hôte.</p>
  </div>
  <div style="display: flex; justify-content: flex-end; margin-top: 1.25rem;">
    <a href="admin/host_installation/" class="lf-btn-secondary">Installation sur l'Hôte &rarr;</a>
  </div>
  </div>

  <div class="lf-quick-install-dev lf-quick-install-update" style="display: block; padding: 1.5rem 2rem;">
  <div class="lf-quick-install-dev-body">
  <div class="lf-quick-install-heading">
  <span class="lf-quick-install-icon lf-quick-install-icon-update">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
  </span>
  <h4>Rester informé ?</h4>
  </div>
  <p>Suivez nos progrès et recevez des notifications sur les nouveautés :</p>
  <ul style="margin: 0.5rem 0 0; padding-left: 1.25rem; font-size: clamp(0.8rem, 2.5vw, 0.9rem); color: var(--md-default-fg-color--light);">
    <li>Cliquez sur <strong>Watch</strong> en haut du dépôt GitHub.</li>
    <li>Sélectionnez <strong>Custom</strong> dans le menu de notifications.</li>
    <li>Cochez <strong>Releases</strong> et cliquez sur <strong>Apply</strong>.</li>
  </ul>
  </div>
  <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.25rem; align-items: center; flex-wrap: wrap;">
    <a href="https://github.com/Librefolio/LibreFolio/subscription" target="_blank" rel="noopener noreferrer" class="lf-btn-secondary" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem;">
      <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" style="vertical-align: text-bottom;"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.35 3.12.88.01.64.01 1.11.01 1.23 0 .21-.15.46-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8z"/></svg>
      <span>Watch</span>
      <span class="lf-github-counter lf-watch-count">-</span>
    </a>
    <a href="https://github.com/Librefolio/LibreFolio" target="_blank" rel="noopener noreferrer" class="lf-btn-secondary" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem;">
      <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" style="vertical-align: text-bottom;"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg>
      <span>Star</span>
      <span class="lf-github-counter lf-star-count">-</span>
    </a>
  </div>
  <style>
    .lf-quick-install-update {
      background: rgba(16, 185, 129, 0.03) !important;
      border: 1px solid rgba(16, 185, 129, 0.15) !important;
    }
    [data-md-color-scheme="slate"] .lf-quick-install-update {
      background: rgba(16, 185, 129, 0.08) !important;
      border: 1px solid rgba(16, 185, 129, 0.25) !important;
    }
    .lf-quick-install-update h4 {
      color: #047857 !important;
    }
    [data-md-color-scheme="slate"] .lf-quick-install-update h4 {
      color: #34d399 !important;
    }
    .lf-quick-install-update .lf-quick-install-icon-update {
      color: #10b981;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .lf-quick-install-update .lf-quick-install-icon-update svg {
      stroke: #10b981;
    }
    [data-md-color-scheme="slate"] .lf-quick-install-update .lf-quick-install-icon-update {
      color: #34d399;
      background: rgba(16, 185, 129, 0.12);
      border-color: rgba(16, 185, 129, 0.24);
    }
    [data-md-color-scheme="slate"] .lf-quick-install-update .lf-quick-install-icon-update svg {
      stroke: #34d399;
    }
    .lf-github-counter {
      background: rgba(0, 0, 0, 0.05);
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 500;
      margin-left: 0.25rem;
      color: var(--md-default-fg-color--light);
    }
    [data-md-color-scheme="slate"] .lf-github-counter {
      background: rgba(255, 255, 255, 0.1);
    }
  </style>
  <script>
  (function() {
    fetch('https://api.github.com/repos/Librefolio/LibreFolio')
      .then(response => response.json())
      .then(data => {
        if (data) {
          if (data.subscribers_count !== undefined) {
            document.querySelectorAll('.lf-watch-count').forEach(el => el.textContent = data.subscribers_count);
          }
          if (data.stargazers_count !== undefined) {
            document.querySelectorAll('.lf-star-count').forEach(el => el.textContent = data.stargazers_count);
          }
        }
      })
      .catch(err => {
        console.warn('Could not fetch GitHub counts', err);
        document.querySelectorAll('.lf-watch-count').forEach(el => el.textContent = '-');
        document.querySelectorAll('.lf-star-count').forEach(el => el.textContent = '-');
      });
  })();
  </script>
  </div>
  </div>
 </section>

 <!-- Deep Dive 1: Dashboard -->
 <div class="deep-dive">
 <div class="deep-dive-content">
 <h2>Tableau de bord</h2>
 <p>Une vue unifiée de l'ensemble de votre portefeuille. Suivez votre valeur nette, votre allocation et vos variations quotidiennes en un seul endroit sécurisé.</p>
 </div>
 <div class="deep-dive-image">
 <div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Tableau de bord principal"
 style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
 </div>
 </div>
 <div class="deep-dive-actions">
 <a href="user/dashboard/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Explorer le tableau de bord &rarr;</a>
 </div>
 </div>

 <!-- Deep Dive 2: Brokers -->
 <div class="deep-dive reverse">
 <div class="deep-dive-content">
 <h2>Intégration des courtiers</h2>
 <p>Importez des données <b>directement</b> depuis les fichiers de rapport de votre courtier à l'aide de plugins dédiés.</p>
 </div>
 <div class="deep-dive-image">
 <div class="screenshot-container">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Liste des courtiers"
 style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
 </div>
 </div>
 <div class="deep-dive-actions">
 <a href="user/transactions/import/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Voir tous les courtiers pris en charge &rarr;</a>
 </div>
 </div>

 <!-- Deep Dive 3: Transactions -->
 <div class="deep-dive">
 <div class="deep-dive-content">
 <h2>Transactions</h2>
 <p>Une transparence totale sur chaque mouvement. Filtrez, recherchez et modifiez les transactions sur tous vos portefeuilles sans effort.</p>
 </div>
 <div class="deep-dive-image">
 <div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="list" alt="Liste des transactions"
 style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
 </div>
 </div>
 <div class="deep-dive-actions">
 <a href="financial-theory/instruments/transaction-types/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Voir les types de transactions &rarr;</a>
 </div>
 </div>

 <!-- Deep Dive 4: Assets -->
 <div class="deep-dive reverse">
 <div class="deep-dive-content">
 <h2>Analyses approfondies</h2>
 <p>Découvrez les tendances du marché avec précision. Analyse technique puissante, signaux de trading et métriques de performance historique pour chaque actif de votre portefeuille.</p>
 </div>
 <div class="deep-dive-image">
 <div class="lf-screenshot-carousel" data-carousel="assets" data-carousel-interval="18000">
 <img class="gallery-img lf-screenshot-carousel-item is-active" 
 data-category="assets" data-name="detail-chart" alt="Graphique de base des détails de l'actif">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
 data-category="assets" data-name="detail-signals-macd" alt="Signaux MACD de l'actif">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
 data-category="assets" data-name="detail-signals-rsi" alt="Signaux RSI de l'actif">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
 data-category="assets" data-name="detail-signals-bollinger" alt="Bandes de Bollinger de l'actif">
 </div>
 </div>
 <div class="deep-dive-actions">
 <a href="financial-theory/technical-analysis/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Explorer l'analyse technique &rarr;</a>
 </div>
 </div>

 <!-- Deep Dive 5: Forex -->
 <div class="deep-dive">
 <div class="deep-dive-content">
 <h2>Actifs &amp; Forex</h2>
 <p>Suivez automatiquement la valorisation des actifs et les taux de change. Gérez des portefeuilles multi-devises avec des données en direct provenant directement de fournisseurs financiers et de banques centrales.</p>
 </div>
 <div class="deep-dive-image">
 <div class="lf-screenshot-carousel" data-carousel="fx-assets-table" data-carousel-interval="18000">
 <img class="gallery-img lf-screenshot-carousel-item is-active" 
 data-category="fx" data-name="list" data-title="Grille Forex" alt="Grille Forex">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
 data-category="fx" data-name="list-table" data-title="Tableau Forex" alt="Tableau Forex">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
 data-category="assets" data-name="list" data-title="Grille d'actifs" alt="Grille d'actifs">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
 data-category="assets" data-name="list-table" data-title="Tableau d'actifs" alt="Tableau d'actifs">
 </div>
 </div>
 <div class="deep-dive-actions">
 <a href="financial-theory/instruments/asset-types/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Types d'actifs &rarr;</a>
 <a href="user/fx/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Gestion Forex &rarr;</a>
 </div>
 </div>

 <!-- Deep Dive: Expandable by the Community -->
 <div class="deep-dive" style="margin-top: 4rem; display: block; text-align: center;">
 <h2 style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
 Un écosystème modulaire
 <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
 </h2>
 <p style="max-width: 680px; margin: 0 auto 3rem auto; color: var(--md-default-fg-color--light); font-size: 1.05rem; line-height: 1.6;">
 Libérez-vous des feuilles de calcul. LibreFolio est conçu pour se <b>connecter parfaitement</b> aux outils financiers que vous utilisez déjà, étendant ses capacités via un écosystème croissant de <b>plugins communautaires</b>.
 </p>
 
 <div class="plugin-radial-hub">
 <div class="hub-core">
 <img id="hub-core-img" alt="Cœur de LibreFolio" src="/LibreFolio/static/logo.png">
 <script>
 (function() {
 var p = window.location.pathname.replace(/\/+$/, '');
 var base = p.replace(/\/(it|fr|es)$/, '');
 document.getElementById('hub-core-img').src = base + '/static/logo.png';
 })();
 </script>
 </div>

 <div class="ellipse-wrapper">
 <div class="satellite-track">
 <svg class="hub-lines" viewBox="0 0 650 650" width="100%" height="100%">
 <line x1="325" y1="325" x2="325" y2="0" />
 <line x1="325" y1="325" x2="43.5" y2="487.5" />
 <line x1="325" y1="325" x2="606.5" y2="487.5" />
 </svg>
 
 <div class="hub-node node-top">
 <div class="hub-node-unscale">
 <a href="user/transactions/import/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="6" rx="2"/><path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
 <div class="provider-info">
 <h4>Importation des Courtiers</h4>
 <p><b>Chargez et traitez</b> les fichiers d'exportation de vos courtiers <b>en quelques secondes</b> grâce aux parseurs intelligents de la communauté.</p>
 </div>
 </a>
 </div>
 </div>

 <div class="hub-node node-bottom-left">
 <div class="hub-node-unscale">
 <a href="user/assets/providers/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
 <div class="provider-info">
 <h4>Prix et Cours des Actifs</h4>
 <p><b>Mettez à jour automatiquement</b> les valeurs de vos actions, ETF et cryptomonnaies en vous connectant à des fournisseurs de données en temps réel.</p>
 </div>
 </a>
 </div>
 </div>

 <div class="hub-node node-bottom-right">
 <div class="hub-node-unscale">
 <a href="user/fx/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/></svg>
 <div class="provider-info">
 <h4>Gestion des Changes et Forex</h4>
 <p><b>Synchronisez les taux de change</b> (FX) pour calculer et équilibrer avec précision vos <b>portefeuilles multi-devises</b>.</p>
 </div>
 </a>
 </div>
 </div>
 </div>
 </div>
 </div>
 </div>

 <!-- Is LibreFolio right for you? Section -->
 <section class="lf-fit-section">
 <div class="lf-fit-header">
 <h2 id="lf-fit-title">LibreFolio est-il fait pour vous ?</h2>
 <p>LibreFolio aide les investisseurs à long terme à regrouper chaque portefeuille dans un espace de travail privé, structuré et prêt pour l'analyse.</p>
 </div>

 <div class="lf-fit-comparison" aria-labelledby="lf-fit-title">
 <!-- Header Row -->
 <div class="lf-fit-top-row">
 <article class="lf-fit-heading-card lf-fit-heading-positive" aria-label="Aspect positif">
 <div class="lf-fit-heading-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
 </div>
 <div class="lf-fit-heading-content">
 <h3><strong>Conçu pour les investisseurs réfléchis</strong></h3>
 <p>Suivre. Comprendre. Décider.</p>
 </div>
 </article>
 <div class="lf-fit-axis-spacer" aria-hidden="true"></div>
 <article class="lf-fit-heading-card lf-fit-heading-secondary" aria-label="Contexte alternatif">
 <div class="lf-fit-heading-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
 </div>
 <div class="lf-fit-heading-content">
 <h3><strong>Mieux adapté avec des produits dédiés</strong></h3>
 <p>Des besoins différents méritent des outils différents.</p>
 </div>
 </article>
 </div>

 <!-- Row 1: Portfolio complexity -->
 <div class="lf-fit-row">
 <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspect positif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
 Adapté à LibreFolio
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Espace de travail de portefeuille complet</h4>
 <p>Regroupez courtiers, actifs, devises et portefeuilles dans une vue structurée.</p>
 </div>
 </div>
 </article>
 <div class="lf-fit-axis">Complexité du portefeuille</div>
 <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexte alternatif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
 Outils spécialisés
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Suivi minimal sans analyse</h4>
 <p>Si vous avez seulement besoin d'une simple liste de positions, un traqueur léger peut suffire.</p>
 </div>
 </div>
 </article>
 </div>

 <!-- Row 2: Analysis depth -->
 <div class="lf-fit-row">
 <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspect positif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
 Adapté à LibreFolio
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Analytique de portefeuille</h4>
 <p>Analysez l'allocation, les rendements, le risque, la performance et la structure du portefeuille.</p>
 </div>
 </div>
 </article>
 <div class="lf-fit-axis">Profondeur d'analyse</div>
 <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexte alternatif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
 Outils spécialisés
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Aperçu basique du solde</h4>
 <p>Si vous n'avez besoin que des valeurs actuelles et des totaux, un tableau de bord plus simple peut suffire.</p>
 </div>
 </div>
 </article>
 </div>

 <!-- Row 3: Privacy & ownership -->
 <div class="lf-fit-row">
 <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspect positif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
 Adapté à LibreFolio
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Confidentialité garantie par le code</h4>
 <p>Un code 100 % libre et visible vous garantit le contrôle absolu de vos données financières, avec l'assurance qu'aucune porte dérobée n'existe.</p>
 </div>
 </div>
 </article>
 <div class="lf-fit-axis">Confidentialité &amp; propriété</div>
 <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexte alternatif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
 Outils spécialisés
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Confidentialité non prioritaire</h4>
 <p>Si vous préférez vous fier aux promesses de sécurité écrites dans les conditions d'utilisation d'entreprises privées sans pouvoir les vérifier.</p>
 </div>
 </div>
 </article>
 </div>

 <!-- Row 4: Trading style -->
 <div class="lf-fit-row">
 <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspect positif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
 Adapté à LibreFolio
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Clarté du portefeuille à long terme</h4>
 <p>Concentrez-vous sur la structure, la performance, l'allocation et des décisions éclairées au fil du temps.</p>
 </div>
 </div>
 </article>
 <div class="lf-fit-axis">Style de trading</div>
 <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexte alternatif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
 Outils spécialisés
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Trading intraday automatisé</h4>
 <p>Si vous avez besoin d'une exécution intraday automatisée, utilisez des outils conçus spécifiquement pour l'automatisation du trading.</p>
 </div>
 </div>
 </article>
 </div>

 <!-- Row 5: Extensibility model -->
 <div class="lf-fit-row">
 <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspect positif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
 Adapté à LibreFolio
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Architecture ouverte et extensible</h4>
 <p>Ajoutez des courtiers, des fournisseurs, des devises et des flux de travail à mesure que le projet grandit.</p>
 </div>
 </div>
 </article>
 <div class="lf-fit-axis">Modèle d'extensibilité</div>
 <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexte alternatif">
 <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
 <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
 Outils spécialisés
 </div>
 <div class="lf-fit-cell-main">
 <div class="lf-fit-icon" aria-hidden="true">
 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
 </div>
 <div class="lf-fit-cell-content">
 <h4>Expérience prédéfinie et prête à l'emploi</h4>
 <p>Si vous voulez un produit fermé sans possibilité de personnalisation, une application plus simple peut mieux convenir.</p>
 </div>
 </div>
 </article>
 </div>
 </div>
 </section>

 <!-- Explore Resources (Existing Cards) -->
 <div class="grid cards">
 <a href="user/getting-started/" class="card-link">
 <div class="card-icon">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M13.13 22.19L11.5 18.36C13.07 17.78 14.54 17 15.9 16.09L13.13 22.19M5.64 12.5L1.81 10.87L7.91 8.1C7 9.46 6.22 10.93 5.64 12.5M21.61 2.39C21.61 2.39 16.66 .29 11 5.96C5.34 11.63 3.23 16.58 3.23 16.58C3.23 16.58 3 16.8 3 17C3 17.2 3.23 17.42 3.23 17.42L9 11.65L12.35 15L6.58 20.77C6.58 20.77 6.8 21 7 21C7.2 21 7.42 20.77 7.42 20.77C7.42 20.77 12.37 18.66 18.04 13C23.71 7.34 21.61 2.39 21.61 2.39M14.5 13.5C14.5 12.67 13.83 12 13.5 12C13.17 12 12.5 12.67 12.5 13.5C12.5 14.33 13.17 15 13.5 15C13.83 15 14.5 14.33 14.5 13.5Z" /></svg>
 </div>
 <div class="card-content">
 <span class="card-title">Prise en main</span>
 <span class="card-desc">Découvrez ce que LibreFolio peut faire pour vous.</span>
 </div>
 </a>

 <a href="user/" class="card-link">
 <div class="card-icon">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M19 2L14 6.5V17.5L19 13V2M6.5 5C4.55 5 2.45 5.4 1 6.5V21.16C1 21.41 1.25 21.66 1.5 21.66C1.6 21.66 1.65 21.59 1.75 21.59C3.1 20.94 5.05 20.5 6.5 20.5C8.45 20.5 10.55 20.9 12 22C13.35 21.15 15.8 20.5 17.5 20.5C19.15 20.5 20.85 20.81 22.25 21.56C22.35 21.61 22.4 21.59 22.5 21.59C22.75 21.59 23 21.34 23 21.09V6.5C22.4 6.05 21.75 5.75 21 5.5V19C19.9 18.65 18.7 18.5 17.5 18.5C15.8 18.5 13.35 19.15 12 20V6.5C10.55 5.4 8.45 5 6.5 5Z" /></svg>
 </div>
 <div class="card-content">
 <span class="card-title">Manuel utilisateur</span>
 <span class="card-desc">Guides étape par étape pour gérer votre portefeuille.</span>
 </div>
 </a>

 <a href="gallery/" class="card-link">
 <div class="card-icon">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M22,16V4A2,2 0 0,0 20,2H8A2,2 0 0,0 6,4V16A2,2 0 0,0 8,18H20A2,2 0 0,0 22,16M11,12L13.03,14.71L16,11L20,16H8L11,12M2,6V20A2,2 0 0,0 4,22H18V20H4V6H2Z" /></svg>
 </div>
 <div class="card-content">
 <span class="card-title">Galerie</span>
 <span class="card-desc">Voyez LibreFolio en action sur différents appareils.</span>
 </div>
 </a>

 <a href="admin/" class="card-link">
 <div class="card-icon">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M20,19V7H4V19H20M20,3A2,2 0 0,1 22,5V19A2,2 0 0,1 20,21H4A2,2 0 0,1 2,19V5C2,3.89 2.9,3 4,3H20M13,17V15H18V17H13M9.58,13L5.57,9H8.4L11.7,12.3C12.09,12.69 12.09,13.33 11.7,13.72L8.42,17H5.59L9.58,13Z" /></svg>
 </div>
 <div class="card-content">
 <span class="card-title">Manuel administrateur</span>
 <span class="card-desc">Installation, Docker et maintenance du système.</span>
 </div>
 </a>

 <a href="developer/" class="card-link">
 <div class="card-icon">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z" /></svg>
 </div>
 <div class="card-content">
 <span class="card-title">Manuel développeur</span>
 <span class="card-desc">Architecture,<br>référence API et guide de contribution.</span>
 </div>
 </a>

 <a href="community/contribute/" class="card-link">
 <div class="card-icon">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M12,21.35L10.55,20.03C5.4,15.36 2,12.27 2,8.5C2,5.41 4.42,3 7.5,3C9.24,3 10.91,3.81 12,5.08C13.09,3.81 14.76,3 16.5,3C19.58,3 22,5.41 22,8.5C22,12.27 18.6,15.36 13.45,20.03L12,21.35Z" /></svg>
 </div>
 <div class="card-content">
 <span class="card-title">Communauté</span>
 <span class="card-desc">Soutenir le projet,<br>FAQ, Crédits &amp; Légal.</span>
 </div>
 </a>

 </div>

</div>
