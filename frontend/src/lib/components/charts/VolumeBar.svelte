<!-- VolumeBar — STUB. Will be implemented in Step 6.
     Bar chart showing daily percentage change (green positive, red negative). -->
<script lang="ts">
    interface Props { height?: string; }
    let { height = '80px' }: Props = $props();
</script>
<div class="flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-dashed border-gray-300 dark:border-slate-600" style="height: {height};">
    <p class="text-gray-400 dark:text-slate-500 text-sm">VolumeBar — Step 6</p>
</div>
