// src/types/i18n.ts

export interface I18nDict {
  scene01: { headline: string; sub?: string };
  scene02: { headline: string };
  scene03: { headline: string; sub: string };
  scene04: { headline: string };
  scene05: { headline: string; sub: string };
  scene06: { headline: string; cta: string };
}

export type Locale = "en" | "it" | "es" | "fr";
