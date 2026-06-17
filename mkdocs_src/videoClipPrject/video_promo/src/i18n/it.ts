import { I18nDict } from "../types/i18n";

export const it: I18nDict = {
  scene01: {
    introStatement: "Bello investire!",
    controlStatement: "Tenere tutto sotto controllo\nè un’altra storia.",
    sourceWords: [
      "Broker diversi.",
      "App diverse.",
      "Report diversi.",
      "Fogli Excel.",
      "Wallet diversi.",
    ],
    formatsStatement: [
      "Formati diversi.",
      "Dati sparsi.",
      "Controlli manuali.",
    ],
    overloadStatement: "Troppe fonti.\nPoca chiarezza.",
    revealPrefix: "E se tutto tornasse chiaro?",
    productName: "LibreFolio",
    shards: {
      csvReport: {
        title: "Report CSV",
        subtitle: "righe · commissioni · date",
      },
      brokerExport: {
        title: "Export Broker",
        subtitle: "formati diversi",
      },
      fxRates: {
        title: "Tassi FX",
        subtitle: "🇪🇺 EUR ⇄ USD 🇺🇸",
      },
      spreadsheets: {
        title: "Fogli Excel",
        subtitle: "tracking manuale",
      },
      wallets: {
        title: "Wallet",
        subtitle: "saldi isolati",
      },
      duplicates: {
        title: "Duplicati",
        subtitle: "stessa operazione?",
      },
      priceNoise: {
        title: "Rumore Prezzi",
        subtitle: "troppi grafici",
      },
      reports: {
        title: "Report",
        subtitle: "PDF · CSV · XLS",
      },
      alerts: {
        title: "Alert",
        subtitle: "controlli manuali",
      },
    },
  },
  scene02: {
    headline: "Una sola dashboard privata.",
    sub: "Tutto il tuo patrimonio, finalmente connesso.",
  },
  scene03: {
    headline: "Il portfolio tracking incontra l'analisi tecnica.",
    sub: "Azioni · ETF · Crypto · FX · Segnali",
  },
  scene04: {
    headline: "Dai report dei broker a dati di portafoglio puliti.",
    sub: "Importa. Riconcilia. Mantieni tutto sincronizzato.",
  },
  scene05: {
    headline: "Controlla. Confronta. Decidi.",
    sub: "Ovunque tu sia.",
  },
  scene06: {
    headline: "I tuoi dati. Le tue regole.",
    sub: "Open source · Self-hosted · Cloud option in arrivo",
  },
  scene07: {
    headline: "LibreFolio è in Alpha.",
    sub: "Segui il progetto. Unisciti allo sviluppo.",
  },
  badges: {
    mobileReady: "Pronto per Mobile",
    darkLight: "Modalità Chiaro/Scuro",
    multiLanguage: "Multilingua",
    openSource: "Open Source",
    selfHosted: "Self-Hosted",
    cloudComingSoon: "Opzione Cloud (In arrivo)",
    extendable: "Estendibile",
    privacyFirst: "Privacy First",
  },
  callouts: {
    netWorth: "Patrimonio Netto",
    allocation: "Allocazione",
    technicalAnalysis: "Analisi Tecnica",
    signals: "Segnali",
    measures: "Misure",
    import: "Importa",
    reconcile: "Riconcilia",
    automate: "Automatizza",
  },
  repo: {
    alpha: "Alpha",
    url: "github.com/LibreFolio/LibreFolio",
  },
};
