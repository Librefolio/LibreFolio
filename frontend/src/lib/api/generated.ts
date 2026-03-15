import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";

type AuthLoginResponse = {
  user: AuthUserResponse;
  user_settings?:
    | ((UserSettingsRead | null) | Array<UserSettingsRead | null>)
    | undefined;
  message?: /**
   * @default "Login successful"
   */
  string | undefined;
};
type AuthUserResponse = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
};
type UserSettingsRead = {
  /**
   * Preferred language (en, it, fr, es)
   */
  language: string;
  /**
   * Base currency for display (ISO 4217)
   */
  base_currency: string;
  /**
   * UI theme
   *
   * @enum light, dark, auto
   */
  theme: "light" | "dark" | "auto";
  avatar_url?:
    | /**
     * URL to user avatar image
     */
    ((string | null) | Array<string | null>)
    | undefined;
};
type AuthMeResponse = {
  user: AuthUserResponse;
};
type AuthRegisterResponse = {
  user: AuthUserResponse;
  message?: /**
   * @default "Registration successful"
   */
  string | undefined;
};
type BRAccessBulkItem = {
  /**
   * User ID
   */
  user_id: number;
  role: UserRole;
  share_percentage?:
    | /**
     * Ownership fraction (0.0-1.0). Only valid for OWNER role. Frontend displays as %.
     *
     * @default "0"
     */
    (| /**
         * @minimum 0
         * @maximum 1
         */
        (| number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
          )
        | Array<
            /**
             * @minimum 0
             * @maximum 1
             */
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
          >
      )
    | undefined;
};
type UserRole =
  /**
 * User role for broker access control.

- OWNER: Full access (CRUD broker, manage access, delete broker)
- EDITOR: Modify broker and transactions, can only remove self
- VIEWER: Read-only access
 *
 * @enum OWNER, EDITOR, VIEWER
 */
  "OWNER" | "EDITOR" | "VIEWER";
type BRAccessBulkResponse = {
  /**
   * Per-item operation results
   */
  results: Array<BRAccessItem>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type BRAccessItem = {
  /**
   * User ID
   */
  user_id: number;
  /**
   * Username
   */
  username: string;
  /**
   * User email
   */
  email: string;
  role: UserRole;
  /**
   * Ownership fraction (0.0-1.0) for portfolio aggregation
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  share_percentage: string;
  avatar_url?:
    | /**
     * User avatar URL
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * When access was granted
   */
  created_at: string;
};
type BRAccessListResponse = Partial<{
  /**
   * List of items
   */
  items: Array<BRAccessItem>;
}>;
type BRAssetHolding = {
  /**
   * Asset ID
   */
  asset_id: number;
  /**
   * Asset display name
   */
  asset_name: string;
  /**
   * Current quantity held
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  quantity: string;
  total_cost: Currency_Output;
  /**
   * Average cost per unit
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  average_cost_per_unit: string;
  current_price?:
    | /**
     * Latest price per unit
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  current_value?:
    | /**
     * Current market value
     */
    ((Currency_Output | null) | Array<Currency_Output | null>)
    | undefined;
  unrealized_pnl?:
    | /**
     * Unrealized profit/loss
     */
    ((Currency_Output | null) | Array<Currency_Output | null>)
    | undefined;
  unrealized_pnl_percent?:
    | /**
     * Unrealized P&L %
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
};
type Currency_Output = {
  /**
   * ISO 4217 currency code or crypto symbol
   */
  code: string;
  /**
   * Amount (can be negative)
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  amount: string;
};
type BRBulkCreateResponse = {
  /**
   * Per-item operation results
   */
  results: Array<BRCreateResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type BRCreateResult = {
  success: boolean;
  broker_id?: ((number | null) | Array<number | null>) | undefined;
  name: string;
  deposits_created?: /**
   * Number of DEPOSIT transactions created
   *
   * @default 0
   * @minimum 0
   */
  number | undefined;
  error?: ((string | null) | Array<string | null>) | undefined;
};
type BRBulkDeleteResponse = {
  /**
   * Per-item operation results
   */
  results: Array<BRDeleteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  /**
   * Total number of records deleted across all items
   *
   * @minimum 0
   */
  total_deleted: number;
};
type BRDeleteResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Broker ID
   */
  id: number;
  transactions_deleted?: /**
   * Number of transactions cascade-deleted (only when force=True)
   *
   * @default 0
   * @minimum 0
   */
  number | undefined;
};
type BRBulkUpdateResponse = {
  /**
   * Per-item operation results
   */
  results: Array<BRUpdateResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type BRUpdateResult = {
  id: number;
  success: boolean;
  validation_triggered?: /**
   * Whether balance validation was triggered due to flag change
   *
   * @default false
   */
  boolean | undefined;
  error?: ((string | null) | Array<string | null>) | undefined;
};
type BRCreateItem = {
  /**
   * Broker name (must be unique)
   *
   * @minLength 1
   * @maxLength 100
   */
  name: string;
  description?:
    | /**
     * Broker description
     */
    (| /**
         * @maxLength 500
         */
        (string | null)
        | Array<
            /**
             * @maxLength 500
             */
            string | null
          >
      )
    | undefined;
  portal_url?:
    | /**
     * URL to broker's web portal
     */
    (| /**
         * @maxLength 255
         */
        (string | null)
        | Array<
            /**
             * @maxLength 255
             */
            string | null
          >
      )
    | undefined;
  icon_url?:
    | /**
     * Custom icon URL for the broker
     */
    (| /**
         * @maxLength 500
         */
        (string | null)
        | Array<
            /**
             * @maxLength 500
             */
            string | null
          >
      )
    | undefined;
  default_import_plugin?:
    | /**
     * Default BRIM plugin for importing transactions
     */
    (| /**
         * @maxLength 100
         */
        (string | null)
        | Array<
            /**
             * @maxLength 100
             */
            string | null
          >
      )
    | undefined;
  allow_cash_overdraft?: /**
   * Allow leveraged buying (negative cash balance)
   *
   * @default false
   */
  boolean | undefined;
  allow_asset_shorting?: /**
   * Allow short selling (negative asset quantities)
   *
   * @default false
   */
  boolean | undefined;
  is_active?: /**
   * Whether the broker account is currently active
   *
   * @default true
   */
  boolean | undefined;
  opened_at?:
    | /**
     * Date when the account was opened in reality
     */
    ((string | null) | Array<string | null>)
    | undefined;
  initial_balances?:
    | /**
     * Initial cash balances. Creates DEPOSIT transactions.
     */
    ((Array<Currency_Input> | null) | Array<Array<Currency_Input> | null>)
    | undefined;
};
type Currency_Input = {
  /**
   * ISO 4217 currency code or crypto symbol
   */
  code: string;
  /**
   * Amount (can be negative)
   */
  amount:
    | (
        | number
        /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        | string
      )
    | Array<
        | number
        /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        | string
      >;
};
type BRIMAssetCandidate = {
  /**
   * Real asset ID from database
   */
  asset_id: number;
  symbol?:
    | /**
     * Asset symbol/ticker
     */
    ((string | null) | Array<string | null>)
    | undefined;
  isin?:
    | /**
     * Asset ISIN
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Asset display name
   */
  name: string;
  match_confidence: BRIMMatchConfidence;
};
type BRIMMatchConfidence =
  /**
 * Confidence level for asset candidate matching.

Criteria:
- EXACT: ISIN match (ISIN is globally unique identifier)
- HIGH: Symbol exact match + same asset type
- MEDIUM: Symbol exact match only (no type verification)
- LOW: Partial name match or fuzzy symbol match
 *
 * @enum exact, high, medium, low
 */
  "exact" | "high" | "medium" | "low";
type BRIMAssetMapping = {
  /**
   * Fake ID used in parsed transactions
   */
  fake_asset_id: number;
  extracted_symbol?:
    | /**
     * Symbol extracted from file
     */
    ((string | null) | Array<string | null>)
    | undefined;
  extracted_isin?:
    | /**
     * ISIN extracted from file
     */
    ((string | null) | Array<string | null>)
    | undefined;
  extracted_name?:
    | /**
     * Name extracted from file
     */
    ((string | null) | Array<string | null>)
    | undefined;
  candidates?: /**
   * Possible asset matches from database (empty = not found)
   */
  Array<BRIMAssetCandidate> | undefined;
  selected_asset_id?:
    | /**
     * Auto-set if 1 candidate, else None (user must choose)
     */
    ((number | null) | Array<number | null>)
    | undefined;
};
type BRIMDuplicateMatch = {
  /**
   * ID of existing transaction in DB
   */
  existing_tx_id: number;
  /**
   * Transaction date
   */
  tx_date: string;
  tx_type: TransactionType;
  /**
   * Transaction quantity
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  tx_quantity: string;
  tx_cash_amount?:
    | /**
     * Cash amount if applicable
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  tx_cash_currency?:
    | /**
     * Cash currency if applicable
     */
    ((string | null) | Array<string | null>)
    | undefined;
  tx_description?:
    | /**
     * Transaction description
     */
    ((string | null) | Array<string | null>)
    | undefined;
  match_level: BRIMDuplicateLevel;
};
type TransactionType =
  /**
 * Unified transaction types for all asset and cash operations.

This enum represents all possible transaction types in the unified
transaction table. Each type has specific rules for quantity and amount signs.

== Asset transactions (quantity != 0) ==

- BUY: Purchase asset with cash
  Signs: quantity > 0, amount < 0
  Example: Buy 10 shares of AAPL for €1500

- SELL: Sell asset for cash
  Signs: quantity < 0, amount > 0
  Example: Sell 5 shares of MSFT for €1500

- TRANSFER: Asset transfer between brokers
  Signs: quantity +/-, amount = 0
  Requires: related_transaction_id (links to paired transfer)
  Example: Transfer 100 shares from Broker A to Broker B

- ADJUSTMENT: Manual asset quantity correction (splits, gifts, etc.)
  Signs: quantity +/-, amount = 0
  Optional: related_transaction_id
  Example: Stock split 2:1 adds 100 shares

== Cash-only transactions (quantity = 0) ==

- DIVIDEND: Dividend payment received
  Signs: quantity = 0, amount > 0
  Example: Receive €50 dividend from AAPL

- INTEREST: Interest payment received
  Signs: quantity = 0, amount > 0
  Example: Monthly interest from crowdfunding loan

- DEPOSIT: Add cash to broker account
  Signs: quantity = 0, amount > 0
  Example: Transfer €1000 to broker

- WITHDRAWAL: Remove cash from broker account
  Signs: quantity = 0, amount < 0
  Example: Withdraw €500 from broker

- FEE: Fee or commission payment
  Signs: quantity = 0, amount < 0
  Example: €5 custody fee

- TAX: Tax payment
  Signs: quantity = 0, amount < 0
  Example: €100 capital gains tax

- FX_CONVERSION: Currency exchange
  Signs: quantity = 0, amount +/-
  Requires: related_transaction_id (links to paired conversion)
  Example: Convert €1000 to $1090

Impact:
- TRANSFER and FX_CONVERSION require related_transaction_id
- Validation ensures sign rules are followed
- All calculations based on settlement date
 *
 * @enum BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE, TAX, TRANSFER, FX_CONVERSION, ADJUSTMENT
 */
  | "BUY"
  | "SELL"
  | "DIVIDEND"
  | "INTEREST"
  | "DEPOSIT"
  | "WITHDRAWAL"
  | "FEE"
  | "TAX"
  | "TRANSFER"
  | "FX_CONVERSION"
  | "ADJUSTMENT";
type BRIMDuplicateLevel =
  /**
 * Confidence level for duplicate detection (ascending order).

Levels (from lowest to highest confidence):
1. POSSIBLE: type + date + quantity + cash match, but asset not resolved
2. POSSIBLE_WITH_ASSET: POSSIBLE + asset auto-resolved (1 candidate)
3. LIKELY: POSSIBLE + identical non-empty description, but asset not resolved
4. LIKELY_WITH_ASSET: LIKELY + asset auto-resolved (practically certain duplicate)

The WITH_ASSET variants are more reliable because the asset was automatically
matched to a single candidate in the database.
 *
 * @enum possible, possible_with_asset, likely, likely_with_asset
 */
  "possible" | "possible_with_asset" | "likely" | "likely_with_asset";
type BRIMDuplicateReport = Partial<{
  /**
   * Row indices of unique (non-duplicate) transactions
   */
  tx_unique_indices: Array<number>;
  /**
   * Transactions that might be duplicates (POSSIBLE level)
   */
  tx_possible_duplicates: Array<BRIMTXDuplicateCandidate>;
  /**
   * Transactions very likely to be duplicates (LIKELY level)
   */
  tx_likely_duplicates: Array<BRIMTXDuplicateCandidate>;
}>;
type BRIMTXDuplicateCandidate = {
  /**
   * Row index in parsed transactions list
   */
  tx_row_index: number;
  tx_parsed: TXCreateItem_Output;
  tx_existing_matches?: /**
   * Existing transactions that match
   */
  Array<BRIMDuplicateMatch> | undefined;
};
type TXCreateItem_Output = {
  /**
   * Broker ID
   */
  broker_id: number;
  asset_id?:
    | /**
     * Asset ID. NULL for pure cash transactions
     */
    ((number | null) | Array<number | null>)
    | undefined;
  type: TransactionType;
  /**
   * Settlement date
   */
  date: string;
  quantity?: /**
   * Asset quantity delta (+ in, - out)
   *
   * @default "0"
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  string | undefined;
  cash?:
    | /**
     * Cash movement (code + amount). Required for cash operations.
     */
    ((Currency_Output | null) | Array<Currency_Output | null>)
    | undefined;
  link_uuid?:
    | /**
     * Temporary UUID to link paired transactions (TRANSFER, FX_CONVERSION)
     */
    (| /**
         * @maxLength 36
         */
        (string | null)
        | Array<
            /**
             * @maxLength 36
             */
            string | null
          >
      )
    | undefined;
  tags?:
    | /**
     * List of tags for filtering/grouping
     */
    ((Array<string> | null) | Array<Array<string> | null>)
    | undefined;
  description?:
    | /**
     * Transaction notes
     */
    (| /**
         * @maxLength 500
         */
        (string | null)
        | Array<
            /**
             * @maxLength 500
             */
            string | null
          >
      )
    | undefined;
  cost_basis_override?:
    | /**
     * Frozen cost basis for TRANSFER_IN. Overrides calculated cost basis.
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
};
type BRIMFileInfo = {
  /**
   * UUID identifier for the file
   */
  file_id: string;
  /**
   * Original filename from upload
   */
  filename: string;
  /**
   * File size in bytes
   *
   * @minimum 0
   */
  size_bytes: number;
  status: BRIMFileStatus;
  /**
   * UTC timestamp when uploaded
   */
  uploaded_at: string;
  processed_at?:
    | /**
     * UTC timestamp when processed
     */
    ((string | null) | Array<string | null>)
    | undefined;
  compatible_plugins?: /**
   * Plugin codes that can parse this file
   */
  Array<string> | undefined;
  error_message?:
    | /**
     * Error description if processing failed
     */
    ((string | null) | Array<string | null>)
    | undefined;
  uploaded_by_user_id?:
    | /**
     * ID of user who uploaded the file
     */
    ((number | null) | Array<number | null>)
    | undefined;
  target_broker_id?:
    | /**
     * ID of broker this file belongs to
     */
    ((number | null) | Array<number | null>)
    | undefined;
  last_parse_result?:
    | /**
     * Cached result from last successful parse
     */
    (({} | null) | Array<{} | null>)
    | undefined;
};
type BRIMFileStatus =
  /**
 * Status of an uploaded broker report file.

Flow: UPLOADED → PARSED (success) or FAILED (error)
After parsing, the file stays in PARSED. The actual transaction import
uses POST /transactions and doesn't change file status.
 *
 * @enum uploaded, parsed, failed
 */
  "uploaded" | "parsed" | "failed";
type BRIMParseResponse = {
  /**
   * UUID of the parsed file
   */
  file_id: string;
  /**
   * Plugin used for parsing
   */
  plugin_code: string;
  /**
   * Target broker ID
   */
  broker_id: number;
  transactions?: /**
   * Parsed transactions (may have fake asset IDs)
   */
  Array<TXCreateItem_Output> | undefined;
  asset_mappings?: /**
   * Fake asset ID → candidate real assets mapping
   */
  Array<BRIMAssetMapping> | undefined;
  duplicates?:
    | /**
     * Duplicate detection results
     */
    ((BRIMDuplicateReport | null) | Array<BRIMDuplicateReport | null>)
    | undefined;
  warnings?: /**
   * Parser warnings (skipped rows, ambiguous data, etc.)
   */
  Array<string> | undefined;
};
type BRSummary = {
  id: number;
  name: string;
  description?: ((string | null) | Array<string | null>) | undefined;
  portal_url?: ((string | null) | Array<string | null>) | undefined;
  icon_url?: ((string | null) | Array<string | null>) | undefined;
  default_import_plugin?: ((string | null) | Array<string | null>) | undefined;
  allow_cash_overdraft: boolean;
  allow_asset_shorting: boolean;
  is_active: boolean;
  opened_at?: ((string | null) | Array<string | null>) | undefined;
  created_at: string;
  updated_at: string;
  user_role?:
    | /**
     * Current user's role on this broker (OWNER/EDITOR/VIEWER)
     */
    ((string | null) | Array<string | null>)
    | undefined;
  user_share_percentage?:
    | /**
     * Current user's ownership percentage
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  cash_balances?: /**
   * Current cash balance per currency
   */
  Array<Currency_Output> | undefined;
  holdings?: /**
   * Current asset holdings with cost basis and market value
   */
  Array<BRAssetHolding> | undefined;
  total_value_base_currency?:
    | /**
     * Total portfolio value in base currency (cash + holdings)
     */
    ((Currency_Output | null) | Array<Currency_Output | null>)
    | undefined;
};
type CountryListResponse = {
  items?: /**
   * List of items
   */
  Array<CountryListItem> | undefined;
  /**
   * Language used for country names
   */
  language: string;
};
type CountryListItem = {
  /**
   * ISO-3166-A3 country code (e.g., USA, ITA)
   */
  iso3: string;
  /**
   * ISO-3166-A2 country code (e.g., US, IT)
   */
  iso2: string;
  /**
   * Country name in requested language
   */
  name: string;
  /**
   * Flag emoji (e.g., 🇺🇸, 🇮🇹)
   */
  flag_emoji: string;
};
type CurrencyListResponse = {
  items?: /**
   * List of items
   */
  Array<CurrencyListItem> | undefined;
  /**
   * Language used for currency names
   */
  language: string;
};
type CurrencyListItem = {
  /**
   * ISO 4217 currency code (e.g., USD, EUR)
   */
  code: string;
  /**
   * Currency name in requested language
   */
  name: string;
  /**
   * Currency symbol (e.g., $, €)
   */
  symbol: string;
  flag_emoji?: /**
   * Flag emoji of primary country using this currency (e.g., 🇺🇸, 🇪🇺, 🪙 for crypto)
   *
   * @default "🏳️"
   */
  string | undefined;
  country_codes?: /**
   * ISO-2 country codes using this currency (e.g., ['US', 'AS', 'EC'] for USD)
   */
  Array<string> | undefined;
  country_names?: /**
   * Localized country names using this currency (e.g., ['United States', 'American Samoa'] for USD in English)
   */
  Array<string> | undefined;
};
type ExportRequest = Partial<{
  format: ExportFormat;
  /**
   * @default ["all"]
   */
  scope: Array<ExportScope>;
  /**
   * @default false
   */
  include_price_history: boolean;
  broker_ids: (Array<number> | null) | Array<Array<number> | null>;
}>;
type ExportFormat =
  /**
   * Supported export formats.
   *
   * @enum json, csv, sqlite
   */
  "json" | "csv" | "sqlite";
type ExportScope =
  /**
   * What to include in export.
   *
   * @enum all, transactions, assets, brokers, settings
   */
  "all" | "transactions" | "assets" | "brokers" | "settings";
type FAAssetCreateItem = {
  /**
   * Human-readable asset name (must be unique)
   */
  display_name: string;
  /**
   * Asset currency (ISO 4217)
   *
   * @minLength 3
   * @maxLength 3
   */
  currency: string;
  asset_type?:
    | /**
     * Asset type (STOCK, ETF, BOND, CROWDFUND_LOAN, etc.)
     */
    ((AssetType | null) | Array<AssetType | null>)
    | undefined;
  icon_url?:
    | /**
     * URL to asset icon (local or remote)
     */
    ((string | null) | Array<string | null>)
    | undefined;
  classification_params?:
    | /**
     * Asset classification metadata
     */
    (| (FAClassificationParams_Input | null)
        | Array<FAClassificationParams_Input | null>
      )
    | undefined;
  identifier_isin?:
    | /**
     * ISIN code (12 chars)
     */
    (| /**
         * @maxLength 12
         */
        (string | null)
        | Array<
            /**
             * @maxLength 12
             */
            string | null
          >
      )
    | undefined;
  identifier_ticker?:
    | /**
     * Ticker symbol
     */
    (| /**
         * @maxLength 20
         */
        (string | null)
        | Array<
            /**
             * @maxLength 20
             */
            string | null
          >
      )
    | undefined;
  identifier_cusip?:
    | /**
     * CUSIP code (9 chars)
     */
    (| /**
         * @maxLength 9
         */
        (string | null)
        | Array<
            /**
             * @maxLength 9
             */
            string | null
          >
      )
    | undefined;
  identifier_sedol?:
    | /**
     * SEDOL code (7 chars)
     */
    (| /**
         * @maxLength 7
         */
        (string | null)
        | Array<
            /**
             * @maxLength 7
             */
            string | null
          >
      )
    | undefined;
  identifier_figi?:
    | /**
     * FIGI code (12 chars)
     */
    (| /**
         * @maxLength 12
         */
        (string | null)
        | Array<
            /**
             * @maxLength 12
             */
            string | null
          >
      )
    | undefined;
  identifier_uuid?:
    | /**
     * UUID for custom assets
     */
    (| /**
         * @maxLength 36
         */
        (string | null)
        | Array<
            /**
             * @maxLength 36
             */
            string | null
          >
      )
    | undefined;
  identifier_other?:
    | /**
     * Other identifier
     */
    (| /**
         * @maxLength 100
         */
        (string | null)
        | Array<
            /**
             * @maxLength 100
             */
            string | null
          >
      )
    | undefined;
};
type AssetType =
  /**
 * Asset type classification.

Usage: Categorize assets by their nature for reporting and analysis.

- STOCK: Individual company shares (e.g., Apple, Microsoft)
- ETF: Exchange Traded Fund (e.g., VWCE, SPY)
- BOND: Fixed income securities (government or corporate bonds)
- CRYPTO: Cryptocurrencies (e.g., Bitcoin, Ethereum)
- FUND: Mutual funds or investment funds
- HOLD: Assets without automatic market pricing (real estate, art, collectibles, unlisted companies)
- CROWDFUND_LOAN: Peer-to-peer lending or crowdfunding loans (e.g., Recrowd, Mintos)
- OTHER: Any other asset type not listed above

Impact:
- Affects default valuation_model:
  - CROWDFUND_LOAN -> SCHEDULED_YIELD
  - HOLD -> MANUAL
  - Others -> MARKET_PRICE
- Used for portfolio breakdown and allocation analysis
- May influence available data plugins (e.g., crypto uses different sources)
 *
 * @enum STOCK, ETF, BOND, CRYPTO, FUND, CROWDFUND_LOAN, HOLD, OTHER
 */
  | "STOCK"
  | "ETF"
  | "BOND"
  | "CRYPTO"
  | "FUND"
  | "CROWDFUND_LOAN"
  | "HOLD"
  | "OTHER";
type FAClassificationParams_Input = Partial<{
  short_description: (string | null) | Array<string | null>;
  geographic_area:
    | (FAGeographicArea_Input | null)
    | Array<FAGeographicArea_Input | null>;
  sector_area: (FASectorArea_Input | null) | Array<FASectorArea_Input | null>;
}>;
type FAGeographicArea_Input = {
  /**
   * Distribution weights (must sum to 1.0)
   */
  distribution: {};
};
type FASectorArea_Input = {
  /**
   * Distribution weights (must sum to 1.0)
   */
  distribution: {};
};
type FAAssetDelete = {
  /**
   * Asset ID
   */
  asset_id: number;
  /**
   * List of date ranges to delete
   */
  date_ranges: Array<DateRangeModel>;
};
type DateRangeModel = {
  /**
   * Start date (inclusive)
   */
  start: string;
  end?:
    | /**
     * End date (inclusive, optional = single day)
     */
    ((string | null) | Array<string | null>)
    | undefined;
};
type FAAssetMetadataResponse = {
  asset_id: number;
  display_name: string;
  currency: string;
  icon_url?: ((string | null) | Array<string | null>) | undefined;
  asset_type?: ((string | null) | Array<string | null>) | undefined;
  classification_params?:
    | (
        | (FAClassificationParams_Output | null)
        | Array<FAClassificationParams_Output | null>
      )
    | undefined;
  has_provider?: /**
   * @default false
   */
  boolean | undefined;
};
type FAClassificationParams_Output = Partial<{
  short_description: (string | null) | Array<string | null>;
  geographic_area:
    | (FAGeographicArea_Output | null)
    | Array<FAGeographicArea_Output | null>;
  sector_area: (FASectorArea_Output | null) | Array<FASectorArea_Output | null>;
}>;
type FAGeographicArea_Output = {
  /**
   * Distribution weights (must sum to 1.0)
   */
  distribution: {};
};
type FASectorArea_Output = {
  /**
   * Distribution weights (must sum to 1.0)
   */
  distribution: {};
};
type FAAssetPatchItem = {
  /**
   * Asset ID to update
   */
  asset_id: number;
  display_name?:
    | /**
     * Update display name
     */
    ((string | null) | Array<string | null>)
    | undefined;
  currency?:
    | /**
     * Update currency (ISO 4217)
     */
    (| /**
         * @minLength 3
         * @maxLength 3
         */
        (string | null)
        | Array<
            /**
             * @minLength 3
             * @maxLength 3
             */
            string | null
          >
      )
    | undefined;
  asset_type?:
    | /**
     * Update asset type (STOCK, ETF, BOND, etc.)
     */
    ((AssetType | null) | Array<AssetType | null>)
    | undefined;
  icon_url?:
    | /**
     * Update icon URL (None = clear)
     */
    ((string | null) | Array<string | null>)
    | undefined;
  classification_params?:
    | /**
     * Update classification (None = clear)
     */
    (| (FAClassificationParams_Input | null)
        | Array<FAClassificationParams_Input | null>
      )
    | undefined;
  active?:
    | /**
     * Update active status
     */
    ((boolean | null) | Array<boolean | null>)
    | undefined;
  identifier_isin?:
    | /**
     * Update ISIN code
     */
    (| /**
         * @maxLength 12
         */
        (string | null)
        | Array<
            /**
             * @maxLength 12
             */
            string | null
          >
      )
    | undefined;
  identifier_ticker?:
    | /**
     * Update ticker symbol
     */
    (| /**
         * @maxLength 20
         */
        (string | null)
        | Array<
            /**
             * @maxLength 20
             */
            string | null
          >
      )
    | undefined;
  identifier_cusip?:
    | /**
     * Update CUSIP code
     */
    (| /**
         * @maxLength 9
         */
        (string | null)
        | Array<
            /**
             * @maxLength 9
             */
            string | null
          >
      )
    | undefined;
  identifier_sedol?:
    | /**
     * Update SEDOL code
     */
    (| /**
         * @maxLength 7
         */
        (string | null)
        | Array<
            /**
             * @maxLength 7
             */
            string | null
          >
      )
    | undefined;
  identifier_figi?:
    | /**
     * Update FIGI code
     */
    (| /**
         * @maxLength 12
         */
        (string | null)
        | Array<
            /**
             * @maxLength 12
             */
            string | null
          >
      )
    | undefined;
  identifier_uuid?:
    | /**
     * Update UUID
     */
    (| /**
         * @maxLength 36
         */
        (string | null)
        | Array<
            /**
             * @maxLength 36
             */
            string | null
          >
      )
    | undefined;
  identifier_other?:
    | /**
     * Update other identifier
     */
    (| /**
         * @maxLength 100
         */
        (string | null)
        | Array<
            /**
             * @maxLength 100
             */
            string | null
          >
      )
    | undefined;
};
type FAAssetPatchResult = {
  /**
   * Asset ID
   */
  asset_id: number;
  /**
   * Whether patch succeeded
   */
  success: boolean;
  /**
   * Success message or error description
   */
  message: string;
  updated_fields?:
    | /**
     * List of fields updated: [{info: field, old: old_value, new: new_value}]
     */
    (| (Array<OldNew_Union_str__NoneType__> | null)
        | Array<Array<OldNew_Union_str__NoneType__> | null>
      )
    | undefined;
};
type OldNew_Union_str__NoneType__ = {
  info?:
    | /**
     * Info message/Field name
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Old value
   */
  old: (string | null) | Array<string | null>;
  /**
   * New value
   */
  new: (string | null) | Array<string | null>;
};
type FABulkAssetCreateResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAAssetCreateResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FAAssetCreateResult = {
  asset_id?:
    | /**
     * Created asset ID (null if failed)
     */
    ((number | null) | Array<number | null>)
    | undefined;
  /**
   * Whether creation succeeded
   */
  success: boolean;
  /**
   * Success message or error description
   */
  message: string;
  /**
   * Asset display name (for identification)
   */
  display_name: string;
};
type FABulkAssetDeleteResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAAssetDeleteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FAAssetDeleteResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Asset ID
   */
  asset_id: number;
};
type FABulkAssetPatchResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAAssetPatchResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FABulkAssignResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAProviderAssignmentResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FAProviderAssignmentResult = {
  asset_id: number;
  success: boolean;
  message: string;
  fields_detail?:
    | /**
     * Field-level refresh details (for refresh operations)
     */
    (| (FAProviderRefreshFieldsDetail | null)
        | Array<FAProviderRefreshFieldsDetail | null>
      )
    | undefined;
};
type FAProviderRefreshFieldsDetail = {
  /**
   * Fields updated with old→new values. Old is None if first time set, new is None if field cleared.
   */
  refreshed_fields: Array<OldNew_Union_str__NoneType__>;
  /**
   * Fields provider couldn't fetch (no data available)
   */
  missing_data_fields: Array<string>;
  /**
   * Fields ignored (not requested when using field selection)
   */
  ignored_fields: Array<string>;
};
type FABulkDeleteResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAPriceDeleteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  /**
   * Total number of records deleted across all items
   *
   * @minimum 0
   */
  total_deleted: number;
};
type FAPriceDeleteResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Asset ID
   */
  asset_id: number;
};
type FABulkMetadataRefreshResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAMetadataRefreshResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FAMetadataRefreshResult = {
  asset_id: number;
  success: boolean;
  message: string;
  fields_detail?:
    | /**
     * Details of refreshed fields with old/new values
     */
    (| (FAProviderRefreshFieldsDetail | null)
        | Array<FAProviderRefreshFieldsDetail | null>
      )
    | undefined;
  warnings?: ((Array<string> | null) | Array<Array<string> | null>) | undefined;
};
type FABulkRefreshResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FARefreshResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FARefreshResult = {
  asset_id: number;
  /**
   * Number of prices fetched from provider
   */
  fetched_count: number;
  /**
   * Number of prices inserted into DB
   */
  inserted_count: number;
  /**
   * Number of prices updated in DB
   */
  updated_count: number;
  errors?: Array<string> | undefined;
};
type FABulkRemoveResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAProviderRemovalResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FAProviderRemovalResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Asset ID
   */
  asset_id: number;
};
type FABulkUpsertResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FAUpsertResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  /**
   * Number of prices inserted
   */
  inserted_count: number;
  /**
   * Number of prices updated
   */
  updated_count: number;
};
type FAUpsertResult = {
  asset_id: number;
  count: number;
  message: string;
};
type FAPricePoint_Input = {
  /**
   * Price date
   */
  date: string;
  open?:
    | /**
     * Opening price
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
  high?:
    | /**
     * High price
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
  low?:
    | /**
     * Low price
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
  /**
   * Closing price (required)
   */
  close:
    | (
        | number
        /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        | string
      )
    | Array<
        | number
        /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        | string
      >;
  volume?:
    | /**
     * Trading volume
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
  /**
   * Currency code (ISO 4217)
   */
  currency: string;
  backward_fill_info?:
    | /**
     * Backward-fill info (only in query results)
     */
    ((BackwardFillInfo | null) | Array<BackwardFillInfo | null>)
    | undefined;
};
type BackwardFillInfo = {
  /**
   * ISO date of actual data used (YYYY-MM-DD)
   */
  actual_rate_date: string;
  /**
   * Number of days back from requested date
   */
  days_back: number;
};
type FAPricePoint_Output = {
  /**
   * Price date
   */
  date: string;
  open?:
    | /**
     * Opening price
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  high?:
    | /**
     * High price
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  low?:
    | /**
     * Low price
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  /**
   * Closing price (required)
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  close: string;
  volume?:
    | /**
     * Trading volume
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  /**
   * Currency code (ISO 4217)
   */
  currency: string;
  backward_fill_info?:
    | /**
     * Backward-fill info (only in query results)
     */
    ((BackwardFillInfo | null) | Array<BackwardFillInfo | null>)
    | undefined;
};
type FAProviderAssignmentItem = {
  /**
   * Asset ID
   */
  asset_id: number;
  /**
   * Provider code (yfinance, cssscraper, scheduled_investment, etc.)
   */
  provider_code: string;
  /**
   * Asset identifier for this provider (ticker, ISIN, UUID, URL, etc.)
   */
  identifier: string;
  identifier_type: IdentifierType;
  provider_params?:
    | /**
     * Provider-specific configuration (JSON)
     */
    (({} | null) | Array<{} | null>)
    | undefined;
  fetch_interval?: /**
   * Refresh frequency in minutes (default: 1440 = 24h)
   *
   * @default 1440
   */
  number | undefined;
};
type IdentifierType =
  /**
 * Asset identifier type.

Usage: Specify which type of identifier is stored in the 'identifier' field.

- ISIN: International Securities Identification Number (e.g., US0378331005 for Apple)
- TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
- CUSIP: Committee on Uniform Securities Identification Procedures (US/Canada)
- SEDOL: Stock Exchange Daily Official List (UK)
- FIGI: Financial Instrument Global Identifier (Bloomberg standard)
- UUID: Universal Unique Identifier (for custom/synthetic assets)
- OTHER: Any other identifier type not listed above

Impact: Used for data validation and plugin selection. Some plugins may only
work with specific identifier types (e.g., Yahoo Finance prefers TICKER).

⚠️  DEPENDENT SCHEMAS - If you add/remove values, update these files:

1. DATABASE SCHEMA:
   - backend/alembic/versions/001_initial.py
     → Add column: identifier_{value.lower()} in assets table
     → Add index if frequently searched (ISIN, TICKER have indexes)

2. SQLMODEL (this file):
   - Asset class below
     → Add field: identifier_{value.lower()}: Optional[str]
     → Add validator if needed (e.g., ISIN requires 12 chars)

3. PYDANTIC SCHEMAS (backend/app/schemas/assets.py):
   - FAAssetCreateItem: Add identifier_{value.lower()} field
   - FAAssetPatchItem: Add identifier_{value.lower()} field
   - FAinfoResponse: Add identifier_{value.lower()} field
   - FAAinfoFiltersRequest: Add filter field (exact or partial match)

4. SERVICE LAYER (backend/app/services/asset_source.py):
   - list_assets(): Add condition for new filter
   - create_assets_bulk(): Pass new field to Asset()

5. BRIM PROVIDER (backend/app/services/brim_provider.py):
   - search_asset_candidates(): Add search priority if relevant

6. TESTS:
   - test_identifier_columns_match_enum() will FAIL automatically
     if Asset.identifier_{value.lower()} is missing

Run: pytest backend/test_scripts/test_db/db_schema_validate.py::test_identifier_columns_match_enum -v
 *
 * @enum ISIN, TICKER, CUSIP, SEDOL, FIGI, UUID, OTHER
 */
  "ISIN" | "TICKER" | "CUSIP" | "SEDOL" | "FIGI" | "UUID" | "OTHER";
