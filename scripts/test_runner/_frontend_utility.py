"""Frontend utility & component E2E tests: auth, settings, files, select, image-crop, utilities."""

import os
import subprocess

from . import _common
from ._common import Colors, _get_category_tests_for_all, _run_test_suite, add_test, make_category, print_error, print_header, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope


def front_utility_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run core store + shared input/select primitive unit tests (Vitest).

    Supplied name-pattern regexes are OR-joined; no names runs the full catalog.
    """
    print(f"\n{Colors.BLUE}Running: Core store Vitest unit tests{Colors.NC}")
    if test_names:
        print(f"{Colors.YELLOW}Filter: {' | '.join(test_names)}{Colors.NC}")
    result = subprocess.run(
        [
            "npx",
            "vitest",
            "run",
            "src/lib/stores/core/entityStore.test.ts",
            "src/lib/stores/app/onboarding.test.ts",
            "src/lib/stores/app/privacyStore.test.ts",
            "src/lib/stores/app/privacyStoreSsr.test.ts",
            "src/lib/stores/app/navigationStore.test.ts",
            "src/lib/stores/app/settings.test.ts",
            "src/lib/stores/app/language.test.ts",
            "src/lib/components/ui/select/optionFilter.test.ts",
            "src/lib/utils/__tests__/dateArrowStep.test.ts",
            "src/lib/utils/__tests__/dateOnly.test.ts",
            "src/lib/utils/__tests__/internalPath.test.ts",
            "src/lib/utils/__tests__/parseDecimalInput.test.ts",
            "src/lib/utils/__tests__/parseTypedDate.test.ts",
            "src/lib/utils/__tests__/requestConcurrency.test.ts",
            "src/lib/api/bulkBatches.test.ts",
            "src/lib/api/bulkRefusal.test.ts",
            "src/lib/utils/__tests__/urlFilters.test.ts",
            "src/lib/utils/__tests__/trySave.test.ts",
            "src/lib/utils/layout/headerScroll.test.ts",
            "src/lib/utils/security/connectionSecurity.test.ts",
            "src/lib/charts/__tests__/loadComparisonData.test.ts",
            "src/lib/charts/__tests__/signalLabel.test.ts",
            "src/lib/charts/__tests__/chartPageSignals.test.ts",
            "src/lib/services/fxCreationSync.test.ts",
            "src/lib/utils/sync/__tests__/syncToastHelpers.test.ts",
            "src/lib/utils/sync/__tests__/syncRange.test.ts",
            "src/lib/utils/sync/__tests__/syncHelpers.test.ts",
            "src/lib/stores/reference/fxRoutesStore.test.ts",
            "src/lib/utils/core/__tests__/formatDecimal.test.ts",
            "src/lib/utils/core/__tests__/escapeHtml.test.ts",
            "src/lib/utils/core/__tests__/entityLink.test.ts",
            "src/lib/utils/core/__tests__/translateOr.test.ts",
            "src/lib/utils/core/__tests__/formatPercent.test.ts",
            "src/lib/utils/core/__tests__/formatFixed.test.ts",
            "src/lib/stores/app/uiLocale.test.ts",
            "src/lib/utils/files/upload.test.ts",
            "src/lib/utils/core/__tests__/positionKey.test.ts",
            "src/lib/utils/core/__tests__/finiteNumber.test.ts",
            "src/lib/utils/core/__tests__/formatAxisDate.test.ts",
            "src/lib/utils/core/__tests__/resizeWatcher.test.ts",
            "src/lib/utils/core/__tests__/clickOutside.test.ts",
            "src/lib/utils/core/__tests__/formatDateTime.test.ts",
            "src/lib/utils/core/__tests__/clearTimer.test.ts",
            "src/lib/utils/__tests__/text.test.ts",
            "src/lib/types/__tests__/safeAccessors.test.ts",
            "src/lib/features/transactions/import/importDedup.test.ts",
            "src/lib/features/transactions/import/importMerge.test.ts",
            "src/lib/features/transactions/import/importCompare.test.ts",
            "src/lib/features/transactions/resolveValidationMessage.test.ts",
            "src/lib/features/transactions/resolveValidationMessage.decimals.test.ts",
            "src/lib/features/transactions/txDisplayHelpers.test.ts",
            "src/lib/features/transactions/commitRefusal.test.ts",
            "src/lib/features/transactions/resolveBrimNotice.test.ts",
            "src/lib/features/transactions/events/eventTypes.test.ts",
            "src/lib/features/transactions/form/signHintColor.test.ts",
            "src/lib/features/transactions/import/importResolutionHelpers.test.ts",
            "src/lib/features/transactions/import/importRowState.test.ts",
            "src/lib/features/transactions/import/importDuplicateResolver.test.ts",
            "src/lib/features/transactions/form/txFormFields.test.ts",
            "src/lib/components/charts/echartsTooltipHelpers.test.ts",
            "src/lib/components/charts/echartsAnimationConfig.test.ts",
            "src/lib/components/charts/echartsZoomPan.test.ts",
            "src/lib/components/charts/geographyMapHelpers.test.ts",
            "src/lib/components/charts/priceChartHelpers.test.ts",
            "src/lib/components/charts/candlestickChartHelpers.test.ts",
            "src/lib/components/charts/chartSignalsHelpers.test.ts",
            "src/lib/components/charts/lineChartHelpers.sessionGaps.test.ts",
            "src/lib/components/charts/scatterChartHelpers.test.ts",
            "src/lib/features/risk/riskAnalysisHelpers.test.ts",
            "src/lib/features/risk/correlationHelpers.test.ts",
            "src/lib/features/risk/assetSetSelection.test.ts",
            "src/lib/features/risk/eligibility.test.ts",
            "src/lib/features/risk/matrixMetadata.test.ts",
            "src/lib/features/risk/assetSetLevels.test.ts",
            "src/lib/features/risk/assetSetI18n.test.ts",
            "src/lib/features/risk/warningTranslatorSites.test.ts",
            "src/lib/features/risk/syncTargets.test.ts",
            "src/lib/features/risk/stressBucketLabel.test.ts",
            "src/lib/components/assets/providerProbe.test.ts",
            "src/lib/components/assets/resolveProviderError.test.ts",
            "src/lib/components/assets/assetIdentifiers.test.ts",
            "src/lib/components/assets/providerComparisonQueue.test.ts",
            "src/lib/components/assets/currencyBlocker.test.ts",
            "src/lib/components/assets/currencyChangeErrors.test.ts",
            "src/lib/components/assets/assetPayload.test.ts",
            "src/lib/components/assets/assetSearchSelection.test.ts",
            "src/lib/components/assets/assetSearchSections.test.ts",
            "src/lib/components/assets/assetSearchReport.test.ts",
            "src/lib/components/assets/assetDataSaveSummary.test.ts",
            "src/lib/components/assets/assetMetadataComparison.test.ts",
            "src/lib/components/assets/assetFormState.test.ts",
            "src/lib/components/assets/scheduleSerialization.test.ts",
            "src/lib/components/assets/assetBrowse.test.ts",
            "src/lib/components/assets/detail/assetDetailPriceQuery.test.ts",
            "src/lib/components/assets/detail/assetDetailChartPoints.test.ts",
            "src/lib/components/assets/detail/assetDetailFxPair.test.ts",
            "src/lib/components/assets/detail/assetDetailFxRequirements.test.ts",
            "src/lib/components/assets/detail/assetDetailLive.svelte.test.ts",
            "src/lib/components/table/dataTableLogic.test.ts",
            "src/lib/features/transactions/resolveFormItems.test.ts",
            "src/lib/features/transactions/events/eventSaveError.test.ts",
            "src/lib/utils/files/imageCrop.test.ts",
            "src/lib/utils/files/pdfPreviewState.test.ts",
            "src/lib/utils/files/pdfViewerAssets.test.ts",
            "src/lib/utils/currency/fxConversionHelper.test.ts",
            "src/lib/utils/currency/currencyFormat.test.ts",
            "src/lib/utils/privacy/maskable.test.ts",
            "src/lib/utils/privacy/moneyRenderSites.test.ts",
            "src/routes/documentTitle.guard.test.ts",
            "src/htmlInterpolation.gate.test.ts",
            "src/htmlSink.gate.test.ts",
            "src/clipboardSink.gate.test.ts",
            "src/themeColorMeta.gate.test.ts",
            "src/themeComponentTokens.gate.test.ts",
            "src/themeModeReads.gate.test.ts",
            "src/themeRoles.gate.test.ts",
            "src/themeTokens.gate.test.ts",
            "src/instanceProfile.gate.test.ts",
            "src/lib/api/dashboardReportFixture.test.ts",
            "src/lib/theme/colorAlpha.test.ts",
            "src/lib/theme/chartTheme.test.ts",
            "src/lib/theme/themeMode.test.ts",
            "src/lib/theme/chartCategories.test.ts",
            "src/lib/theme/chartShades.test.ts",
            "src/lib/theme/contrast.test.ts",
            "src/lib/theme/roleColors.test.ts",
            "src/lib/theme/drawnColors.test.ts",
            "src/lib/theme/roleColors.dom.test.ts",
            "src/lib/features/brokers/lots/lotChartShared.test.ts",
            "src/lib/features/brokers/lots/lotWacPriceChartHelpers.test.ts",
            "src/lib/features/brokers/lots/lotComparisonChartHelpers.test.ts",
            "src/lib/features/brokers/lots/lotGanttChartHelpers.test.ts",
            "src/lib/features/brokers/lots/lotStateVisual.test.ts",
            "src/lib/features/brokers/lots/unifiedLotsTableHelpers.test.ts",
            "src/lib/features/brokers/lots/lotCustodyModalHelpers.test.ts",
            "src/lib/features/brokers/lots/lotCustodyModalHelpers.closureValueLabel.test.ts",
            "src/lib/features/brokers/lots/lotsAnalysisHelpers.test.ts",
            "src/lib/features/brokers/lots/lotDataQualityHelpers.test.ts",
            "src/lib/stores/chartSettingsStore.test.ts",
            "src/lib/stores/chartSettingsStoreSsr.test.ts",
            "src/lib/stores/chartSettingsStore.migration.test.ts",
            "src/lib/stores/reference/brokerStore.test.ts",
            "src/lib/stores/reference/brokerStoreIconHydration.test.ts",
            "src/lib/stores/reference/sectorStore.test.ts",
            "src/lib/features/changelog/changelog.test.ts",
            "src/lib/features/update-check/updateCheck.test.ts",
            "src/lib/features/update-check/updateCheck.managed.test.ts",
            "src/lib/features/support/donations.test.ts",
            "src/lib/features/onboarding/guideAnchors.test.ts",
            "src/lib/features/onboarding/onboardingTourSurfaces.test.ts",
            "src/lib/features/onboarding/guideCopy.test.ts",
            "src/lib/features/tools/client.test.ts",
            "src/lib/features/tools/registry.test.ts",
            "src/lib/features/tools/pac-allocator/planner/decimal.test.ts",
            "src/lib/features/tools/pac-allocator/planner/format.test.ts",
            "src/lib/features/tools/pac-allocator/planner/modeText.test.ts",
            "src/lib/features/tools/pac-allocator/planner/categoryLabels.test.ts",
            "src/lib/features/tools/pac-allocator/planner/result/exposureBarColours.test.ts",
            "src/lib/features/tools/pac-allocator/planner/pluralCountSites.test.ts",
            "src/lib/features/tools/pac-allocator/planner/source.test.ts",
            "src/lib/i18n/catalogIcuLocale.test.ts",
            "src/lib/i18n/riskGlossary.test.ts",
            "src/lib/i18n/importWizardAssetsCount.test.ts",
            "src/lib/features/support/supportLinks.test.ts",
            "src/lib/features/settings/settingsTabs.test.ts",
            "src/lib/features/settings/security/securityChecksApi.test.ts",
            "src/lib/features/settings/security/securityFindings.test.ts",
            "src/lib/features/settings/security/securityChecks.test.ts",
            "src/lib/features/plugin-settings/pluginSettingsForm.test.ts",
            "src/lib/features/plugin-settings/pluginSettingsApi.test.ts",
            "src/lib/features/settings/users/linkShare.test.ts",
            "src/lib/features/settings/users/addressProbe.test.ts",
            "src/lib/features/settings/users/accountErrors.test.ts",
            "src/lib/features/instance/instanceConfig.test.ts",
            "src/lib/features/instance/profile.test.ts",
            "src/lib/features/instance/instanceNotices.test.ts",
            "src/lib/features/auth/authFlash.test.ts",
            "src/lib/features/auth/linkToken.test.ts",
            "src/lib/features/auth/registrationErrors.test.ts",
            "src/lib/features/auth/passwordRules.test.ts",
            "src/lib/features/auth/emailCase.test.ts",
            "src/lib/features/auth/localHost.test.ts",
            "src/lib/features/auth/openRegistrationNotice.test.ts",
            "src/lib/features/instance/instanceBlock.test.ts",
            "src/lib/api/zodios-client.test.ts",
            "src/lib/api/apiClientRuneFree.gate.test.ts",
            "src/lib/features/live-updates/activityTracker.test.ts",
            "src/lib/features/live-updates/activePolling.test.ts",
            "src/lib/services/livePriceService.test.ts",
            "src/lib/features/price-refresh/priceRefresh.test.ts",
            "src/lib/features/email/emailText.test.ts",
            "src/lib/features/email/emailApi.test.ts",
            "src/lib/features/email/emailLinks.test.ts",
            "src/lib/features/email/verificationApi.test.ts",
            "src/lib/features/email/sendLinkApi.test.ts",
            "src/lib/features/email/forgotPasswordApi.test.ts",
            "src/lib/stores/app/auth.verification.test.ts",
            "src/lib/features/auth/registrationErrors.verification.test.ts",
            "src/lib/features/backup/backupApi.test.ts",
            "src/lib/features/backup/backupJob.test.ts",
            "src/lib/features/backup/restoreFlow.test.ts",
            "src/lib/features/backup/restoreI18n.test.ts",
            "src/lib/charts/signals/__tests__/registry.test.ts",
            "src/lib/charts/signals/__tests__/syntheticSignals.test.ts",
            "src/lib/charts/signals/__tests__/syntheticSignals.languageSwitch.test.ts",
            "src/lib/charts/signals/__tests__/comparisonSignals.test.ts",
            "src/lib/charts/signals/__tests__/comparisonSignalPages.test.ts",
            "src/lib/charts/signals/__tests__/measureSignal.test.ts",
            "src/lib/charts/signals/__tests__/signalProblemSeverity.test.ts",
            "src/lib/charts/signals/__tests__/catalogPartitions.test.ts",
            "src/lib/charts/signals/__tests__/backendRendererSegments.test.ts",
            *(["-t", "|".join(test_names)] if test_names else []),
        ],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Core store Vitest unit tests - PASSED")
        return True

    print_error(f"Core store Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_component_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Svelte component unit tests (Vitest + jsdom).

    Kept separate from ``core-unit`` on purpose. These mount real ``.svelte``
    components in a simulated DOM, so they need the jsdom environment and the
    testing-library harness, and they cover a surface — the UI primitives — that
    E2E reaches only incidentally, if at all. Splitting them also means the two
    families can be run, timed and parallelised independently.

    Supplied ``test_names`` are Vitest name-pattern regexes, combined with OR.
    With no names, the entire registered file catalog runs unchanged.
    """
    print(f"\n{Colors.BLUE}Running: Svelte component unit tests (jsdom){Colors.NC}")
    if test_names:
        print(f"{Colors.YELLOW}Filter: {' | '.join(test_names)}{Colors.NC}")
    result = subprocess.run(
        [
            "npx",
            "vitest",
            "run",
            "src/lib/components/ui/date/CalendarMonth.test.ts",
            "src/lib/components/ui/date/SingleDatePicker.test.ts",
            "src/lib/components/ui/date/DateRangePicker.test.ts",
            "src/lib/components/ui/input/ExactDecimalInput.test.ts",
            "src/lib/components/ui/input/ExactQuantityInput.test.ts",
            "src/lib/components/ui/input/TagInput.test.ts",
            "src/lib/components/ui/input/PasswordInput.test.ts",
            "src/lib/components/ui/input/PasswordStrength.test.ts",
            "src/lib/components/ui/select/SimpleSelect.test.ts",
            "src/lib/components/ui/select/SearchSelect.test.ts",
            "src/lib/components/ui/select/SearchSelect.reopen.test.ts",
            "src/lib/components/ui/select/CurrencySearchSelect.test.ts",
            "src/lib/components/ui/select/FxProviderSelect.test.ts",
            "src/lib/components/ui/select/TreeSelect.test.ts",
            "src/lib/components/ui/select/AssetTypeSelect.test.ts",
            "src/lib/components/ui/select/AssetPickerPanel.test.ts",
            "src/lib/components/ui/data-editor/DataEditor.test.ts",
            "src/lib/components/ui/media/AssetPickerModal.test.ts",
            "src/lib/components/ui/media/ImageEditModal.test.ts",
            "src/lib/components/ui/modals/SyncModalBase.test.ts",
            "src/lib/components/ui/modals/ModalBase.test.ts",
            "src/lib/components/ui/modals/ModalBase.escapeLayers.test.ts",
            "src/lib/components/ui/modals/SyncResultRow.test.ts",
            "src/lib/components/ui/media/FileEditModal.test.ts",
            "src/lib/components/ui/media/FileUploader.test.ts",
            "src/lib/components/ui/modals/PageSyncModal.test.ts",
            "src/lib/components/ui/feedback/ToastContainer.test.ts",
            "src/lib/components/ui/feedback/Tooltip.test.ts",
            "src/lib/components/ui/tabs/TabBar.test.ts",
            "src/lib/components/table/DataTableColumnFilter.test.ts",
            "src/lib/components/table/DataTable.test.ts",
            "src/lib/components/table/DataTable.rowOrder.test.ts",
            "src/lib/components/table/DataTablePagination.test.ts",
            "src/lib/components/assets/ScheduledInvestmentEditor.test.ts",
            "src/lib/components/assets/AssetModal.test.ts",
            "src/lib/components/assets/AssetModal.providerLifecycle.test.ts",
            "src/lib/components/assets/AssetSearchAutocomplete.test.ts",
            "src/lib/components/assets/AssetCurrencyChangeModal.test.ts",
            "src/lib/components/assets/ProviderComparisonModal.test.ts",
            "src/lib/components/assets/CellDateRange.test.ts",
            "src/lib/components/assets/ProviderAssignmentSection.test.ts",
            "src/lib/components/assets/providerProbeState.test.ts",
            "src/lib/components/assets/AssetSyncModal.test.ts",
            "src/lib/components/assets/AssetBrowseNav.test.ts",
            "src/lib/components/assets/detail/AssetDetailSignalsPanel.test.ts",
            "src/lib/components/assets/detail/AssetDetailMeasuresSection.test.ts",
            "src/lib/components/assets/detail/AssetChartModeToggle.test.ts",
            "src/lib/components/assets/detail/AssetCalendarWindowControls.test.ts",
            "src/lib/components/fx/FxSyncModal.test.ts",
            "src/lib/components/fx/FxMissingRate.test.ts",
            "src/lib/components/fx/FxPairAddModal.test.ts",
            "src/lib/features/files/FilePreviewModal.test.ts",
            "src/lib/features/files/FilesTable.test.ts",
            "src/lib/features/files/FileGrid.test.ts",
            "src/lib/features/transactions/import/ImportWizardModal.test.ts",
            "src/lib/features/transactions/import/TransactionCompareModal.test.ts",
            "src/lib/features/transactions/form/TransactionFormModal.test.ts",
            "src/lib/features/transactions/TransactionsTable.privacy.test.ts",
            "src/lib/features/transactions/wac/WacPreviewSection.test.ts",
            "src/lib/features/transactions/events/EventExistsPanel.test.ts",
            "src/lib/features/transactions/events/EventCreateMiniModal.test.ts",
            "src/lib/features/transactions/form/CompactCashCell.test.ts",
            "src/lib/components/ui/display/KpiMetricBar.test.ts",
            "src/lib/components/ui/display/KpiDivergingFlowBar.test.ts",
            "src/lib/components/ui/display/RiskMetricCard.test.ts",
            "src/lib/components/ui/display/RiskCardGrid.test.ts",
            "src/lib/components/ui/display/CurrencyAmount.test.ts",
            "src/lib/components/ui/HeaderToggles.i18n.test.ts",
            "src/lib/components/charts/ChartSignalsSection.test.ts",
            "src/lib/components/charts/SignalTreeSelect.test.ts",
            "src/lib/components/charts/MeasurePanel.test.ts",
            "src/lib/components/charts/PriceChartFull.test.ts",
            "src/lib/components/charts/LineChart.test.ts",
            "src/lib/components/charts/SemiDonutChart.test.ts",
            "src/lib/features/risk/AssetSetLossComparisonSection.test.ts",
            "src/lib/features/risk/AssetSetRiskReturnSection.test.ts",
            "src/lib/components/charts/ScatterChart.test.ts",
            "src/lib/features/risk/AssetSetReplaySection.test.ts",
            "src/lib/features/risk/AssetSetComparisonLevels.test.ts",
            "src/lib/features/risk/AssetSetCorrelationSection.test.ts",
            "src/lib/features/risk/CorrelationHeatmap.test.ts",
            "src/lib/features/risk/AssetChip.test.ts",
            "src/lib/features/auth/RegisterCard.test.ts",
            "src/lib/features/auth/LoginCard.test.ts",
            "src/lib/features/auth/AuthCard.test.ts",
            "src/lib/features/auth/AuthPageFrame.test.ts",
            "src/lib/features/auth/AuthPageFrame.managed.test.ts",
            "src/lib/features/auth/AuthPageFrame.legal.test.ts",
            "src/lib/features/auth/LinkStatusCard.test.ts",
            "src/lib/features/auth/ResetPasswordCard.test.ts",
            "src/lib/features/auth/SetupCard.test.ts",
            "src/routes/page.authFlash.test.ts",
            "src/routes/invite/page.test.ts",
            "src/routes/reset-password/page.test.ts",
            "src/routes/setup/page.test.ts",
            "src/routes/verify-email/page.test.ts",
            "src/lib/features/support/DonationPopupModal.test.ts",
            "src/lib/features/support/SupportActions.test.ts",
            "src/lib/features/support/SupportActions.managed.test.ts",
            "src/lib/features/legal/LegalNotice.test.ts",
            "src/lib/features/legal/LegalLinks.test.ts",
            "src/lib/features/support/SocialShareModal.test.ts",
            "src/lib/features/support/shareNavigation.test.ts",
            "src/lib/utils/clipboard.test.ts",
            "src/lib/utils/core/sanitizeHtml.test.ts",
            "src/lib/features/brokers/BrokerModal.test.ts",
            "src/lib/features/brokers/BrokerSharingPanel.test.ts",
            "src/lib/features/brokers/BrokerCard.test.ts",
            "src/lib/features/brokers/BrokerImportFilesModal.test.ts",
            "src/lib/components/assets/AssetTable.test.ts",
            "src/lib/components/assets/AssetTable.privacy.test.ts",
            "src/lib/features/dashboard/KpiSection.test.ts",
            "src/lib/features/dashboard/ExposureTable.test.ts",
            "src/lib/features/dashboard/ExposureTreemap.test.ts",
            "src/lib/features/dashboard/GrowthChart.tooltip.test.ts",
            "src/lib/features/dashboard/ContributionTable.test.ts",
            "src/lib/features/dashboard/PerformanceChart.test.ts",
            "src/lib/features/dashboard/OtherPeriodEffectsTable.test.ts",
            "src/lib/features/dashboard/AllocationPanel.test.ts",
            "src/lib/components/table/DataTableHeaderTooltip.test.ts",
            "src/lib/features/transactions/import/FixFlaggedStep.test.ts",
            "src/lib/features/transactions/import/ReportSetCard.escape.test.ts",
            "src/lib/components/layout/ChangelogModal.test.ts",
            "src/lib/components/layout/ChangelogModal.managed.test.ts",
            "src/lib/components/layout/Header.test.ts",
            "src/lib/components/layout/Header.managed.test.ts",
            "src/lib/components/layout/HelpMenu.managed.test.ts",
            "src/lib/components/layout/Sidebar.legal.test.ts",
            "src/lib/components/layout/ConnectionSecurityIndicator.test.ts",
            "src/lib/features/update-check/UpdateAvailableModal.test.ts",
            "src/lib/features/settings/SettingControls.test.ts",
            "src/lib/features/settings/SettingsLayout.test.ts",
            "src/lib/features/settings/PasswordChangeModal.test.ts",
            "src/lib/features/settings/SchedulerConfigModal.test.ts",
            "src/lib/features/settings/SchedulerLogModal.test.ts",
            "src/lib/features/settings/AccountDeletionDialog.test.ts",
            "src/lib/features/settings/tabs/PreferencesTab.test.ts",
            "src/lib/features/settings/tabs/ProfileTab.test.ts",
            "src/lib/features/settings/tabs/AboutTab.test.ts",
            "src/lib/features/settings/tabs/AboutTab.legal.test.ts",
            "src/lib/features/settings/tabs/GlobalSettingsTab.test.ts",
            "src/lib/features/settings/tabs/UsersTab.test.ts",
            "src/lib/features/settings/security/SecurityTab.test.ts",
            "src/lib/features/settings/users/LinkShare.component.test.ts",
            "src/lib/features/settings/users/InviteDialog.test.ts",
            "src/lib/features/settings/users/ResetLinkDialog.test.ts",
            "src/lib/features/email/EmailSettingsTab.test.ts",
            "src/lib/features/plugin-settings/PluginSettingsForm.component.test.ts",
            "src/lib/features/plugin-settings/PluginSettingsTab.test.ts",
            "src/lib/features/plugin-settings/PluginSettingsModal.test.ts",
            "src/lib/features/email/VerifyEmailCard.test.ts",
            "src/lib/features/email/VerificationNotice.test.ts",
            "src/lib/features/email/SendLinkByEmail.test.ts",
            "src/lib/features/email/ForgotPasswordEmailForm.test.ts",
            "src/lib/features/email/linkShareRegistration.test.ts",
            "src/lib/features/auth/ForgotPasswordCard.email.test.ts",
            "src/lib/features/auth/ForgotPasswordCard.managed.test.ts",
            "src/lib/features/auth/LoginCard.verification.test.ts",
            "src/lib/features/auth/RegisterCard.verification.test.ts",
            "src/lib/features/settings/tabs/GlobalSettingsTab.verification.test.ts",
            "src/lib/features/settings/users/UserRow.verification.test.ts",
            "src/lib/features/settings/users/UserRow.pendingSetup.test.ts",
            "src/routes/(app)/settings/page.tabs.test.ts",
            "src/lib/features/tools/ToolsHub.test.ts",
            "src/lib/features/tools/ToolHost.test.ts",
            "src/lib/features/tools/pac-allocator/planner/result/StateNotice.test.ts",
            "src/lib/features/tools/pac-allocator/planner/result/ResultCell.test.ts",
            "src/lib/features/tools/pac-allocator/planner/result/ExposureBars.test.ts",
            "src/lib/features/tools/pac-allocator/planner/result/model.test.ts",
            "src/lib/features/tools/pac-allocator/planner/result/text.test.ts",
            "src/lib/features/tools/pac-allocator/planner/request.test.ts",
            "src/lib/components/ui/display/BrokerBadge.test.ts",
            "src/lib/features/instance/components/InstanceNotices.test.ts",
            "src/lib/features/instance/components/InstanceBlockedPage.test.ts",
            "src/lib/features/live-updates/LiveUpdatesStatus.test.ts",
            "src/lib/features/backup/BackupDownloadCard.test.ts",
            "src/lib/features/backup/RestoreCard.test.ts",
            "src/lib/features/backup/RestoreReportModal.test.ts",
            "src/lib/features/backup/RestartOverlay.test.ts",
            *(["-t", "|".join(test_names)] if test_names else []),
        ],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Svelte component unit tests - PASSED")
        return True

    print_error(f"Svelte component unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_onboarding_component_unit(
    verbose: bool = False,
    ui: bool = False,
    headed: bool = False,
    debug: bool = False,
    test_names: list = None,
    coverage: bool = False,
) -> bool:
    """Run the isolated onboarding component tests without importing the full UI catalog."""
    print(f"\n{Colors.BLUE}Running: Onboarding component unit tests{Colors.NC}")
    if test_names:
        print(f"{Colors.YELLOW}Filter: {' | '.join(test_names)}{Colors.NC}")
    result = subprocess.run(
        [
            "npx",
            "vitest",
            "run",
            "src/lib/features/onboarding/components/OnboardingCoachmark.test.ts",
            "src/lib/features/onboarding/components/OnboardingIntroScene.test.ts",
            "src/lib/features/onboarding/components/OnboardingReplaySection.test.ts",
            "src/lib/features/onboarding/components/WelcomeForm.test.ts",
            "src/lib/features/onboarding/components/WelcomePage.test.ts",
            "src/lib/features/onboarding/components/WelcomePage.legal.test.ts",
            "src/lib/features/onboarding/components/DeferredAppPopups.test.ts",
            "src/lib/features/onboarding/onboardingRouteSettlement.test.ts",
            "src/routes/(app)/layout.gate.test.ts",
            "src/routes/(app)/layout.authGate.test.ts",
            "src/lib/components/assets/AssetModal.test.ts",
            "src/lib/features/brokers/BrokerModal.test.ts",
            "src/lib/components/fx/FxPairAddModal.test.ts",
            "src/lib/components/layout/Header.test.ts",
            "src/lib/features/settings/tabs/PreferencesTab.test.ts",
            "src/lib/features/transactions/import/ImportWizardModal.test.ts",
            *(["-t", "|".join(test_names)] if test_names else []),
        ],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Onboarding component unit tests - PASSED")
        return True

    print_error(f"Onboarding component unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_auth(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run auth E2E tests."""
    print_section("Frontend Auth Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("auth.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_auth_links(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the account link pages, /invite, /reset-password (accounts lot A5b) and /setup (A7b)."""
    print_section("Frontend Auth Links Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("auth-links.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_admin_users(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Settings → Users tab (accounts lot A6b): account actions, links and their address check, deletion with preview."""
    print_section("Frontend Admin Users Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings/admin-users.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_security_tab(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Settings › Security tab (accounts lot A8b) and its «Administration» group: the badge, the findings, a re-read; a member's view."""
    print_section("Frontend Security Tab Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings/security-tab.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_legal_managed(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the instance's legal notice (F09) and the managed profile's account-side effects (F05), lot A9: GET /system/instance patched per page."""
    print_section("Frontend Legal Notice & Managed Profile Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/legal-and-managed.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run settings E2E tests."""
    print_section("Frontend Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run files E2E tests."""
    print_section("Frontend Files Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("files.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files_pdf_offline(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the PDF preview with every origin but the lane's refused (1.2 gap 7)."""
    print_section("Frontend Files PDF Offline Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("files-pdf-offline.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files_uploader(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run uploader URL, list/grid and avatar regressions with synthetic APIs."""
    print_section("Frontend Files Uploader Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("files-uploader.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_support_copy_and_go(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run native popup ordering, denied-copy flows and the legacy-copy limit on desktop and mobile."""
    print_section("Frontend Support Copy And Go Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("support-copy-and-go.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_header_scroll(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all-device header geometry and scroll-state regressions."""
    print_section("Frontend Header Scroll Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/header-scroll.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_document_title(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the window-title regression across client-side route changes."""
    print_section("Frontend Document Title Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/document-title.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_theme_roles(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the colour roles of the sign-in page, of its background and of the signed-in app shell, in light and in dark, on desktop and mobile (workstream T, steps T-2, T-3 and T-5)."""
    print_section("Frontend Theme Roles Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/theme-roles.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_pac_allocator_real(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the PAC allocator (beta) end to end on real data (1.2 gap 3) on the desktop project, the runner default."""
    print_section("Frontend PAC Allocator Real-Data Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("pac-allocator-real.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_changelog_locale(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the changelog modal's chapter languages in the Italian and English UI (lot CL, desktop)."""
    print_section("Frontend Changelog Locale Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/changelog-locale.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_toolbar_width_sweep(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Sweep the five PageToolbar bars 1700 → 320 px in English, French, Italian and Spanish, plus the Assets lifecycle pill at phone widths (K step 13, item 5; lot 51)."""
    print_section("Frontend Toolbar Width Sweep Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/toolbar-width-sweep.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_app_start_auth(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the app-start auth gate: a slow /auth/me is not a sign-out, and the login keeps the requested page (K step 19)."""
    print_section("Frontend App Start Auth Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/app-start-auth.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_connection_security(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the connection-security indicator: localhost, a mapped .lan name and a public name, with and without a public source (plan 36)."""
    print_section("Frontend Connection Security Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/connection-security.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_docs_offline_math(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the documentation's formulas without internet: nested pages in English and Italian, MathJax and its fonts from the site's own copy (M-19)."""
    print_section("Frontend Docs Offline Math Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/docs-offline-math.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_page_policy(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the page policy of H-42, injected by the spec as the managed profile sends it: positive controls, then the documentation's search, the PDF preview and the Dashboard with no enforced violation."""
    print_section("Frontend Page Policy Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/page-policy.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


#: The cloud smoke (H-43): existing specs over the main pages and the surfaces the managed profile's policies touch (the
#: PDF preview, forms, frames), run on a managed lane so that the report-only policy's violations reach the collector of
#: e2e/fixtures/playwright.ts. Desktop only. layout/legal-and-managed.spec.ts stays out until its «lane's answer» tests
#: (LGM-E-01, LGM-E-03) read the lane's profile: they pin a self-hosted lane, and fail on a managed one by design.
CLOUD_SMOKE_SPECS = [
    "auth.spec.ts",
    "layout/page-policy.spec.ts",
    "layout/csp-collector.spec.ts",
    "portfolio/dashboard.spec.ts",
    "portfolio/risk-analysis.spec.ts",
    "assets/asset-modal.spec.ts",
    "transactions/transactions-table.spec.ts",
    "transactions/tx-brim-import.spec.ts",
    "files.spec.ts",
    "brokers/brokers.spec.ts",
    "settings/security-tab.spec.ts",
    "settings/admin-users.spec.ts",
    "ai-export/ai-export-panel.spec.ts",
]


def front_csp_collector(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run H-43's collector of Content-Security-Policy violations: its helpers, synthetic pages with a policy of their own, and the app's two inline scripts as the baseline knows them."""
    print_section("Frontend CSP Collector Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/csp-collector.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_cloud_smoke(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the cloud smoke (H-43) on a managed lane: CLOUD_SMOKE_SPECS, desktop, the collector failing on a violation of the report-only policy the baseline does not know."""
    print_section("Frontend Cloud Smoke (managed lane)")
    if os.environ.get("LIBREFOLIO_PROFILE") != "managed":
        print_error("cloud-smoke runs on a managed lane: add --lane-setting LIBREFOLIO_PROFILE=managed")
        return False
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright(CLOUD_SMOKE_SPECS, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_datatable_mobile(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the DataTable's pinned selection and actions columns at phone width: header and cells scroll with the table, the header row still sticks (Y7, D-Y17)."""
    print_section("Frontend DataTable Mobile Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/datatable-mobile.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_datatable_resize(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the DataTable column resize: a mouse drag on an auto-layout column edge moves it by the drag, with a fixed-layout control, and a finger drag on a phone (Y7, C-62, D-Y18)."""
    print_section("Frontend DataTable Resize Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("layout/datatable-resize.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files_destructive(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run files destructive-route E2E tests (single/bulk delete, failure, BRIM)."""
    print_section("Frontend Files Destructive Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("files-destructive.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_select(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run select components E2E tests."""
    print_section("Frontend Select Components Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("select-components.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_image_crop(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run image crop & media components E2E tests."""
    print_section("Frontend Image Crop & Media Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("image-crop.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_utilities(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run utilities API E2E tests."""
    print_section("Frontend Utilities API Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("utilities.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_onboarding_tour(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the onboarding tour on desktop and mobile."""
    print_section("Frontend Onboarding Tour Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("onboarding-tour.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_onboarding_guides(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the contextual onboarding guide walks on desktop and mobile."""
    print_section("Frontend Onboarding Guides Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("onboarding-guides.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_tooltip(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run shared Tooltip component E2E tests (pinned hover/click model)."""
    print_section("Frontend Tooltip Component Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("tooltip-component.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_scheduler(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run scheduler settings E2E tests (admin: config modal, log modal, regression)."""
    print_section("Frontend Scheduler Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings/scheduler.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_email_tab(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Settings › Administration › Email E2E tests (admin tab: the lane's own status, and a test email on a simulated server)."""
    print_section("Frontend Email Settings Tab Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings/email-tab.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_email_verification(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the email-verification E2E tests (sign-up and sign-in on simulated answers; the Settings › Admin switch with GET /system/instance simulated)."""
    print_section("Frontend Email Verification Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("auth-email-verification.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_email_send_link(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the «send by email» E2E tests (Settings › Users share dialogs, GET /system/instance and POST /email/links simulated)."""
    print_section("Frontend Send Link by Email Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings/email-send-link.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_forgot_password_email(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the «forgot password» by email E2E tests (the sign-in page's card, GET /system/instance and POST /email/password-reset simulated)."""
    print_section("Frontend Forgot Password by Email Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("auth-forgot-password-email.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_backup(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Settings › Administration › Backup tab E2E (workstream B, lot B5a) on desktop: the tab for administrators only, a backup created, downloaded, deleted, picked up after a reload."""
    print_section("Frontend Backup Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    # Desktop only (the default project), like every other serial spec: the tab's mobile rendering is the gallery's to cover.
    return _run_playwright("settings/backup.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_plugin_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Settings › Plugins and «Configure» E2E (workstream X, lot CP11c) on desktop: the tab read only, mockprov's settings through the asset dialog, the search's «to configure» row."""
    print_section("Frontend Plugin Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    # Desktop only (the default project): the member and administrator tests write mockprov fields one account each, which a second project in the same invocation would share.
    return _run_playwright("settings/plugin-settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_utility_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, coverage: bool = False) -> bool:
    """Run all frontend utility/component E2E tests."""
    print_header("Frontend Utility Tests (Playwright)")
    if _common.nothing_left_to_run("front-utility"):
        return _common.consolidated_verdict("front-utility")
    reset_setup_scope()
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_test_suite(
        suite_name="Frontend Utility Tests",
        tests=_get_category_tests_for_all("front-utility", verbose, ui=ui, headed=headed, debug=debug, coverage=coverage),
        verbose=verbose,
        header_msg=None,
        summary_title="Frontend Utility Test Summary",
        success_msg="All frontend utility tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend utility test entries."""
    cat = make_category(help_text="Frontend utility & component E2E tests (auth, settings, files, select, image-crop)", description="""Frontend Utility & Component Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "auth", front_auth, name="Auth Tests", desc="Login, register, logout, language change", prereq="Test users created", tests="auth.spec.ts")
    add_test(
        cat,
        "auth-links",
        front_auth_links,
        name="Auth Links Tests",
        desc="The account link pages (accounts lot A5b), on invitations and reset links an administrator issues over the API: the token, in the fragment, leaves the address bar on load; an invitation with an address prefills it (editable), its registration carries the token, ends on the login page with login-success and signs in as an ordinary member, and the same link then reads consumed; an admin invitation shows its notice; revoked and unknown tokens say so; a page without a token reads missing and sends no inspection; a reset link names its account and takes a new password, after which only the new one signs in; link-status-goto-login leads to /; served registration_mode invite (page only) a valid invitation still opens the registration, served disabled it reads closed; every pending invitation revoked and every account self-deleted after each test. The setup page of the initial administrator (A7b), /setup, with a link it cannot use: an unknown token leaves the address bar, is inspected for admin_setup, reads unknown with its own hint and stays on /setup (no-referrer); no token, or a token in the query, reads missing and sends no inspection",
        prereq="Test users created (e2e_test_admin an administrator); registration_mode open on the lane",
        tests="auth-links.spec.ts",
    )
    add_test(
        cat,
        "admin-users",
        front_admin_users,
        name="Admin Users Tab Tests",
        desc="Settings → Users (accounts lot A6b), e2e_test_admin acting on disposable accounts only: the tab for administrators alone (a member has none, ?tab=users opens Profile); the own row with users-self-hint and no action; deactivate/reactivate and promote/demote through users-confirm, with their accounts.user.* events and a server read-back, delete disabled demote-first while admin; a password-reset link and an invitation through LinkShare, each token inspected live, the invitation listed then revoked; the address check on the lane's other loopback origin (match through the real CORS path), a closed port (unverifiable), ftp (invalid, copy off), a stubbed stranger (mismatch), back to the prefill (idle); deletion with preview (one broker with one deposit, typed username, brokers_deleted 1, broker gone); sign-out everywhere (the account's session gets 401) and restart guides (every skipped flow pending again); every invitation it wrote revoked and every account self-deleted after each test",
        prereq="Test users created (e2e_test_admin an administrator, e2e_test_user an ordinary member); registration_mode open on the lane; no user limit on the lane",
        tests="settings/admin-users.spec.ts",
    )
    add_test(
        cat,
        "security-tab",
        front_security_tab,
        name="Security Tab E2E",
        desc="Settings › Security (accounts lot A8b) inside the «Administration» group (decision P13 b), read-only on the lane: e2e_test_admin sees a badge of at least 1 on settings-tab-administration before anything of the group is opened (the checks read by the page's prefetch, accounts.login_limit a warning with LIBREFOLIO_LOGIN_LIMIT=off, read first from GET /security/checks as a precondition); Security opened through the group settles data-status ready, lists accounts.login_limit as a warning and folds the passed checks (security-passed), its badge counting exactly the errors and warnings it lists and the group's including it; ?tab=security opens it inside the group, and «check again» re-reads (the request held: loading, busy, the refresh disabled, the last findings still listed; then ready with the warning); e2e_test_user, a member: «Administration» opens Global Settings directly, no settings-subtabs, no settings-tab-security, no badge, no read of the checks, and ?tab=security opens Profile without mounting the tab",
        prereq="Test users created (e2e_test_admin an administrator, e2e_test_user an ordinary member); the lane's server started with LIBREFOLIO_LOGIN_LIMIT=off (dev.py server --test's default)",
        tests="settings/security-tab.spec.ts",
    )
    add_test(
        cat,
        "legal-managed",
        front_legal_managed,
        name="Legal Notice & Managed Profile E2E",
        desc="The instance's legal notice (F09) and the managed profile's account-side effects (F05), lot A9 of workstream A, desktop: GET /system/instance answered with the real response, observed untouched or patched per page (profile, legal; fixtures/instance-config.ts serveInstanceConfig, checked against the generated schema); signed out on the lane's answer auth-legal-links under the login card (after it, below it) holding legal-links without legal-terms-link/legal-privacy-link, and auth-donate-link once the configuration is in; with legal stubbed to two https pages both links there, href exactly those pages, target _blank, rel noopener noreferrer, never clicked; signed in as e2e_test_user header-donate-link, sidebar-legal-links after sidebar-version, Settings › About's about-legal-card holding legal-notice, and the self-hosted contrast (changelog-check-update, help-donate-link, support-coffee); profile stubbed managed with legal set to the same two pages and signed in: first sidebar-legal-links holding legal-terms-link with exactly the stubbed href (the proof the managed answer is in force: the links come from the stubbed answer alone, which the store applies whole), then the changelog opened from sidebar-version without changelog-check-update, no header-donate-link, no help-donate-link in the open Help menu (its GitHub issues item, found by its link, stays), About's legal-notice linking the same pages and no support-coffee in its support card (its support-share-* buttons stay), no link to the donation page anywhere, the proof and every absence in one app runtime (a mark on window set before the proof); profile stubbed managed and signed out: the forgot card shows forgot-ask-admin, neither forgot-reset-commands nor forgot-email-unavailable, no auth-donate-link",
        prereq="Test users created (e2e_test_user an ordinary member, grandfathered on every onboarding flow); the lane self-hosted (LIBREFOLIO_PROFILE unset) and without LIBREFOLIO_TOS_URL or LIBREFOLIO_PRIVACY_URL",
        tests="layout/legal-and-managed.spec.ts",
    )
    add_test(
        cat,
        "core-unit",
        front_utility_unit,
        test_names=True,
        name="Core Store Unit Tests",
        desc="entityStore, option filter, date/decimal parsing, request concurrency, bulk request batches (Z-27: planned under the caps, sent in sequence, split after a bulk_too_many_days 422), HTML escaping for hand-built markup, the clipboard gate (only the shared helper reaches navigator.clipboard or execCommand('copy'), so every copy button keeps working over plain HTTP), safe accessors for widened API unions, import-wizard dedup/merge/compare pure logic, URL filter round trip for DataTable deep links, trySave error seam (FastAPI detail ladder, pydantic issue unpacking and formatting, toast/prefix/pre-handler), comparison-overlay loader (query shape, resolved series injected back into the signal, currency filter, refused conversions), sync toast variants for asset/FX results, the stored-row question behind the sync dialog's overwrite warning (C-66: hasStoredPointInRange, a point inside [start, end] with both bounds included, a 'min' start unbounded, a point filled backward never a stored row), chart helpers (echarts tooltip/animation/zoom-pan, geography map, price-chart & candlestick series/scale arithmetic and event markers (a partial last week or month keeps its markers on its bar), signal-problem formatting), chart-settings store (per-account hydration, scoped global vs per-item overrides, sanitising, debounced persistence, SSR silence, the storage-version-3 migration that turns a saved observation Rolling Return into the calendar one), signal registry (palette assignment, config creation, round trip), local signal maths (linear/compound/sine benchmarks, measure ruler, asset & FX comparison overlays), signal catalog partition rules and backend renderer slice capping, onboarding tour surface contracts and the tour/guide copy gate (no step names a guide or a tour unless its key is registered with a reason), transaction form-item resolution (paired orientation, hidden-broker sentinel, injected lookups) and image-crop presets/MIME/file-naming with the cropper contract faked, FX tooltip data assembly where a zero rate is the absence sentinel and not a quote, brokerStore.getOwnedBrokers roles×shares matrix (F2 dashboard scope), changelog chapter parsing incl. the canonical-Unreleased known gap, and the update-check probe (version compare, 24h throttle, dismissal memory, never-throw fetch), plus the Asset Global laboratory pure layer (F): correlation banding/symmetric lookup/average-linkage clustering/lower-triangle points where every pair keeps its square even when the payload never mentioned it, and the D19 initial-selection ladder (persisted ∩ existing → owned → a readable handful) with its storage seam, filter composition and mass actions, plus the per-asset comparison arithmetic behind L1° and L3°: a row survives for an asset that could not be measured because a missing row reads as an unselected one, and the scatter can hold no portfolio point at all since the contract has no field to carry one, plus the laboratory's eligibility wording read off the generated reason enum (a reason the engine adds, such as no_price_history, stays red until reasonText words it and all four catalogues carry its sentence, naming only the values reasonText supplies), and the warning-translator gate: every component call of warningSentence, resultReasons or partialNotice, found through the Svelte compiler's AST with aliases and member calls followed, passes a translator as its second argument, and the colour gates of workstream T: the ratchet on the legacy colour classes and literals (no total and no file rises above src/themeRoles.baseline.tsv, a swapped colour is a rise, a move keeps its record and a split is declared), the grammar of the role utilities (no dark: on a role, no unknown role, no element mixing roles with legacy classes, no arbitrary colour value), and the contract of tokens.css (the same base roles in both themes, every utility a declared role, the WCAG contrast pairs in both themes) with the legacy dark remap of app.css exempting migrated elements and losing each rule with its class's last use, and the Settings tab registry (plan A3): today's tabs with unique URL-safe ids and unique orders, their labels in all four catalogues, their icons and tab modules, admin visible to everyone with canEdit for an administrator only and alignEnd, users (order 110), backup and email for administrators only, and visibleSettingsTabs keeping what visible(ctx) allows, sorted by order, without touching its input, and the Email tab's words, colours and API seam (workstream E, lot E2): problem, SMTP and API codes to whole i18n keys present in the four catalogues with exactly the placeholders they are filled with (own entries only: constructor or __proto__ fall back to the unknown key), the minutes of a rate limit rounded up, class maps of declared colour roles only (a positive control proves the detectors), GET /email/status normalized to its five keys (an empty string or an array where the schema allows none dropped to null), and readTestFailure on each refusal of POST /email/test, carried by an AxiosError or an ApiError, also as the generated client really raises it through the real Zodios and axios stack with only the transport faked; the Users tab's pure helpers (lot A6b): linkShare (the prefilled base from url/path or the origin, the link composed) and addressProbe (normalizeBase, probeUrl, checkAddress: one bare GET without credentials or headers, match/mismatch/unverifiable, the timeout, never throws); and the rune-free gate (Z-20): from src/lib/api/index.ts and from scripts/ai-export-render-prompt-probe.ts (the graph the AI Export probe bridge loads without Svelte's compiler) no static import reaches a .svelte.ts module or a .svelte component, and zodios-client.ts imports none directly, with synthetic and real-site controls; and the Security tab's data (lot A8b): fetchSecurityChecks (the items of GET /security/checks through the generated client, a failure propagated), securityFindings (the checks not ok sorted error → warning → info in the server's order, the browser's open-registration warning from openRegistrationNoticeFor after the server's warnings, the links to Settings › Administration › Email and Settings › Plugins, the ok checks passed without a link, its inputs untouched) with attentionCount (errors and warnings, never info), and the createSecurityChecks store (idle → loading → ready or error, overlapping ensureLoaded() sharing one request, reload() keeping the last checks, nothing listed before the first answer, the browser's state read from instanceConfig only once it has answered and from the page's host)",
        tests=("src/lib/stores/core/entityStore.test.ts", "src/lib/features/onboarding/onboardingTourSurfaces.test.ts"),
    )
    add_test(
        cat,
        "component-unit",
        front_component_unit,
        test_names=True,
        name="Svelte Component Unit Tests",
        desc="UI primitives mounted in jsdom: CalendarMonth grid/states, SingleDatePicker typed/calendar seam, TagInput keyboard model, PasswordInput's decorative icon (aria-hidden, inside the field, no test id when the field has none) and its eye button (K-17: named $_(auth.showPassword) or $_(auth.hidePassword) in aria-label and title, in the tab order, no aria-pressed) and PasswordStrength's checklist (each rule's data-passed, a check or a cross by glyph and by shape, nothing for an empty password, the zxcvbn score in data-strength), SimpleSelect keyboard/unavailable states, FxProviderSelect route picker, DataTableColumnFilter filter modes, DataTable sorting/paging/selection/row actions, ScheduledInvestmentEditor schedule payload round trip, ImportWizardModal shell/open-gating/close, TransactionCompareModal outlier judgement and diff highlighting, TransactionFormModal draft seeding (create-mode empty quantity T1-b, duplicate-mode date preservation T3), CompactCashCell decimal typing through the parent prop loop (T1-a), SyncModalBase run/timeout/retry/session engine and its overwrite warning before Start (C-66: one per active section whose targets already hold stored data, counting only targets, led by the section title only beside another active section, gone once the run starts and back on a fresh open, the sentence in all four catalogues) with the three sync modals handing that data to their sections, with SyncResultRow the one result line the three sync modals share, MeasurePanel measure add/preview/summary table, RegisterCard sign-up validation gate and server-error ladder, DonationPopupModal deliberate absence of every escape hatch, BrokerSharingPanel role ladder and last-owner guard, the five Setting* controls plus SettingsLayout bulk bar, PasswordChangeModal validation and post-success window, SchedulerConfigModal day/time/timezone payload, SchedulerLogModal run outcomes, PreferencesTab theme/language/currency save payloads and the un-rolled-back optimistic apply, ProfileTab edit lock with its discard dialog plus the per-field save/undo/revert ladder, AboutTab system facts, copy-for-issue payload and plugin discovery status, GlobalSettingsTab admin lock, value_type dispatch, 403 ladder and bulk save, FX card/table/editor rendering an absent rate as absent rather than as 0.0000, plus the beta-feedback batch: AssetTable txCount scope badge palette (F15), KpiSection absolute-vs-period ROI separation (F5), ExposureTable/ContributionTable analyzed-row tint (F9), DataTable header tooltips opening upward via a Tooltip probe (F10), the import wizard's report-issue banner (F11), ChangelogModal chapter rendering, clickable search hits and the header update-check delegation (F12/F14) and UpdateAvailableModal show/later/skip (F12/F14), plus the promoted primitives and the risk metric card: KpiMetricBar and KpiDivergingFlowBar proving their defaults still render the dashboard bars unchanged after the move out of dashboard/, and that a non-finite percentage renders 0% instead of having `width: NaN%` rejected by the CSS parser and leaving the fill at its previous width, and RiskMetricCard proving by node identity across a loading flip — the same DOM object before and after — that the value never leaves the DOM and the card cannot shift layout, and RiskCardGrid proving the risk cards are laid out by auto-fit rather than by enumerated breakpoints, and that the column floor stays capped at the container width so a narrow screen stacks the cards instead of cropping them, and the laboratory's historical replay section mounted over a real, observed panel controller: a replay answer discarded three times running is disclosed as risk.errors.answer_discarded while a discard the re-ask recovered from is not, and a keyed replay warning is worded through its catalogue key and values in all four locales instead of the backend's English sentence, and the Settings page as the runtime of the tab registry (plan A3): the bar and the body from SETTINGS_TABS through visibleSettingsTabs, by order, sm:ml-auto from alignEnd alone, props(ctx) spread and kept in step with the auth store, ?tab= applied at the first render without mounting the default body, again on every change and once per value, unknown or hidden ids ignored, and an administrators' tab appearing with the store and taking a pending ?tab=, and the Email settings tab (workstream E, lot E2): off, invalid with the problem and its variable, ready with the hourly budget left or spent, the configuration notices worth a line (not ok, not email.smtp) with their id and severity, the load error (alone on a first read, above the last state and the outcome on a later one), and the test email offered only when ready, even with the shown budget spent (one request at a time: the button disabled, a click refused even before the DOM catches up, and data-busy true without a break from the click to the end of the status read again; outcome sent or failed worded from state and following the language, refusals read as the generated client raises them (AxiosError) and as an ApiError, email.test.sent/failed events without a toast); and the Users tab (lot A6b): UsersTab (both lists at once, data-busy, usage and billing link, the limit banner, the invite button's reasons, the rows' actions and their disabled reasons, confirmations, events, reloads, errors), LinkShare (prefill, the debounced address check, copy, the extra-action registry), InviteDialog, ResetLinkDialog and AccountDeletionDialog (the preview, deactivate first, the typed username, error codes), ProfileTab through that dialog; and the Security tab (lot A8b): the store it is given asked once on mount (ensureLoaded, never the generated client), data-status, the loading placeholder, one finding per attention finding (most severe first, the browser's warning after the server's, its message with its values, its severity in words, the link to where it is fixed), all clear only with nothing listed, the passed checks in a details counting them, check again disabled while it runs with the last findings kept, the load-error banner (role alert) with retry and the last findings under it, colour roles only, its words in the four catalogues",
        tests="src/lib/components/ui/date/CalendarMonth.test.ts",
    )
    add_test(
        cat,
        "onboarding-component-unit",
        front_onboarding_component_unit,
        test_names=True,
        name="Onboarding Component Unit Tests",
        desc="Isolated welcome, replay, coachmark, header and import-guide behavior",
        tests=(
            "src/lib/features/onboarding/components/OnboardingCoachmark.test.ts",
            "src/lib/features/onboarding/components/OnboardingIntroScene.test.ts",
            "src/lib/features/onboarding/components/OnboardingReplaySection.test.ts",
            "src/lib/features/onboarding/components/WelcomeForm.test.ts",
            "src/lib/features/onboarding/components/WelcomePage.test.ts",
            "src/lib/features/onboarding/components/WelcomePage.legal.test.ts",
            "src/lib/features/onboarding/components/DeferredAppPopups.test.ts",
            "src/lib/features/onboarding/onboardingRouteSettlement.test.ts",
            "src/lib/components/assets/AssetModal.test.ts",
            "src/lib/features/brokers/BrokerModal.test.ts",
            "src/lib/components/fx/FxPairAddModal.test.ts",
            "src/lib/components/layout/Header.test.ts",
            "src/lib/features/settings/tabs/PreferencesTab.test.ts",
            "src/lib/features/transactions/import/ImportWizardModal.test.ts",
        ),
    )
    add_test(cat, "settings", front_settings, name="Settings Tests", desc="User preferences, global settings (admin)", prereq="Login working", tests="settings.spec.ts")
    add_test(cat, "files", front_files, name="Files Tests", desc="Files page, tabs, URL filters", prereq="Login working", tests="files.spec.ts")
    add_test(
        cat,
        "files-pdf-offline",
        front_files_pdf_offline,
        name="Files PDF Offline Tests",
        desc="The PDF preview without internet (1.2 gap 7): every origin but the lane's refused and every browser request recorded from before the first navigation; signed in through the API as an ordinary member, a one-page Latin PDF (Helvetica, not embedded) uploaded and previewed from the Files list reaches file-preview-pdf data-state=ready with not one request to another origin; positive controls: the engine's worker fetched /_app/immutable/assets/pdfium.<hash>.wasm from the lane (GET, 200), every viewer fallback font asked for is a 200 from the lane, a jsDelivr probe from the page is refused and recorded",
        prereq="Test users created (TEST_USER an ordinary member)",
        tests="files-pdf-offline.spec.ts",
    )
    add_test(cat, "files-uploader", front_files_uploader, name="Files Uploader Tests", desc="Uploader URL/list-grid/reload parity, unknown/null identities and avatar geometry with synthetic APIs", tests="files-uploader.spec.ts")
    add_test(
        cat,
        "support-copy-and-go",
        front_support_copy_and_go,
        name="Support Copy And Go Tests",
        desc="Icon-to-dialog, fixed public clipboard payload, native blank-tab reservation, safe navigation and denied-copy cleanup; a refused secure write falls back once to the legacy copy, which fails explicitly because opening the share tab already consumed the click's user activation (known limit)",
        tests="support-copy-and-go.spec.ts",
    )
    add_test(
        cat,
        "header-scroll",
        front_header_scroll,
        name="Header Scroll Tests",
        desc="Desktop/mobile document-scroll geometry, retained layout, menu pins and reduced motion with synthetic APIs; a mouse click on a header control leaves the header free to hide, keyboard focus pins it; signed out, the sign-in page's top bar (auth-page-controls) is fixed on desktop and, on a phone, scrolls away with the page instead of covering the card (T-8b)",
        tests="layout/header-scroll.spec.ts",
    )
    add_test(cat, "document-title", front_document_title, name="Document Title Tests", desc="No page changes the tab title: direct landing on every main page and a tool page, sidebar hops in one runtime, a Files query change", prereq="Test users created", tests="layout/document-title.spec.ts")
    add_test(
        cat,
        "theme-roles",
        front_theme_roles,
        name="Theme Roles Tests",
        desc="Colour roles as the browser resolves them, in light and in dark (a probe element per role, never a hex), a positive control first (the probe resolves, the two themes differ, the page is drawn in the theme set): (a) signed out on /, the login card in relief (--lf-border-raised, in dark its own colour and proof that the legacy rounded-container rule of app.css exempts it), the username field's border at rest and in focus, its text and its placeholder (proof that the legacy input rule exempts it), the primary action; on desktop the username and password fields under the pointer (--lf-border-input-hover, D-T18) and focused there (--lf-focus beats the hover); the register card's password requirements once every rule passes (the box on --lf-surface-panel with a --lf-border-subtle border, each rule's ✓ in --lf-success and its text in --lf-text-secondary); the forgot-password card in relief, its terminal box on --lf-terminal-bg with a --lf-terminal-border border, its commands in --lf-terminal-prompt and its comment lines in --lf-terminal-comment (Q6); (b) signed in as TEST_USER on /dashboard, --lf-surface-app resolving to --lf-surface-page, the app shell on --lf-surface-app; the green sidebar from its own roles (D-T17): on --lf-surface-bar in --lf-bar-text with no right border (D-T23), its logo block with no surface of its own and its text in --lf-on-brand, its active item (nav-dashboard, whose href is the page on view) on --lf-bar-active-bg in --lf-bar-active-text with a --lf-bar-indicator left border, an inactive item (nav-settings, read at rest) in --lf-bar-text, its connection-security line once the server has answered (the icon in the bar's status role of the level: secure --lf-bar-success, local --lf-bar-warning, insecure --lf-bar-danger; the label in --lf-bar-text), and a sidebar item reached by Tab drawing a solid --lf-bar-focus ring; the neutral header from the page's roles (D-T23): on --lf-surface-header with a --lf-border-subtle bottom border, theme-toggle in --lf-text-secondary, the donation link in --lf-donate, on mobile the burger in --lf-text-primary, and a header control reached by Tab drawing a solid --lf-focus ring; (c) in dark, the negative control: a probe container in the page content without a role utility still takes the remap's structural border (var(--theme-border-primary)), its twin with one escapes it (--lf-border-subtle), while the language menu opened over the page draws --lf-surface-card with a --lf-border-raised border; (d) signed out on /, the login background (AnimatedBackground) on --lf-surface-page, its three waves (rendered after mount, waited for) each a gradient with a stop in its own --lf-art-hill-N in DOM order and no opacity on top, its three chart lines stroked in --lf-art-line, and in dark none of the retired literals (#11151c, #00ff9a, #4ade80) drawn again — workstream T, steps T-2, T-3, T-5, T-8 and T-8b (decisions D-T17, D-T18, D-T23)",
        prereq="Test users created (TEST_USER grandfathered on onboarding)",
        tests="layout/theme-roles.spec.ts",
    )
    add_test(
        cat,
        "pac-allocator-real",
        front_pac_allocator_real,
        name="PAC Allocator Real-Data Tests",
        desc="The PAC allocator (beta) end to end on real data (1.2 gap 3): a disposable account holds two priced positions and cash in its own broker; the Tools hub opens the planner (tool code read from the catalogue), «copy from LibreFolio» brings the broker's cash, the positions with their stored prices and their current distribution as the targets, a budget is typed and «Calculate plan» runs the real engine; the tool's own request carries the copied facts, its answer is a proven optimum, and the screen prints it — run state, result state and proof the answer's, per Asset the value after the plan, the ideal value and the signed gap, per order the amount and the fee, on sign and digits at the currency's minor unit — within the budget",
        prereq="Populated DB + test users (registration enabled)",
        tests="pac-allocator-real.spec.ts",
    )
    add_test(
        cat,
        "changelog-locale",
        front_changelog_locale,
        name="Changelog Locale Tests",
        desc="The changelog modal opened from the sidebar version: in the Italian UI each chapter is Italian when the repository's CHANGELOG.it.md translates it and English with the Italian not-translated pill otherwise; in the English UI every chapter is English with no pill (content-agnostic, desktop, lot CL)",
        prereq="Test users created",
        tests="layout/changelog-locale.spec.ts",
    )
    add_test(
        cat,
        "toolbar-width-sweep",
        front_toolbar_width_sweep,
        name="Toolbar Width Sweep",
        desc="The five PageToolbar bars (assets list and detail, dashboard, broker detail, FX list) swept 1700 → 320 px every 10 px in English, French, Italian and Spanish: no box past its bar, no sideways page scroll, every violation in one table per bar and language; then the Assets Active/Inactive pill from 390 to 320 px in the same four languages, both labels whole inside it and Search still usable beside it (K step 13, item 5; lot 51)",
        prereq="Populated DB + test users",
        tests="layout/toolbar-width-sweep.spec.ts",
    )
    add_test(
        cat,
        "app-start-auth",
        front_app_start_auth,
        name="App Start Auth",
        desc="Only a 401 signs out: a GET /auth/me silent past 5 s shows the server-unreachable panel on the requested page instead of leaving it, and its late answer loads that page; signed out, an app page goes to /?redirect=<path+query> and signing in there lands on it; a 401 mid-session goes to the login carrying the page it happened on (K step 19)",
        prereq="Populated DB + test users",
        tests="layout/app-start-auth.spec.ts",
    )
    add_test(
        cat,
        "connection-security",
        front_connection_security,
        name="Connection Security Indicator",
        desc="The sidebar's connection indicator from the browser's view and the server's (GET /system/connection): secure on localhost, local network on a mapped .lan name, uncertain on a public name the server sees as local, not secure with the menu dot when the server sees a public source; details, docs link (plan 36)",
        prereq="Populated DB + test users",
        tests="layout/connection-security.spec.ts",
    )
    add_test(
        cat,
        "docs-offline-math",
        front_docs_offline_math,
        name="Docs Offline Math",
        desc="The documentation draws its formulas without internet: on a nested page in English and its Italian twin a folder deeper, every origin but the lane's refused, lib-loader.js loads MathJax from the site's root (/mkdocs/javascripts/vendor/mathjax/tex-mml-chtml.js, 200), every formula gets its mjx-container, every MathJax font is a 200 from the site's copy (vendor/mathjax/output/chtml/fonts/woff-v2/) with at least one MJX face loaded and none in error, MathJax is never asked of another origin (jsDelivr included), and mathjax.js raises no typesetPromise page error (M-19, batch 25)",
        prereq="Docs site built with the MathJax copy and its fonts (dev.py cache js, then dev.py mkdocs build)",
        tests="layout/docs-offline-math.spec.ts",
    )
    add_test(
        cat,
        "page-policy",
        front_page_policy,
        name="Page Policy",
        desc="The page policy of H-42 (PAGE_POLICY of security_headers.py: frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'), injected by the spec into every HTML document of the lane with service workers blocked, on any lane (a self-hosted one sends none; on a managed one the same policy replaces the lane's own); every securitypolicyviolation recorded in the page, only enforce counted. Positive controls first, on the sign-in page: the document reaches the browser with the policy, an injected <base> and a form posted to https://example.invalid and an <object> typed application/pdf on the lane each raise an enforced violation (base-uri, form-action, object-src), the base URL stays the lane's, no control request is made, and nothing else raises one. Then, each flow's page the only document, carrying the policy, and no enforced violation at its end: a nested documentation page and Material's search for 'conventions' (a result on screen), a one-page Latin PDF uploaded and previewed from the Files page to file-preview-pdf data-state=ready (deleted after the test), and the Dashboard's main view (dashboard-page settled, dashboard-overview-tab)",
        prereq="Docs site built (dev.py mkdocs build), populated DB + test users (TEST_USER with no onboarding due)",
        tests="layout/page-policy.spec.ts",
    )
    add_test(
        cat,
        "csp-collector",
        front_csp_collector,
        name="CSP Collector",
        desc="H-43: the collector of Content-Security-Policy violations of e2e/fixtures/playwright.ts (e2e/fixtures/csp.ts, e2e/csp-baseline.json): its helpers, a report-only violation of a synthetic page recorded (the script still runs), one the baseline does not know failing the test, violations of two documents in a row, and on the app's index.html with the managed report-only policy exactly its two inline scripts, both known",
        prereq="Populated DB + test users",
        tests="layout/csp-collector.spec.ts",
    )
    add_test(
        cat,
        "cloud-smoke",
        front_cloud_smoke,
        name="Cloud Smoke (managed lane)",
        desc="H-43: CLOUD_SMOKE_SPECS (sign-in, page policy, CSP collector, dashboard, risk, asset modal, transactions, BRIM import, files, brokers, security and users settings, AI Export) on desktop, on a lane started with --lane-setting LIBREFOLIO_PROFILE=managed (refused otherwise): frame protection and the report-only policy for real, the collector failing on any violation e2e/csp-baseline.json does not know",
        prereq="--lane-setting LIBREFOLIO_PROFILE=managed; populated DB + test users",
        tests=CLOUD_SMOKE_SPECS,
        named_only=True,  # refused on a self-hosted lane, the default; every spec it runs has an action of its own
    )
    add_test(
        cat,
        "datatable-mobile",
        front_datatable_mobile,
        name="DataTable Mobile Pinned Columns",
        desc="At 390 px, read-only on seeded data, on Transactions (stickyActions false) and the Files static list (sticky actions): scrolled half an actions cell short of the far right, the actions header sits over its row's actions cell and both end with the table; the selection header and cell have scrolled out past the scroll area's left edge; and, the scroll area bounded to the header and two rows and scrolled down, every header cell stays on its top while the body passes under (Y7, D-Y17; needs the dt-scroll / dt-select-* / dt-actions-* test ids)",
        prereq="Populated DB + test users",
        tests="layout/datatable-mobile.spec.ts",
    )
    add_test(
        cat,
        "datatable-resize",
        front_datatable_resize,
        name="DataTable Column Resize",
        desc="Read-only on seeded data. The contract: a drag of a column's resize handle (found by cursor: col-resize under the title cell's right edge, pressed at its centre) by Δ px changes the column's drawn width by Δ ±4 px. Files static list (tableLayout auto), by mouse: at 1280 px the File name column +80 then -40 px; at 390 px, where the table is wider than its box and draws every column at its minimum, +60 px, and the table's scroll width grows by as much (a resized column keeps its width as min-width, so the other columns are not squeezed back). Control: the Transactions Date column (fixed layout, table wider than its dt-scroll area) by mouse, +80 then -40 px. The input path alone, independent of the layout: at 390 x 844 with isMobile and hasTouch, a finger (Chromium CDP Input.dispatchTouchEvent: touchStart on the handle's centre, touchMove in 6 steps, touchEnd) drags the Date handle +60 px on that fixed table (Y7, C-62, D-Y18)",
        prereq="Populated DB + test users",
        tests="layout/datatable-resize.spec.ts",
    )
    add_test(cat, "files-destructive", front_files_destructive, name="Files Destructive Tests", desc="Single + bulk file delete, confirm/cancel, delete failure, BRIM delete + empty state (disposable rows, self-restoring)", prereq="Login working", tests="files-destructive.spec.ts")
    add_test(cat, "select", front_select, name="Select Components Tests", desc="SimpleSelect, SearchSelect, keyboard nav", prereq="Login working", tests="select-components.spec.ts")
    add_test(cat, "image-crop", front_image_crop, name="Image Crop & Media Tests", desc="ImageEditModal, AssetPicker, FileGrid, avatar", prereq="Login working", tests="image-crop.spec.ts")
    add_test(cat, "utilities", front_utilities, name="Utilities API E2E", desc="Currencies, countries, sectors API", prereq="Login working", tests="utilities.spec.ts")
    add_test(cat, "onboarding-tour", front_onboarding_tour, name="Onboarding Tour Tests", desc="Welcome handoff, semantic intro tour and contextual import guide on desktop/mobile", prereq="Test users created", tests="onboarding-tour.spec.ts")
    add_test(
        cat,
        "onboarding-guides",
        front_onboarding_guides,
        name="Onboarding Guides Tests",
        desc="The nine broker/FX/asset contextual guides walked step by step against their real pages (anchored, stable, one described target, completed on the server), pause-on-leave/resume-on-return with the Add-modal restart contrast, and replay persistence across tabs, logout and cross-tab close on desktop/mobile",
        prereq="Test users created",
        tests="onboarding-guides.spec.ts",
    )
    add_test(cat, "tooltip", front_tooltip, name="Tooltip Component Tests", desc="Pinned hover/click model: hover-only, click-to-pin, grace dismiss, click-outside", prereq="Login working", tests="tooltip-component.spec.ts")
    add_test(cat, "scheduler", front_scheduler, name="Scheduler Settings E2E", desc="ConfigModal, LogModal, status row, fetch_interval regression", prereq="Admin user + populated DB", tests="settings/scheduler.spec.ts")
    add_test(
        cat,
        "email-tab",
        front_email_tab,
        name="Email Settings Tab E2E",
        desc="Settings › Administration › Email (workstream E, lot E2b): on the lane's backend an administrator opens ?tab=email and finds email off (no SMTP server on the lane, asserted first through GET /api/v1/email/status), explained, the docs link opening admin/email/; a user has no Email tab and ?tab=email opens profile instead; on a simulated server (page.route on /email/status and /email/test, owned and unrouted by each test) ready with 48 of 50 left and a warning notice, a test email sent (200, busy and disabled while held, email.test.sent), refused by the SMTP server (502 EMAIL_DELIVERY_FAILED AUTH_FAILED) and by the hourly limit (429 EMAIL_RATE_LIMITED, retry_after), each read as the generated client rejects (email.test.failed) and followed by a second status read",
        prereq="Admin user + test users; no SMTP server on the lane (LIBREFOLIO_SMTP_HOST unset)",
        tests="settings/email-tab.spec.ts",
    )
    add_test(
        cat,
        "email-verification",
        front_email_verification,
        name="Email Verification E2E",
        desc="E5b (developer decision 44), signed out on simulated answers: a 201 with verification_required goes back to the sign-in with a success line of its own and signs nobody in; a 409 EMAIL_VERIFICATION_UNAVAILABLE stays on the register card with words of its own; a 403 EMAIL_NOT_VERIFIED draws the verification notice instead of the danger box, and «send the link again» goes with the typed credentials (email.verification.resent). As e2e_test_admin with GET /system/instance simulated: the require_email_verification switch of Settings › Admin disabled with email.links false (not the lock: the sibling switch usable; no placeholder badge), usable with true; nothing saved",
        prereq="Admin user + test users; no SMTP server on the lane; require_email_verification saved off",
        tests="auth-email-verification.spec.ts",
    )
    add_test(
        cat,
        "email-send-link",
        front_email_send_link,
        name="Send Link by Email E2E",
        desc="«Send by email» in Settings › Users (workstream E, lots E4b and E-8): the invitation and reset dialogs on the lane's backend, GET /system/instance answered with the real response and email.links true or false, POST /email/links on a simulated server: offered only with links, an invitation prefilled with its address posting {purpose, token, to} with no language by default, or with language: it chosen in its select, a reset link posting {purpose, token} without to or language, no select, «sent» and email.link.sent, a 429 with its wait in email.link.sendFailed; every invitation and disposable account it creates removed after it",
        prereq="Admin user + test users; registration open on the lane; no SMTP server on the lane (LIBREFOLIO_SMTP_HOST unset)",
        tests="settings/email-send-link.spec.ts",
    )
    add_test(
        cat,
        "forgot-password-email",
        front_forgot_password_email,
        name="Forgot Password by Email E2E",
        desc="«Forgot password» on the sign-in page (workstream E, lot E4b), signed out: GET /system/instance answered with the real response and email.links true or false, POST /email/password-reset on a simulated server; with links the card shows E's form in the warning's place beside the commands, two identifiers get the same accepted notice and go once each, trimmed, a 429 is «failed» with its wait in email.forgot.refused; without links the warning (forgot-email-unavailable) instead of the form, the card and its commands there; nothing written",
        prereq="Test users created; no SMTP server on the lane (LIBREFOLIO_SMTP_HOST unset)",
        tests="auth-forgot-password-email.spec.ts",
    )
    add_test(
        cat,
        "backup",
        front_backup,
        name="Backup Settings E2E",
        desc="Settings › Administration › Backup (lot B5a), desktop: a regular user has no Backup tab and ?tab=backup opens the first tab, an administrator has it and it opens the card idle; from ?tab=backup a backup started and followed to done (backup.created with its 32-hex job id), the card naming the archive, a link to that job's file, the download a zip as large as the job reports under librefolio-backup-YYYYMMDD-HHMMSS.zip (backup.download.started); the delete back to idle (backup.deleted, GET of the job 404 backup_job_not_found); a reload picks the finished job up again without a second backup.created. Serial (one backup at a time per instance); every job deleted and the followed job id cleared after each test",
        prereq="Admin user + populated DB",
        tests="settings/backup.spec.ts",
    )
    add_test(
        cat,
        "plugin-settings",
        front_plugin_settings,
        name="Plugin Settings E2E",
        desc="Settings › Plugins and «Configure» (workstream X, lot CP11c), desktop: as a member and as an administrator ?tab=plugins selects the tab and its read settles (data-busy); the asset family lists justETF and Borsa Italiana, configured, each personal select (preferred_currency all/EUR/USD/CHF/GBP, preferred_language all/it/en) on its default and editable, its list opened and closed with Escape, nothing chosen, and never the test-only mockprov; «Configure» on mockprov from the edit dialog of an asset of the test's own (mockprov assigned over the API under the identifier the mock refuses to quote: the provider select never offers mockprov), no «not configured» badge; the dialog over mockprov's seven fields scrolls its body between title and «Close» at 1280×720 (precondition: the body overflows; «Close» whole in the window, Save reached by scrolling the body): a member finds the four instance fields read only (data-editable false, note adminOnly) and the instance secret only set or unset with no control, saves results_limit 25 and a personal_token (the PATCH sends the number as a number and the secret only in secret_value; pluginSettings.saved names the fields, never a value), reads them back (data-source db, the secret «set» and its field gone, the API never returning it), then «Use the default» and Clear, saved, back to default and unset on screen and through the API; an administrator saves mockprov's instance api_key the same way, finds «Replace» opening an empty field and cancels it, clears it; search on a simulated stream (page.route; the REST fallback aborted and recorded): justETF reported NOT_CONFIGURED gets its «to configure» row (data-provider), a 👑 result brings asset-search-crown-legend, and the row's «Configure» opens justETF's settings over the asset dialog, closed without saving (the preference still the default through the API). Every mockprov field a test may write is recorded before its Save and cleared over the API by its owner after each test, whatever happened, and the asset deleted",
        prereq="Populated DB + test users (e2e_test_user a member, e2e_test_admin an administrator); no environment variable sets a mockprov field on the lane (LIBREFOLIO_MOCKPROV_API_KEY, LIBREFOLIO_PLUGIN_ASSET_MOCKPROV_*); the justETF and Borsa Italiana search preferences of both users on their default",
        tests="settings/plugin-settings.spec.ts",
    )
    add_test(cat, "all", front_utility_all, test_names=False, name="All Frontend Utility Tests", desc="Run all utility/component E2E tests")
    registry["front-utility"] = cat
