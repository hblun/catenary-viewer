<script lang="ts">
	import { MTA_CHATEAU_ID, isSubwayRouteId } from '../utils/mta_subway_utils';
	import { IDFM_CHATEAU_ID, isRatpRoute } from '../utils/ratp_utils';
	import MtaBullet from './mtabullet.svelte';
	import RatpBullet from './ratpbullet.svelte';

	export let connections: { chateau_id: string; route_id: string; route: any }[] = [];
	export let darkMode: boolean = false;

	$: national_rail_connections = connections.filter((c) => c.chateau_id === 'nationalrailuk');

	$: gwr_routes = national_rail_connections.filter((c) => c.route.agency_id === 'GW');
	$: sw_routes = national_rail_connections.filter((c) => c.route.agency_id === 'SW');
	$: sn_routes = national_rail_connections.filter((c) => c.route.agency_id === 'SN');
	$: cc_routes = national_rail_connections.filter((c) => c.route.agency_id === 'CC');
	$: le_routes = national_rail_connections.filter((c) => c.route.agency_id === 'LE');

	$: grouped_route_ids = new Set([
		...gwr_routes.map((c) => c.route_id),
		...sw_routes.map((c) => c.route_id),
		...sn_routes.map((c) => c.route_id),
		...cc_routes.map((c) => c.route_id),
		...le_routes.map((c) => c.route_id)
	]);
</script>

{#if gwr_routes.length > 0}
	<div class="flex flex-row items-center mr-2 bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">
		<img
			src="/agencyicons/GreaterWesternRailway.svg"
			alt="Great Western Railway"
			class="h-3 inline-block dark:hidden mr-1"
		/>
		<img
			src="/agencyicons/GreaterWesternRailwayBrighter.svg"
			alt="Great Western Railway"
			class="h-3 hidden dark:inline-block mr-1"
		/>
		<span class="text-xs font-semibold">Great Western Railway</span>
	</div>
{/if}

{#if sw_routes.length > 0}
	<div class="flex flex-row items-center mr-2 bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">
		<img
			src="/agencyicons/SouthWesternRailway.svg"
			alt="South Western Railway"
			class="h-3 inline-block mr-1"
		/>
		<span class="text-xs font-semibold">South Western Railway</span>
	</div>
{/if}

{#if sn_routes.length > 0}
	<div class="flex flex-row items-center mr-2 bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">
		<img src="/agencyicons/SouthernIcon.svg" alt="Southern" class="h-3 inline-block mr-1" />
		<span class="text-xs font-semibold">Southern</span>
	</div>
{/if}

{#if cc_routes.length > 0}
	<div class="flex flex-row items-center mr-2 bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">
		<img src="/agencyicons/c2c_logo.svg" alt="c2c" class="h-3 inline-block mr-1" />
		<span class="text-xs font-semibold">c2c</span>
	</div>
{/if}

{#if le_routes.length > 0}
	<div class="flex flex-row items-center mr-2 bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">
		<span class="text-xs font-semibold">Greater Anglia</span>
	</div>
{/if}

{#each connections as conn}
	{#if !grouped_route_ids.has(conn.route_id) || conn.chateau_id !== 'nationalrailuk'}
		{#if isSubwayRouteId(conn.route_id) && conn.chateau_id === MTA_CHATEAU_ID}
			<MtaBullet route_short_name={conn.route.short_name} matchTextHeight={false} />
		{:else if conn.chateau_id === IDFM_CHATEAU_ID && isRatpRoute(conn.route.short_name)}
			<RatpBullet route_short_name={conn.route.short_name} matchTextHeight={false} />
		{:else}
			<div
				class="px-0.5 py-0.5 text-[10px] leading-none rounded-sm"
				style={`background-color: ${conn.route.color}; color: ${conn.route.text_color};`}
			>
				{#if conn.route.short_name}
					<span class="font-semibold">{conn.route.short_name}</span>
				{:else if conn.route.long_name}
					<span class="font-medium">{conn.route.long_name}</span>
				{/if}
			</div>
		{/if}
	{/if}
{/each}
