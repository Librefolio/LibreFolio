<script lang="ts">
	import AnimatedBackground from '$lib/components/AnimatedBackground.svelte';
	import { ShieldCheck } from 'lucide-svelte'; // Using lucide-svelte for icons if available, or SVG fallback

	// Placeholder for form handling
	let username = '';
	let password = '';

	function handleLogin() {
		console.log('Login attempt:', username);
		// TODO: Integrate with backend /auth/login
	}
</script>

<AnimatedBackground />

<div class="min-h-screen flex items-center justify-center p-4">
	<!-- Card Container -->
	<div class="w-full max-w-[400px] bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans">
		
		<!-- Header Section (Dark Green) -->
		<div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-3">
			<!-- Logo Area -->
			<div class="flex items-center space-x-2 text-white">
				<!-- SVG Shield Icon Fallback if lucide is not installed -->
				<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
					<path d="m9 12 2 2 4-4"/>
				</svg>
				<span class="text-2xl font-bold tracking-wide">LibreFolio</span>
			</div>
		</div>

		<!-- Body Section (Beige) -->
		<div class="p-8 pt-10">
			<form on:submit|preventDefault={handleLogin} class="space-y-5">
				
				<!-- Username Input -->
				<div class="relative">
					<input 
						type="text" 
						placeholder="Username or Email" 
						bind:value={username}
						class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all"
					/>
				</div>

				<!-- Password Input -->
				<div class="relative">
					<input 
						type="password" 
						placeholder="Password" 
						bind:value={password}
						class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all"
					/>
				</div>

				<!-- Forgot Password Link -->
				<div class="flex justify-end">
					<a href="/" class="text-xs font-semibold text-libre-dark hover:text-libre-green underline decoration-1 underline-offset-2">
						Forgot Password?
					</a>
				</div>

				<!-- Login Button -->
				<button 
					type="submit" 
					class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98]"
				>
					Login
				</button>

				<!-- Register Link -->
				<div class="text-center pt-2 text-xs text-gray-600">
					<span>Don't have an account? </span>
					<a href="/" class="font-bold text-libre-dark hover:underline">Register here</a>
				</div>

			</form>
		</div>
	</div>
</div>
