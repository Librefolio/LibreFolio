import type {AiMethodology, AiTechnicalAsset} from '../types';

export interface AiFxIdentity {
    base: string;
    quote: string;
    /** 1 unit of `base` = this many units of `quote` (canonical direction, independent of any UI invert toggle) */
    rate_base_to_quote: number;
    /** = 1 / rate_base_to_quote, pre-computed so the LLM never needs to invert */
    rate_quote_to_base: number;
    rate_date: string;
}

export interface AiFxMetadata {
    generated_at: string;
    response_language: string;
    export_purpose: string;
}

export interface AiFxDataQuality {
    stale_rate: boolean;
}

export interface AiFxExport {
    metadata: AiFxMetadata;
    methodology: AiMethodology;
    identity: AiFxIdentity;
    technical: AiTechnicalAsset | null;
    technical_unavailable_reason?: string;
    data_quality: AiFxDataQuality;
}
