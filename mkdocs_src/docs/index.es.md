---
hide:
  - navigation
  - toc
description: Libre para entender, libre para actuar. LibreFolio reúne todas tus inversiones en un panel privado y seguro con potentes herramientas de análisis.
---

<!-- Fondo animado -->
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

  <!-- Sección hero -->
  <div class="premium-hero">
    <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-bottom: 0; margin-top: 2rem;">
      <img id="home-logo-img" alt="Logotipo de LibreFolio" class="premium-logo-img" />
      <script>
        (function() {
          var p = window.location.pathname.replace(/\/+$/, '');
          var base = p.replace(/\/(it|fr|es)$/, '');
          document.getElementById('home-logo-img').src = base + '/static/logo.png';
        })();
      </script>
      <h1>LibreFolio</h1>
    </div>

    <h2>Libre para entender,<span class="desktop-space"> </span><span class="mobile-break"></span>libre para actuar.</h2>

    <p class="hero-subtitle" style="margin-top: 2rem;">
      Reúne todas tus inversiones en un panel seguro.<br><br>
      Tus datos cobran vida mediante herramientas de análisis diseñadas para ti.<br>
      Todo claro, todo bajo control — porque las buenas decisiones empiezan con buena información.
    </p>

    <div class="premium-badges">
      <span class="badge badge-open-source">100% CÓDIGO ABIERTO</span>
      <span class="badge badge-expandable">ALTAMENTE AMPLIABLE</span>
      <span class="badge badge-self-hosted">AUTOALOJADO O NUBE</span>
    </div>
  </div>

  <!-- Sección de video: Eliminada temporalmente (Trabajo en progreso) -->

    <!-- Instalación rápida -->
  <section class="lf-quick-install-section" id="get-started-quick">
    <div class="lf-quick-install-card">
      <h2 class="lf-quick-install-title">¿Listo para probar<br><img id="quick-install-logo" alt="Logotipo de LibreFolio" style="height: 1em; width: auto; vertical-align: text-bottom; margin-right: 0.2em; border-radius: 4px;"><script>(function(){var p=window.location.pathname.replace(/\/+$/,"");var base=p.replace(/\/(it|fr|es)$/,"");document.getElementById("quick-install-logo").src=base+"/static/logo.png";})();</script>LibreFolio?</h2>

      <div class="lf-quick-install-docker" style="display: block; padding: 2rem;">
        <span class="lf-quick-install-eyebrow">Recomendado</span>
        <div class="lf-quick-install-docker-body">
          <div class="lf-quick-install-heading">
            <span class="lf-quick-install-icon lf-quick-install-icon-primary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
            </span>
            <h3>Instalar con Docker</h3>
          </div>
          <p>La forma estándar de ejecutar LibreFolio de forma privada y fiable.</p>
        </div>
        <div style="display: flex; justify-content: flex-end; margin-top: 1.25rem;">
          <a href="user/installation/" class="lf-btn-primary">Leer la guía de Docker &rarr;</a>
        </div>
      </div>

      <div class="lf-quick-install-dev" style="display: block; padding: 1.5rem 2rem;">
        <div class="lf-quick-install-dev-body">
          <div class="lf-quick-install-heading">
            <span class="lf-quick-install-icon lf-quick-install-icon-secondary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            </span>
            <h4>¿Ejecutar en el host?</h4>
          </div>
          <p>Configura el entorno de Python + Pipenv para ejecutar LibreFolio directamente en tu máquina host.</p>
        </div>
        <div style="display: flex; justify-content: flex-end; margin-top: 1.25rem;">
          <a href="admin/host_installation/" class="lf-btn-secondary">Instalación en host &rarr;</a>
        </div>
      </div>

      <div class="lf-quick-install-dev lf-quick-install-update" style="display: block; padding: 1.5rem 2rem;">
        <div class="lf-quick-install-dev-body">
          <div class="lf-quick-install-heading">
            <span class="lf-quick-install-icon lf-quick-install-icon-update">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
            </span>
            <h4>¿Mantenerte actualizado?</h4>
          </div>
          <p>Sigue nuestro progreso y recibe notificaciones sobre nuevas funciones:</p>
          <ul style="margin: 0.5rem 0 0; padding-left: 1.25rem; font-size: clamp(0.8rem, 2.5vw, 0.9rem); color: var(--md-default-fg-color--light);">
            <li>Haz clic en <strong>Seguir</strong> en la parte superior del repositorio de GitHub.</li>
            <li>Selecciona <strong>Personalizado</strong> en el menú desplegable de notificaciones.</li>
            <li>Marca <strong>Versiones</strong> y haz clic en <strong>Aplicar</strong>.</li>
          </ul>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.25rem; align-items: center; flex-wrap: wrap;">
          <a href="https://github.com/Librefolio/LibreFolio/subscription" target="_blank" rel="noopener noreferrer" class="lf-btn-secondary" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem;">
            <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" style="vertical-align: text-bottom;"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.35 3.12.88.01.64.01 1.11.01 1.23 0 .21-.15.46-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8z"/></svg>
            <span>Seguir</span>
            <span class="lf-github-counter lf-watch-count">-</span>
          </a>
          <a href="https://github.com/Librefolio/LibreFolio" target="_blank" rel="noopener noreferrer" class="lf-btn-secondary" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem;">
            <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" style="vertical-align: text-bottom;"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg>
            <span>Destacar</span>
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

  <!-- Análisis en profundidad 1: Panel -->
  <div class="deep-dive">
    <div class="deep-dive-content">
      <h2>Panel</h2>
      <p>Una vista unificada de toda tu cartera. Sigue tu patrimonio neto, la asignación y los cambios diarios en un único lugar seguro.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="dashboard" data-name="main" alt="Panel principal"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
    <div class="deep-dive-actions">
      <a href="user/dashboard/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Explorar panel &rarr;</a>
    </div>
  </div>

  <!-- Análisis en profundidad 2: Brokers -->
  <div class="deep-dive reverse">
    <div class="deep-dive-content">
      <h2>Integración con brókers</h2>
      <p>Importa datos <b>directamente</b> desde los archivos de informe de tu bróker usando plugins dedicados.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de brókers"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
    <div class="deep-dive-actions">
      <a href="user/transactions/import/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Ver todos los brókers compatibles &rarr;</a>
    </div>
  </div>

  <!-- Análisis en profundidad 3: Transacciones -->
  <div class="deep-dive">
    <div class="deep-dive-content">
      <h2>Transacciones</h2>
      <p>Transparencia total sobre cada movimiento. Filtra, busca y edita transacciones en todas tus carteras sin esfuerzo.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="transactions" data-name="list" alt="Lista de transacciones"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
    <div class="deep-dive-actions">
      <a href="financial-theory/instruments/transaction-types/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Ver tipos de transacción &rarr;</a>
    </div>
  </div>

  <!-- Análisis en profundidad 4: Activos -->
  <div class="deep-dive reverse">
    <div class="deep-dive-content">
      <h2>Análisis en profundidad</h2>
      <p>Descubre tendencias de mercado con precisión. Potente análisis técnico, señales de trading y métricas de rendimiento histórico para cada activo de tu cartera.</p>
    </div>
    <div class="deep-dive-image">
      <div class="lf-screenshot-carousel" data-carousel="assets" data-carousel-interval="18000">
        <img class="gallery-img lf-screenshot-carousel-item is-active"
             data-category="assets" data-name="detail-chart" alt="Gráfico base de detalles del activo">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="detail-signals-macd" alt="Señales MACD de detalles del activo">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="detail-signals-rsi" alt="Señales RSI de detalles del activo">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="detail-signals-bollinger" alt="Bandas de Bollinger de detalles del activo">
      </div>
    </div>
    <div class="deep-dive-actions">
      <a href="financial-theory/technical-analysis/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Explorar análisis técnico &rarr;</a>
    </div>
  </div>

  <!-- Análisis en profundidad 5: Forex -->
  <div class="deep-dive">
    <div class="deep-dive-content">
      <h2>Activos y Forex</h2>
      <p>Sigue automáticamente las valoraciones de activos y los tipos de cambio. Gestiona carteras multidivisa con datos en vivo obtenidos directamente de proveedores financieros y bancos centrales.</p>
    </div>
    <div class="deep-dive-image">
      <div class="lf-screenshot-carousel" data-carousel="fx-assets-table" data-carousel-interval="18000">
        <img class="gallery-img lf-screenshot-carousel-item is-active"
             data-category="fx" data-name="list" data-title="Cuadrícula de Forex" alt="Cuadrícula de Forex">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="fx" data-name="list-table" data-title="Tabla de Forex" alt="Tabla de Forex">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="list" data-title="Cuadrícula de activos" alt="Cuadrícula de activos">
        <img class="gallery-img lf-screenshot-carousel-item" loading="lazy"
             data-category="assets" data-name="list-table" data-title="Tabla de activos" alt="Tabla de activos">
      </div>
    </div>
    <div class="deep-dive-actions">
      <a href="financial-theory/instruments/asset-types/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Tipos de activos &rarr;</a>
      <a href="user/fx/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Gestión de Forex &rarr;</a>
    </div>
  </div>

  <!-- Análisis en profundidad 6: Herramientas -->
  <div class="deep-dive reverse">
    <div class="deep-dive-content">
      <h2>Herramientas</h2>
      <p>LibreFolio incluye un conjunto de herramientas, ¡una para cada tarea útil! Cada una parte de tu cartera real y te muestra los números antes de actuar. A partir de ahora, hacer cálculos y tomar decisiones es pan comido.</p>
    </div>
    <div class="deep-dive-image">
      <div class="screenshot-container">
          <img class="gallery-img" data-category="tools" data-name="hub" alt="Catálogo de herramientas"
               style="width: 100%; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
      </div>
    </div>
    <div class="deep-dive-actions">
      <a href="user/tools/" class="lf-btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">Explorar herramientas &rarr;</a>
    </div>
  </div>

  <!-- Análisis en profundidad: Ampliable por la comunidad -->
  <div class="deep-dive" style="margin-top: 4rem; display: block; text-align: center;">
    <h2 style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
      Un ecosistema modular
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
    </h2>
    <p style="max-width: 680px; margin: 0 auto 3rem auto; color: var(--md-default-fg-color--light); font-size: 1.05rem; line-height: 1.6;">
      Libérate de las hojas de cálculo. LibreFolio está diseñado para <b>conectarse sin problemas</b> con las herramientas financieras que ya usas, ampliando sus capacidades mediante un ecosistema creciente de <b>plugins impulsados por la comunidad</b>.
    </p>

    <div class="plugin-radial-hub plugin-radial-hub--five">
      <div class="hub-core">
        <img id="hub-core-img" alt="Núcleo de LibreFolio" src="/LibreFolio/static/logo.png">
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
          <svg class="hub-lines" viewBox="0 0 720 720" width="100%" height="100%">
            <line x1="360" y1="360" x2="360" y2="0" />
            <line x1="360" y1="360" x2="702.4" y2="248.8" />
            <line x1="360" y1="360" x2="571.6" y2="651.2" />
            <line x1="360" y1="360" x2="148.4" y2="651.2" />
            <line x1="360" y1="360" x2="17.6" y2="248.8" />
          </svg>

          <div class="hub-node node-penta-1">
            <div class="hub-node-unscale">
              <a href="user/transactions/import/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="6" rx="2"/><path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                <div class="provider-info">
                  <h4>Importación de brókers</h4>
                  <p><b>Sube y procesa</b> los archivos de exportación de tu bróker <b>en segundos</b> usando analizadores inteligentes impulsados por la comunidad.</p>
                </div>
              </a>
            </div>
          </div>

          <div class="hub-node node-penta-2">
            <div class="hub-node-unscale">
              <a href="user/assets/providers/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
                <div class="provider-info">
                  <h4>Precios y cotizaciones de activos</h4>
                  <p><b>Actualiza automáticamente</b> los valores de acciones, ETFs y cripto conectándote a proveedores de datos en tiempo real.</p>
                </div>
              </a>
            </div>
          </div>

          <div class="hub-node node-penta-3">
            <div class="hub-node-unscale">
              <a href="user/fx/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/></svg>
                <div class="provider-info">
                  <h4>Tipos de cambio y Forex</h4>
                  <p><b>Sincroniza los tipos de cambio</b> (FX) para calcular y equilibrar con precisión tus <b>carteras multidivisa</b>.</p>
                </div>
              </a>
            </div>
          </div>

          <div class="hub-node node-penta-4">
            <div class="hub-node-unscale">
              <a href="developer/architecture/patterns/signal_plugin_guide/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m7 16 4-5 4 3 4-7"/></svg>
                <div class="provider-info">
                  <h4>Plugins de señales técnicas</h4>
                  <p><b>Añade nuevos indicadores</b> como plugins de Python aislados con parámetros, salidas, umbrales y documentación basados en esquemas.</p>
                </div>
              </a>
            </div>
          </div>

          <div class="hub-node node-penta-5">
            <div class="hub-node-unscale">
              <a href="user/tools/" class="card-link provider-row" style="padding: 1rem; margin: 0; color: inherit; text-decoration: none; text-align: left;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                <div class="provider-info">
                  <h4>Herramientas</h4>
                  <p><b>Planifica y calcula</b> con plugins de herramientas, uno para cada tarea, <b>partiendo de tu propia cartera</b>.</p>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Sección: ¿Es LibreFolio para ti? -->
  <section class="lf-fit-section">
    <div class="lf-fit-header">
      <h2 id="lf-fit-title">¿Es LibreFolio para ti?</h2>
      <p>LibreFolio ayuda a los inversores a largo plazo a reunir todas sus carteras en un espacio de trabajo privado, estructurado y listo para el análisis.</p>
    </div>

    <div class="lf-fit-comparison" aria-labelledby="lf-fit-title">
      <!-- Fila de encabezado -->
      <div class="lf-fit-top-row">
        <article class="lf-fit-heading-card lf-fit-heading-positive" aria-label="Aspecto positivo">
          <div class="lf-fit-heading-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
          <div class="lf-fit-heading-content">
            <h3><strong>Creado para inversores reflexivos</strong></h3>
            <p>Sigue. Comprende. Decide.</p>
          </div>
        </article>
        <div class="lf-fit-axis-spacer" aria-hidden="true"></div>
        <article class="lf-fit-heading-card lf-fit-heading-secondary" aria-label="Contexto alternativo">
          <div class="lf-fit-heading-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
          </div>
          <div class="lf-fit-heading-content">
            <h3><strong>Mejor con productos dedicados</strong></h3>
            <p>Diferentes necesidades merecen diferentes herramientas.</p>
          </div>
        </article>
      </div>

      <!-- Fila 1: Complejidad de la cartera -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspecto positivo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Encaja con LibreFolio
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Espacio de trabajo completo para la cartera</h4>
              <p>Reúne brókers, activos, divisas y carteras en una vista estructurada.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Complejidad de la cartera</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexto alternativo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Herramientas especializadas
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Seguimiento mínimo sin análisis</h4>
              <p>Si solo necesitas una lista simple de posiciones, un rastreador ligero puede ser suficiente.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Fila 2: Profundidad del análisis -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspecto positivo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Encaja con LibreFolio
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Análisis de la cartera</h4>
              <p>Analiza asignación, rentabilidad, riesgo, rendimiento y estructura de la cartera.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Profundidad del análisis</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexto alternativo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Herramientas especializadas
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Resumen básico de saldos</h4>
              <p>Si solo necesitas valores actuales y totales, un panel más simple puede ser suficiente.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Fila 3: Privacidad y propiedad -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspecto positivo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Encaja con LibreFolio
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Privacidad garantizada por el código</h4>
              <p>El código 100% libre y visible te da control absoluto sobre tus datos financieros, con la certeza de que no existen puertas traseras.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Privacidad y propiedad</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexto alternativo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Herramientas especializadas
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>La privacidad no es prioridad</h4>
              <p>Si prefieres confiar en las promesas de seguridad escritas en los Términos de Servicio de empresas privadas sin poder verificarlas.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Fila 4: Estilo de trading -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspecto positivo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Encaja con LibreFolio
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Claridad de la cartera a largo plazo</h4>
              <p>Céntrate en la estructura, el rendimiento, la asignación y las decisiones informadas a lo largo del tiempo.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Estilo de trading</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexto alternativo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Herramientas especializadas
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Trading intradía automatizado</h4>
              <p>Si necesitas ejecución intradía automatizada, usa herramientas creadas específicamente para la automatización del trading.</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Fila 5: Modelo de extensibilidad -->
      <div class="lf-fit-row">
        <article class="lf-fit-cell lf-fit-cell-positive" aria-label="Aspecto positivo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-positive">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Encaja con LibreFolio
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Arquitectura abierta y ampliable</h4>
              <p>Añade brókers, proveedores, divisas y flujos de trabajo a medida que el proyecto crece.</p>
            </div>
          </div>
        </article>
        <div class="lf-fit-axis">Modelo de extensibilidad</div>
        <article class="lf-fit-cell lf-fit-cell-secondary" aria-label="Contexto alternativo">
          <div class="lf-fit-mobile-badge lf-fit-mobile-badge-secondary">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
            Herramientas especializadas
          </div>
          <div class="lf-fit-cell-main">
            <div class="lf-fit-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
            </div>
            <div class="lf-fit-cell-content">
              <h4>Experiencia fija ya preparada</h4>
              <p>Si quieres un producto cerrado sin opciones de personalización, una aplicación más simple puede encajar mejor.</p>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>

  <!-- Explorar recursos (tarjetas existentes) -->
  <div class="grid cards">
    <a href="user/getting-started/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M13.13 22.19L11.5 18.36C13.07 17.78 14.54 17 15.9 16.09L13.13 22.19M5.64 12.5L1.81 10.87L7.91 8.1C7 9.46 6.22 10.93 5.64 12.5M21.61 2.39C21.61 2.39 16.66 .29 11 5.96C5.34 11.63 3.23 16.58 3.23 16.58C3.23 16.58 3 16.8 3 17C3 17.2 3.23 17.42 3.23 17.42L9 11.65L12.35 15L6.58 20.77C6.58 20.77 6.8 21 7 21C7.2 21 7.42 20.77 7.42 20.77C7.42 20.77 12.37 18.66 18.04 13C23.71 7.34 21.61 2.39 21.61 2.39M14.5 13.5C14.5 12.67 13.83 12 13.5 12C13.17 12 12.5 12.67 12.5 13.5C12.5 14.33 13.17 15 13.5 15C13.83 15 14.5 14.33 14.5 13.5Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Primeros pasos</span>
        <span class="card-desc">Descubre lo que LibreFolio puede hacer por ti.</span>
      </div>
    </a>

    <a href="user/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M19 2L14 6.5V17.5L19 13V2M6.5 5C4.55 5 2.45 5.4 1 6.5V21.16C1 21.41 1.25 21.66 1.5 21.66C1.6 21.66 1.65 21.59 1.75 21.59C3.1 20.94 5.05 20.5 6.5 20.5C8.45 20.5 10.55 20.9 12 22C13.35 21.15 15.8 20.5 17.5 20.5C19.15 20.5 20.85 20.81 22.25 21.56C22.35 21.61 22.4 21.59 22.5 21.59C22.75 21.59 23 21.34 23 21.09V6.5C22.4 6.05 21.75 5.75 21 5.5V19C19.9 18.65 18.7 18.5 17.5 18.5C15.8 18.5 13.35 19.15 12 20V6.5C10.55 5.4 8.45 5 6.5 5Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Manual de usuario</span>
        <span class="card-desc">Guías paso a paso para gestionar tu cartera.</span>
      </div>
    </a>

    <a href="gallery/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M22,16V4A2,2 0 0,0 20,2H8A2,2 0 0,0 6,4V16A2,2 0 0,0 8,18H20A2,2 0 0,0 22,16M11,12L13.03,14.71L16,11L20,16H8L11,12M2,6V20A2,2 0 0,0 4,22H18V20H4V6H2Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Galería</span>
        <span class="card-desc">Ve LibreFolio en acción en distintos dispositivos.</span>
      </div>
    </a>

    <a href="admin/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M20,19V7H4V19H20M20,3A2,2 0 0,1 22,5V19A2,2 0 0,1 20,21H4A2,2 0 0,1 2,19V5C2,3.89 2.9,3 4,3H20M13,17V15H18V17H13M9.58,13L5.57,9H8.4L11.7,12.3C12.09,12.69 12.09,13.33 11.7,13.72L8.42,17H5.59L9.58,13Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Manual de administración</span>
        <span class="card-desc">Instalación, Docker y mantenimiento del sistema.</span>
      </div>
    </a>

    <a href="developer/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Manual del desarrollador</span>
        <span class="card-desc">Arquitectura,<br>referencia de API y guía de contribución.</span>
      </div>
    </a>

    <a href="community/contribute/" class="card-link">
      <div class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36"><path fill="currentColor" d="M12,21.35L10.55,20.03C5.4,15.36 2,12.27 2,8.5C2,5.41 4.42,3 7.5,3C9.24,3 10.91,3.81 12,5.08C13.09,3.81 14.76,3 16.5,3C19.58,3 22,5.41 22,8.5C22,12.27 18.6,15.36 13.45,20.03L12,21.35Z" /></svg>
      </div>
      <div class="card-content">
        <span class="card-title">Comunidad</span>
        <span class="card-desc">Apoya al proyecto,<br>Preguntas frecuentes, créditos y aviso legal.</span>
      </div>
    </a>

  </div>

</div>
