<!--
  SettingsIconProbe — test-only icon for `routes/(app)/settings/page.tabs.test.ts` (Vitest + jsdom).

  The Settings page hands TabBar an icon for every entry of its bars: a tab's own, or — for the entry that stands for a
  group of tabs (lot A8b) — the group's. Every lucide icon draws an `<svg>` a test cannot tell from another, so the page
  test gives each synthetic tab and each synthetic group this probe instead, told what it stands for:
    - `icon` names the synthetic tab or group the icon belongs to, and is drawn as `data-icon`;
    - `size` is what TabBar asks of any icon, taken so that the probe stands where a lucide icon would.
  It draws one empty `<svg>` and nothing else.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    interface Props {
        /** The synthetic tab or group this icon stands for. */
        icon: string;
        /** The size TabBar asks of an icon. */
        size?: number;
    }

    let {icon, size = 24}: Props = $props();
</script>

<svg data-icon={icon} data-testid="settings-icon-probe" height={size} width={size}></svg>