type FAProviderAssignmentReadItem = {
  /**
   * Asset ID
   */
  asset_id: number;
  /**
   * Provider code
   */
  provider_code: string;
  /**
   * Asset identifier for provider
   */
  identifier: string;
  identifier_type: IdentifierType;
  provider_params?:
    | /**
     * Provider configuration
     */
    (({} | null) | Array<{} | null>)
    | undefined;
  fetch_interval?:
    | /**
     * Refresh frequency in minutes
     */
    ((number | null) | Array<number | null>)
    | undefined;
  last_fetch_at?:
    | /**
     * Last fetch timestamp (ISO format)
     */
    ((string | null) | Array<string | null>)
    | undefined;
};
type FAProviderSearchResponse = {
  /**
   * Original search query
   */
  query: string;
  /**
   * Total number of results across all providers
   */
  total_results: number;
  /**
   * Search results
   */
  results: Array<FAProviderSearchResultItem>;
  /**
   * Provider codes that were queried
   */
  providers_queried: Array<string>;
  providers_with_errors?: /**
   * Providers that returned errors
   */
  Array<string> | undefined;
};
type FAProviderSearchResultItem = {
  /**
   * Asset identifier (ISIN, ticker, URL, etc.)
   */
  identifier: string;
  identifier_type: IdentifierType;
  /**
   * Human-readable asset name
   */
  display_name: string;
  /**
   * Provider that returned this result
   */
  provider_code: string;
  currency?:
    | /**
     * Asset currency if known
     */
    ((string | null) | Array<string | null>)
    | undefined;
  asset_type?:
    | /**
     * Asset type (ETF, stock, bond, etc.)
     */
    ((string | null) | Array<string | null>)
    | undefined;
};
type FARefreshItem = {
  /**
   * Asset ID
   */
  asset_id: number;
  date_range: DateRangeModel;
};
type FAUpsert = {
  /**
   * Asset ID
   */
  asset_id: number;
  /**
   * List of price points
   */
  prices: Array<FAPricePoint_Input>;
};
type FAinfoResponse = {
  /**
   * Asset ID
   */
  id: number;
  /**
   * Asset display name
   */
  display_name: string;
  /**
   * Asset currency
   */
  currency: string;
  icon_url?:
    | /**
     * Asset icon URL
     */
    ((string | null) | Array<string | null>)
    | undefined;
  asset_type?:
    | /**
     * Asset type
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Whether asset is active
   */
  active: boolean;
  /**
   * Whether asset has a provider assigned
   */
  has_provider: boolean;
  /**
   * Whether asset has classification metadata
   */
  has_metadata: boolean;
  identifier_isin?:
    | /**
     * ISIN code
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_ticker?:
    | /**
     * Ticker symbol
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_cusip?:
    | /**
     * CUSIP code
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_sedol?:
    | /**
     * SEDOL code
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_figi?:
    | /**
     * FIGI code
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_uuid?:
    | /**
     * UUID for custom assets
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_other?:
    | /**
     * Other identifier
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier?:
    | /**
     * Primary identifier (from provider assignment)
     */
    ((string | null) | Array<string | null>)
    | undefined;
  identifier_type?:
    | /**
     * Primary identifier type
     */
    ((IdentifierType | null) | Array<IdentifierType | null>)
    | undefined;
};
type FXBulkDeleteResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FXDeleteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  /**
   * Total number of records deleted across all items
   *
   * @minimum 0
   */
  total_deleted: number;
};
type FXDeleteResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Base currency (normalized)
   */
  base: string;
  /**
   * Quote currency (normalized)
   */
  quote: string;
  date_range: DateRangeModel;
  /**
   * Number of rates present before deletion
   */
  existing_count: number;
};
type FXBulkUpsertResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FXUpsertResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FXUpsertResult = {
  /**
   * Whether the operation was successful
   */
  success: boolean;
  /**
   * Action taken: 'inserted' or 'updated'
   */
  action: string;
  /**
   * The rate value stored
   *
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  rate: string;
  /**
   * Date of the rate (ISO format)
   */
  date: string;
  /**
   * Base currency
   */
  base: string;
  /**
   * Quote currency
   */
  quote: string;
};
type FXConversionRequest = {
  from_amount: Currency_Input;
  /**
   * Target currency (ISO 4217)
   *
   * @minLength 3
   * @maxLength 3
   */
  to: string;
  date_range: DateRangeModel;
};
type FXConversionResult = {
  from_amount: Currency_Output;
  to_amount: Currency_Output;
  /**
   * Date requested for conversion (ISO format)
   */
  conversion_date: string;
  rate?:
    | /**
     * Exchange rate used (if not identity)
     */
    (| /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  backward_fill_info?:
    | /**
     * Backward-fill info (only present if rate from a different date was used). If null, rate_date = conversion_date
     */
    ((BackwardFillInfo | null) | Array<BackwardFillInfo | null>)
    | undefined;
};
type FXConversionRouteItem = {
  /**
   * @minLength 3
   * @maxLength 3
   */
  base: string;
  /**
   * @minLength 3
   * @maxLength 3
   */
  quote: string;
  /**
   * @minimum 1
   */
  priority: number;
  /**
   * Ordered list of conversion steps (edges of the graph)
   */
  chain_steps: Array<FXRouteStep>;
};
type FXRouteStep = {
  /**
   * @minLength 3
   * @maxLength 3
   */
  from: string;
  /**
   * @minLength 3
   * @maxLength 3
   */
  to: string;
  /**
   * Provider code for this step
   */
  provider: string;
};
type FXConversionRouteResult = {
  /**
   * Whether the operation succeeded
   */
  success: boolean;
  /**
   * Base currency
   */
  base: string;
  /**
   * Quote currency
   */
  quote: string;
  /**
   * Priority level
   */
  priority: number;
  /**
   * Chain steps configured
   */
  chain_steps: Array<FXRouteStep>;
  /**
   * Action taken: 'created' or 'updated'
   */
  action: string;
  message?:
    | /**
     * Additional info/warning
     */
    ((string | null) | Array<string | null>)
    | undefined;
};
type FXConversionRoutesResponse = Partial<{
  /**
   * List of items
   */
  items: Array<FXConversionRouteItem>;
}>;
type FXConvertResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FXConversionResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type FXCreateRoutesResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FXConversionRouteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  error_count?: /**
   * Number of failed operations
   *
   * @default 0
   */
  number | undefined;
};
type FXDeleteItem = {
  /**
   * Source currency (ISO 4217)
   *
   * @minLength 3
   * @maxLength 3
   */
  from: string;
  /**
   * Target currency (ISO 4217)
   *
   * @minLength 3
   * @maxLength 3
   */
  to: string;
  date_range?:
    | /**
     * Date range to delete (start required, end optional for single day). Required unless delete_all=True.
     */
    ((DateRangeModel | null) | Array<DateRangeModel | null>)
    | undefined;
  delete_all?: /**
   * If True, delete ALL rates for this pair (ignores date_range)
   *
   * @default false
   */
  boolean | undefined;
};
type FXDeleteRoutesResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FXDeleteRouteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  /**
   * Total number of records deleted across all items
   *
   * @minimum 0
   */
  total_deleted: number;
};
type FXDeleteRouteResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Base currency
   */
  base: string;
  /**
   * Quote currency
   */
  quote: string;
  priority?:
    | /**
     * Priority level (if specified)
     */
    ((number | null) | Array<number | null>)
    | undefined;
};
type FXSyncBulkResponse = {
  /**
   * Per-item operation results
   */
  results: Array<FXSyncPairResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  date_range: DateRangeModel;
  total_points_changed?: /**
   * Sum of points_changed across all pairs
   *
   * @default 0
   * @minimum 0
   */
  number | undefined;
};
type FXSyncPairResult = {
  /**
   * Normalized pair slug, e.g. 'EUR-USD'
   */
  pair: string;
  status: FXSyncStatus;
  provider_used?:
    | /**
     * Provider code that served data (None if failed/skipped)
     */
    ((string | null) | Array<string | null>)
    | undefined;
  points_fetched?: /**
   * Number of rate points fetched from provider
   *
   * @default 0
   * @minimum 0
   */
  number | undefined;
  points_changed?: /**
   * Number of rate points actually inserted/updated in DB
   *
   * @default 0
   * @minimum 0
   */
  number | undefined;
  message?:
    | /**
     * Optional note (e.g. 'monthly data only', 'fallback used')
     */
    ((string | null) | Array<string | null>)
    | undefined;
  elapsed_ms?:
    | /**
     * Backend sync time for this pair in integer milliseconds. Measured from bulk start (Phase 1) to commit completion, via time.monotonic_ns() with integer division (// 1_000_000). None for SKIPPED/MANUAL pairs.
     */
    (| /**
         * @minimum 0
         */
        (number | null)
        | Array<
            /**
             * @minimum 0
             */
            number | null
          >
      )
    | undefined;
};
type FXSyncStatus =
  /**
   * Status of a single pair sync operation.
   *
   * @enum ok, partial, failed, skipped
   */
  "ok" | "partial" | "failed" | "skipped";
