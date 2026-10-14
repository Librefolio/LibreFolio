<!--
  Stand-in for `OnboardingReplaySection` in tests that only care about *where*
  PreferencesTab mounts it (which category shows/hides it), not its own
  replay/busy/error behaviour — that is `OnboardingReplaySection.test.ts`'s
  job. The component takes no props, so this probe needs none either: a
  single stable `data-testid` is the whole contract.
-->
<div data-testid="onboarding-replay-section-probe"></div>
