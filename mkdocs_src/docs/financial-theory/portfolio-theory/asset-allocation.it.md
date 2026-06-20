# ⚖️ Asset Allocation

L'asset allocation è il processo di decisione su **come distribuire il proprio portafoglio** tra diverse classi di asset. La ricerca dimostra costantemente che l'asset allocation spiega la maggior parte della variabilità dei rendimenti di un portafoglio — più della selezione di singoli titoli o del market timing.

---

## 📊 Allocazione Strategica vs Tattica

### 🏗️ Strategic Asset Allocation (SAA)

Un **obiettivo a lungo termine** basato sulla propria tolleranza al rischio, l'orizzonte temporale e gli obiettivi:

| Profilo | Azioni | Obbligazioni | Alternative | Liquidità |
|---------|--------|-------|-------------|------|
| Aggressivo (orizzonte lungo) | 80-90% | 5-15% | 5-10% | 0-5% |
| Bilanciato | 50-60% | 30-40% | 5-10% | 5% |
| Conservativo (orizzonte breve) | 20-30% | 50-60% | 5-10% | 10-20% |

La SAA viene revisionata raramente (annualmente o in caso di grandi cambiamenti di vita).

### 🎯 Tactical Asset Allocation (TAA)

**Deviazioni a breve termine** dall'obiettivo strategico per sfruttare opportunità di mercato percepite:

- Sovrappesare una classe di asset che si prevede avrà un rendimento superiore
- Ridurre l'esposizione a una classe di asset che mostra segni di debolezza
- Adeguarsi alle condizioni macroeconomiche

!!! warning "La TAA è difficile"

    Riuscire a fare market timing è estremamente difficile. La maggior parte della ricerca accademica mostra che gli aggiustamenti tattici danneggiano più di quanto aiutino l'investitore medio.

---

## 📈 Glide Path & Strategia Target-Date

Un **glide path** sposta gradualmente l'allocazione da aggressiva (più azioni) a conservativa (più obbligazioni) man mano che l'investitore si avvicina alla data obiettivo (tipicamente il pensionamento):

$$
w_{stocks}(t) = w_{max} - (w_{max} - w_{min}) \cdot \frac{t}{T}
$$

dove $t$ rappresenta gli anni trascorsi e $T$ è il tempo rimanente fino alla data obiettivo.

### 📉 La Logica

- **Gli investitori giovani** hanno un orizzonte temporale lungo → possono tollerare la volatilità a breve termine → dovrebbero detenere più azioni
- **Gli investitori prossimi al pensionamento** necessitano della preservazione del capitale → dovrebbero detenere più obbligazioni
- Il glide path automatizza questa transizione

---

## 🔄 Ribilanciamento

Nel tempo, i movimenti dei prezzi degli asset causano un **drift** (deriva) del portafoglio rispetto all'allocazione obiettivo. Il ribilanciamento ripristina i pesi originali.

### 📊 Metodi di Ribilanciamento

| Metodo | Trigger | Pro | Contro |
|--------|---------|------|------|
| **Calendario** | Programmazione fissa (mensile, trimestrale) | Semplice, prevedibile | Può innescare operazioni non necessarie |
| **Soglia** | Quando l'allocazione deriva di X% | Opera solo quando necessario | Richiede monitoraggio |
| **Ibrido** | Controllo a calendario, operazione se oltre la soglia | Il meglio di entrambi | Leggermente più complesso |

### 📐 Bonus di ribilanciamento

In un portafoglio di asset volatili e non correlati, il ribilanciamento sistematico genera un **bonus di ribilanciamento** — un piccolo rendimento in eccesso derivante dalla disciplina di "comprare basso, vendere alto" automaticamente:

$$
R_{rebalanced} \approx R_{buy\&hold} + \frac{1}{2} \sum_i w_i \sigma_i^2 (1 - \rho_{avg})
$$

Il bonus è maggiore quando le volatilità sono alte e le correlazioni sono basse.

---

## 🌍 Diversificazione Geografica

Oltre all'allocazione per classi di asset, la diversificazione geografica distribuisce il rischio tra diverse economie:

| Regione | Ruolo | Rischio Valutario |
|--------|------|---------------|
| Domestica | Posizioni core, nessun rischio FX | Nessuno |
| Sviluppate (US, EU, JP) | Crescita + stabilità | Moderato |
| Emergenti (CN, IN, BR) | Maggiore potenziale di crescita | Più elevato |

!!! info "Copertura valutaria"

    Gli investimenti esteri introducono il [rischio FX](../../user/fx/index.md). Alcuni ETF offrono varianti hedged che neutralizzano l'esposizione valutaria, al costo del premio di copertura.

---

## 🔗 Correlati

- 🔀 **[Diversificazione](diversification.md)** — La matematica dietro le decisioni di allocazione
- 📊 **[Metriche di Rischio](../technical-analysis/risk-metrics/index.md)** — Misurare il rischio del portafoglio
- 📊 **[Tipi di Asset](../instruments/asset-types/index.md)** — Le classi di asset tra cui allocare
- 💰 **[Tassazione](../fundamentals/taxation.md)** — Strategie di allocazione fiscalmente efficienti
