# 🔌 Provider

Un provider mantiene aggiornati per te i prezzi di un asset: il prezzo odierno, il suo storico e, per alcuni, dettagli come il tipo o il settore. Ogni asset ha al massimo un provider: scegli un risultato di **Ricerca Online** per collegarlo, oppure configuralo tu stesso in **Assegnazione Provider** — vedi [Crea e Modifica](../create-edit.md).

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon di Yahoo Finance">
            <span class="card-title" style="margin: 0;">Yahoo Finance</span>
        </div>
        <span class="card-desc">Azioni, ETF, fondi e criptovalute dalle borse di tutto il mondo.</span>
    </a>
    <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon di justETF">
            <span class="card-title" style="margin: 0;">justETF</span>
        </div>
        <span class="card-desc">Confronto, prezzi e strutture patrimoniali degli ETF europei.</span>
    </a>
    <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon di Borsa Italiana">
            <span class="card-title" style="margin: 0;">Borsa Italiana</span>
        </div>
        <span class="card-desc">Azioni, obbligazioni, ETF e fondi italiani, in italiano o in inglese.</span>
    </a>
    <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icona di CSS Scraper">
            <span class="card-title" style="margin: 0;">CSS Scraper</span>
        </div>
        <span class="card-desc">Scraper tramite selettori di pagine web per prezzi di obbligazioni personalizzate o strumenti esotici.</span>
    </a>
    <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icona di Scheduled Investment">
            <span class="card-title" style="margin: 0;">Investimento Programmato</span>
        </div>
        <span class="card-desc">Asset a reddito fisso il cui valore è calcolato tramite piani interessi.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Richiedi Nuovo Plugin</span>
     </div>
     <span class="card-desc">Manca il tuo provider di prezzi? Richiedi un nuovo plugin o contribuisci con il codice!</span>
    </a>
    </div>

## 📊 Confronto dei Provider

| Provider | Prezzo attuale | Storico | Ricerca | Dettagli | Identificatore | Ideale per |
|----------|:---:|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | ✅ | Ticker (`AAPL`, `VWCE.DE`) o ISIN | Azioni, ETF, fondi e criptovalute in tutto il mondo |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ | ✅ | ✅ | ✅ | ISIN (`IE00B4L5Y983`) | ETF europei, quotati in EUR, USD, CHF o GBP |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ✅ | ISIN (`IT0003128367`) | Strumenti quotati a Milano, fondi comuni italiani |
| <img src="../../../static/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | ❌ | URL della pagina | Un prezzo mostrato su qualsiasi pagina web pubblica |
| <img src="../../../static/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Investimento Programmato** | ✅ | ✅ | ❌ | ❌ | Nessuno — creato per te | Depositi, prestiti e obbligazioni valutati in base ai loro interessi |

I **Dettagli** sono il tipo, la valuta, la descrizione e dati simili che LibreFolio propone di
compilare per te. Alcuni provider registrano anche gli [eventi dell'asset](../detail/events.md): dividendi (Yahoo
Finance, justETF), split (Yahoo Finance), pagamenti di interessi e scadenza (Investimento Programmato).

## 🎯 Scegliere un Provider

- **Azioni, ETF o criptovalute su qualsiasi borsa** → **Yahoo Finance**.
- **Un ETF europeo**, o prezzi di ETF in USD, CHF o GBP → **justETF**.
- **Azioni, obbligazioni, ETF o fondi negoziati a Milano**, e fondi comuni italiani → **Borsa Italiana**.
- **Un prezzo che compare solo su una pagina web** → **CSS Scraper**.
- **Un conto di risparmio, un deposito a termine, un prestito P2P o un'obbligazione seguita in base ai suoi interessi** →
  **Investimento Programmato**.
- **Niente è adatto?** Seleziona **Nessun Provider** e inserisci i prezzi tu stesso nell'[editor dati](../detail/data-editor.md).

## 🔗 Correlati

- 🛠️ **Per gli sviluppatori: [Provider Asset](../../../developer/backend/assets/system_providers.md)** — Come funziona ogni provider al suo interno
