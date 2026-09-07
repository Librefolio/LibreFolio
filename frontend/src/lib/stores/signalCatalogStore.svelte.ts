import {zodiosApi} from '$lib/api';
import {mergeSignalDefinitions} from '$lib/charts/signals/catalogMapper';
import {getLocalSignalDefinitions} from '$lib/charts/signals/registry';
import type {BackendSignalCatalogResponse, SignalDefinition, SignalDomain} from '$lib/charts/signals';

export type SignalCatalogLoader = (domain: SignalDomain) => Promise<BackendSignalCatalogResponse>;

async function loadCatalogFromApi(domain: SignalDomain): Promise<BackendSignalCatalogResponse> {
    return domain === 'asset' ? zodiosApi.list_asset_signal_catalog_api_v1_assets_prices_signals_get() : zodiosApi.list_fx_signal_catalog_api_v1_fx_currencies_signals_get();
}

export class SignalCatalogStore {
    private readonly loader: SignalCatalogLoader;
    private readonly inflight = new Map<SignalDomain, Promise<SignalDefinition[]>>();
    private definitionsByDomain = new Map<SignalDomain, SignalDefinition[]>();
    private errorsByDomain = new Map<SignalDomain, string>();
    private loadingDomains = new Set<SignalDomain>();

    constructor(loader: SignalCatalogLoader = loadCatalogFromApi) {
        this.loader = loader;
    }

    definitions(domain: SignalDomain): SignalDefinition[] {
        return this.definitionsByDomain.get(domain) ?? [];
    }

    error(domain: SignalDomain): string | null {
        return this.errorsByDomain.get(domain) ?? null;
    }

    isLoading(domain: SignalDomain): boolean {
        return this.loadingDomains.has(domain);
    }

    async load(domain: SignalDomain, force = false): Promise<SignalDefinition[]> {
        const cached = this.definitionsByDomain.get(domain);
        if (!force && cached) return cached;

        const active = this.inflight.get(domain);
        if (active) return active;

        this.loadingDomains = new Set(this.loadingDomains).add(domain);
        const nextErrors = new Map(this.errorsByDomain);
        nextErrors.delete(domain);
        this.errorsByDomain = nextErrors;

        const request = this.loader(domain)
            .then((response) => {
                const definitions = mergeSignalDefinitions(response.items ?? [], getLocalSignalDefinitions(), domain);
                this.definitionsByDomain = new Map(this.definitionsByDomain).set(domain, definitions);
                return definitions;
            })
            .catch((error: unknown) => {
                const message = error instanceof Error ? error.message : `Failed to load ${domain} signal catalog`;
                this.errorsByDomain = new Map(this.errorsByDomain).set(domain, message);
                throw error;
            })
            .finally(() => {
                this.inflight.delete(domain);
                const loadingDomains = new Set(this.loadingDomains);
                loadingDomains.delete(domain);
                this.loadingDomains = loadingDomains;
            });

        this.inflight.set(domain, request);
        return request;
    }
}

export const signalCatalogStore = new SignalCatalogStore();
