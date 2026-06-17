import { I18nDict } from "../types/i18n";

export const fr: I18nDict = {
  scene01: {
    introStatement: "Investir, c’est agréable.",
    controlStatement: "Tout garder sous contrôle\nest une autre histoire.",
    sourceWords: [
      "Différents courtiers.",
      "Différentes apps.",
      "Différents rapports.",
      "Tableurs.",
      "Différents wallets.",
    ],
    formatsStatement: [
      "Formats différents.",
      "Données dispersées.",
      "Contrôles manuels.",
    ],
    overloadStatement: "Trop de sources.\nPas assez de clarté.",
    revealPrefix: "Et si tout redevenait clair ?",
    productName: "LibreFolio",
    shards: {
      csvReport: {
        title: "CSV Report",
        subtitle: "rows · fees · dates",
      },
      brokerExport: {
        title: "Broker Export",
        subtitle: "different formats",
      },
      fxRates: {
        title: "FX Rates",
        subtitle: "🇪🇺 EUR ⇄ USD 🇺🇸",
      },
      spreadsheets: {
        title: "Spreadsheets",
        subtitle: "manual tracking",
      },
      wallets: {
        title: "Wallets",
        subtitle: "isolated balances",
      },
      duplicates: {
        title: "Duplicates",
        subtitle: "same trade?",
      },
      priceNoise: {
        title: "Price Noise",
        subtitle: "too many charts",
      },
      reports: {
        title: "Reports",
        subtitle: "PDF · CSV · XLS",
      },
      alerts: {
        title: "Alerts",
        subtitle: "manual checks",
      },
    },
  },
  scene02: {
    headline: "Un seul tableau de bord privé.",
    sub: "Tout votre patrimoine, enfin connecté.",
  },
  scene03: {
    headline: "Le suivi de portefeuille rencontre l'analyse technique.",
    sub: "Actions · ETF · Crypto · FX · Signaux",
  },
  scene04: {
    headline: "Des rapports de courtiers aux données de portefeuille nettes.",
    sub: "Importez. Réconciliez. Gardez tout synchronisé.",
  },
  scene05: {
    headline: "Vérifiez. Comparez. Décidez.",
    sub: "Où que vous soyez.",
  },
  scene06: {
    headline: "Vos données. Vos règles.",
    sub: "Open source · Auto-hébergé · Option cloud à venir",
  },
  scene07: {
    headline: "LibreFolio est en Alpha.",
    sub: "Suivez le projet. Rejoignez le développement.",
  },
  badges: {
    mobileReady: "Prêt pour Mobile",
    darkLight: "Mode Clair/Sombre",
    multiLanguage: "Multilingue",
    openSource: "Open Source",
    selfHosted: "Auto-hébergé",
    cloudComingSoon: "Option Cloud (À venir)",
    extendable: "Extensible",
    privacyFirst: "Confidentialité d'abord",
  },
  callouts: {
    netWorth: "Valeur Nette",
    allocation: "Allocation",
    technicalAnalysis: "Analyse Technique",
    signals: "Signaux",
    measures: "Mesures",
    import: "Importer",
    reconcile: "Réconcilier",
    automate: "Automatiser",
  },
  repo: {
    alpha: "Alpha",
    url: "github.com/LibreFolio/LibreFolio",
  },
};
