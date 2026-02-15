<script lang="ts">
	import { getRatpIconPath } from '../utils/ratp_utils';

	export let route_short_name: string;
	export let matchTextHeight: boolean = false;

	$: iconPath = getRatpIconPath(route_short_name);
</script>

{#if iconPath}
	<img
		class="inline-block"
		class:match-text-height={matchTextHeight}
		src={iconPath}
		alt={`RATP icon for ${route_short_name}`}
	/>
{:else}
	<!-- Fallback to text -->
	<span class="fallback">{route_short_name}</span>
{/if}

<style>
	.fallback {
		font-weight: bold;
		padding: 0 0.2em;
	}
	.match-text-height {
		height: 1.1em;
		width: 1.1em;
		vertical-align: middle;
	}
	img:not(.match-text-height) {
		height: 1.25em;
		width: 1.25em;
		vertical-align: middle;
	}
</style>
