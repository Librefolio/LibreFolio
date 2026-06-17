import { I18nDict } from "../types/i18n";

export const en: I18nDict = {
  scene01: {
    introStatement: "Investing feels good.",
    controlStatement: "Keeping everything under control\nis another story.",
    sourceWords: [
      "Different brokers.",
      "Different apps.",
      "Different reports.",
      "Spreadsheets.",
      "Different wallets.",
    ],
    formatsStatement: [
      "Different formats.",
      "Scattered data.",
      "Manual checks.",
    ],
    overloadStatement: "Too many sources.\nNot enough clarity.",
    revealPrefix: "What if everything became clear?",
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
    headline: "One private dashboard.",
    sub: "All your wealth, finally connected.",
  },
  scene03: {
    headline: "Portfolio tracking meets technical analysis.",
    sub: "Stocks · ETFs · Crypto · FX · Signals",
  },
  scene04: {
    headline: "From broker reports to clean portfolio data.",
    sub: "Import. Reconcile. Keep everything in sync.",
  },
  scene05: {
    headline: "Check. Compare. Decide.",
    sub: "Wherever you are.",
  },
  scene06: {
    headline: "Your data. Your rules.",
    sub: "Open source · Self-hosted · Cloud option coming soon",
  },
  scene07: {
    headline: "LibreFolio is in Alpha.",
    sub: "Follow the project. Join the build.",
  },
  badges: {
    mobileReady: "Mobile-ready",
    darkLight: "Dark/Light mode",
    multiLanguage: "Multi-language",
    openSource: "Open Source",
    selfHosted: "Self-Hosted",
    cloudComingSoon: "Cloud option (Coming soon)",
    extendable: "Extendable",
    privacyFirst: "Privacy-first",
  },
  callouts: {
    netWorth: "Net Worth",
    allocation: "Allocation",
    technicalAnalysis: "Technical Analysis",
    signals: "Signals",
    measures: "Measures",
    import: "Import",
    reconcile: "Reconcile",
    automate: "Automate",
  },
  repo: {
    alpha: "Alpha",
    url: "github.com/LibreFolio/LibreFolio",
  },
};
