export type Locale = "en" | "it" | "es" | "fr";

export interface I18nDict {
  scene01: {
    introStatement: string;
    controlStatement: string;
    sourceWords: string[];
    formatsStatement: string[];
    overloadStatement: string;
    revealPrefix: string;
    productName: string;
    shards: {
      csvReport: { title: string; subtitle: string };
      brokerExport: { title: string; subtitle: string };
      fxRates: { title: string; subtitle: string };
      spreadsheets: { title: string; subtitle: string };
      wallets: { title: string; subtitle: string };
      duplicates: { title: string; subtitle: string };
      priceNoise: { title: string; subtitle: string };
      reports: { title: string; subtitle: string };
      alerts: { title: string; subtitle: string };
    };
  };
  scene02: {
    headline: string;
    sub: string;
  };
  scene03: {
    headline: string;
    sub: string;
  };
  scene04: {
    headline: string;
    sub: string;
  };
  scene05: {
    headline: string;
    sub: string;
  };
  scene06: {
    headline: string;
    sub: string;
  };
  scene07: {
    headline: string;
    sub: string;
  };
  badges: {
    mobileReady: string;
    darkLight: string;
    multiLanguage: string;
    openSource: string;
    selfHosted: string;
    cloudComingSoon: string;
    extendable: string;
    privacyFirst: string;
  };
  callouts: {
    netWorth: string;
    allocation: string;
    technicalAnalysis: string;
    signals: string;
    measures: string;
    import: string;
    reconcile: string;
    automate: string;
  };
  repo: {
    alpha: string;
    url: string;
  };
}
