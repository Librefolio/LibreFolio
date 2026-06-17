---
hide:
  - navigation
  - toc
description: Free to understand, free to act. LibreFolio brings all your investments into one private, secure dashboard with powerful analytics tools.
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
      <img id="home-logo-img" alt="LibreFolio Logo" class="premium-logo-img" />
      <script>
        (function() {
          var p = window.location.pathname.replace(/\/+$/, '');
          var base = p.replace(/\/(it|fr|es)$/, '');
          document.getElementById('home-logo-img').src = base + '/static/logo.png';
        })();
      </script>
      <h1>LibreFolio</h1>
    </div>
    
    <h2>Free to understand,<span class="desktop-space"> </span><span class="mobile-break"></span>free to act.</h2>
    
    <p class="hero-subtitle" style="margin-top: 2rem;">
      Bring all your investments together, in a secure dashboard.<br><br>
      Your data comes to life through analytics tools designed for you.<br>
      Everything clear, everything under control — because good decisions start with good information.
    </p>

    <div class="premium-badges">
      <span class="badge badge-open-source">100% OPEN SOURCE</span>
      <span class="badge badge-expandable">HIGHLY EXPANDABLE</span>
      <span class="badge badge-self-hosted">SELF-HOSTED OR CLOUD</span>
    </div>
  </div>

  <!-- Video Section: Temporaneamente rimosso (Work in Progress) -->

    <!-- Quick Install -->
  <section class="lf-quick-install-section" id="get-started-quick">
    <div class="lf-quick-install-card">
      <h2 class="lf-quick-install-title">Ready to try LibreFolio?</h2>
      
      <div class="lf-quick-install-docker">
        <span class="lf-quick-install-eyebrow">Recommended</span>
        <div class="lf-quick-install-docker-body">
          <div class="lf-quick-install-heading">
            <span class="lf-quick-install-icon lf-quick-install-icon-primary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
            </span>
            <h3>Install with Docker</h3>
          </div>
          <p>The standard path to run LibreFolio privately and reliably.</p>
        </div>
        <a href="user/installation/" class="lf-btn-primary">Read Docker guide &rarr;</a>
      </div>
      
      <div class="lf-quick-install-dev">
        <div class="lf-quick-install-dev-body">
          <div class="lf-quick-install-heading">
            <span class="lf-quick-install-icon lf-quick-install-icon-secondary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            </span>
            <h4>Developer?</h4>
          </div>
          <p>Set up the Python + Pipenv environment to contribute or customize.</p>
        </div>
        <a href="developer/dev-installation/" class="lf-btn-secondary">Developer installation &rarr;</a>
      </div>
    </div>
  </section>

  <!-- Deep Dive 1: Dashboard -->
  <div class="deep-dive">
    <div class="deep-dive-content">
      <h2>Dashboard</h2>
      <p>A unified view of your entire portfolio. Track your net worth, allocation, and daily changes in one secure place.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
  </div>

  <!-- Deep Dive 2: Brokers -->
  <div class="deep-dive reverse">
    <div class="deep-dive-content">
      <h2>Brokers Integration</h2>
      <p>Seamlessly import data from your brokers. Standardize your transaction history and keep everything organized automatically.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="brokers" data-name="list" alt="Brokers List"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
  </div>

  <!-- Deep Dive 3: Transactions -->
  <div class="deep-dive">
    <div class="deep-dive-content">
      <h2>Transactions</h2>
      <p>Full transparency over every single movement. Filter, search, and edit transactions across all your portfolios effortlessly.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="transactions" data-name="list" alt="Transactions List"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
  </div>

  <!-- Deep Dive 4: Assets -->
  <div class="deep-dive reverse">
    <div class="deep-dive-content">
      <h2>Assets & Analytics</h2>
      <p>Dive deep into individual assets. Advanced charts, technical indicators (EMA, MACD, RSI), and historical data directly imported from global providers.</p>
    </div>
    <div class="deep-dive-image">
      <div class="lf-screenshot-carousel" data-carousel="assets" data-carousel-interval="4000">
        <img class="gallery-img lf-screenshot-carousel-item is-active" 
             data-category="assets" data-name="detail-chart" alt="Asset Details Base Chart">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="detail-signals-macd" alt="Asset Details MACD Signals">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="detail-signals-rsi" alt="Asset Details RSI Signals">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="detail-signals-bollinger" alt="Asset Details Bollinger Bands">
      </div>
    </div>
  </div>

  <!-- Deep Dive 5: Forex -->
  <div class="deep-dive">
    <div class="deep-dive-content">
      <h2>Forex & Currencies</h2>
      <p>Track exchange rates automatically. Manage multi-currency portfolios with live rates fetched straight from central banks.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="fx" data-name="list" alt="Forex Details"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
  </div>

  <!-- Deep Dive: Expandable by the Community -->
  <div class="deep-dive" style="margin-top: 4rem; display: block; text-align: center;">
    <h2 style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
      Expandable by the Community
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
    </h2>
    <p style="max-width: 600px; margin: 0 auto 3rem auto; color: var(--md-default-fg-color--light);">LibreFolio is built around a plugin architecture. It's incredibly easy to write new integrations or leverage existing ones.</p>
    
    <div class="plugin-radial-hub">
      <div class="hub-core">
        <img id="hub-core-img" alt="LibreFolio Core" src="/LibreFolio/static/logo.png">
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
              <a href="user/brokers/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="6" rx="2"/><path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                <div class="provider-info">
                  <h4>Import Brokers Report</h4>
                  <p>Load your transactions directly from your broker's export files in one click.</p>
                </div>
              </a>
            </div>
          </div>

          <div class="hub-node node-bottom-left">
            <div class="hub-node-unscale">
              <a href="user/assets/providers/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
                <div class="provider-info">
                  <h4>Asset Providers</h4>
                  <p>Sync real-time asset valuations from your preferred financial data sources.</p>
                </div>
              </a>
            </div>
          </div>

          <div class="hub-node node-bottom-right">
            <div class="hub-node-unscale">
              <a href="user/fx/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/></svg>
                <div class="provider-info">
                  <h4>Forex Providers</h4>
                  <p>Fetch reliable daily currency exchange rates from your trusted financial providers.</p>
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
      <h2 id="lf-fit-title">Is LibreFolio for you?</h2>
      <p>LibreFolio helps long-term investors bring every portfolio into one private, structured, analytics-ready workspace.</p>
    </div>

    <div class="lf-fit-comparison" aria-labelledby="lf-fit-title">
      <!-- Header Row -->
      <div class="lf-fit-top-row">
        <article class="lf-fit-heading-card lf-fit-heading-positive" aria-label="Positive aspect">
          <div class="lf-fit-heading-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
          <div class="lf-fit-heading-content">
            <h3><strong>Built for thoughtful investors</strong></h3>
            <p>Track. Understand. Decide.</p>
          </div>
        </article>
        <div class="lf-fit-axis-spacer" aria-hidden="true"></div>
        <article class="lf-fit-heading-card lf-fit-heading-secondary" aria-label="Alternative context">
          <div class="lf-fit-heading-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
          </div>
          <div class="lf-fit-heading-content">
            <h3><strong>Better with dedicated products</strong></h3>
            <p>Different needs deserve different tools.</p>
          </div>
        </article>
      </div>

      <!-- Row 1: Portfolio complexity -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Positive aspect">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            LibreFolio fit
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Complete portfolio workspace</h4>
              <p>Bring brokers, assets, currencies, and portfolios into one structured view.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Portfolio complexity</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Alternative context">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Specialized tools
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Minimal tracking without analysis</h4>
              <p>If you only need a simple list of holdings, a lightweight tracker may be enough.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Row 2: Analysis depth -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Positive aspect">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            LibreFolio fit
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Portfolio analytics</h4>
              <p>Analyze allocation, returns, risk, performance, and portfolio structure.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Analysis depth</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Alternative context">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Specialized tools
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Basic balance overview</h4>
              <p>If you only need current values and totals, a simpler dashboard may be enough.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Row 3: Privacy & ownership -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Positive aspect">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            LibreFolio fit
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Privacy-aware data ownership</h4>
              <p>Keep your financial data in an environment you control.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Privacy & ownership</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Alternative context">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Specialized tools
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Hands-off hosted workflow</h4>
              <p>If you want someone else to operate the service end-to-end, a managed product may fit better.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Row 4: Trading style -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Positive aspect">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            LibreFolio fit
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Long-term portfolio clarity</h4>
              <p>Focus on structure, performance, allocation, and informed decisions over time.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Trading style</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Alternative context">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Specialized tools
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Automated intraday trading</h4>
              <p>If you need automated intraday execution, use tools built specifically for trading automation.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Row 5: Extensibility model -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Positive aspect">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            LibreFolio fit
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Open, expandable architecture</h4>
              <p>Add brokers, providers, currencies, and workflows as the project grows.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Extensibility model</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Alternative context">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Specialized tools
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Fixed ready-made experience</h4>
              <p>If you want a closed product with no customization path, a simpler app may fit better.</p>
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
        <span class="card-title">Getting Started</span>
        <span class="card-desc">Discover what LibreFolio can do for you.</span>
      </div>
    </a>

    <a href="user/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M19 2L14 6.5V17.5L19 13V2M6.5 5C4.55 5 2.45 5.4 1 6.5V21.16C1 21.41 1.25 21.66 1.5 21.66C1.6 21.66 1.65 21.59 1.75 21.59C3.1 20.94 5.05 20.5 6.5 20.5C8.45 20.5 10.55 20.9 12 22C13.35 21.15 15.8 20.5 17.5 20.5C19.15 20.5 20.85 20.81 22.25 21.56C22.35 21.61 22.4 21.59 22.5 21.59C22.75 21.59 23 21.34 23 21.09V6.5C22.4 6.05 21.75 5.75 21 5.5V19C19.9 18.65 18.7 18.5 17.5 18.5C15.8 18.5 13.35 19.15 12 20V6.5C10.55 5.4 8.45 5 6.5 5Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">User Manual</span>
        <span class="card-desc">Step-by-step guides to manage your portfolio.</span>
      </div>
    </a>

    <a href="gallery/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M22,16V4A2,2 0 0,0 20,2H8A2,2 0 0,0 6,4V16A2,2 0 0,0 8,18H20A2,2 0 0,0 22,16M11,12L13.03,14.71L16,11L20,16H8L11,12M2,6V20A2,2 0 0,0 4,22H18V20H4V6H2Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Gallery</span>
        <span class="card-desc">See LibreFolio in action across devices.</span>
      </div>
    </a>

    <a href="admin/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M20,19V7H4V19H20M20,3A2,2 0 0,1 22,5V19A2,2 0 0,1 20,21H4A2,2 0 0,1 2,19V5C2,3.89 2.9,3 4,3H20M13,17V15H18V17H13M9.58,13L5.57,9H8.4L11.7,12.3C12.09,12.69 12.09,13.33 11.7,13.72L8.42,17H5.59L9.58,13Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Admin Manual</span>
        <span class="card-desc">Installation, Docker, and system maintenance.</span>
      </div>
    </a>

    <a href="developer/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Developer Manual</span>
        <span class="card-desc">Architecture,<br>API reference, and contribution guide.</span>
      </div>
    </a>

    <a href="community/contribute/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M12,21.35L10.55,20.03C5.4,15.36 2,12.27 2,8.5C2,5.41 4.42,3 7.5,3C9.24,3 10.91,3.81 12,5.08C13.09,3.81 14.76,3 16.5,3C19.58,3 22,5.41 22,8.5C22,12.27 18.6,15.36 13.45,20.03L12,21.35Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Community</span>
        <span class="card-desc">Support the project,<br>FAQ, Credits & Legal.</span>
      </div>
    </a>

  </div>

</div>
