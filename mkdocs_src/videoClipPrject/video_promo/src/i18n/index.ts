// src/i18n/index.ts
import { en } from "./en";
import { it } from "./it";
import { es } from "./es";
import { fr } from "./fr";
import { Locale, I18nDict } from "../types/i18n";

export const dictionaries: Record<Locale, I18nDict> = { en, it, es, fr };
