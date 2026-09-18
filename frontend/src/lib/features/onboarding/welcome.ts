export interface WelcomeDraft {
    language: string;
    baseCurrency: string;
    avatarUrl: string | null;
}

export interface WelcomeCopy {
    productName: string;
    title: string;
    description: string;
    defaultsHint: string;
    avatarLabel: string;
    avatarHint: string;
    chooseAvatar: string;
    removeAvatar: string;
    avatarAlt: string;
    languageLabel: string;
    languageHint: string;
    currencyLabel: string;
    currencyHint: string;
    themeHint: string;
    skip: string;
    skipHint: string;
    continue: string;
    logout: string;
    completed: string;
    skipped: string;
}