type GlobalSettingsListResponse = Partial<{
  /**
   * List of items
   */
  items: Array<GlobalSettingRead>;
}>;
type GlobalSettingRead = {
  /**
   * Setting key
   */
  key: string;
  /**
   * Setting value (as string)
   */
  value: string;
  /**
   * Value type: string, int, bool, json
   */
  value_type: string;
  description?:
    | /**
     * Human-readable description
     */
    ((string | null) | Array<string | null>)
    | undefined;
  updated_at?:
    | /**
     * Last update timestamp
     */
    ((string | null) | Array<string | null>)
    | undefined;
  updated_by?:
    | /**
     * User ID who last updated
     */
    ((number | null) | Array<number | null>)
    | undefined;
};
type HTTPValidationError = Partial<{
  detail: Array<ValidationError>;
}>;
type ValidationError = {
  loc: Array<(string | number) | Array<string | number>>;
  msg: string;
  type: string;
};
type SystemInfoResponse = {
  app_version: string;
  python_version: string;
  os_name: string;
  os_version: string;
  platform: string;
  backend_dependencies: Array<DependencyInfo>;
  frontend_dependencies: Array<DependencyInfo>;
};
type DependencyInfo = {
  name: string;
  version: string;
};
type TXBulkCreateResponse = {
  /**
   * Per-item operation results
   */
  results: Array<TXCreateResultItem>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type TXCreateResultItem = {
  success: boolean;
  transaction_id?: ((number | null) | Array<number | null>) | undefined;
  link_uuid?: ((string | null) | Array<string | null>) | undefined;
  error?: ((string | null) | Array<string | null>) | undefined;
};
type TXBulkDeleteResponse = {
  /**
   * Per-item operation results
   */
  results: Array<TXDeleteResult>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
  /**
   * Total number of records deleted across all items
   *
   * @minimum 0
   */
  total_deleted: number;
};
type TXDeleteResult = {
  /**
   * Whether the deletion succeeded
   */
  success: boolean;
  /**
   * Number of items deleted
   *
   * @minimum 0
   */
  deleted_count: number;
  message?:
    | /**
     * Info/warning/error message
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * Transaction ID
   */
  id: number;
};
type TXBulkUpdateResponse = {
  /**
   * Per-item operation results
   */
  results: Array<TXUpdateResultItem>;
  /**
   * Number of successful operations
   *
   * @minimum 0
   */
  success_count: number;
  errors?: /**
   * Operation-level errors (not per-item)
   */
  Array<string> | undefined;
};
type TXUpdateResultItem = {
  id: number;
  success: boolean;
  error?: ((string | null) | Array<string | null>) | undefined;
};
type TXCreateItem_Input = {
  /**
   * Broker ID
   */
  broker_id: number;
  asset_id?:
    | /**
     * Asset ID. NULL for pure cash transactions
     */
    ((number | null) | Array<number | null>)
    | undefined;
  type: TransactionType;
  /**
   * Settlement date
   */
  date: string;
  quantity?:
    | /**
     * Asset quantity delta (+ in, - out)
     *
     * @default "0"
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
          >
      )
    | undefined;
  cash?:
    | /**
     * Cash movement (code + amount). Required for cash operations.
     */
    ((Currency_Input | null) | Array<Currency_Input | null>)
    | undefined;
  link_uuid?:
    | /**
     * Temporary UUID to link paired transactions (TRANSFER, FX_CONVERSION)
     */
    (| /**
         * @maxLength 36
         */
        (string | null)
        | Array<
            /**
             * @maxLength 36
             */
            string | null
          >
      )
    | undefined;
  tags?:
    | /**
     * List of tags for filtering/grouping
     */
    ((Array<string> | null) | Array<Array<string> | null>)
    | undefined;
  description?:
    | /**
     * Transaction notes
     */
    (| /**
         * @maxLength 500
         */
        (string | null)
        | Array<
            /**
             * @maxLength 500
             */
            string | null
          >
      )
    | undefined;
  cost_basis_override?:
    | /**
     * Frozen cost basis for TRANSFER_IN. Overrides calculated cost basis.
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
};
type TXReadItem = {
  id: number;
  broker_id: number;
  asset_id?: ((number | null) | Array<number | null>) | undefined;
  type: TransactionType;
  date: string;
  /**
   * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
   */
  quantity: string;
  cash?: ((Currency_Output | null) | Array<Currency_Output | null>) | undefined;
  related_transaction_id?: ((number | null) | Array<number | null>) | undefined;
  tags?: ((Array<string> | null) | Array<Array<string> | null>) | undefined;
  description?: ((string | null) | Array<string | null>) | undefined;
  cost_basis_override?:
    | (
        | /**
         * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
         */
        (string | null)
        | Array<
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            string | null
          >
      )
    | undefined;
  created_at: string;
  updated_at: string;
};
type TXUpdateItem = {
  /**
   * Transaction ID to update
   */
  id: number;
  date?:
    | /**
     * New settlement date
     */
    ((string | null) | Array<string | null>)
    | undefined;
  quantity?:
    | /**
     * New quantity
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
  cash?:
    | /**
     * New cash (code + amount)
     */
    ((Currency_Input | null) | Array<Currency_Input | null>)
    | undefined;
  tags?:
    | /**
     * New tags (replaces existing)
     */
    ((Array<string> | null) | Array<Array<string> | null>)
    | undefined;
  description?:
    | /**
     * New description
     */
    (| /**
         * @maxLength 500
         */
        (string | null)
        | Array<
            /**
             * @maxLength 500
             */
            string | null
          >
      )
    | undefined;
  cost_basis_override?:
    | /**
     * Frozen cost basis for TRANSFER_IN. Set to override calculated cost basis.
     */
    (| (
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          )
        | Array<
            | number
            /**
             * @pattern ^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$
             */
            | string
            | null
          >
      )
    | undefined;
};
type UpdateProfileResponse = {
  user: AuthUserResponse;
  message?: /**
   * @default "Profile updated successfully"
   */
  string | undefined;
};
type UploadListResponse = Partial<{
  /**
   * List of items
   */
  items: Array<UploadFileInfo>;
}>;
type UploadFileInfo = {
  /**
   * Unique file ID (UUID)
   */
  id: string;
  /**
   * Original filename
   */
  original_name: string;
  /**
   * MIME type of the file
   */
  mime_type: string;
  /**
   * File size in bytes
   */
  size_bytes: number;
  /**
   * Upload timestamp (UTC)
   */
  uploaded_at: string;
  /**
   * ID of user who uploaded the file
   */
  uploaded_by_user_id: number;
  description?:
    | /**
     * User-provided description
     */
    ((string | null) | Array<string | null>)
    | undefined;
  /**
   * URL to access the file
   */
  url: string;
};
type UploadResponse = {
  success?: /**
   * @default true
   */
  boolean | undefined;
  file: UploadFileInfo;
  message?: /**
   * @default "File uploaded successfully"
   */
  string | undefined;
};
type UserSearchResponse = Partial<{
  /**
   * List of items
   */
  items: Array<UserSearchItem>;
}>;
type UserSearchItem = {
  /**
   * User ID
   */
  id: number;
  /**
   * Username
   */
  username: string;
  avatar_url?:
    | /**
     * User avatar URL
     */
    ((string | null) | Array<string | null>)
    | undefined;
};

const AuthLoginRequest = z
  .object({
    username: z.string().min(1).describe("Username or email"),
    password: z.string().min(1).describe("Password"),
  })
  .passthrough();
const AuthUserResponse: z.ZodType<AuthUserResponse> = z
  .object({
    id: z.number().int(),
    username: z.string(),
    email: z.string(),
    is_active: z.boolean(),
    is_superuser: z.boolean(),
    created_at: z.string(),
  })
  .passthrough();
const UserSettingsRead: z.ZodType<UserSettingsRead> = z
  .object({
    language: z.string().describe("Preferred language (en, it, fr, es)"),
    base_currency: z.string().describe("Base currency for display (ISO 4217)"),
    theme: z.enum(["light", "dark", "auto"]).describe("UI theme"),
    avatar_url: z
      .union([z.string(), z.null()])
      .describe("URL to user avatar image")
      .optional(),
  })
  .passthrough();
const AuthLoginResponse: z.ZodType<AuthLoginResponse> = z
  .object({
    user: AuthUserResponse.describe(
      "User info returned after login or from /me endpoint."
    ),
    user_settings: z.union([UserSettingsRead, z.null()]).optional(),
    message: z.string().optional().default("Login successful"),
  })
  .passthrough();
const ValidationError: z.ZodType<ValidationError> = z
  .object({
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
    type: z.string(),
  })
  .passthrough();
const HTTPValidationError: z.ZodType<HTTPValidationError> = z
  .object({ detail: z.array(ValidationError) })
  .partial()
  .passthrough();
const AuthLogoutResponse = z
  .object({ message: z.string().default("Logged out successfully") })
  .partial()
  .passthrough();
const AuthMeResponse: z.ZodType<AuthMeResponse> = z
  .object({
    user: AuthUserResponse.describe(
      "User info returned after login or from /me endpoint."
    ),
  })
  .passthrough();
const AuthRegisterRequest = z
  .object({
    username: z.string().min(3).max(50).describe("Username"),
    email: z.string().email().describe("Email address"),
    password: z.string().min(8).describe("Password (min 8 chars)"),
  })
  .passthrough();
const AuthRegisterResponse: z.ZodType<AuthRegisterResponse> = z
  .object({
    user: AuthUserResponse.describe(
      "User info returned after login or from /me endpoint."
    ),
    message: z.string().optional().default("Registration successful"),
  })
  .passthrough();
const ChangePasswordRequest = z
  .object({
    current_password: z.string().min(1).describe("Current password"),
    new_password: z.string().min(8).describe("New password (min 8 chars)"),
  })
  .passthrough();
const ChangePasswordResponse = z
  .object({ message: z.string().default("Password changed successfully") })
  .partial()
  .passthrough();
const UpdateProfileRequest = z
  .object({
    username: z.union([z.string(), z.null()]).describe("New username"),
    email: z.union([z.string(), z.null()]).describe("New email address"),
  })
  .partial()
  .passthrough();
const UpdateProfileResponse: z.ZodType<UpdateProfileResponse> = z
  .object({
    user: AuthUserResponse.describe(
      "User info returned after login or from /me endpoint."
    ),
    message: z.string().optional().default("Profile updated successfully"),
  })
  .passthrough();
const UserSettingsUpdate = z
  .object({
    language: z.union([z.string(), z.null()]),
    base_currency: z.union([z.string(), z.null()]),
    theme: z.union([z.enum(["light", "dark", "auto"]), z.null()]),
    avatar_url: z
      .union([z.string(), z.null()])
      .describe("URL to user avatar image"),
  })
  .partial()
  .passthrough();
const GlobalSettingRead: z.ZodType<GlobalSettingRead> = z
  .object({
    key: z.string().describe("Setting key"),
    value: z.string().describe("Setting value (as string)"),
    value_type: z.string().describe("Value type: string, int, bool, json"),
    description: z
      .union([z.string(), z.null()])
      .describe("Human-readable description")
      .optional(),
    updated_at: z
      .union([z.string(), z.null()])
      .describe("Last update timestamp")
      .optional(),
    updated_by: z
      .union([z.number(), z.null()])
      .describe("User ID who last updated")
      .optional(),
  })
  .passthrough();
const GlobalSettingsListResponse: z.ZodType<GlobalSettingsListResponse> = z
  .object({ items: z.array(GlobalSettingRead).describe("List of items") })
  .partial();
const GlobalSettingUpdate = z
  .object({ value: z.string().describe("New value (as string)") })
  .passthrough();
const DependencyInfo: z.ZodType<DependencyInfo> = z
  .object({ name: z.string(), version: z.string() })
  .passthrough();
const SystemInfoResponse: z.ZodType<SystemInfoResponse> = z
  .object({
    app_version: z.string(),
    python_version: z.string(),
    os_name: z.string(),
    os_version: z.string(),
    platform: z.string(),
    backend_dependencies: z.array(DependencyInfo),
    frontend_dependencies: z.array(DependencyInfo),
  })
  .passthrough();
const Body_upload_file_api_v1_uploads_post = z
  .object({
    file: z.instanceof(File),
    description: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const UploadFileInfo: z.ZodType<UploadFileInfo> = z.object({
  id: z.string().describe("Unique file ID (UUID)"),
  original_name: z.string().describe("Original filename"),
  mime_type: z.string().describe("MIME type of the file"),
  size_bytes: z.number().int().describe("File size in bytes"),
  uploaded_at: z.string().describe("Upload timestamp (UTC)"),
  uploaded_by_user_id: z
    .number()
    .int()
    .describe("ID of user who uploaded the file"),
  description: z
    .union([z.string(), z.null()])
    .describe("User-provided description")
    .optional(),
  url: z.string().describe("URL to access the file"),
});
const UploadResponse: z.ZodType<UploadResponse> = z
  .object({
    success: z.boolean().optional().default(true),
    file: UploadFileInfo.describe("Information about an uploaded file."),
    message: z.string().optional().default("File uploaded successfully"),
  })
  .passthrough();
const UploadListResponse: z.ZodType<UploadListResponse> = z
  .object({ items: z.array(UploadFileInfo).describe("List of items") })
  .partial();
const UploadDeleteResponse = z
  .object({ success: z.boolean(), message: z.string(), file_id: z.string() })
  .passthrough();
const offset = z.union([z.number(), z.null()]).optional();
const img_preview = z.union([z.string(), z.null()]).optional();
const exclude_broker_id = z
  .union([z.number(), z.null()])
  .describe("Exclude users already on this broker")
  .optional();
const UserSearchItem: z.ZodType<UserSearchItem> = z.object({
  id: z.number().int().describe("User ID"),
  username: z.string().describe("Username"),
  avatar_url: z
    .union([z.string(), z.null()])
    .describe("User avatar URL")
    .optional(),
});
const UserSearchResponse: z.ZodType<UserSearchResponse> = z
  .object({ items: z.array(UserSearchItem).describe("List of items") })
  .partial();
const providers = z
  .union([z.array(z.string()), z.null()])
  .describe(
    "Optional list of provider codes to filter. If empty, returns all providers."
  )
  .optional();
const FXProviderInfo = z
  .object({
    code: z.string().describe("Provider code (e.g., ECB, FED, BOE, SNB)"),
    name: z.string().describe("Provider full name"),
    base_currency: z.string().describe("Default base currency"),
    base_currencies: z
      .array(z.string())
      .describe("All supported base currencies"),
    target_currencies: z
      .array(z.string())
      .describe(
        "All target currencies this provider can convert to (from get_supported_currencies)"
      )
      .optional(),
    description: z.string().describe("Provider description"),
    description_i18n: z
      .record(z.string())
      .describe("Multilingual provider descriptions {lang_code: description}")
      .optional(),
    icon_url: z
      .union([z.string(), z.null()])
      .describe("Provider icon URL (hardcoded)")
      .optional(),
    docs_url: z
      .union([z.string(), z.null()])
      .describe("URL to documentation page for this provider")
      .optional(),
  })
  .passthrough();
const FXRouteStep: z.ZodType<FXRouteStep> = z
  .object({
    from: z.string().min(3).max(3),
    to: z.string().min(3).max(3),
    provider: z.string().describe("Provider code for this step"),
  })
  .passthrough();
const FXConversionRouteItem: z.ZodType<FXConversionRouteItem> = z
  .object({
    base: z.string().min(3).max(3),
    quote: z.string().min(3).max(3),
    priority: z.number().int().gte(1),
    chain_steps: z
      .array(FXRouteStep)
      .min(1)
      .describe("Ordered list of conversion steps (edges of the graph)"),
  })
  .passthrough();
const FXConversionRoutesResponse: z.ZodType<FXConversionRoutesResponse> = z
  .object({ items: z.array(FXConversionRouteItem).describe("List of items") })
  .partial();
const FXConversionRouteResult: z.ZodType<FXConversionRouteResult> = z
  .object({
    success: z.boolean().describe("Whether the operation succeeded"),
    base: z.string().describe("Base currency"),
    quote: z.string().describe("Quote currency"),
    priority: z.number().int().describe("Priority level"),
    chain_steps: z.array(FXRouteStep).describe("Chain steps configured"),
    action: z.string().describe("Action taken: 'created' or 'updated'"),
    message: z
      .union([z.string(), z.null()])
      .describe("Additional info/warning")
      .optional(),
  })
  .passthrough();
const FXCreateRoutesResponse: z.ZodType<FXCreateRoutesResponse> = z.object({
  results: z
    .array(FXConversionRouteResult)
    .describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  error_count: z
    .number()
    .int()
    .describe("Number of failed operations")
    .optional()
    .default(0),
});
const FXDeleteRouteItem = z
  .object({
    base: z.string().min(3).max(3).describe("Base currency (ISO 4217)"),
    quote: z.string().min(3).max(3).describe("Quote currency (ISO 4217)"),
    priority: z
      .union([z.number(), z.null()])
      .describe(
        "Priority level (optional, if not provided deletes all priorities)"
      )
      .optional(),
  })
  .passthrough();
const FXDeleteRouteResult: z.ZodType<FXDeleteRouteResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  base: z.string().describe("Base currency"),
  quote: z.string().describe("Quote currency"),
  priority: z
    .union([z.number(), z.null()])
    .describe("Priority level (if specified)")
    .optional(),
});
const FXDeleteRoutesResponse: z.ZodType<FXDeleteRoutesResponse> = z.object({
  results: z.array(FXDeleteRouteResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  total_deleted: z
    .number()
    .int()
    .gte(0)
    .describe("Total number of records deleted across all items"),
});
const FXSyncPairRequest = z.object({
  pairs: z
    .array(z.string())
    .min(1)
    .describe("Pair slugs, e.g. ['EUR-USD', 'CHF-CNY']"),
  start: z.string().describe("Start date (inclusive)"),
  end: z.string().describe("End date (inclusive)"),
});
const FXSyncStatus = z.enum(["ok", "partial", "failed", "skipped"]);
const FXSyncPairResult: z.ZodType<FXSyncPairResult> = z.object({
  pair: z.string().describe("Normalized pair slug, e.g. 'EUR-USD'"),
  status: FXSyncStatus.describe("Status of a single pair sync operation."),
  provider_used: z
    .union([z.string(), z.null()])
    .describe("Provider code that served data (None if failed/skipped)")
    .optional(),
  points_fetched: z
    .number()
    .int()
    .gte(0)
    .describe("Number of rate points fetched from provider")
    .optional()
    .default(0),
  points_changed: z
    .number()
    .int()
    .gte(0)
    .describe("Number of rate points actually inserted/updated in DB")
    .optional()
    .default(0),
  message: z
    .union([z.string(), z.null()])
    .describe("Optional note (e.g. 'monthly data only', 'fallback used')")
    .optional(),
  elapsed_ms: z
    .union([z.number(), z.null()])
    .describe(
      "Backend sync time for this pair in integer milliseconds. Measured from bulk start (Phase 1) to commit completion, via time.monotonic_ns() with integer division (// 1_000_000). None for SKIPPED/MANUAL pairs."
    )
    .optional(),
});
const DateRangeModel: z.ZodType<DateRangeModel> = z.object({
  start: z.string().describe("Start date (inclusive)"),
  end: z
    .union([z.string(), z.null()])
    .describe("End date (inclusive, optional = single day)")
    .optional(),
});
const FXSyncBulkResponse: z.ZodType<FXSyncBulkResponse> = z.object({
  results: z.array(FXSyncPairResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  date_range:
    DateRangeModel.describe(`Reusable date range model for FA and FX operations.

Used across multiple operations: price deletion, FX rate queries, etc.
Represents an inclusive date range [start, end].

Attributes:
    start: Start date (inclusive, required)
    end: End date (inclusive, optional - defaults to start for single day)

Design Notes:
    - If end is None, represents a single day (start only)
    - If end is provided, represents a range [start, end] inclusive
    - Validator ensures end >= start when provided

Examples:
    # Single day
    {"start": "2025-11-05", "end": null}  # Just 2025-11-05

    # Range
    {"start": "2025-11-01", "end": "2025-11-30"}  # Entire November`),
  total_points_changed: z
    .number()
    .int()
    .gte(0)
    .describe("Sum of points_changed across all pairs")
    .optional()
    .default(0),
});
const FXUpsertItem = z
  .object({
    date: z.string().describe("Date of the rate (ISO format)"),
    base: z.string().min(3).max(3).describe("Base currency (ISO 4217)"),
    quote: z.string().min(3).max(3).describe("Quote currency (ISO 4217)"),
    rate: z
      .union([z.number(), z.string()])
      .describe("Exchange rate (must be positive)"),
    source: z
      .string()
      .describe("Source of the rate")
      .optional()
      .default("MANUAL"),
  })
  .passthrough();
const FXUpsertResult: z.ZodType<FXUpsertResult> = z
  .object({
    success: z.boolean().describe("Whether the operation was successful"),
    action: z.string().describe("Action taken: 'inserted' or 'updated'"),
    rate: z
      .string()
      .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
      .describe("The rate value stored"),
    date: z.string().describe("Date of the rate (ISO format)"),
    base: z.string().describe("Base currency"),
    quote: z.string().describe("Quote currency"),
  })
  .passthrough();
const FXBulkUpsertResponse: z.ZodType<FXBulkUpsertResponse> = z.object({
  results: z.array(FXUpsertResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const FXDeleteItem: z.ZodType<FXDeleteItem> = z
  .object({
    from: z.string().min(3).max(3).describe("Source currency (ISO 4217)"),
    to: z.string().min(3).max(3).describe("Target currency (ISO 4217)"),
    date_range: z
      .union([DateRangeModel, z.null()])
      .describe(
        "Date range to delete (start required, end optional for single day). Required unless delete_all=True."
      )
      .optional(),
    delete_all: z
      .boolean()
      .describe("If True, delete ALL rates for this pair (ignores date_range)")
      .optional()
      .default(false),
  })
  .passthrough();
const FXDeleteResult: z.ZodType<FXDeleteResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  base: z.string().describe("Base currency (normalized)"),
  quote: z.string().describe("Quote currency (normalized)"),
  date_range:
    DateRangeModel.describe(`Reusable date range model for FA and FX operations.

Used across multiple operations: price deletion, FX rate queries, etc.
Represents an inclusive date range [start, end].

Attributes:
    start: Start date (inclusive, required)
    end: End date (inclusive, optional - defaults to start for single day)

Design Notes:
    - If end is None, represents a single day (start only)
    - If end is provided, represents a range [start, end] inclusive
    - Validator ensures end >= start when provided

Examples:
    # Single day
    {"start": "2025-11-05", "end": null}  # Just 2025-11-05

    # Range
    {"start": "2025-11-01", "end": "2025-11-30"}  # Entire November`),
  existing_count: z
    .number()
    .int()
    .describe("Number of rates present before deletion"),
});
const FXBulkDeleteResponse: z.ZodType<FXBulkDeleteResponse> = z.object({
  results: z.array(FXDeleteResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  total_deleted: z
    .number()
    .int()
    .gte(0)
    .describe("Total number of records deleted across all items"),
});
const Currency_Input: z.ZodType<Currency_Input> = z.object({
  code: z.string().describe("ISO 4217 currency code or crypto symbol"),
  amount: z
    .union([z.number(), z.string()])
    .describe("Amount (can be negative)"),
});
const FXConversionRequest: z.ZodType<FXConversionRequest> = z
  .object({
    from_amount:
      Currency_Input.describe(`Currency amount with validation and arithmetic operations.

Validates currency codes against ISO 4217 (via pycountry) + crypto dict.
Supports addition/subtraction only between same currencies.
Amount can be negative.

Attributes:
    code: ISO 4217 currency code (USD, EUR) or crypto symbol (BTC, ETH)
    amount: Decimal amount (can be negative)

Examples:
    >>> usd = Currency(code="USD", amount=Decimal("100.50"))
    >>> fee = Currency(code="USD", amount=Decimal("2.50"))
    >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))

    >>> eur = Currency(code="EUR", amount=Decimal("50"))
    >>> usd + eur  # ValueError: Cannot add USD and EUR

    >>> btc = Currency(code="BTC", amount=Decimal("0.5"))  # Valid crypto

    >>> negative = -usd  # Currency(code="USD", amount=Decimal("-100.50"))

Raises:
    ValueError: If currency code is not valid ISO 4217 or supported crypto`),
    to: z.string().min(3).max(3).describe("Target currency (ISO 4217)"),
    date_range:
      DateRangeModel.describe(`Reusable date range model for FA and FX operations.

Used across multiple operations: price deletion, FX rate queries, etc.
Represents an inclusive date range [start, end].

Attributes:
    start: Start date (inclusive, required)
    end: End date (inclusive, optional - defaults to start for single day)

Design Notes:
    - If end is None, represents a single day (start only)
    - If end is provided, represents a range [start, end] inclusive
    - Validator ensures end >= start when provided

Examples:
    # Single day
    {"start": "2025-11-05", "end": null}  # Just 2025-11-05

    # Range
    {"start": "2025-11-01", "end": "2025-11-30"}  # Entire November`),
  })
  .passthrough();
const Currency_Output: z.ZodType<Currency_Output> = z.object({
  code: z.string().describe("ISO 4217 currency code or crypto symbol"),
  amount: z
    .string()
    .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
    .describe("Amount (can be negative)"),
});
const BackwardFillInfo: z.ZodType<BackwardFillInfo> = z
  .object({
    actual_rate_date: z
      .string()
      .describe("ISO date of actual data used (YYYY-MM-DD)"),
    days_back: z
      .number()
      .int()
      .describe("Number of days back from requested date"),
  })
  .passthrough();
const FXConversionResult: z.ZodType<FXConversionResult> = z
  .object({
    from_amount:
      Currency_Output.describe(`Currency amount with validation and arithmetic operations.

Validates currency codes against ISO 4217 (via pycountry) + crypto dict.
Supports addition/subtraction only between same currencies.
Amount can be negative.

Attributes:
    code: ISO 4217 currency code (USD, EUR) or crypto symbol (BTC, ETH)
    amount: Decimal amount (can be negative)

Examples:
    >>> usd = Currency(code="USD", amount=Decimal("100.50"))
    >>> fee = Currency(code="USD", amount=Decimal("2.50"))
    >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))

    >>> eur = Currency(code="EUR", amount=Decimal("50"))
    >>> usd + eur  # ValueError: Cannot add USD and EUR

    >>> btc = Currency(code="BTC", amount=Decimal("0.5"))  # Valid crypto

    >>> negative = -usd  # Currency(code="USD", amount=Decimal("-100.50"))

Raises:
    ValueError: If currency code is not valid ISO 4217 or supported crypto`),
    to_amount:
      Currency_Output.describe(`Currency amount with validation and arithmetic operations.

Validates currency codes against ISO 4217 (via pycountry) + crypto dict.
Supports addition/subtraction only between same currencies.
Amount can be negative.

Attributes:
    code: ISO 4217 currency code (USD, EUR) or crypto symbol (BTC, ETH)
    amount: Decimal amount (can be negative)

Examples:
    >>> usd = Currency(code="USD", amount=Decimal("100.50"))
    >>> fee = Currency(code="USD", amount=Decimal("2.50"))
    >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))

    >>> eur = Currency(code="EUR", amount=Decimal("50"))
    >>> usd + eur  # ValueError: Cannot add USD and EUR

    >>> btc = Currency(code="BTC", amount=Decimal("0.5"))  # Valid crypto

    >>> negative = -usd  # Currency(code="USD", amount=Decimal("-100.50"))

Raises:
    ValueError: If currency code is not valid ISO 4217 or supported crypto`),
    conversion_date: z
      .string()
      .describe("Date requested for conversion (ISO format)"),
    rate: z
      .union([z.string(), z.null()])
      .describe("Exchange rate used (if not identity)")
      .optional(),
    backward_fill_info: z
      .union([BackwardFillInfo, z.null()])
      .describe(
        "Backward-fill info (only present if rate from a different date was used). If null, rate_date = conversion_date"
      )
      .optional(),
  })
  .passthrough();
const FXConvertResponse: z.ZodType<FXConvertResponse> = z.object({
  results: z.array(FXConversionResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const AssetType = z.enum([
  "STOCK",
  "ETF",
  "BOND",
  "CRYPTO",
  "FUND",
  "CROWDFUND_LOAN",
  "HOLD",
  "OTHER",
]);
const FAGeographicArea_Input: z.ZodType<FAGeographicArea_Input> = z.object({
  distribution: z
    .record(z.union([z.number(), z.string()]))
    .describe("Distribution weights (must sum to 1.0)"),
});
const FASectorArea_Input: z.ZodType<FASectorArea_Input> = z.object({
  distribution: z
    .record(z.union([z.number(), z.string()]))
    .describe("Distribution weights (must sum to 1.0)"),
});
const FAClassificationParams_Input: z.ZodType<FAClassificationParams_Input> = z
  .object({
    short_description: z.union([z.string(), z.null()]),
    geographic_area: z.union([FAGeographicArea_Input, z.null()]),
    sector_area: z.union([FASectorArea_Input, z.null()]),
  })
  .partial();
const FAAssetCreateItem: z.ZodType<FAAssetCreateItem> = z.object({
  display_name: z
    .string()
    .describe("Human-readable asset name (must be unique)"),
  currency: z.string().min(3).max(3).describe("Asset currency (ISO 4217)"),
  asset_type: z
    .union([AssetType, z.null()])
    .describe("Asset type (STOCK, ETF, BOND, CROWDFUND_LOAN, etc.)")
    .optional(),
  icon_url: z
    .union([z.string(), z.null()])
    .describe("URL to asset icon (local or remote)")
    .optional(),
  classification_params: z
    .union([FAClassificationParams_Input, z.null()])
    .describe("Asset classification metadata")
    .optional(),
  identifier_isin: z
    .union([z.string(), z.null()])
    .describe("ISIN code (12 chars)")
    .optional(),
  identifier_ticker: z
    .union([z.string(), z.null()])
    .describe("Ticker symbol")
    .optional(),
  identifier_cusip: z
    .union([z.string(), z.null()])
    .describe("CUSIP code (9 chars)")
    .optional(),
  identifier_sedol: z
    .union([z.string(), z.null()])
    .describe("SEDOL code (7 chars)")
    .optional(),
  identifier_figi: z
    .union([z.string(), z.null()])
    .describe("FIGI code (12 chars)")
    .optional(),
  identifier_uuid: z
    .union([z.string(), z.null()])
    .describe("UUID for custom assets")
    .optional(),
  identifier_other: z
    .union([z.string(), z.null()])
    .describe("Other identifier")
    .optional(),
});
const FAAssetCreateResult: z.ZodType<FAAssetCreateResult> = z.object({
  asset_id: z
    .union([z.number(), z.null()])
    .describe("Created asset ID (null if failed)")
    .optional(),
  success: z.boolean().describe("Whether creation succeeded"),
  message: z.string().describe("Success message or error description"),
  display_name: z.string().describe("Asset display name (for identification)"),
});
const FABulkAssetCreateResponse: z.ZodType<FABulkAssetCreateResponse> =
  z.object({
    results: z
      .array(FAAssetCreateResult)
      .describe("Per-item operation results"),
    success_count: z
      .number()
      .int()
      .gte(0)
      .describe("Number of successful operations"),
    errors: z
      .array(z.string())
      .describe("Operation-level errors (not per-item)")
      .optional(),
  });
const FAAssetPatchItem: z.ZodType<FAAssetPatchItem> = z.object({
  asset_id: z.number().int().describe("Asset ID to update"),
  display_name: z
    .union([z.string(), z.null()])
    .describe("Update display name")
    .optional(),
  currency: z
    .union([z.string(), z.null()])
    .describe("Update currency (ISO 4217)")
    .optional(),
  asset_type: z
    .union([AssetType, z.null()])
    .describe("Update asset type (STOCK, ETF, BOND, etc.)")
    .optional(),
  icon_url: z
    .union([z.string(), z.null()])
    .describe("Update icon URL (None = clear)")
    .optional(),
  classification_params: z
    .union([FAClassificationParams_Input, z.null()])
    .describe("Update classification (None = clear)")
    .optional(),
  active: z
    .union([z.boolean(), z.null()])
    .describe("Update active status")
    .optional(),
  identifier_isin: z
    .union([z.string(), z.null()])
    .describe("Update ISIN code")
    .optional(),
  identifier_ticker: z
    .union([z.string(), z.null()])
    .describe("Update ticker symbol")
    .optional(),
  identifier_cusip: z
    .union([z.string(), z.null()])
    .describe("Update CUSIP code")
    .optional(),
  identifier_sedol: z
    .union([z.string(), z.null()])
    .describe("Update SEDOL code")
    .optional(),
  identifier_figi: z
    .union([z.string(), z.null()])
    .describe("Update FIGI code")
    .optional(),
  identifier_uuid: z
    .union([z.string(), z.null()])
    .describe("Update UUID")
    .optional(),
  identifier_other: z
    .union([z.string(), z.null()])
    .describe("Update other identifier")
    .optional(),
});
const OldNew_Union_str__NoneType__: z.ZodType<OldNew_Union_str__NoneType__> =
  z.object({
    info: z
      .union([z.string(), z.null()])
      .describe("Info message/Field name")
      .optional(),
    old: z.union([z.string(), z.null()]).describe("Old value"),
    new: z.union([z.string(), z.null()]).describe("New value"),
  });
const FAAssetPatchResult: z.ZodType<FAAssetPatchResult> = z.object({
  asset_id: z.number().int().describe("Asset ID"),
  success: z.boolean().describe("Whether patch succeeded"),
  message: z.string().describe("Success message or error description"),
  updated_fields: z
    .union([z.array(OldNew_Union_str__NoneType__), z.null()])
    .describe(
      "List of fields updated: [{info: field, old: old_value, new: new_value}]"
    )
    .optional(),
});
const FABulkAssetPatchResponse: z.ZodType<FABulkAssetPatchResponse> = z.object({
  results: z.array(FAAssetPatchResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const FAAssetDeleteResult: z.ZodType<FAAssetDeleteResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  asset_id: z.number().int().describe("Asset ID"),
});
const FABulkAssetDeleteResponse: z.ZodType<FABulkAssetDeleteResponse> =
  z.object({
    results: z
      .array(FAAssetDeleteResult)
      .describe("Per-item operation results"),
    success_count: z
      .number()
      .int()
      .gte(0)
      .describe("Number of successful operations"),
    errors: z
      .array(z.string())
      .describe("Operation-level errors (not per-item)")
      .optional(),
  });
const FAGeographicArea_Output: z.ZodType<FAGeographicArea_Output> = z.object({
  distribution: z
    .record(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/))
    .describe("Distribution weights (must sum to 1.0)"),
});
const FASectorArea_Output: z.ZodType<FASectorArea_Output> = z.object({
  distribution: z
    .record(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/))
    .describe("Distribution weights (must sum to 1.0)"),
});
const FAClassificationParams_Output: z.ZodType<FAClassificationParams_Output> =
  z
    .object({
      short_description: z.union([z.string(), z.null()]),
      geographic_area: z.union([FAGeographicArea_Output, z.null()]),
      sector_area: z.union([FASectorArea_Output, z.null()]),
    })
    .partial();
const FAAssetMetadataResponse: z.ZodType<FAAssetMetadataResponse> = z.object({
  asset_id: z.number().int(),
  display_name: z.string(),
  currency: z.string(),
  icon_url: z.union([z.string(), z.null()]).optional(),
  asset_type: z.union([z.string(), z.null()]).optional(),
  classification_params: z
    .union([FAClassificationParams_Output, z.null()])
    .optional(),
  has_provider: z.boolean().optional().default(false),
});
const IdentifierType = z.enum([
  "ISIN",
  "TICKER",
  "CUSIP",
  "SEDOL",
  "FIGI",
  "UUID",
  "OTHER",
]);
const FAinfoResponse: z.ZodType<FAinfoResponse> = z.object({
  id: z.number().int().describe("Asset ID"),
  display_name: z.string().describe("Asset display name"),
  currency: z.string().describe("Asset currency"),
  icon_url: z
    .union([z.string(), z.null()])
    .describe("Asset icon URL")
    .optional(),
  asset_type: z.union([z.string(), z.null()]).describe("Asset type").optional(),
  active: z.boolean().describe("Whether asset is active"),
  has_provider: z.boolean().describe("Whether asset has a provider assigned"),
  has_metadata: z
    .boolean()
    .describe("Whether asset has classification metadata"),
  identifier_isin: z
    .union([z.string(), z.null()])
    .describe("ISIN code")
    .optional(),
  identifier_ticker: z
    .union([z.string(), z.null()])
    .describe("Ticker symbol")
    .optional(),
  identifier_cusip: z
    .union([z.string(), z.null()])
    .describe("CUSIP code")
    .optional(),
  identifier_sedol: z
    .union([z.string(), z.null()])
    .describe("SEDOL code")
    .optional(),
  identifier_figi: z
    .union([z.string(), z.null()])
    .describe("FIGI code")
    .optional(),
  identifier_uuid: z
    .union([z.string(), z.null()])
    .describe("UUID for custom assets")
    .optional(),
  identifier_other: z
    .union([z.string(), z.null()])
    .describe("Other identifier")
    .optional(),
  identifier: z
    .union([z.string(), z.null()])
    .describe("Primary identifier (from provider assignment)")
    .optional(),
  identifier_type: z
    .union([IdentifierType, z.null()])
    .describe("Primary identifier type")
    .optional(),
});
const currency = z
  .union([z.string(), z.null()])
  .describe("Filter by currency (ISO 4217, e.g., USD)")
  .optional();
const asset_type = z
  .union([AssetType, z.null()])
  .describe("Filter by asset type enum")
  .optional();
const search = z
  .union([z.string(), z.null()])
  .describe("Search in display_name (partial match)")
  .optional();
const isin = z
  .union([z.string(), z.null()])
  .describe("Exact ISIN match")
  .optional();
const ticker = z
  .union([z.string(), z.null()])
  .describe("Exact ticker match")
  .optional();
const cusip = z
  .union([z.string(), z.null()])
  .describe("Exact CUSIP match")
  .optional();
const sedol = z
  .union([z.string(), z.null()])
  .describe("Exact SEDOL match")
  .optional();
const figi = z
  .union([z.string(), z.null()])
  .describe("Exact FIGI match")
  .optional();
const uuid = z
  .union([z.string(), z.null()])
  .describe("Exact UUID match")
  .optional();
const identifier_other = z
  .union([z.string(), z.null()])
  .describe("Partial match in identifier_other")
  .optional();
const identifier_contains = z
  .union([z.string(), z.null()])
  .describe("Partial match in any identifier field")
  .optional();
const FAPricePoint_Input: z.ZodType<FAPricePoint_Input> = z.object({
  date: z.string().describe("Price date"),
  open: z
    .union([z.number(), z.string(), z.null()])
    .describe("Opening price")
    .optional(),
  high: z
    .union([z.number(), z.string(), z.null()])
    .describe("High price")
    .optional(),
  low: z
    .union([z.number(), z.string(), z.null()])
    .describe("Low price")
    .optional(),
  close: z.union([z.number(), z.string()]).describe("Closing price (required)"),
  volume: z
    .union([z.number(), z.string(), z.null()])
    .describe("Trading volume")
    .optional(),
  currency: z.string().describe("Currency code (ISO 4217)"),
  backward_fill_info: z
    .union([BackwardFillInfo, z.null()])
    .describe("Backward-fill info (only in query results)")
    .optional(),
});
const FAUpsert: z.ZodType<FAUpsert> = z.object({
  asset_id: z.number().int().describe("Asset ID"),
  prices: z.array(FAPricePoint_Input).min(1).describe("List of price points"),
});
const FAUpsertResult: z.ZodType<FAUpsertResult> = z.object({
  asset_id: z.number().int(),
  count: z.number().int(),
  message: z.string(),
});
const FABulkUpsertResponse: z.ZodType<FABulkUpsertResponse> = z.object({
  results: z.array(FAUpsertResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  inserted_count: z.number().int().describe("Number of prices inserted"),
  updated_count: z.number().int().describe("Number of prices updated"),
});
const FAAssetDelete: z.ZodType<FAAssetDelete> = z.object({
  asset_id: z.number().int().describe("Asset ID"),
  date_ranges: z
    .array(DateRangeModel)
    .min(1)
    .describe("List of date ranges to delete"),
});
const FAPriceDeleteResult: z.ZodType<FAPriceDeleteResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  asset_id: z.number().int().describe("Asset ID"),
});
const FABulkDeleteResponse: z.ZodType<FABulkDeleteResponse> = z.object({
  results: z.array(FAPriceDeleteResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  total_deleted: z
    .number()
    .int()
    .gte(0)
    .describe("Total number of records deleted across all items"),
});
const end_date = z
  .union([z.string(), z.null()])
  .describe("End date (optional, defaults to start_date)")
  .optional();
const FAPricePoint_Output: z.ZodType<FAPricePoint_Output> = z.object({
  date: z.string().describe("Price date"),
  open: z.union([z.string(), z.null()]).describe("Opening price").optional(),
  high: z.union([z.string(), z.null()]).describe("High price").optional(),
  low: z.union([z.string(), z.null()]).describe("Low price").optional(),
  close: z
    .string()
    .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
    .describe("Closing price (required)"),
  volume: z.union([z.string(), z.null()]).describe("Trading volume").optional(),
  currency: z.string().describe("Currency code (ISO 4217)"),
  backward_fill_info: z
    .union([BackwardFillInfo, z.null()])
    .describe("Backward-fill info (only in query results)")
    .optional(),
});
const FARefreshItem: z.ZodType<FARefreshItem> = z.object({
  asset_id: z.number().int().describe("Asset ID"),
  date_range:
    DateRangeModel.describe(`Reusable date range model for FA and FX operations.

Used across multiple operations: price deletion, FX rate queries, etc.
Represents an inclusive date range [start, end].

Attributes:
    start: Start date (inclusive, required)
    end: End date (inclusive, optional - defaults to start for single day)

Design Notes:
    - If end is None, represents a single day (start only)
    - If end is provided, represents a range [start, end] inclusive
    - Validator ensures end >= start when provided

Examples:
    # Single day
    {"start": "2025-11-05", "end": null}  # Just 2025-11-05

    # Range
    {"start": "2025-11-01", "end": "2025-11-30"}  # Entire November`),
});
const FARefreshResult: z.ZodType<FARefreshResult> = z.object({
  asset_id: z.number().int(),
  fetched_count: z
    .number()
    .int()
    .describe("Number of prices fetched from provider"),
  inserted_count: z
    .number()
    .int()
    .describe("Number of prices inserted into DB"),
  updated_count: z.number().int().describe("Number of prices updated in DB"),
  errors: z.array(z.string()).optional(),
});
const FABulkRefreshResponse: z.ZodType<FABulkRefreshResponse> = z.object({
  results: z.array(FARefreshResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const FAProviderInfo = z.object({
  code: z.string().describe("Provider code (e.g., yfinance, cssscraper)"),
  name: z.string().describe("Provider full name"),
  description: z.string().describe("Provider description"),
  icon_url: z
    .union([z.string(), z.null()])
    .describe("Provider icon URL (hardcoded)")
    .optional(),
  supports_search: z
    .boolean()
    .describe("Whether provider supports asset search"),
});
const FAProviderAssignmentItem: z.ZodType<FAProviderAssignmentItem> = z.object({
  asset_id: z.number().int().describe("Asset ID"),
  provider_code: z
    .string()
    .describe(
      "Provider code (yfinance, cssscraper, scheduled_investment, etc.)"
    ),
  identifier: z
    .string()
    .describe(
      "Asset identifier for this provider (ticker, ISIN, UUID, URL, etc.)"
    ),
  identifier_type: IdentifierType.describe(`Asset identifier type.

Usage: Specify which type of identifier is stored in the 'identifier' field.

- ISIN: International Securities Identification Number (e.g., US0378331005 for Apple)
- TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
- CUSIP: Committee on Uniform Securities Identification Procedures (US/Canada)
- SEDOL: Stock Exchange Daily Official List (UK)
- FIGI: Financial Instrument Global Identifier (Bloomberg standard)
- UUID: Universal Unique Identifier (for custom/synthetic assets)
- OTHER: Any other identifier type not listed above

Impact: Used for data validation and plugin selection. Some plugins may only
work with specific identifier types (e.g., Yahoo Finance prefers TICKER).

⚠️  DEPENDENT SCHEMAS - If you add/remove values, update these files:

1. DATABASE SCHEMA:
   - backend/alembic/versions/001_initial.py
     → Add column: identifier_{value.lower()} in assets table
     → Add index if frequently searched (ISIN, TICKER have indexes)

2. SQLMODEL (this file):
   - Asset class below
     → Add field: identifier_{value.lower()}: Optional[str]
     → Add validator if needed (e.g., ISIN requires 12 chars)

3. PYDANTIC SCHEMAS (backend/app/schemas/assets.py):
   - FAAssetCreateItem: Add identifier_{value.lower()} field
   - FAAssetPatchItem: Add identifier_{value.lower()} field
   - FAinfoResponse: Add identifier_{value.lower()} field
   - FAAinfoFiltersRequest: Add filter field (exact or partial match)

4. SERVICE LAYER (backend/app/services/asset_source.py):
   - list_assets(): Add condition for new filter
   - create_assets_bulk(): Pass new field to Asset()

5. BRIM PROVIDER (backend/app/services/brim_provider.py):
   - search_asset_candidates(): Add search priority if relevant

6. TESTS:
   - test_identifier_columns_match_enum() will FAIL automatically
     if Asset.identifier_{value.lower()} is missing

Run: pytest backend/test_scripts/test_db/db_schema_validate.py::test_identifier_columns_match_enum -v`),
  provider_params: z
    .union([z.object({}).partial().passthrough(), z.null()])
    .describe("Provider-specific configuration (JSON)")
    .optional(),
  fetch_interval: z
    .number()
    .int()
    .describe("Refresh frequency in minutes (default: 1440 = 24h)")
    .optional()
    .default(1440),
});
const FAProviderRefreshFieldsDetail: z.ZodType<FAProviderRefreshFieldsDetail> =
  z.object({
    refreshed_fields: z
      .array(OldNew_Union_str__NoneType__)
      .describe(
        "Fields updated with old→new values. Old is None if first time set, new is None if field cleared."
      ),
    missing_data_fields: z
      .array(z.string())
      .describe("Fields provider couldn't fetch (no data available)"),
    ignored_fields: z
      .array(z.string())
      .describe("Fields ignored (not requested when using field selection)"),
  });
const FAProviderAssignmentResult: z.ZodType<FAProviderAssignmentResult> =
  z.object({
    asset_id: z.number().int(),
    success: z.boolean(),
    message: z.string(),
    fields_detail: z
      .union([FAProviderRefreshFieldsDetail, z.null()])
      .describe("Field-level refresh details (for refresh operations)")
      .optional(),
  });
const FABulkAssignResponse: z.ZodType<FABulkAssignResponse> = z.object({
  results: z
    .array(FAProviderAssignmentResult)
    .describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const FAProviderRemovalResult: z.ZodType<FAProviderRemovalResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  asset_id: z.number().int().describe("Asset ID"),
});
const FABulkRemoveResponse: z.ZodType<FABulkRemoveResponse> = z.object({
  results: z
    .array(FAProviderRemovalResult)
    .describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const providers__2 = z
  .union([z.string(), z.null()])
  .describe("Comma-separated provider codes (default: all)")
  .optional();
const FAProviderSearchResultItem: z.ZodType<FAProviderSearchResultItem> =
  z.object({
    identifier: z
      .string()
      .describe("Asset identifier (ISIN, ticker, URL, etc.)"),
    identifier_type: IdentifierType.describe(`Asset identifier type.

Usage: Specify which type of identifier is stored in the 'identifier' field.

- ISIN: International Securities Identification Number (e.g., US0378331005 for Apple)
- TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
- CUSIP: Committee on Uniform Securities Identification Procedures (US/Canada)
- SEDOL: Stock Exchange Daily Official List (UK)
- FIGI: Financial Instrument Global Identifier (Bloomberg standard)
- UUID: Universal Unique Identifier (for custom/synthetic assets)
- OTHER: Any other identifier type not listed above

Impact: Used for data validation and plugin selection. Some plugins may only
work with specific identifier types (e.g., Yahoo Finance prefers TICKER).

⚠️  DEPENDENT SCHEMAS - If you add/remove values, update these files:

1. DATABASE SCHEMA:
   - backend/alembic/versions/001_initial.py
     → Add column: identifier_{value.lower()} in assets table
     → Add index if frequently searched (ISIN, TICKER have indexes)

2. SQLMODEL (this file):
   - Asset class below
     → Add field: identifier_{value.lower()}: Optional[str]
     → Add validator if needed (e.g., ISIN requires 12 chars)

3. PYDANTIC SCHEMAS (backend/app/schemas/assets.py):
   - FAAssetCreateItem: Add identifier_{value.lower()} field
   - FAAssetPatchItem: Add identifier_{value.lower()} field
   - FAinfoResponse: Add identifier_{value.lower()} field
   - FAAinfoFiltersRequest: Add filter field (exact or partial match)

4. SERVICE LAYER (backend/app/services/asset_source.py):
   - list_assets(): Add condition for new filter
   - create_assets_bulk(): Pass new field to Asset()

5. BRIM PROVIDER (backend/app/services/brim_provider.py):
   - search_asset_candidates(): Add search priority if relevant

6. TESTS:
   - test_identifier_columns_match_enum() will FAIL automatically
     if Asset.identifier_{value.lower()} is missing

Run: pytest backend/test_scripts/test_db/db_schema_validate.py::test_identifier_columns_match_enum -v`),
    display_name: z.string().describe("Human-readable asset name"),
    provider_code: z.string().describe("Provider that returned this result"),
    currency: z
      .union([z.string(), z.null()])
      .describe("Asset currency if known")
      .optional(),
    asset_type: z
      .union([z.string(), z.null()])
      .describe("Asset type (ETF, stock, bond, etc.)")
      .optional(),
  });
const FAProviderSearchResponse: z.ZodType<FAProviderSearchResponse> = z.object({
  query: z.string().describe("Original search query"),
  total_results: z
    .number()
    .int()
    .describe("Total number of results across all providers"),
  results: z.array(FAProviderSearchResultItem).describe("Search results"),
  providers_queried: z
    .array(z.string())
    .describe("Provider codes that were queried"),
  providers_with_errors: z
    .array(z.string())
    .describe("Providers that returned errors")
    .optional(),
});
const FAProviderAssignmentReadItem: z.ZodType<FAProviderAssignmentReadItem> =
  z.object({
    asset_id: z.number().int().describe("Asset ID"),
    provider_code: z.string().describe("Provider code"),
    identifier: z.string().describe("Asset identifier for provider"),
    identifier_type: IdentifierType.describe(`Asset identifier type.

Usage: Specify which type of identifier is stored in the 'identifier' field.

- ISIN: International Securities Identification Number (e.g., US0378331005 for Apple)
- TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
- CUSIP: Committee on Uniform Securities Identification Procedures (US/Canada)
- SEDOL: Stock Exchange Daily Official List (UK)
- FIGI: Financial Instrument Global Identifier (Bloomberg standard)
- UUID: Universal Unique Identifier (for custom/synthetic assets)
- OTHER: Any other identifier type not listed above

Impact: Used for data validation and plugin selection. Some plugins may only
work with specific identifier types (e.g., Yahoo Finance prefers TICKER).

⚠️  DEPENDENT SCHEMAS - If you add/remove values, update these files:

1. DATABASE SCHEMA:
   - backend/alembic/versions/001_initial.py
     → Add column: identifier_{value.lower()} in assets table
     → Add index if frequently searched (ISIN, TICKER have indexes)

2. SQLMODEL (this file):
   - Asset class below
     → Add field: identifier_{value.lower()}: Optional[str]
     → Add validator if needed (e.g., ISIN requires 12 chars)

3. PYDANTIC SCHEMAS (backend/app/schemas/assets.py):
   - FAAssetCreateItem: Add identifier_{value.lower()} field
   - FAAssetPatchItem: Add identifier_{value.lower()} field
   - FAinfoResponse: Add identifier_{value.lower()} field
   - FAAinfoFiltersRequest: Add filter field (exact or partial match)

4. SERVICE LAYER (backend/app/services/asset_source.py):
   - list_assets(): Add condition for new filter
   - create_assets_bulk(): Pass new field to Asset()

5. BRIM PROVIDER (backend/app/services/brim_provider.py):
   - search_asset_candidates(): Add search priority if relevant

6. TESTS:
   - test_identifier_columns_match_enum() will FAIL automatically
     if Asset.identifier_{value.lower()} is missing

Run: pytest backend/test_scripts/test_db/db_schema_validate.py::test_identifier_columns_match_enum -v`),
    provider_params: z
      .union([z.object({}).partial().passthrough(), z.null()])
      .describe("Provider configuration")
      .optional(),
    fetch_interval: z
      .union([z.number(), z.null()])
      .describe("Refresh frequency in minutes")
      .optional(),
    last_fetch_at: z
      .union([z.string(), z.null()])
      .describe("Last fetch timestamp (ISO format)")
      .optional(),
  });
const FAMetadataRefreshResult: z.ZodType<FAMetadataRefreshResult> = z.object({
  asset_id: z.number().int(),
  success: z.boolean(),
  message: z.string(),
  fields_detail: z
    .union([FAProviderRefreshFieldsDetail, z.null()])
    .describe("Details of refreshed fields with old/new values")
    .optional(),
  warnings: z.union([z.array(z.string()), z.null()]).optional(),
});
const FABulkMetadataRefreshResponse: z.ZodType<FABulkMetadataRefreshResponse> =
  z.object({
    results: z
      .array(FAMetadataRefreshResult)
      .describe("Per-item operation results"),
    success_count: z
      .number()
      .int()
      .gte(0)
      .describe("Number of successful operations"),
    errors: z
      .array(z.string())
      .describe("Operation-level errors (not per-item)")
      .optional(),
  });
const TransactionType = z.enum([
  "BUY",
  "SELL",
  "DIVIDEND",
  "INTEREST",
  "DEPOSIT",
  "WITHDRAWAL",
  "FEE",
  "TAX",
  "TRANSFER",
  "FX_CONVERSION",
  "ADJUSTMENT",
]);
const TXCreateItem_Input: z.ZodType<TXCreateItem_Input> = z.object({
  broker_id: z.number().int().gt(0).describe("Broker ID"),
  asset_id: z
    .union([z.number(), z.null()])
    .describe("Asset ID. NULL for pure cash transactions")
    .optional(),
  type: TransactionType.describe(`Unified transaction types for all asset and cash operations.

This enum represents all possible transaction types in the unified
transaction table. Each type has specific rules for quantity and amount signs.

== Asset transactions (quantity != 0) ==

- BUY: Purchase asset with cash
  Signs: quantity > 0, amount < 0
  Example: Buy 10 shares of AAPL for €1500

- SELL: Sell asset for cash
  Signs: quantity < 0, amount > 0
  Example: Sell 5 shares of MSFT for €1500

- TRANSFER: Asset transfer between brokers
  Signs: quantity +/-, amount = 0
  Requires: related_transaction_id (links to paired transfer)
  Example: Transfer 100 shares from Broker A to Broker B

- ADJUSTMENT: Manual asset quantity correction (splits, gifts, etc.)
  Signs: quantity +/-, amount = 0
  Optional: related_transaction_id
  Example: Stock split 2:1 adds 100 shares

== Cash-only transactions (quantity = 0) ==

- DIVIDEND: Dividend payment received
  Signs: quantity = 0, amount > 0
  Example: Receive €50 dividend from AAPL

- INTEREST: Interest payment received
  Signs: quantity = 0, amount > 0
  Example: Monthly interest from crowdfunding loan

- DEPOSIT: Add cash to broker account
  Signs: quantity = 0, amount > 0
  Example: Transfer €1000 to broker

- WITHDRAWAL: Remove cash from broker account
  Signs: quantity = 0, amount < 0
  Example: Withdraw €500 from broker

- FEE: Fee or commission payment
  Signs: quantity = 0, amount < 0
  Example: €5 custody fee

- TAX: Tax payment
  Signs: quantity = 0, amount < 0
  Example: €100 capital gains tax

- FX_CONVERSION: Currency exchange
  Signs: quantity = 0, amount +/-
  Requires: related_transaction_id (links to paired conversion)
  Example: Convert €1000 to $1090

Impact:
- TRANSFER and FX_CONVERSION require related_transaction_id
- Validation ensures sign rules are followed
- All calculations based on settlement date`),
  date: z.string().describe("Settlement date"),
  quantity: z
    .union([z.number(), z.string()])
    .describe("Asset quantity delta (+ in, - out)")
    .optional()
    .default("0"),
  cash: z
    .union([Currency_Input, z.null()])
    .describe("Cash movement (code + amount). Required for cash operations.")
    .optional(),
  link_uuid: z
    .union([z.string(), z.null()])
    .describe(
      "Temporary UUID to link paired transactions (TRANSFER, FX_CONVERSION)"
    )
    .optional(),
  tags: z
    .union([z.array(z.string()), z.null()])
    .describe("List of tags for filtering/grouping")
    .optional(),
  description: z
    .union([z.string(), z.null()])
    .describe("Transaction notes")
    .optional(),
  cost_basis_override: z
    .union([z.number(), z.string(), z.null()])
    .describe(
      "Frozen cost basis for TRANSFER_IN. Overrides calculated cost basis."
    )
    .optional(),
});
const TXCreateResultItem: z.ZodType<TXCreateResultItem> = z.object({
  success: z.boolean(),
  transaction_id: z.union([z.number(), z.null()]).optional(),
  link_uuid: z.union([z.string(), z.null()]).optional(),
  error: z.union([z.string(), z.null()]).optional(),
});
const TXBulkCreateResponse: z.ZodType<TXBulkCreateResponse> = z.object({
  results: z.array(TXCreateResultItem).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const broker_id = z
  .union([z.number(), z.null()])
  .describe("Filter by broker")
  .optional();
const asset_id = z
  .union([z.number(), z.null()])
  .describe("Filter by asset")
  .optional();
const types = z
  .union([z.array(TransactionType), z.null()])
  .describe("Filter by types")
  .optional();
const date_start = z
  .union([z.string(), z.null()])
  .describe("Start date (YYYY-MM-DD)")
  .optional();
const date_end = z
  .union([z.string(), z.null()])
  .describe("End date (YYYY-MM-DD)")
  .optional();
const tags = z
  .union([z.array(z.string()), z.null()])
  .describe("Filter by tags")
  .optional();
const currency__2 = z
  .union([z.string(), z.null()])
  .describe("Filter by currency")
  .optional();
const TXReadItem: z.ZodType<TXReadItem> = z.object({
  id: z.number().int(),
  broker_id: z.number().int(),
  asset_id: z.union([z.number(), z.null()]).optional(),
  type: TransactionType.describe(`Unified transaction types for all asset and cash operations.

This enum represents all possible transaction types in the unified
transaction table. Each type has specific rules for quantity and amount signs.

== Asset transactions (quantity != 0) ==

- BUY: Purchase asset with cash
  Signs: quantity > 0, amount < 0
  Example: Buy 10 shares of AAPL for €1500

- SELL: Sell asset for cash
  Signs: quantity < 0, amount > 0
  Example: Sell 5 shares of MSFT for €1500

- TRANSFER: Asset transfer between brokers
  Signs: quantity +/-, amount = 0
  Requires: related_transaction_id (links to paired transfer)
  Example: Transfer 100 shares from Broker A to Broker B

- ADJUSTMENT: Manual asset quantity correction (splits, gifts, etc.)
  Signs: quantity +/-, amount = 0
  Optional: related_transaction_id
  Example: Stock split 2:1 adds 100 shares

== Cash-only transactions (quantity = 0) ==

- DIVIDEND: Dividend payment received
  Signs: quantity = 0, amount > 0
  Example: Receive €50 dividend from AAPL

- INTEREST: Interest payment received
  Signs: quantity = 0, amount > 0
  Example: Monthly interest from crowdfunding loan

- DEPOSIT: Add cash to broker account
  Signs: quantity = 0, amount > 0
  Example: Transfer €1000 to broker

- WITHDRAWAL: Remove cash from broker account
  Signs: quantity = 0, amount < 0
  Example: Withdraw €500 from broker

- FEE: Fee or commission payment
  Signs: quantity = 0, amount < 0
  Example: €5 custody fee

- TAX: Tax payment
  Signs: quantity = 0, amount < 0
  Example: €100 capital gains tax

- FX_CONVERSION: Currency exchange
  Signs: quantity = 0, amount +/-
  Requires: related_transaction_id (links to paired conversion)
  Example: Convert €1000 to $1090

Impact:
- TRANSFER and FX_CONVERSION require related_transaction_id
- Validation ensures sign rules are followed
- All calculations based on settlement date`),
  date: z.string(),
  quantity: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  cash: z.union([Currency_Output, z.null()]).optional(),
  related_transaction_id: z.union([z.number(), z.null()]).optional(),
  tags: z.union([z.array(z.string()), z.null()]).optional(),
  description: z.union([z.string(), z.null()]).optional(),
  cost_basis_override: z.union([z.string(), z.null()]).optional(),
  created_at: z.string(),
  updated_at: z.string(),
});
const TXUpdateItem: z.ZodType<TXUpdateItem> = z.object({
  id: z.number().int().gt(0).describe("Transaction ID to update"),
  date: z
    .union([z.string(), z.null()])
    .describe("New settlement date")
    .optional(),
  quantity: z
    .union([z.number(), z.string(), z.null()])
    .describe("New quantity")
    .optional(),
  cash: z
    .union([Currency_Input, z.null()])
    .describe("New cash (code + amount)")
    .optional(),
  tags: z
    .union([z.array(z.string()), z.null()])
    .describe("New tags (replaces existing)")
    .optional(),
  description: z
    .union([z.string(), z.null()])
    .describe("New description")
    .optional(),
  cost_basis_override: z
    .union([z.number(), z.string(), z.null()])
    .describe(
      "Frozen cost basis for TRANSFER_IN. Set to override calculated cost basis."
    )
    .optional(),
});
const TXUpdateResultItem: z.ZodType<TXUpdateResultItem> = z.object({
  id: z.number().int(),
  success: z.boolean(),
  error: z.union([z.string(), z.null()]).optional(),
});
const TXBulkUpdateResponse: z.ZodType<TXBulkUpdateResponse> = z.object({
  results: z.array(TXUpdateResultItem).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const TXDeleteResult: z.ZodType<TXDeleteResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  id: z.number().int().describe("Transaction ID"),
});
const TXBulkDeleteResponse: z.ZodType<TXBulkDeleteResponse> = z.object({
  results: z.array(TXDeleteResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  total_deleted: z
    .number()
    .int()
    .gte(0)
    .describe("Total number of records deleted across all items"),
});
const TXTypeMetadata = z.object({
  code: z.string().describe("Enum code (e.g., 'BUY')"),
  name: z.string().describe("Display name"),
  description: z.string().describe("Human-readable description"),
  icon: z.string().describe("Icon identifier or emoji"),
  asset_mode: z
    .enum(["REQUIRED", "OPTIONAL", "FORBIDDEN"])
    .describe(
      "REQUIRED: must have asset_id, OPTIONAL: can have, FORBIDDEN: must not have"
    ),
  requires_link: z.boolean().describe("Whether link_uuid is required"),
  requires_cash: z.boolean().describe("Whether cash is required"),
  allowed_quantity_sign: z
    .enum(["+", "-", "0", "+/-"])
    .describe("Allowed quantity sign"),
  allowed_cash_sign: z
    .enum(["+", "-", "0", "+/-"])
    .describe("Allowed cash amount sign"),
});
const BRCreateItem: z.ZodType<BRCreateItem> = z.object({
  name: z.string().min(1).max(100).describe("Broker name (must be unique)"),
  description: z
    .union([z.string(), z.null()])
    .describe("Broker description")
    .optional(),
  portal_url: z
    .union([z.string(), z.null()])
    .describe("URL to broker's web portal")
    .optional(),
  icon_url: z
    .union([z.string(), z.null()])
    .describe("Custom icon URL for the broker")
    .optional(),
  default_import_plugin: z
    .union([z.string(), z.null()])
    .describe("Default BRIM plugin for importing transactions")
    .optional(),
  allow_cash_overdraft: z
    .boolean()
    .describe("Allow leveraged buying (negative cash balance)")
    .optional()
    .default(false),
  allow_asset_shorting: z
    .boolean()
    .describe("Allow short selling (negative asset quantities)")
    .optional()
    .default(false),
  is_active: z
    .boolean()
    .describe("Whether the broker account is currently active")
    .optional()
    .default(true),
  opened_at: z
    .union([z.string(), z.null()])
    .describe("Date when the account was opened in reality")
    .optional(),
  initial_balances: z
    .union([z.array(Currency_Input), z.null()])
    .describe("Initial cash balances. Creates DEPOSIT transactions.")
    .optional(),
});
const BRCreateResult: z.ZodType<BRCreateResult> = z.object({
  success: z.boolean(),
  broker_id: z.union([z.number(), z.null()]).optional(),
  name: z.string(),
  deposits_created: z
    .number()
    .int()
    .gte(0)
    .describe("Number of DEPOSIT transactions created")
    .optional()
    .default(0),
  error: z.union([z.string(), z.null()]).optional(),
});
const BRBulkCreateResponse: z.ZodType<BRBulkCreateResponse> = z.object({
  results: z.array(BRCreateResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const as_user_id = z
  .union([z.string(), z.null()])
  .describe("Superuser: impersonate user ID or 'all'")
  .optional();
const BRReadItem = z.object({
  id: z.number().int(),
  name: z.string(),
  description: z.union([z.string(), z.null()]).optional(),
  portal_url: z.union([z.string(), z.null()]).optional(),
  icon_url: z.union([z.string(), z.null()]).optional(),
  default_import_plugin: z.union([z.string(), z.null()]).optional(),
  allow_cash_overdraft: z.boolean(),
  allow_asset_shorting: z.boolean(),
  is_active: z.boolean(),
  opened_at: z.union([z.string(), z.null()]).optional(),
  created_at: z.string(),
  updated_at: z.string(),
  user_role: z
    .union([z.string(), z.null()])
    .describe("Current user's role on this broker (OWNER/EDITOR/VIEWER)")
    .optional(),
});
const BRDeleteResult: z.ZodType<BRDeleteResult> = z.object({
  success: z.boolean().describe("Whether the deletion succeeded"),
  deleted_count: z.number().int().gte(0).describe("Number of items deleted"),
  message: z
    .union([z.string(), z.null()])
    .describe("Info/warning/error message")
    .optional(),
  id: z.number().int().describe("Broker ID"),
  transactions_deleted: z
    .number()
    .int()
    .gte(0)
    .describe("Number of transactions cascade-deleted (only when force=True)")
    .optional()
    .default(0),
});
const BRBulkDeleteResponse: z.ZodType<BRBulkDeleteResponse> = z.object({
  results: z.array(BRDeleteResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
  total_deleted: z
    .number()
    .int()
    .gte(0)
    .describe("Total number of records deleted across all items"),
});
const BRUpdateItem = z
  .object({
    name: z.union([z.string(), z.null()]).describe("New broker name"),
    description: z.union([z.string(), z.null()]).describe("New description"),
    portal_url: z.union([z.string(), z.null()]).describe("New portal URL"),
    icon_url: z
      .union([z.string(), z.null()])
      .describe("Custom icon URL for the broker"),
    default_import_plugin: z
      .union([z.string(), z.null()])
      .describe("Default BRIM plugin for importing transactions"),
    allow_cash_overdraft: z
      .union([z.boolean(), z.null()])
      .describe("Update leveraged buying permission"),
    allow_asset_shorting: z
      .union([z.boolean(), z.null()])
      .describe("Update short selling permission"),
    is_active: z
      .union([z.boolean(), z.null()])
      .describe("Update account active status"),
    opened_at: z
      .union([z.string(), z.null()])
      .describe("Update account opening date"),
  })
  .partial();
const BRUpdateResult: z.ZodType<BRUpdateResult> = z.object({
  id: z.number().int(),
  success: z.boolean(),
  validation_triggered: z
    .boolean()
    .describe("Whether balance validation was triggered due to flag change")
    .optional()
    .default(false),
  error: z.union([z.string(), z.null()]).optional(),
});
const BRBulkUpdateResponse: z.ZodType<BRBulkUpdateResponse> = z.object({
  results: z.array(BRUpdateResult).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const BRAssetHolding: z.ZodType<BRAssetHolding> = z.object({
  asset_id: z.number().int().describe("Asset ID"),
  asset_name: z.string().describe("Asset display name"),
  quantity: z
    .string()
    .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
    .describe("Current quantity held"),
  total_cost:
    Currency_Output.describe(`Currency amount with validation and arithmetic operations.

Validates currency codes against ISO 4217 (via pycountry) + crypto dict.
Supports addition/subtraction only between same currencies.
Amount can be negative.

Attributes:
    code: ISO 4217 currency code (USD, EUR) or crypto symbol (BTC, ETH)
    amount: Decimal amount (can be negative)

Examples:
    >>> usd = Currency(code="USD", amount=Decimal("100.50"))
    >>> fee = Currency(code="USD", amount=Decimal("2.50"))
    >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))

    >>> eur = Currency(code="EUR", amount=Decimal("50"))
    >>> usd + eur  # ValueError: Cannot add USD and EUR

    >>> btc = Currency(code="BTC", amount=Decimal("0.5"))  # Valid crypto

    >>> negative = -usd  # Currency(code="USD", amount=Decimal("-100.50"))

Raises:
    ValueError: If currency code is not valid ISO 4217 or supported crypto`),
  average_cost_per_unit: z
    .string()
    .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
    .describe("Average cost per unit"),
  current_price: z
    .union([z.string(), z.null()])
    .describe("Latest price per unit")
    .optional(),
  current_value: z
    .union([Currency_Output, z.null()])
    .describe("Current market value")
    .optional(),
  unrealized_pnl: z
    .union([Currency_Output, z.null()])
    .describe("Unrealized profit/loss")
    .optional(),
  unrealized_pnl_percent: z
    .union([z.string(), z.null()])
    .describe("Unrealized P&L %")
    .optional(),
});
const BRSummary: z.ZodType<BRSummary> = z.object({
  id: z.number().int(),
  name: z.string(),
  description: z.union([z.string(), z.null()]).optional(),
  portal_url: z.union([z.string(), z.null()]).optional(),
  icon_url: z.union([z.string(), z.null()]).optional(),
  default_import_plugin: z.union([z.string(), z.null()]).optional(),
  allow_cash_overdraft: z.boolean(),
  allow_asset_shorting: z.boolean(),
  is_active: z.boolean(),
  opened_at: z.union([z.string(), z.null()]).optional(),
  created_at: z.string(),
  updated_at: z.string(),
  user_role: z
    .union([z.string(), z.null()])
    .describe("Current user's role on this broker (OWNER/EDITOR/VIEWER)")
    .optional(),
  user_share_percentage: z
    .union([z.string(), z.null()])
    .describe("Current user's ownership percentage")
    .optional(),
  cash_balances: z
    .array(Currency_Output)
    .describe("Current cash balance per currency")
    .optional(),
  holdings: z
    .array(BRAssetHolding)
    .describe("Current asset holdings with cost basis and market value")
    .optional(),
  total_value_base_currency: z
    .union([Currency_Output, z.null()])
    .describe("Total portfolio value in base currency (cash + holdings)")
    .optional(),
});
const UserRole = z.enum(["OWNER", "EDITOR", "VIEWER"]);
const BRAccessItem: z.ZodType<BRAccessItem> = z.object({
  user_id: z.number().int().describe("User ID"),
  username: z.string().describe("Username"),
  email: z.string().describe("User email"),
  role: UserRole.describe(`User role for broker access control.

- OWNER: Full access (CRUD broker, manage access, delete broker)
- EDITOR: Modify broker and transactions, can only remove self
- VIEWER: Read-only access`),
  share_percentage: z
    .string()
    .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
    .describe("Ownership fraction (0.0-1.0) for portfolio aggregation"),
  avatar_url: z
    .union([z.string(), z.null()])
    .describe("User avatar URL")
    .optional(),
  created_at: z.string().describe("When access was granted"),
});
const BRAccessListResponse: z.ZodType<BRAccessListResponse> = z
  .object({ items: z.array(BRAccessItem).describe("List of items") })
  .partial();
const BRAccessBulkItem: z.ZodType<BRAccessBulkItem> = z.object({
  user_id: z.number().int().gt(0).describe("User ID"),
  role: UserRole.describe(`User role for broker access control.

- OWNER: Full access (CRUD broker, manage access, delete broker)
- EDITOR: Modify broker and transactions, can only remove self
- VIEWER: Read-only access`),
  share_percentage: z
    .union([z.number(), z.string()])
    .describe(
      "Ownership fraction (0.0-1.0). Only valid for OWNER role. Frontend displays as %."
    )
    .optional()
    .default("0"),
});
const BRAccessBulkResponse: z.ZodType<BRAccessBulkResponse> = z.object({
  results: z.array(BRAccessItem).describe("Per-item operation results"),
  success_count: z
    .number()
    .int()
    .gte(0)
    .describe("Number of successful operations"),
  errors: z
    .array(z.string())
    .describe("Operation-level errors (not per-item)")
    .optional(),
});
const Body_upload_file_api_v1_brokers_import_upload_post = z
  .object({ file: z.instanceof(File).describe("Broker report file to upload") })
  .passthrough();
const BRIMFileStatus = z.enum(["uploaded", "parsed", "failed"]);
const BRIMFileInfo: z.ZodType<BRIMFileInfo> = z
  .object({
    file_id: z.string().describe("UUID identifier for the file"),
    filename: z.string().describe("Original filename from upload"),
    size_bytes: z.number().int().gte(0).describe("File size in bytes"),
    status: BRIMFileStatus.describe(`Status of an uploaded broker report file.

Flow: UPLOADED → PARSED (success) or FAILED (error)
After parsing, the file stays in PARSED. The actual transaction import
uses POST /transactions and doesn't change file status.`),
    uploaded_at: z.string().describe("UTC timestamp when uploaded"),
    processed_at: z
      .union([z.string(), z.null()])
      .describe("UTC timestamp when processed")
      .optional(),
    compatible_plugins: z
      .array(z.string())
      .describe("Plugin codes that can parse this file")
      .optional(),
    error_message: z
      .union([z.string(), z.null()])
      .describe("Error description if processing failed")
      .optional(),
    uploaded_by_user_id: z
      .union([z.number(), z.null()])
      .describe("ID of user who uploaded the file")
      .optional(),
    target_broker_id: z
      .union([z.number(), z.null()])
      .describe("ID of broker this file belongs to")
      .optional(),
    last_parse_result: z
      .union([z.object({}).partial().passthrough(), z.null()])
      .describe("Cached result from last successful parse")
      .optional(),
  })
  .passthrough();
const status = z
  .union([BRIMFileStatus, z.null()])
  .describe("Filter by status: uploaded, imported, failed")
  .optional();
const broker_ids = z
  .union([z.array(z.number().int()), z.null()])
  .describe(
    "Filter by broker IDs (repeated query params, e.g., ?broker_ids=1&broker_ids=2)"
  )
  .optional();
const BRIMParseRequest = z
  .object({
    plugin_code: z
      .string()
      .describe(
        "Plugin code to use for parsing. Use 'auto' for automatic detection."
      )
      .optional()
      .default("auto"),
    broker_id: z.number().int().gt(0).describe("Target broker ID"),
  })
  .passthrough();
const TXCreateItem_Output: z.ZodType<TXCreateItem_Output> = z.object({
  broker_id: z.number().int().gt(0).describe("Broker ID"),
  asset_id: z
    .union([z.number(), z.null()])
    .describe("Asset ID. NULL for pure cash transactions")
    .optional(),
  type: TransactionType.describe(`Unified transaction types for all asset and cash operations.

This enum represents all possible transaction types in the unified
transaction table. Each type has specific rules for quantity and amount signs.

== Asset transactions (quantity != 0) ==

- BUY: Purchase asset with cash
  Signs: quantity > 0, amount < 0
  Example: Buy 10 shares of AAPL for €1500

- SELL: Sell asset for cash
  Signs: quantity < 0, amount > 0
  Example: Sell 5 shares of MSFT for €1500

- TRANSFER: Asset transfer between brokers
  Signs: quantity +/-, amount = 0
  Requires: related_transaction_id (links to paired transfer)
  Example: Transfer 100 shares from Broker A to Broker B

- ADJUSTMENT: Manual asset quantity correction (splits, gifts, etc.)
  Signs: quantity +/-, amount = 0
  Optional: related_transaction_id
  Example: Stock split 2:1 adds 100 shares

== Cash-only transactions (quantity = 0) ==

- DIVIDEND: Dividend payment received
  Signs: quantity = 0, amount > 0
  Example: Receive €50 dividend from AAPL

- INTEREST: Interest payment received
  Signs: quantity = 0, amount > 0
  Example: Monthly interest from crowdfunding loan

- DEPOSIT: Add cash to broker account
  Signs: quantity = 0, amount > 0
  Example: Transfer €1000 to broker

- WITHDRAWAL: Remove cash from broker account
  Signs: quantity = 0, amount < 0
  Example: Withdraw €500 from broker

- FEE: Fee or commission payment
  Signs: quantity = 0, amount < 0
  Example: €5 custody fee

- TAX: Tax payment
  Signs: quantity = 0, amount < 0
  Example: €100 capital gains tax

- FX_CONVERSION: Currency exchange
  Signs: quantity = 0, amount +/-
  Requires: related_transaction_id (links to paired conversion)
  Example: Convert €1000 to $1090

Impact:
- TRANSFER and FX_CONVERSION require related_transaction_id
- Validation ensures sign rules are followed
- All calculations based on settlement date`),
  date: z.string().describe("Settlement date"),
  quantity: z
    .string()
    .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
    .describe("Asset quantity delta (+ in, - out)")
    .optional()
    .default("0"),
  cash: z
    .union([Currency_Output, z.null()])
    .describe("Cash movement (code + amount). Required for cash operations.")
    .optional(),
  link_uuid: z
    .union([z.string(), z.null()])
    .describe(
      "Temporary UUID to link paired transactions (TRANSFER, FX_CONVERSION)"
    )
    .optional(),
  tags: z
    .union([z.array(z.string()), z.null()])
    .describe("List of tags for filtering/grouping")
    .optional(),
  description: z
    .union([z.string(), z.null()])
    .describe("Transaction notes")
    .optional(),
  cost_basis_override: z
    .union([z.string(), z.null()])
    .describe(
      "Frozen cost basis for TRANSFER_IN. Overrides calculated cost basis."
    )
    .optional(),
});
const BRIMMatchConfidence = z.enum(["exact", "high", "medium", "low"]);
const BRIMAssetCandidate: z.ZodType<BRIMAssetCandidate> = z
  .object({
    asset_id: z.number().int().describe("Real asset ID from database"),
    symbol: z
      .union([z.string(), z.null()])
      .describe("Asset symbol/ticker")
      .optional(),
    isin: z.union([z.string(), z.null()]).describe("Asset ISIN").optional(),
    name: z.string().describe("Asset display name"),
    match_confidence:
      BRIMMatchConfidence.describe(`Confidence level for asset candidate matching.

Criteria:
- EXACT: ISIN match (ISIN is globally unique identifier)
- HIGH: Symbol exact match + same asset type
- MEDIUM: Symbol exact match only (no type verification)
- LOW: Partial name match or fuzzy symbol match`),
  })
  .passthrough();
const BRIMAssetMapping: z.ZodType<BRIMAssetMapping> = z
  .object({
    fake_asset_id: z
      .number()
      .int()
      .describe("Fake ID used in parsed transactions"),
    extracted_symbol: z
      .union([z.string(), z.null()])
      .describe("Symbol extracted from file")
      .optional(),
    extracted_isin: z
      .union([z.string(), z.null()])
      .describe("ISIN extracted from file")
      .optional(),
    extracted_name: z
      .union([z.string(), z.null()])
      .describe("Name extracted from file")
      .optional(),
    candidates: z
      .array(BRIMAssetCandidate)
      .describe("Possible asset matches from database (empty = not found)")
      .optional(),
    selected_asset_id: z
      .union([z.number(), z.null()])
      .describe("Auto-set if 1 candidate, else None (user must choose)")
      .optional(),
  })
  .passthrough();
const BRIMDuplicateLevel = z.enum([
  "possible",
  "possible_with_asset",
  "likely",
  "likely_with_asset",
]);
const BRIMDuplicateMatch: z.ZodType<BRIMDuplicateMatch> = z
  .object({
    existing_tx_id: z
      .number()
      .int()
      .describe("ID of existing transaction in DB"),
    tx_date: z.string().describe("Transaction date"),
    tx_type:
      TransactionType.describe(`Unified transaction types for all asset and cash operations.

This enum represents all possible transaction types in the unified
transaction table. Each type has specific rules for quantity and amount signs.

== Asset transactions (quantity != 0) ==

- BUY: Purchase asset with cash
  Signs: quantity > 0, amount < 0
  Example: Buy 10 shares of AAPL for €1500

- SELL: Sell asset for cash
  Signs: quantity < 0, amount > 0
  Example: Sell 5 shares of MSFT for €1500

- TRANSFER: Asset transfer between brokers
  Signs: quantity +/-, amount = 0
  Requires: related_transaction_id (links to paired transfer)
  Example: Transfer 100 shares from Broker A to Broker B

- ADJUSTMENT: Manual asset quantity correction (splits, gifts, etc.)
  Signs: quantity +/-, amount = 0
  Optional: related_transaction_id
  Example: Stock split 2:1 adds 100 shares

== Cash-only transactions (quantity = 0) ==

- DIVIDEND: Dividend payment received
  Signs: quantity = 0, amount > 0
  Example: Receive €50 dividend from AAPL

- INTEREST: Interest payment received
  Signs: quantity = 0, amount > 0
  Example: Monthly interest from crowdfunding loan

- DEPOSIT: Add cash to broker account
  Signs: quantity = 0, amount > 0
  Example: Transfer €1000 to broker

- WITHDRAWAL: Remove cash from broker account
  Signs: quantity = 0, amount < 0
  Example: Withdraw €500 from broker

- FEE: Fee or commission payment
  Signs: quantity = 0, amount < 0
  Example: €5 custody fee

- TAX: Tax payment
  Signs: quantity = 0, amount < 0
  Example: €100 capital gains tax

- FX_CONVERSION: Currency exchange
  Signs: quantity = 0, amount +/-
  Requires: related_transaction_id (links to paired conversion)
  Example: Convert €1000 to $1090

Impact:
- TRANSFER and FX_CONVERSION require related_transaction_id
- Validation ensures sign rules are followed
- All calculations based on settlement date`),
    tx_quantity: z
      .string()
      .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)
      .describe("Transaction quantity"),
    tx_cash_amount: z
      .union([z.string(), z.null()])
      .describe("Cash amount if applicable")
      .optional(),
    tx_cash_currency: z
      .union([z.string(), z.null()])
      .describe("Cash currency if applicable")
      .optional(),
    tx_description: z
      .union([z.string(), z.null()])
      .describe("Transaction description")
      .optional(),
    match_level:
      BRIMDuplicateLevel.describe(`Confidence level for duplicate detection (ascending order).

Levels (from lowest to highest confidence):
1. POSSIBLE: type + date + quantity + cash match, but asset not resolved
2. POSSIBLE_WITH_ASSET: POSSIBLE + asset auto-resolved (1 candidate)
3. LIKELY: POSSIBLE + identical non-empty description, but asset not resolved
4. LIKELY_WITH_ASSET: LIKELY + asset auto-resolved (practically certain duplicate)

The WITH_ASSET variants are more reliable because the asset was automatically
matched to a single candidate in the database.`),
  })
  .passthrough();
const BRIMTXDuplicateCandidate: z.ZodType<BRIMTXDuplicateCandidate> = z
  .object({
    tx_row_index: z
      .number()
      .int()
      .describe("Row index in parsed transactions list"),
    tx_parsed:
      TXCreateItem_Output.describe(`DTO for creating a single transaction.

Used by POST /api/v1/transactions endpoint.

Field semantics:
- quantity: Asset delta (+ buy/in, - sell/out). Default 0.
- cash: Currency object with code + amount. None if no cash movement.
- link_uuid: Temporary UUID to link paired transactions in bulk create

Sign rules per type:
- BUY: quantity > 0, cash.amount < 0
- SELL: quantity < 0, cash.amount > 0
- DIVIDEND/INTEREST: quantity = 0, cash.amount > 0
- DEPOSIT: quantity = 0, cash.amount > 0
- WITHDRAWAL: quantity = 0, cash.amount < 0
- FEE/TAX: quantity = 0, cash.amount < 0
- TRANSFER: quantity +/-, cash = None, link_uuid REQUIRED
- FX_CONVERSION: quantity = 0, cash.amount +/-, link_uuid REQUIRED
- ADJUSTMENT: quantity +/-, cash = None`),
    tx_existing_matches: z
      .array(BRIMDuplicateMatch)
      .describe("Existing transactions that match")
      .optional(),
  })
  .passthrough();
const BRIMDuplicateReport: z.ZodType<BRIMDuplicateReport> = z
  .object({
    tx_unique_indices: z
      .array(z.number().int())
      .describe("Row indices of unique (non-duplicate) transactions"),
    tx_possible_duplicates: z
      .array(BRIMTXDuplicateCandidate)
      .describe("Transactions that might be duplicates (POSSIBLE level)"),
    tx_likely_duplicates: z
      .array(BRIMTXDuplicateCandidate)
      .describe("Transactions very likely to be duplicates (LIKELY level)"),
  })
  .partial()
  .passthrough();
const BRIMParseResponse: z.ZodType<BRIMParseResponse> = z
  .object({
    file_id: z.string().describe("UUID of the parsed file"),
    plugin_code: z.string().describe("Plugin used for parsing"),
    broker_id: z.number().int().gt(0).describe("Target broker ID"),
    transactions: z
      .array(TXCreateItem_Output)
      .describe("Parsed transactions (may have fake asset IDs)")
      .optional(),
    asset_mappings: z
      .array(BRIMAssetMapping)
      .describe("Fake asset ID → candidate real assets mapping")
      .optional(),
    duplicates: z
      .union([BRIMDuplicateReport, z.null()])
      .describe("Duplicate detection results")
      .optional(),
    warnings: z
      .array(z.string())
      .describe("Parser warnings (skipped rows, ambiguous data, etc.)")
      .optional(),
  })
  .passthrough();
const BRIMPluginInfo = z
  .object({
    code: z.string().describe("Unique plugin identifier"),
    name: z.string().describe("Human-readable plugin name"),
    description: z.string().describe("Plugin description for UI"),
    supported_extensions: z
      .array(z.string())
      .describe("Supported file extensions (e.g., ['.csv', '.xlsx'])")
      .optional(),
    icon_url: z
      .union([z.string(), z.null()])
      .describe("URL to broker icon/logo (absolute URL or relative path)")
      .optional(),
  })
  .passthrough();
const ExportFormat = z.enum(["json", "csv", "sqlite"]);
const ExportScope = z.enum([
  "all",
  "transactions",
  "assets",
  "brokers",
  "settings",
]);
const ExportRequest: z.ZodType<ExportRequest> = z
  .object({
    format: ExportFormat.describe("Supported export formats."),
    scope: z.array(ExportScope).default(["all"]),
    include_price_history: z.boolean().default(false),
    broker_ids: z.union([z.array(z.number().int()), z.null()]),
  })
  .partial()
  .passthrough();
const ExportResponse = z
  .object({
    download_url: z.string(),
    filename: z.string(),
    size_bytes: z.number().int(),
    expires_at: z.string(),
  })
  .passthrough();
const RestoreRequest = z
  .object({
    file_id: z.string(),
    overwrite_existing: z.boolean().optional().default(false),
  })
  .passthrough();
const RestoreResponse = z
  .object({
    success: z.boolean(),
    restored_count: z.object({}).partial().passthrough(),
    warnings: z.array(z.string()).optional().default([]),
  })
  .passthrough();
const CountryNormalizationResponse = z.object({
  query: z.string().describe("Original query string"),
  iso3_codes: z.array(z.string()).describe("List of ISO-3166-A3 country codes"),
  match_type: z
    .string()
    .describe("Match type: exact, region, multi-match, not_found"),
  error: z
    .union([z.string(), z.null()])
    .describe("Error message if normalization failed")
    .optional(),
});
const SectorListResponse = z
  .object({ items: z.array(z.string()).describe("List of items") })
  .partial();
const CountryListItem: z.ZodType<CountryListItem> = z.object({
  iso3: z.string().describe("ISO-3166-A3 country code (e.g., USA, ITA)"),
  iso2: z.string().describe("ISO-3166-A2 country code (e.g., US, IT)"),
  name: z.string().describe("Country name in requested language"),
  flag_emoji: z.string().describe("Flag emoji (e.g., 🇺🇸, 🇮🇹)"),
});
const CountryListResponse: z.ZodType<CountryListResponse> = z.object({
  items: z.array(CountryListItem).describe("List of items").optional(),
  language: z.string().describe("Language used for country names"),
});
const CurrencyListItem: z.ZodType<CurrencyListItem> = z.object({
  code: z.string().describe("ISO 4217 currency code (e.g., USD, EUR)"),
  name: z.string().describe("Currency name in requested language"),
  symbol: z.string().describe("Currency symbol (e.g., $, €)"),
  flag_emoji: z
    .string()
    .describe(
      "Flag emoji of primary country using this currency (e.g., 🇺🇸, 🇪🇺, 🪙 for crypto)"
    )
    .optional()
    .default("🏳️"),
  country_codes: z
    .array(z.string())
    .describe(
      "ISO-2 country codes using this currency (e.g., ['US', 'AS', 'EC'] for USD)"
    )
    .optional(),
  country_names: z
    .array(z.string())
    .describe(
      "Localized country names using this currency (e.g., ['United States', 'American Samoa'] for USD in English)"
    )
    .optional(),
});
const CurrencyListResponse: z.ZodType<CurrencyListResponse> = z.object({
  items: z.array(CurrencyListItem).describe("List of items").optional(),
  language: z.string().describe("Language used for currency names"),
});
const CurrencyNormalizationResponse = z.object({
  query: z.string().describe("Original query string"),
  iso_codes: z.array(z.string()).describe("List of ISO 4217 currency codes"),
  match_type: z
    .string()
    .describe("Match type: exact, symbol_ambiguous, multi-match, not_found"),
  error: z
    .union([z.string(), z.null()])
    .describe("Error message if normalization failed")
    .optional(),
});

export const schemas = {
  AuthLoginRequest,
  AuthUserResponse,
  UserSettingsRead,
  AuthLoginResponse,
  ValidationError,
  HTTPValidationError,
  AuthLogoutResponse,
  AuthMeResponse,
  AuthRegisterRequest,
  AuthRegisterResponse,
  ChangePasswordRequest,
  ChangePasswordResponse,
  UpdateProfileRequest,
  UpdateProfileResponse,
  UserSettingsUpdate,
  GlobalSettingRead,
  GlobalSettingsListResponse,
  GlobalSettingUpdate,
  DependencyInfo,
  SystemInfoResponse,
  Body_upload_file_api_v1_uploads_post,
  UploadFileInfo,
  UploadResponse,
  UploadListResponse,
  UploadDeleteResponse,
  offset,
  img_preview,
  exclude_broker_id,
  UserSearchItem,
  UserSearchResponse,
  providers,
  FXProviderInfo,
  FXRouteStep,
  FXConversionRouteItem,
  FXConversionRoutesResponse,
  FXConversionRouteResult,
  FXCreateRoutesResponse,
  FXDeleteRouteItem,
  FXDeleteRouteResult,
  FXDeleteRoutesResponse,
  FXSyncPairRequest,
  FXSyncStatus,
  FXSyncPairResult,
  DateRangeModel,
  FXSyncBulkResponse,
  FXUpsertItem,
  FXUpsertResult,
  FXBulkUpsertResponse,
  FXDeleteItem,
  FXDeleteResult,
  FXBulkDeleteResponse,
  Currency_Input,
  FXConversionRequest,
  Currency_Output,
  BackwardFillInfo,
  FXConversionResult,
  FXConvertResponse,
  AssetType,
  FAGeographicArea_Input,
  FASectorArea_Input,
  FAClassificationParams_Input,
  FAAssetCreateItem,
  FAAssetCreateResult,
  FABulkAssetCreateResponse,
  FAAssetPatchItem,
  OldNew_Union_str__NoneType__,
  FAAssetPatchResult,
  FABulkAssetPatchResponse,
  FAAssetDeleteResult,
  FABulkAssetDeleteResponse,
  FAGeographicArea_Output,
  FASectorArea_Output,
  FAClassificationParams_Output,
  FAAssetMetadataResponse,
  IdentifierType,
  FAinfoResponse,
  currency,
  asset_type,
  search,
  isin,
  ticker,
  cusip,
  sedol,
  figi,
  uuid,
  identifier_other,
  identifier_contains,
  FAPricePoint_Input,
  FAUpsert,
  FAUpsertResult,
  FABulkUpsertResponse,
  FAAssetDelete,
  FAPriceDeleteResult,
  FABulkDeleteResponse,
  end_date,
  FAPricePoint_Output,
  FARefreshItem,
  FARefreshResult,
  FABulkRefreshResponse,
  FAProviderInfo,
  FAProviderAssignmentItem,
  FAProviderRefreshFieldsDetail,
  FAProviderAssignmentResult,
  FABulkAssignResponse,
  FAProviderRemovalResult,
  FABulkRemoveResponse,
  providers__2,
  FAProviderSearchResultItem,
  FAProviderSearchResponse,
  FAProviderAssignmentReadItem,
  FAMetadataRefreshResult,
  FABulkMetadataRefreshResponse,
  TransactionType,
  TXCreateItem_Input,
  TXCreateResultItem,
  TXBulkCreateResponse,
  broker_id,
  asset_id,
  types,
  date_start,
  date_end,
  tags,
  currency__2,
  TXReadItem,
  TXUpdateItem,
  TXUpdateResultItem,
  TXBulkUpdateResponse,
  TXDeleteResult,
  TXBulkDeleteResponse,
  TXTypeMetadata,
  BRCreateItem,
  BRCreateResult,
  BRBulkCreateResponse,
  as_user_id,
  BRReadItem,
  BRDeleteResult,
  BRBulkDeleteResponse,
  BRUpdateItem,
  BRUpdateResult,
  BRBulkUpdateResponse,
  BRAssetHolding,
  BRSummary,
  UserRole,
  BRAccessItem,
  BRAccessListResponse,
  BRAccessBulkItem,
  BRAccessBulkResponse,
  Body_upload_file_api_v1_brokers_import_upload_post,
  BRIMFileStatus,
  BRIMFileInfo,
  status,
  broker_ids,
  BRIMParseRequest,
  TXCreateItem_Output,
  BRIMMatchConfidence,
  BRIMAssetCandidate,
  BRIMAssetMapping,
  BRIMDuplicateLevel,
  BRIMDuplicateMatch,
  BRIMTXDuplicateCandidate,
  BRIMDuplicateReport,
  BRIMParseResponse,
  BRIMPluginInfo,
  ExportFormat,
  ExportScope,
  ExportRequest,
  ExportResponse,
  RestoreRequest,
  RestoreResponse,
  CountryNormalizationResponse,
  SectorListResponse,
  CountryListItem,
  CountryListResponse,
  CurrencyListItem,
  CurrencyListResponse,
  CurrencyNormalizationResponse,
};

const endpoints = makeApi([
  {
    method: "get",
    path: "/",
    alias: "root__get",
    description: `Root endpoint.
Serves frontend if build exists, otherwise provides API information.`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/:path",
    alias: "frontend_catchall__path__get",
    description: `Serve frontend for any non-API route (SPA support).`,
    requestFormat: "json",
    parameters: [
      {
        name: "path",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/assets",
    alias: "create_assets_bulk_api_v1_assets_post",
    description: `Create multiple assets in bulk (partial success allowed).

Creates asset records with optional classification metadata.
Provider assignment can be done separately via POST /assets/provider.

**Request Example**:
&#x60;&#x60;&#x60;json
[
  {
    &quot;display_name&quot;: &quot;Apple Inc.&quot;,
    &quot;currency&quot;: &quot;USD&quot;,
    &quot;asset_type&quot;: &quot;STOCK&quot;,
    &quot;icon_url&quot;: &quot;https://example.com/aapl.png&quot;,
    &quot;classification_params&quot;: {
      &quot;sector&quot;: &quot;Technology&quot;,
      &quot;geographic_area&quot;: {&quot;USA&quot;: &quot;1.0&quot;}
    }
  }
]
&#x60;&#x60;&#x60;

**Response Example**:
&#x60;&#x60;&#x60;json
{
  &quot;results&quot;: [
    {
      &quot;asset_id&quot;: 1,
      &quot;success&quot;: true,
      &quot;message&quot;: &quot;Asset created successfully&quot;,
      &quot;display_name&quot;: &quot;Apple Inc.&quot;
    }
  ],
  &quot;success_count&quot;: 1,
  &quot;failed_count&quot;: 0
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FAAssetCreateItem),
      },
    ],
    response: FABulkAssetCreateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/assets",
    alias: "patch_assets_bulk_api_v1_assets_patch",
    description: `Update multiple assets in bulk (partial success allowed).

**Merge Logic**:
- Field present (even if None): UPDATE or BLANK value
- Field absent: IGNORE (keep existing value)

**Example Request**:
&#x60;&#x60;&#x60;json
[
  {
    &quot;asset_id&quot;: 1,
    &quot;display_name&quot;: &quot;Apple Inc. - Updated&quot;,
    &quot;classification_params&quot;: {
      &quot;sector&quot;: &quot;Technology&quot;,
      &quot;short_description&quot;: &quot;New description&quot;
    }
  },
  {
    &quot;asset_id&quot;: 2,
    &quot;classification_params&quot;: null,
    &quot;active&quot;: false
  }
]
&#x60;&#x60;&#x60;

**Classification Params Optimization**:
- If None: Clears metadata (DB column set to NULL)
- If present: Only non-null subfields saved to DB (JSON optimization)

**Response Fields**:
- &#x60;updated_fields&#x60;: List of field names actually changed
- Per-item success/failure status`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FAAssetPatchItem),
      },
    ],
    response: FABulkAssetPatchResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/assets",
    alias: "delete_assets_bulk_api_v1_assets_delete",
    description: `Delete multiple assets in bulk (partial success allowed).

**Warning**: This will CASCADE DELETE:
- Provider assignments (asset_provider_assignments table)
- Price history (price_history table)

**Blocks deletion** if asset has transactions (foreign key constraint).

**Request Example**:
&#x60;&#x60;&#x60;
DELETE /api/v1/assets?asset_ids&#x3D;1&amp;asset_ids&#x3D;2&amp;asset_ids&#x3D;3
&#x60;&#x60;&#x60;

**Response Example**:
&#x60;&#x60;&#x60;json
{
  &quot;results&quot;: [
    {
      &quot;asset_id&quot;: 1,
      &quot;success&quot;: true,
      &quot;message&quot;: &quot;Asset deleted successfully&quot;
    },
    {
      &quot;asset_id&quot;: 2,
      &quot;success&quot;: false,
      &quot;message&quot;: &quot;Cannot delete asset 2: has existing transactions&quot;
    }
  ],
  &quot;success_count&quot;: 1,
  &quot;failed_count&quot;: 1
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "asset_ids",
        type: "Query",
        schema: z
          .array(z.number().int())
          .min(1)
          .describe("List of asset IDs to delete"),
      },
    ],
    response: FABulkAssetDeleteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets",
    alias: "read_assets_bulk_api_v1_assets_get",
    description: `Bulk read assets with classification metadata (preserves request order).

Fetches basic asset information along with parsed classification_params
for multiple assets in a single request. Assets not found are silently
skipped.

**Request query**:
&#x60;&#x60;&#x60;json
GET /api/v1/assets?asset_ids&#x3D;1&amp;asset_ids&#x3D;2&amp;asset_ids&#x3D;3
&#x60;&#x60;&#x60;

**Response** (ordered by request):
&#x60;&#x60;&#x60;json
[
  {
    &quot;asset_id&quot;: 1,
    &quot;display_name&quot;: &quot;Apple Inc.&quot;,
    &quot;identifier&quot;: &quot;AAPL&quot;,
    &quot;currency&quot;: &quot;USD&quot;,
    &quot;asset_type&quot;: &quot;stock&quot;,
    &quot;classification_params&quot;: {
      &quot;sector&quot;: &quot;Technology&quot;,
      &quot;short_description&quot;: &quot;Consumer electronics&quot;,
      &quot;geographic_area&quot;: {
        &quot;USA&quot;: &quot;1.0000&quot;
      }
    },
    has_provider: false
  },
  {
    &quot;asset_id&quot;: 2,
    &quot;display_name&quot;: &quot;Vanguard S&amp;P 500&quot;,
    &quot;identifier&quot;: &quot;VOO&quot;,
    &quot;currency&quot;: &quot;USD&quot;,
    &quot;asset_type&quot;: &quot;etf&quot;,
    &quot;classification_params&quot;: {
      &quot;geographic_area&quot;: {
        &quot;USA&quot;: &quot;1.0000&quot;
      }
    },
    has_provider: true
  }
]
&#x60;&#x60;&#x60;

**Classification Params**:
- Parsed from JSON stored in database
- May be null if no metadata set
- Geographic area contains ISO-3166-A3 codes
- Weights are Decimal strings (4 decimal places)

Args:
    asset_ids: Bulk read request with list of asset IDs
    session: Database session

Returns:
    List of FAAssetMetadataResponse in request order (missing assets skipped)

Raises:
    HTTPException: 500 if unexpected error occurs`,
    requestFormat: "json",
    parameters: [
      {
        name: "asset_ids",
        type: "Query",
        schema: z.array(z.number().int()).describe("List of asset IDs to read"),
      },
    ],
    response: z.array(FAAssetMetadataResponse),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets/all",
    alias: "get_all_assets_api_v1_assets_all_get",
    description: `Get all active assets without filters.

Simple endpoint for frontend to load complete asset list.
Returns all active assets with identifier info.

**Response Fields**:
- &#x60;identifier&#x60;: Asset identifier (ticker, ISIN, etc.) if provider assigned
- &#x60;identifier_type&#x60;: Type of identifier (TICKER, ISIN, UUID, OTHER)`,
    requestFormat: "json",
    response: z.array(FAinfoResponse),
  },
  {
    method: "post",
    path: "/api/v1/assets/prices",
    alias: "upsert_prices_bulk_api_v1_assets_prices_post",
    description: `Bulk upsert prices manually (PRIMARY bulk endpoint).`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FAUpsert),
      },
    ],
    response: FABulkUpsertResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/assets/prices",
    alias: "delete_prices_bulk_api_v1_assets_prices_delete",
    description: `Bulk delete price ranges (PRIMARY bulk endpoint).`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FAAssetDelete),
      },
    ],
    response: FABulkDeleteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets/prices/:asset_id",
    alias: "get_prices_api_v1_assets_prices__asset_id__get",
    description: `Get prices for asset with backward-fill support.

Returns a list of FAPricePoint with OHLC data, volume, and backward-fill info.`,
    requestFormat: "json",
    parameters: [
      {
        name: "asset_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "start_date",
        type: "Query",
        schema: z.string().describe("Start date (required)"),
      },
      {
        name: "end_date",
        type: "Query",
        schema: end_date,
      },
    ],
    response: z.array(FAPricePoint_Output),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/assets/prices/refresh",
    alias: "refresh_prices_bulk_api_v1_assets_prices_refresh_post",
    description: `Bulk refresh prices via providers (PRIMARY bulk endpoint).`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FARefreshItem),
      },
    ],
    response: FABulkRefreshResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets/provider",
    alias: "list_providers_api_v1_assets_provider_get",
    description: `List all available asset pricing providers.`,
    requestFormat: "json",
    response: z.array(FAProviderInfo),
  },
  {
    method: "post",
    path: "/api/v1/assets/provider",
    alias: "assign_providers_bulk_api_v1_assets_provider_post",
    description: `Bulk assign providers to assets (PRIMARY bulk endpoint).`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FAProviderAssignmentItem),
      },
    ],
    response: FABulkAssignResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/assets/provider",
    alias: "remove_providers_bulk_api_v1_assets_provider_delete",
    description: `Bulk remove provider assignments (PRIMARY bulk endpoint).`,
    requestFormat: "json",
    parameters: [
      {
        name: "asset_ids",
        type: "Query",
        schema: z
          .array(z.number().int())
          .describe("List of asset IDs to remove providers from"),
      },
    ],
    response: FABulkRemoveResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets/provider/assignments",
    alias: "get_provider_assignments_api_v1_assets_provider_assignments_get",
    description: `Get provider assignments for multiple assets.

Returns identifier, identifier_type, and provider_params for each assigned asset.

**Example**:
&#x60;&#x60;&#x60;
GET /api/v1/assets/provider/assignments?asset_ids&#x3D;1&amp;asset_ids&#x3D;2&amp;asset_ids&#x3D;3
&#x60;&#x60;&#x60;

**Response**:
&#x60;&#x60;&#x60;json
[
  {
    &quot;asset_id&quot;: 1,
    &quot;provider_code&quot;: &quot;yfinance&quot;,
    &quot;identifier&quot;: &quot;AAPL&quot;,
    &quot;identifier_type&quot;: &quot;TICKER&quot;,
    &quot;provider_params&quot;: {},
    &quot;fetch_interval&quot;: 1440,
    &quot;last_fetch_at&quot;: &quot;2025-01-15T10:30:00Z&quot;
  }
]
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "asset_ids",
        type: "Query",
        schema: z.array(z.number().int()).describe("List of asset IDs"),
      },
    ],
    response: z.array(FAProviderAssignmentReadItem),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/assets/provider/refresh",
    alias: "refresh_assets_from_provider_api_v1_assets_provider_refresh_post",
    description: `Refresh asset data from assigned providers (bulk operation).

**EXPLICIT REFRESH** - No auto-refresh during provider assignment.

Fetches latest metadata from provider and updates:
- asset_type (if provider supports)
- classification_params (sector, short_description, geographic_area)

**Field-level response**:
- refreshed_fields: Successfully updated from provider
- missing_data_fields: Provider couldn&#x27;t fetch (no data available)
- ignored_fields: Provider doesn&#x27;t support these fields

**Example Request**:
&#x60;&#x60;&#x60;
POST /api/v1/assets/provider/refresh
{
  &quot;asset_ids&quot;: [1, 2, 3]
}
&#x60;&#x60;&#x60;

**Example Response**:
&#x60;&#x60;&#x60;json
{
  &quot;results&quot;: [
    {
      &quot;asset_id&quot;: 1,
      &quot;success&quot;: true,
      &quot;message&quot;: &quot;Refreshed from yfinance&quot;,
      &quot;fields_detail&quot;: {
        &quot;refreshed_fields&quot;: [&quot;asset_type&quot;, &quot;sector&quot;, &quot;short_description&quot;],
        &quot;missing_data_fields&quot;: [&quot;geographic_area&quot;],
        &quot;ignored_fields&quot;: []
      }
    }
  ],
  &quot;success_count&quot;: 1,
  &quot;failed_count&quot;: 0
}
&#x60;&#x60;&#x60;

**Per-Item Outcomes**:
- success&#x3D;true: Metadata refreshed (may have 0 changes)
- success&#x3D;false: No provider, provider doesn&#x27;t support metadata, or error

Args:
    asset_ids: List of asset IDs to refresh
    session: Database session

Returns:
    FABulkMetadataRefreshResponse with per-item results and field-level details

Raises:
    HTTPException: 500 if unexpected error occurs`,
    requestFormat: "json",
    parameters: [
      {
        name: "asset_ids",
        type: "Query",
        schema: z
          .array(z.number().int())
          .describe("List of asset IDs to refresh metadata for"),
      },
    ],
    response: FABulkMetadataRefreshResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets/provider/search",
    alias: "search_assets_via_providers_api_v1_assets_provider_search_get",
    description: `Search for assets across one or more providers in parallel.

Queries the specified providers (or all providers that support search) and
returns aggregated results. Searches are executed in parallel using asyncio.gather
for optimal performance.

**Query Parameters**:
- &#x60;q&#x60;: Search query (required, min 1 character)
- &#x60;providers&#x60;: Comma-separated provider codes to query (optional, default: all with search support)

**Example Requests**:
&#x60;&#x60;&#x60;
GET /api/v1/assets/provider/search?q&#x3D;Apple
GET /api/v1/assets/provider/search?q&#x3D;MSCI+World&amp;providers&#x3D;justetf
GET /api/v1/assets/provider/search?q&#x3D;AAPL&amp;providers&#x3D;yfinance,justetf
&#x60;&#x60;&#x60;

**Response**:
&#x60;&#x60;&#x60;json
{
  &quot;query&quot;: &quot;Apple&quot;,
  &quot;total_results&quot;: 5,
  &quot;results&quot;: [
    {
      &quot;identifier&quot;: &quot;AAPL&quot;,
      &quot;display_name&quot;: &quot;Apple Inc.&quot;,
      &quot;provider_code&quot;: &quot;yfinance&quot;,
      &quot;currency&quot;: &quot;USD&quot;,
      &quot;asset_type&quot;: &quot;stock&quot;
    }
  ],
  &quot;providers_queried&quot;: [&quot;yfinance&quot;, &quot;justetf&quot;],
  &quot;providers_with_errors&quot;: []
}
&#x60;&#x60;&#x60;

**Notes**:
- Searches are executed in parallel across all providers
- Providers that don&#x27;t support search are skipped (no error)
- Provider-specific errors are logged but don&#x27;t fail the entire request
- Results are not deduplicated (same asset may appear from multiple providers)`,
    requestFormat: "json",
    parameters: [
      {
        name: "q",
        type: "Query",
        schema: z.string().min(1).describe("Search query"),
      },
      {
        name: "providers",
        type: "Query",
        schema: providers__2,
      },
    ],
    response: FAProviderSearchResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/assets/query",
    alias: "list_assets_api_v1_assets_query_get",
    description: `List all assets with optional filters - enhanced for BRIM asset matching.

**Query Parameters**:
- &#x60;currency&#x60;: Filter by currency code (e.g., &quot;USD&quot;, &quot;EUR&quot;)
- &#x60;asset_type&#x60;: Filter by type enum (STOCK, ETF, BOND, etc.)
- &#x60;active&#x60;: Include only active assets (default: true)
- &#x60;search&#x60;: Search text in display_name (case-insensitive partial match)
- &#x60;isin&#x60;: Exact ISIN match
- &#x60;ticker&#x60;: Exact ticker match
- &#x60;cusip&#x60;: Exact CUSIP match
- &#x60;sedol&#x60;: Exact SEDOL match
- &#x60;figi&#x60;: Exact FIGI match
- &#x60;uuid&#x60;: Exact UUID match
- &#x60;identifier_other&#x60;: Partial match in identifier_other field
- &#x60;identifier_contains&#x60;: Partial match in any identifier

**Response Fields**:
- &#x60;has_provider&#x60;: True if asset has a pricing provider assigned
- &#x60;has_metadata&#x60;: True if asset has classification metadata
- &#x60;identifier&#x60;: Asset identifier (ticker, ISIN, etc.) if provider assigned
- &#x60;identifier_type&#x60;: Type of identifier (TICKER, ISIN, UUID, OTHER)

**Example**:
&#x60;&#x60;&#x60;
GET /api/v1/assets/query?currency&#x3D;USD&amp;asset_type&#x3D;STOCK&amp;search&#x3D;Apple
GET /api/v1/assets/query?isin&#x3D;US0378331005
GET /api/v1/assets/query?ticker&#x3D;AAPL
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "currency",
        type: "Query",
        schema: currency,
      },
      {
        name: "asset_type",
        type: "Query",
        schema: asset_type,
      },
      {
        name: "active",
        type: "Query",
        schema: z
          .boolean()
          .describe("Include only active assets (default: true)")
          .optional()
          .default(true),
      },
      {
        name: "search",
        type: "Query",
        schema: search,
      },
      {
        name: "isin",
        type: "Query",
        schema: isin,
      },
      {
        name: "ticker",
        type: "Query",
        schema: ticker,
      },
      {
        name: "cusip",
        type: "Query",
        schema: cusip,
      },
      {
        name: "sedol",
        type: "Query",
        schema: sedol,
      },
      {
        name: "figi",
        type: "Query",
        schema: figi,
      },
      {
        name: "uuid",
        type: "Query",
        schema: uuid,
      },
      {
        name: "identifier_other",
        type: "Query",
        schema: identifier_other,
      },
      {
        name: "identifier_contains",
        type: "Query",
        schema: identifier_contains,
      },
    ],
    response: z.array(FAinfoResponse),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/change-password",
    alias: "change_password_api_v1_auth_change_password_post",
    description: `Change password for the currently authenticated user.

Requires the current password for verification.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ChangePasswordRequest,
      },
    ],
    response: z
      .object({ message: z.string().default("Password changed successfully") })
      .partial()
      .passthrough(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/login",
    alias: "login_api_v1_auth_login_post",
    description: `Authenticate user and create session.

Accepts username or email in the &#x60;username&#x60; field.
Returns user info and sets session cookie.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AuthLoginRequest,
      },
    ],
    response: AuthLoginResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/logout",
    alias: "logout_api_v1_auth_logout_post",
    description: `Logout current user and destroy session.`,
    requestFormat: "json",
    response: z
      .object({ message: z.string().default("Logged out successfully") })
      .partial()
      .passthrough(),
  },
  {
    method: "get",
    path: "/api/v1/auth/me",
    alias: "get_me_api_v1_auth_me_get",
    description: `Get current authenticated user info.`,
    requestFormat: "json",
    response: AuthMeResponse,
  },
  {
    method: "put",
    path: "/api/v1/auth/profile",
    alias: "update_profile_api_v1_auth_profile_put",
    description: `Update profile for the currently authenticated user.

Allows changing username and/or email.
Validates uniqueness constraints before committing.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UpdateProfileRequest,
      },
    ],
    response: UpdateProfileResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/register",
    alias: "register_api_v1_auth_register_post",
    description: `Register a new user.

Note: The first user registered becomes admin (is_superuser&#x3D;True).
In production, you may want to add email verification.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AuthRegisterRequest,
      },
    ],
    response: AuthRegisterResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/auth/users/me",
    alias: "delete_own_account_api_v1_auth_users_me_delete",
    description: `Delete the currently authenticated user&#x27;s account.

This is a destructive action that:
- Deletes all user data (brokers, transactions, settings)
- Cannot be undone

Constraints:
- Cannot delete if you are the only superuser
- Session is invalidated after deletion`,
    requestFormat: "json",
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/v1/backup/export",
    alias: "export_data_api_v1_backup_export_post",
    description: `Export portfolio data to file.

**Supported Formats:**
- &#x60;json&#x60;: Human-readable JSON file
- &#x60;csv&#x60;: Multiple CSV files in ZIP archive
- &#x60;sqlite&#x60;: Full SQLite database file

**Scope Options:**
- &#x60;all&#x60;: Export everything
- &#x60;transactions&#x60;: Only transactions
- &#x60;assets&#x60;: Only assets and metadata
- &#x60;brokers&#x60;: Only broker definitions
- &#x60;settings&#x60;: Only user settings

**Note:** This endpoint is not yet implemented.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ExportRequest,
      },
    ],
    response: ExportResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/backup/formats",
    alias: "list_export_formats_api_v1_backup_formats_get",
    description: `List available export formats.

Returns information about each supported format.`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/backup/restore",
    alias: "restore_data_api_v1_backup_restore_post",
    description: `Restore portfolio data from backup file.

**Important:**
- If &#x60;overwrite_existing&#x3D;False&#x60; (default), only imports new data
- If &#x60;overwrite_existing&#x3D;True&#x60;, replaces all existing data

**Supported Formats:**
- JSON export files created by &#x60;/export&#x60;
- SQLite database files

**Note:** This endpoint is not yet implemented.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: RestoreRequest,
      },
    ],
    response: RestoreResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/backup/status",
    alias: "backup_status_api_v1_backup_status_get",
    description: `Get backup/export system status.

Returns current implementation status.`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/brokers",
    alias: "create_brokers_api_v1_brokers_post",
    description: `Create multiple brokers.

If initial_balances is provided, automatically creates DEPOSIT
transactions for each currency.

The current user becomes the OWNER of all created brokers.

Args:
    items: List of brokers to create

Returns:
    BRBulkCreateResponse with results for each item`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(BRCreateItem),
      },
    ],
    response: BRBulkCreateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers",
    alias: "list_brokers_api_v1_brokers_get",
    description: `List brokers accessible by the current user.

Superusers can use as_user_id to impersonate another user or see all brokers.

Returns basic broker information without balances.
Use GET /brokers/{id}/summary for full details.

Returns:
    List of brokers ordered by name`,
    requestFormat: "json",
    parameters: [
      {
        name: "as_user_id",
        type: "Query",
        schema: as_user_id,
      },
    ],
    response: z.array(BRReadItem),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/brokers",
    alias: "delete_brokers_api_v1_brokers_delete",
    description: `Delete multiple brokers.

Requires OWNER access to each broker.
Superusers can use as_user_id to impersonate another user.

If force&#x3D;False (default), fails if broker has any transactions.
If force&#x3D;True, cascade deletes all transactions.

Args:
    ids: List of broker IDs to delete
    force: If True, delete broker even if it has transactions

Returns:
    BRBulkDeleteResponse with results`,
    requestFormat: "json",
    parameters: [
      {
        name: "ids",
        type: "Query",
        schema: z.array(z.number().int()).describe("Broker IDs to delete"),
      },
      {
        name: "force",
        type: "Query",
        schema: z
          .boolean()
          .describe("Force delete with transactions")
          .optional()
          .default(false),
      },
      {
        name: "as_user_id",
        type: "Query",
        schema: as_user_id,
      },
    ],
    response: BRBulkDeleteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/:broker_id",
    alias: "get_broker_api_v1_brokers__broker_id__get",
    description: `Get a single broker by ID.

Superusers can use as_user_id to impersonate another user.

Returns basic broker information without balances.
Use GET /brokers/{id}/summary for full details.

Args:
    broker_id: Broker ID

Returns:
    Broker details

Raises:
    HTTPException 404: If broker not found or not accessible`,
    requestFormat: "json",
    parameters: [
      {
        name: "broker_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "as_user_id",
        type: "Query",
        schema: as_user_id,
      },
    ],
    response: BRReadItem,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/brokers/:broker_id",
    alias: "update_broker_api_v1_brokers__broker_id__patch",
    description: `Update a broker.

Only provided fields will be updated.
Requires at least EDITOR access (OWNER or EDITOR can modify).

Superusers can use as_user_id to impersonate another user.

If disabling overdraft/shorting flags, validates that current
balances don&#x27;t violate the new constraints.

Args:
    broker_id: Broker ID to update
    item: Update data

Returns:
    BRBulkUpdateResponse with result`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BRUpdateItem,
      },
      {
        name: "broker_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "as_user_id",
        type: "Query",
        schema: as_user_id,
      },
    ],
    response: BRBulkUpdateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/:broker_id/access",
    alias: "list_broker_access_api_v1_brokers__broker_id__access_get",
    description: `List all users with access to a broker.

Any user with access to the broker can view the access list.
Superusers can view any broker&#x27;s access list.`,
    requestFormat: "json",
    parameters: [
      {
        name: "broker_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: BRAccessListResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "put",
    path: "/api/v1/brokers/:broker_id/access",
    alias: "bulk_update_broker_access_api_v1_brokers__broker_id__access_put",
    description: `Atomically replace the access configuration for a broker.

Sends the COMPLETE desired access list. The backend computes the diff
(adds, updates, removes) and applies all changes in a single transaction.

Rules:
- Only OWNERs (or superusers) can call this endpoint.
- At least one OWNER must remain after the operation.
- Only OWNERs can have share_percentage &gt; 0.
- Sum of all share_percentage values must be ≤ 1.0 (fraction, not percent).
- The calling user cannot remove themselves as the last OWNER.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(BRAccessBulkItem),
      },
      {
        name: "broker_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: BRAccessBulkResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/:broker_id/summary",
    alias: "get_broker_summary_api_v1_brokers__broker_id__summary_get",
    description: `Get broker with full summary.

Superusers can use as_user_id to impersonate another user.

Includes:
- Basic broker info
- Cash balances per currency
- Asset holdings with cost basis and market value

Args:
    broker_id: Broker ID

Returns:
    BRSummary with full details

Raises:
    HTTPException 404: If broker not found or not accessible`,
    requestFormat: "json",
    parameters: [
      {
        name: "broker_id",
        type: "Path",
        schema: z.number().int(),
      },
      {
        name: "as_user_id",
        type: "Query",
        schema: as_user_id,
      },
    ],
    response: BRSummary,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/import/files",
    alias: "list_files_api_v1_brokers_import_files_get",
    description: `List all uploaded broker report files.

Optionally filter by status and/or broker IDs.
Non-superusers can only see files for brokers they have access to.
Results are sorted by upload time (newest first).`,
    requestFormat: "json",
    parameters: [
      {
        name: "status",
        type: "Query",
        schema: status,
      },
      {
        name: "broker_ids",
        type: "Query",
        schema: broker_ids,
      },
    ],
    response: z.array(BRIMFileInfo),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/import/files/:file_id",
    alias: "get_file_api_v1_brokers_import_files__file_id__get",
    description: `Get details for a specific file.

User must have access to the file&#x27;s broker.`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: BRIMFileInfo,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/brokers/import/files/:file_id",
    alias: "delete_file_api_v1_brokers_import_files__file_id__delete",
    description: `Delete a file and its metadata.

Requires EDITOR or OWNER access on the file&#x27;s broker.`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.object({}).partial().passthrough(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/import/files/:file_id/download",
    alias: "download_file_api_v1_brokers_import_files__file_id__download_get",
    description: `Download a file by its ID.

Returns the file content with appropriate headers for download.
Any user with access to the broker can download files (VIEWER+).`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/import/files/:file_id/last-parse",
    alias:
      "get_last_parse_result_api_v1_brokers_import_files__file_id__last_parse_get",
    description: `Get the cached result from the last successful parse.

Useful for reloading a preview without re-parsing the file.
Returns None if no parse result is cached.`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.union([z.object({}).partial().passthrough(), z.null()]),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/brokers/import/files/:file_id/parse",
    alias: "parse_file_api_v1_brokers_import_files__file_id__parse_post",
    description: `Parse a file and return transactions for preview.

This is a preview operation - no data is persisted to the database.
The user can review and modify the parsed transactions before
sending them to POST /transactions endpoint.

Requires EDITOR or OWNER access on the file&#x27;s broker.

If plugin_code is &#x27;auto&#x27; (default), the system will automatically
detect the best plugin based on file content analysis.

Returns:
- transactions: Parsed transactions (may have fake asset IDs)
- asset_mappings: Mapping from fake IDs to candidate real assets
- duplicates: Report of potential duplicate transactions
- warnings: Parser warnings (skipped rows, etc.)

Note: Asset mapping and duplicate detection are done in CORE,
not in the plugin. Plugins only parse the file format.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BRIMParseRequest,
      },
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: BRIMParseResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/brokers/import/plugins",
    alias: "list_plugins_api_v1_brokers_import_plugins_get",
    description: `List all available import plugins.

Returns plugin metadata including code, name, description,
and supported file extensions.`,
    requestFormat: "json",
    response: z.array(BRIMPluginInfo),
  },
  {
    method: "post",
    path: "/api/v1/brokers/import/upload",
    alias: "upload_file_api_v1_brokers_import_upload_post",
    description: `Upload a broker report file for future processing.

The file is saved with a UUID-based name. Compatible plugins are
auto-detected based on file extension and content.

Requires EDITOR or OWNER access on the target broker.

Returns file metadata including compatible plugins.`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({
            file: z.instanceof(File).describe("Broker report file to upload"),
          })
          .passthrough(),
      },
      {
        name: "broker_id",
        type: "Query",
        schema: z.number().int().describe("Target broker ID for this report"),
      },
    ],
    response: BRIMFileInfo,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/fx/currencies/convert",
    alias: "convert_currency_bulk_api_v1_fx_currencies_convert_post",
    description: `Convert one or more amounts between currencies (bulk operation).

This endpoint accepts a list of conversions to perform. Each conversion can specify:
- A single date (start_date only) for single-day conversion
- A date range (start_date + end_date) for multi-day conversion

When a date range is specified, the conversion is automatically expanded to process
each day in the range individually (both start_date and end_date are inclusive).

Uses unlimited backward-fill logic: if rate for exact date is not available,
uses the most recent rate before the requested date.

Args:
    request: List of conversions to perform
    session: Database session

Returns:
    Conversion results with rate information for each conversion (one result per day)`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FXConversionRequest),
      },
    ],
    response: FXConvertResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/fx/currencies/rate",
    alias: "upsert_rates_endpoint_api_v1_fx_currencies_rate_post",
    description: `Manually insert or update one or more FX rates (bulk operation).

This endpoint accepts a list of rates to insert/update.

Uses UPSERT logic: if a rate for the same date/base/quote exists, it will be updated.
Automatic alphabetical ordering and rate inversion is applied.

Args:
    rates: List of rates to insert/update
    session: Database session

Returns:
    Operation results with action taken (inserted/updated) for each rate`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FXUpsertItem),
      },
    ],
    response: FXBulkUpsertResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/fx/currencies/rate",
    alias: "delete_rates_endpoint_api_v1_fx_currencies_rate_delete",
    description: `Delete one or more FX rates (bulk operation).

This endpoint accepts a list of deletion requests. Each request can specify a date range
to delete rates (using DateRangeModel).

Currency pairs are automatically normalized to alphabetical order in the backend,
so deleting USD/EUR will delete the stored EUR/USD rate.

Args:
    deletions: List of deletion requests with date ranges
    session: Database session

Returns:
    Deletion results with counts (existing vs deleted) for each request

Example:
    DELETE /fx/rate-set/bulk
    {
        &quot;deletions&quot;: [
            {
                &quot;from&quot;: &quot;EUR&quot;,
                &quot;to&quot;: &quot;USD&quot;,
                &quot;start_date&quot;: &quot;2025-01-01&quot;
            },
            {
                &quot;from&quot;: &quot;GBP&quot;,
                &quot;to&quot;: &quot;USD&quot;,
                &quot;start_date&quot;: &quot;2025-01-01&quot;,
                &quot;end_date&quot;: &quot;2025-01-05&quot;
            }
        ]
    }`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FXDeleteItem),
      },
    ],
    response: FXBulkDeleteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/fx/currencies/sync",
    alias: "sync_rates_api_v1_fx_currencies_sync_post",
    description: `Synchronize FX rates for specified currency pairs and date range.

**Pair-based sync** — accepts explicit pair slugs (e.g. [&#x27;EUR-USD&#x27;, &#x27;CHF-CNY&#x27;]).
Each pair is synced independently using configured routes from
fx_conversion_routes table, supporting both direct and chain conversions.

Pairs are normalized to alphabetical order (USD-EUR → EUR-USD).

**Status per pair:**
- &#x60;ok&#x60; — provider returned data, inserted/updated in DB
- &#x60;partial&#x60; — provider returned empty or incomplete data
- &#x60;failed&#x60; — all providers for this pair failed
- &#x60;skipped&#x60; — pair is MANUAL-only, nothing to sync

Args:
    body: FXSyncPairRequest with pairs list and date range

Returns:
    FXSyncBulkResponse with per-pair results and summary`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: FXSyncPairRequest,
      },
    ],
    response: FXSyncBulkResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/fx/providers",
    alias: "list_providers_api_v1_fx_providers_get",
    description: `Get the list of available FX rate providers.

Returns information about each provider including:
- Provider code and name
- Default base currency
- All supported base currencies (for multi-base providers)
- All target currencies (from get_supported_currencies)
- Description and icon URL

Note: This endpoint absorbed the former GET /fx/currencies endpoint.
Target currencies are now returned per-provider instead of a separate call.

Installed providers: MANUAL, BOE, FED, ECB, SNB

Use the &#x60;providers&#x60; query parameter to filter by specific provider codes.`,
    requestFormat: "json",
    parameters: [
      {
        name: "providers",
        type: "Query",
        schema: providers,
      },
    ],
    response: z.array(FXProviderInfo),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/fx/providers/routes",
    alias: "list_routes_api_v1_fx_providers_routes_get",
    description: `Get the list of configured conversion routes.

Returns all configured routes ordered by base, quote, and priority.
Each route contains chain_steps describing how to compute the rate.

Returns:
    List of conversion route configurations`,
    requestFormat: "json",
    response: FXConversionRoutesResponse,
  },
  {
    method: "post",
    path: "/api/v1/fx/providers/routes",
    alias: "create_routes_bulk_api_v1_fx_providers_routes_post",
    description: `Create or update multiple conversion routes in a single atomic transaction.

Validations:
- base &lt; quote (alphabetical ordering)
- Provider codes must be registered in FXProviderRegistry
- Chain steps must be valid (continuity, no repeated edges, matching endpoints)

Args:
    routes: List of routes to create/update
    session: Database session

Returns:
    Results for each route operation`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FXConversionRouteItem),
      },
    ],
    response: FXCreateRoutesResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/fx/providers/routes",
    alias: "delete_routes_bulk_api_v1_fx_providers_routes_delete",
    description: `Delete multiple conversion routes.

If priority is specified, deletes only that specific priority level.
If priority is omitted, deletes ALL priorities for that pair.

Args:
    routes: List of FXDeleteRouteItem to delete
    session: Database session

Returns:
    FXDeleteRoutesResponse with results for each deletion operation`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(FXDeleteRouteItem),
      },
    ],
    response: FXDeleteRoutesResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/settings/global",
    alias: "list_global_settings_api_v1_settings_global_get",
    description: `List all global settings.

Public read access - anyone can view global settings.`,
    requestFormat: "json",
    response: GlobalSettingsListResponse,
  },
  {
    method: "get",
    path: "/api/v1/settings/global/:key",
    alias: "get_global_setting_endpoint_api_v1_settings_global__key__get",
    description: `Get a specific global setting by key.

Public read access.`,
    requestFormat: "json",
    parameters: [
      {
        name: "key",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: GlobalSettingRead,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "put",
    path: "/api/v1/settings/global/:key",
    alias: "update_global_setting_endpoint_api_v1_settings_global__key__put",
    description: `Update a global setting.

Admin only - requires is_superuser&#x3D;True.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ value: z.string().describe("New value (as string)") })
          .passthrough(),
      },
      {
        name: "key",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: GlobalSettingRead,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/settings/global/initialize",
    alias:
      "initialize_global_settings_endpoint_api_v1_settings_global_initialize_post",
    description: `Initialize global settings with default values.

Admin only. Creates only missing settings.`,
    requestFormat: "json",
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/v1/settings/user",
    alias: "get_user_settings_endpoint_api_v1_settings_user_get",
    description: `Get current user&#x27;s settings.

Creates default settings if they don&#x27;t exist.`,
    requestFormat: "json",
    response: UserSettingsRead,
  },
  {
    method: "put",
    path: "/api/v1/settings/user",
    alias: "update_user_settings_endpoint_api_v1_settings_user_put",
    description: `Update current user&#x27;s settings.

All fields are optional. Only provided fields will be updated.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: UserSettingsUpdate,
      },
    ],
    response: UserSettingsRead,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/system/health",
    alias: "health_check_api_v1_system_health_get",
    description: `Health check endpoint for monitoring and load balancers.

Returns:
    dict: Status message with &quot;ok&quot; status`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/system/info",
    alias: "get_system_info_api_v1_system_info_get",
    description: `Get system information including versions and dependencies.

Returns app version, Python version, OS details, and dependency versions.`,
    requestFormat: "json",
    response: SystemInfoResponse,
  },
  {
    method: "post",
    path: "/api/v1/transactions",
    alias: "create_transactions_api_v1_transactions_post",
    description: `Create multiple transactions.

Requires EDITOR or OWNER role on each broker. For linked transactions
(TRANSFER, FX_CONVERSION), use the same link_uuid for both transactions.

Args:
    items: List of transactions to create

Returns:
    TXBulkCreateResponse with results for each item`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(TXCreateItem_Input),
      },
    ],
    response: TXBulkCreateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/transactions",
    alias: "query_transactions_api_v1_transactions_get",
    description: `Query transactions with filters.

All filters are optional. Results ordered by date desc, id desc.

Args:
    broker_id: Filter by broker
    asset_id: Filter by asset
    types: Filter by transaction types
    date_start: Filter by start date (inclusive)
    date_end: Filter by end date (inclusive)
    tags: Filter by tags (any match)
    currency: Filter by currency code
    limit: Max results (default 100, max 1000)
    offset: Offset for pagination (first index to of list return (use if limit is low then the total size of the assets, to move the show window)

Returns:
    List of matching transactions`,
    requestFormat: "json",
    parameters: [
      {
        name: "broker_id",
        type: "Query",
        schema: broker_id,
      },
      {
        name: "asset_id",
        type: "Query",
        schema: asset_id,
      },
      {
        name: "types",
        type: "Query",
        schema: types,
      },
      {
        name: "date_start",
        type: "Query",
        schema: date_start,
      },
      {
        name: "date_end",
        type: "Query",
        schema: date_end,
      },
      {
        name: "tags",
        type: "Query",
        schema: tags,
      },
      {
        name: "currency",
        type: "Query",
        schema: currency__2,
      },
      {
        name: "limit",
        type: "Query",
        schema: z
          .number()
          .int()
          .gte(1)
          .lte(1000)
          .describe("Max results")
          .optional()
          .default(100),
      },
      {
        name: "offset",
        type: "Query",
        schema: z
          .number()
          .int()
          .gte(0)
          .describe("Offset for pagination")
          .optional()
          .default(0),
      },
    ],
    response: z.array(TXReadItem),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/transactions",
    alias: "update_transactions_api_v1_transactions_patch",
    description: `Update multiple transactions.

Only provided fields will be updated.
Type cannot be changed. related_transaction_id cannot be updated directly.

Args:
    items: List of updates (each must include id)

Returns:
    TXBulkUpdateResponse with results for each item`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.array(TXUpdateItem),
      },
    ],
    response: TXBulkUpdateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/transactions",
    alias: "delete_transactions_api_v1_transactions_delete",
    description: `Delete multiple transactions.

For linked transactions, both must be included in the delete request.
Validates balances after deletion.

Args:
    ids: List of transaction IDs to delete

Returns:
    TXBulkDeleteResponse with results`,
    requestFormat: "json",
    parameters: [
      {
        name: "ids",
        type: "Query",
        schema: z.array(z.number().int()).describe("Transaction IDs to delete"),
      },
    ],
    response: TXBulkDeleteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/transactions/:tx_id",
    alias: "get_transaction_api_v1_transactions__tx_id__get",
    description: `Get a single transaction by ID.

Args:
    tx_id: Transaction ID

Returns:
    Transaction details

Raises:
    HTTPException 404: If transaction not found`,
    requestFormat: "json",
    parameters: [
      {
        name: "tx_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: TXReadItem,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/transactions/types",
    alias: "get_transaction_types_api_v1_transactions_types_get",
    description: `Get metadata for all transaction types.

Returns icons, descriptions, and validation rules for each type.
Frontend uses this to validate user input and show correct UI.

Returns:
    List of transaction type metadata`,
    requestFormat: "json",
    response: z.array(TXTypeMetadata),
  },
  {
    method: "post",
    path: "/api/v1/uploads",
    alias: "upload_file_api_v1_uploads_post",
    description: `Upload a file.

Files are stored with UUID-based names for security.
Executable files and scripts are blocked.

Args:
    file: File to upload
    description: Optional description

Returns:
    UploadResponse with file info

Raises:
    400: If file type is not allowed (executable/script)
    413: If file is too large`,
    requestFormat: "form-data",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: Body_upload_file_api_v1_uploads_post,
      },
    ],
    response: UploadResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/uploads",
    alias: "list_files_api_v1_uploads_get",
    description: `List all uploaded files.

Args:
    my_files_only: If True, only show files uploaded by current user

Returns:
    List of files with metadata`,
    requestFormat: "json",
    parameters: [
      {
        name: "my_files_only",
        type: "Query",
        schema: z.boolean().optional().default(false),
      },
    ],
    response: UploadListResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/uploads/:file_id",
    alias: "get_file_info_api_v1_uploads__file_id__get",
    description: `Get metadata for a specific file.

Args:
    file_id: File UUID

Returns:
    File metadata`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: UploadFileInfo,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/uploads/:file_id",
    alias: "delete_file_api_v1_uploads__file_id__delete",
    description: `Delete an uploaded file.

Users can only delete their own files unless they are superuser.

Args:
    file_id: File UUID

Returns:
    Deletion confirmation`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: UploadDeleteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/uploads/file/:file_id",
    alias: "serve_file_api_v1_uploads_file__file_id__get",
    description: `Serve the actual file content.

This endpoint does not require authentication to allow
embedding in images/documents.

Preview modes:
- Text preview: ?offset&#x3D;0&amp;window&#x3D;1000 (returns first 1000 chars)
- Image preview: ?img_preview&#x3D;200x200 (returns resized image, max dimension)

Args:
    file_id: File UUID
    download: If True, force download with original filename
    offset: Start byte for text preview (text files only)
    window: Number of bytes to read for text preview (text files only)
    img_preview: Image resize format &quot;WIDTHxHEIGHT&quot; (images only)

Returns:
    File content with appropriate MIME type

Raises:
    400: If preview params used on incompatible file type
    404: If file not found`,
    requestFormat: "json",
    parameters: [
      {
        name: "file_id",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "download",
        type: "Query",
        schema: z.boolean().optional().default(false),
      },
      {
        name: "offset",
        type: "Query",
        schema: offset,
      },
      {
        name: "window",
        type: "Query",
        schema: offset,
      },
      {
        name: "img_preview",
        type: "Query",
        schema: img_preview,
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/uploads/plugin/:provider_type/:path",
    alias:
      "serve_plugin_static_api_v1_uploads_plugin__provider_type___path__get",
    description: `Serve static assets from plugin directories.

Plugin developers can place static files (icons, images, etc.)
in their plugin&#x27;s static/ folder.

Structure:
    brim_providers/static/{path}
    fx_providers/static/{path}
    asset_source_providers/static/{path}

Example URLs:
    /api/v1/uploads/plugin/brim/directa/logo.png
    /api/v1/uploads/plugin/fx/ecb/icon.svg
    /api/v1/uploads/plugin/asset/yfinance/logo.png

Args:
    provider_type: One of &#x27;brim&#x27;, &#x27;fx&#x27;, &#x27;asset&#x27;
    path: Path to file within static folder

Returns:
    File content`,
    requestFormat: "json",
    parameters: [
      {
        name: "provider_type",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "path",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/users/search",
    alias: "search_users_endpoint_api_v1_users_search_get",
    description: `Search for users by username (ILIKE match). Does NOT expose email for privacy. Optionally excludes users already having access to a specific broker.`,
    requestFormat: "json",
    parameters: [
      {
        name: "q",
        type: "Query",
        schema: z.string().min(2).describe("Search query (min 2 chars)"),
      },
      {
        name: "exclude_broker_id",
        type: "Query",
        schema: exclude_broker_id,
      },
    ],
    response: UserSearchResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/utilities/countries",
    alias: "list_countries_api_v1_utilities_countries_get",
    description: `Get list of all countries with ISO codes and flag emoji.

Returns all ISO-3166 countries with:
- ISO-3166-A3 code (e.g., USA)
- ISO-3166-A2 code (e.g., US)
- Country name in requested language (via Babel)
- Flag emoji (e.g., 🇺🇸)

**Supported Languages**:
- en (English) - default
- it (Italian)
- fr (French)
- es (Spanish)
- Other languages supported by Babel
- Falls back to English if language not supported

**Example Request**:
&#x60;&#x60;&#x60;
GET /api/v1/utilities/countries
GET /api/v1/utilities/countries?language&#x3D;it
&#x60;&#x60;&#x60;

**Response**:
&#x60;&#x60;&#x60;json
{
  &quot;countries&quot;: [
    {&quot;iso3&quot;: &quot;USA&quot;, &quot;iso2&quot;: &quot;US&quot;, &quot;name&quot;: &quot;Stati Uniti&quot;, &quot;flag_emoji&quot;: &quot;🇺🇸&quot;},
    {&quot;iso3&quot;: &quot;ITA&quot;, &quot;iso2&quot;: &quot;IT&quot;, &quot;name&quot;: &quot;Italia&quot;, &quot;flag_emoji&quot;: &quot;🇮🇹&quot;},
    ...
  ],
  &quot;count&quot;: 249,
  &quot;language&quot;: &quot;it&quot;
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "language",
        type: "Query",
        schema: z
          .string()
          .describe("Language for country names (default: en)")
          .optional()
          .default("en"),
      },
    ],
    response: CountryListResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/utilities/countries/normalize",
    alias: "normalize_country_api_v1_utilities_countries_normalize_get",
    description: `Normalize country name/code to ISO-3166-A3 format.

Accepts:
- ISO-3166-A3 codes (e.g., USA, GBR)
- ISO-3166-A2 codes (e.g., US, GB)
- Country names (e.g., &quot;United States&quot;, &quot;Italy&quot;)
- Regions (e.g., &quot;EUR&quot;, &quot;ASIA&quot;) - returns list of countries

**Example Requests**:
&#x60;&#x60;&#x60;
GET /api/v1/utilities/countries/normalize?name&#x3D;USA
GET /api/v1/utilities/countries/normalize?name&#x3D;Italy
GET /api/v1/utilities/countries/normalize?name&#x3D;EUR
&#x60;&#x60;&#x60;

**Response**:
&#x60;&#x60;&#x60;json
{
  &quot;query&quot;: &quot;Italy&quot;,
  &quot;iso3_codes&quot;: [&quot;ITA&quot;],
  &quot;match_type&quot;: &quot;exact&quot;
}
&#x60;&#x60;&#x60;

For regions like EUR, ASIA, G7, returns multiple countries:
&#x60;&#x60;&#x60;json
{
  &quot;query&quot;: &quot;G7&quot;,
  &quot;iso3_codes&quot;: [&quot;USA&quot;, &quot;CAN&quot;, &quot;GBR&quot;, &quot;DEU&quot;, &quot;FRA&quot;, &quot;ITA&quot;, &quot;JPN&quot;],
  &quot;match_type&quot;: &quot;region&quot;
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "name",
        type: "Query",
        schema: z.string().min(1).describe("Country name or code to normalize"),
      },
    ],
    response: CountryNormalizationResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/utilities/currencies",
    alias: "list_currencies_api_v1_utilities_currencies_get",
    description: `Get list of all currencies with ISO codes, names, and symbols.

Returns all ISO 4217 currencies with:
- ISO 4217 code (e.g., USD, EUR)
- Currency name in requested language (via Babel)
- Currency symbol (e.g., $, €)

**Supported Languages**:
- en (English) - default
- it (Italian)
- fr (French)
- es (Spanish)
- Other languages supported by Babel
- Falls back to English if language not supported

**Example Request**:
&#x60;&#x60;&#x60;
GET /api/v1/utilities/currencies
GET /api/v1/utilities/currencies?language&#x3D;it
&#x60;&#x60;&#x60;

**Response**:
&#x60;&#x60;&#x60;json
{
  &quot;currencies&quot;: [
    {&quot;code&quot;: &quot;USD&quot;, &quot;name&quot;: &quot;Dollaro statunitense&quot;, &quot;symbol&quot;: &quot;$&quot;},
    {&quot;code&quot;: &quot;EUR&quot;, &quot;name&quot;: &quot;Euro&quot;, &quot;symbol&quot;: &quot;€&quot;},
    ...
  ],
  &quot;count&quot;: 182,
  &quot;language&quot;: &quot;it&quot;
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "language",
        type: "Query",
        schema: z
          .string()
          .describe("Language for currency names (default: en)")
          .optional()
          .default("en"),
      },
    ],
    response: CurrencyListResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/utilities/currencies/normalize",
    alias:
      "normalize_currency_endpoint_api_v1_utilities_currencies_normalize_get",
    description: `Normalize currency name/code/symbol to ISO 4217 format.

Accepts:
- ISO 4217 codes (e.g., USD, EUR)
- Currency symbols (e.g., $, €, £)
- Currency names in requested language (e.g., &quot;Dollar&quot;, &quot;Euro&quot;)

**Example Requests**:
&#x60;&#x60;&#x60;
GET /api/v1/utilities/currencies/normalize?name&#x3D;USD
GET /api/v1/utilities/currencies/normalize?name&#x3D;$
GET /api/v1/utilities/currencies/normalize?name&#x3D;Dollar&amp;language&#x3D;en
&#x60;&#x60;&#x60;

**Response for exact match**:
&#x60;&#x60;&#x60;json
{
  &quot;query&quot;: &quot;EUR&quot;,
  &quot;iso_codes&quot;: [&quot;EUR&quot;],
  &quot;match_type&quot;: &quot;exact&quot;,
  &quot;error&quot;: null
}
&#x60;&#x60;&#x60;

**Response for ambiguous symbol**:
&#x60;&#x60;&#x60;json
{
  &quot;query&quot;: &quot;$&quot;,
  &quot;iso_codes&quot;: [&quot;USD&quot;, &quot;CAD&quot;, &quot;AUD&quot;, &quot;NZD&quot;, &quot;HKD&quot;, &quot;SGD&quot;, &quot;MXN&quot;],
  &quot;match_type&quot;: &quot;symbol_ambiguous&quot;,
  &quot;error&quot;: &quot;Symbol &#x27;$&#x27; matches multiple currencies&quot;
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "name",
        type: "Query",
        schema: z
          .string()
          .min(1)
          .describe("Currency code, symbol, or name to normalize"),
      },
      {
        name: "language",
        type: "Query",
        schema: z
          .string()
          .describe("Language for name matching (default: en)")
          .optional()
          .default("en"),
      },
    ],
    response: CurrencyNormalizationResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/utilities/sectors",
    alias: "list_sectors_api_v1_utilities_sectors_get",
    description: `Get list of all standard financial sectors.

Returns the list of sectors that the system recognizes and stores.
Based on GICS (Global Industry Classification Standard).

**Example Request**:
&#x60;&#x60;&#x60;
GET /api/v1/utilities/sectors
GET /api/v1/utilities/sectors?include_other&#x3D;false
&#x60;&#x60;&#x60;

**Response**:
&#x60;&#x60;&#x60;json
{
  &quot;sectors&quot;: [
    &quot;Industrials&quot;,
    &quot;Technology&quot;,
    &quot;Financials&quot;,
    &quot;Consumer Discretionary&quot;,
    &quot;Health Care&quot;,
    &quot;Real Estate&quot;,
    &quot;Basic Materials&quot;,
    &quot;Energy&quot;,
    &quot;Consumer Staples&quot;,
    &quot;Telecommunication&quot;,
    &quot;Utilities&quot;,
    &quot;Other&quot;
  ],
  &quot;count&quot;: 12
}
&#x60;&#x60;&#x60;`,
    requestFormat: "json",
    parameters: [
      {
        name: "include_other",
        type: "Query",
        schema: z
          .boolean()
          .describe("Include 'Other' in the list")
          .optional()
          .default(true),
      },
    ],
    response: SectorListResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/mkdocs",
    alias: "mkdocs_root_mkdocs_get",
    requestFormat: "json",
    response: z.void(),
  },
  {
    method: "get",
    path: "/mkdocs/:path",
    alias: "mkdocs_static_mkdocs__path__get",
    requestFormat: "json",
    parameters: [
      {
        name: "path",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
