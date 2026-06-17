import { I18nDict } from "../types/i18n";

export const es: I18nDict = {
  scene01: {
    introStatement: "Invertir está bien.",
    controlStatement: "Mantenerlo todo bajo control\nes otra historia.",
    sourceWords: [
      "Brókers distintos.",
      "Apps distintas.",
      "Informes distintos.",
      "Hojas de cálculo.",
      "Wallets distintos.",
    ],
    formatsStatement: [
      "Formatos diferentes.",
      "Datos dispersos.",
      "Controles manuales.",
    ],
    overloadStatement: "Demasiadas fuentes.\nPoca claridad.",
    revealPrefix: "¿Y si todo volviera a estar claro?",
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
    headline: "Un único panel privado.",
    sub: "Todo tu patrimonio, finalmente conectado.",
  },
  scene03: {
    headline: "Seguimiento de cartera se une al análisis técnico.",
    sub: "Acciones · ETFs · Cripto · FX · Señales",
  },
  scene04: {
    headline: "De reportes del bróker a datos de cartera limpios.",
    sub: "Importa. Reconcilia. Mantén todo sincronizado.",
  },
  scene05: {
    headline: "Revisa. Compara. Decide.",
    sub: "Dondequiera que estés.",
  },
  scene06: {
    headline: "Tus datos. Tus reglas.",
    sub: "Código abierto · Autohospedado · Opción en la nube pronto",
  },
  scene07: {
    headline: "LibreFolio está en Alpha.",
    sub: "Sigue el proyecto. Únete al desarrollo.",
  },
  badges: {
    mobileReady: "Listo para Móvil",
    darkLight: "Modo Claro/Oscuro",
    multiLanguage: "Multilingüe",
    openSource: "Código Abierto",
    selfHosted: "Autohospedado",
    cloudComingSoon: "Opción en la nube (Pronto)",
    extendable: "Extensible",
    privacyFirst: "Privacidad Primero",
  },
  callouts: {
    netWorth: "Patrimonio Neto",
    allocation: "Asignación",
    technicalAnalysis: "Análisis Técnico",
    signals: "Señales",
    measures: "Medidas",
    import: "Importar",
    reconcile: "Reconciliar",
    automate: "Automatizar",
  },
  repo: {
    alpha: "Alpha",
    url: "github.com/LibreFolio/LibreFolio",
  },
};
