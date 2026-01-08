<!--
  AnimatedBackground.svelte
  Animated financial chart-like background
-->
<script lang="ts">
	import { onMount } from 'svelte';

	let mounted = false;
	onMount(() => {
		mounted = true;
	});
</script>

<div class="animated-bg">
	<!-- Animated waves -->
	{#if mounted}
		<div class="wave wave-1"></div>
		<div class="wave wave-2"></div>
		<div class="wave wave-3"></div>
	{/if}

	<!-- Chart lines container - multiple lines that cycle -->
	<svg class="chart-svg" viewBox="0 0 1200 200" preserveAspectRatio="none">
		<path
			class="chart-line line-1"
			d="M0,150 L100,130 L200,140 L300,100 L400,120 L500,80 L600,90 L700,60 L800,70 L900,40 L1000,55 L1100,30 L1200,45"
			fill="none"
			stroke="#1a4031"
			stroke-width="2"
		/>
		<path
			class="chart-line line-2"
			d="M0,120 L100,140 L200,100 L300,130 L400,90 L500,110 L600,70 L700,95 L800,55 L900,80 L1000,45 L1100,65 L1200,35"
			fill="none"
			stroke="#1a4031"
			stroke-width="2"
		/>
		<path
			class="chart-line line-3"
			d="M0,140 L100,110 L200,130 L300,85 L400,115 L500,75 L600,100 L700,50 L800,85 L900,60 L1000,75 L1100,40 L1200,55"
			fill="none"
			stroke="#1a4031"
			stroke-width="2"
		/>
	</svg>
</div>

<style>
	.animated-bg {
		position: fixed;
		inset: 0;
		z-index: -10;
		background-color: #f5f4ef;
		overflow: hidden;
	}

	.wave {
		position: absolute;
		bottom: 0;
		left: -5%;
		width: 110%;
		height: 60%;
		background: linear-gradient(to top, #9caf9c, transparent);
		transform-origin: bottom center;
	}

	.wave-1 {
		opacity: 0.25;
		animation: wave1 12s ease-in-out infinite;
		clip-path: polygon(
			0% 100%, 0% 60%, 15% 55%, 30% 65%, 45% 50%,
			60% 60%, 75% 45%, 90% 55%, 100% 40%, 100% 100%
		);
	}

	.wave-2 {
		opacity: 0.18;
		animation: wave2 16s ease-in-out infinite;
		clip-path: polygon(
			0% 100%, 0% 70%, 20% 60%, 40% 70%, 60% 55%,
			80% 65%, 100% 50%, 100% 100%
		);
	}

	.wave-3 {
		opacity: 0.12;
		animation: wave3 20s ease-in-out infinite;
		clip-path: polygon(
			0% 100%, 0% 55%, 25% 65%, 50% 50%, 75% 60%, 100% 45%, 100% 100%
		);
	}

	@keyframes wave1 {
		0%, 100% {
			transform: scaleY(1);
		}
		25% {
			transform: scaleY(1.15);
		}
		50% {
			transform: scaleY(0.9);
		}
		75% {
			transform: scaleY(1.1);
		}
	}

	@keyframes wave2 {
		0%, 100% {
			transform: scaleY(1);
		}
		33% {
			transform: scaleY(1.2);
		}
		66% {
			transform: scaleY(0.85);
		}
	}

	@keyframes wave3 {
		0%, 100% {
			transform: scaleY(1);
		}
		50% {
			transform: scaleY(1.25);
		}
	}

	.chart-svg {
		position: absolute;
		bottom: 40%;
		left: 0;
		width: 100%;
		height: 30%;
	}

	.chart-line {
		opacity: 0;
		stroke-dasharray: 2000;
		stroke-dashoffset: 2000;
	}

	.line-1 {
		animation: drawAndFade 12s ease-in-out infinite;
	}

	.line-2 {
		animation: drawAndFade 12s ease-in-out infinite;
		animation-delay: 4s;
	}

	.line-3 {
		animation: drawAndFade 12s ease-in-out infinite;
		animation-delay: 8s;
	}

	@keyframes drawAndFade {
	0% {
		stroke-dashoffset: 2000;
		opacity: 0;
	}
	5% {
		opacity: 0.15;
	}
    30% {
		stroke-dashoffset: -0;
	}
	55% {
		opacity: 0.15;
	}
	60% {
		stroke-dashoffset: -2000;
		opacity: 0;
	}
}
</style>
