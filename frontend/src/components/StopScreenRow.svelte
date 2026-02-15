<script lang="ts">
	import TimeDiff from './TimeDiff.svelte';

	import BullseyeArrow from './svg_icons/bullseye_arrow.svelte';
	import DelayDiff from './DelayDiff.svelte';
	import { _ } from 'svelte-i18n';
	import Clock from './Clock.svelte';

	export let event: any;
	export let timezone: string;
	export let current_time: number;
	export let show_seconds: boolean;
	export let show_arrivals: boolean = false;
	export let vertical: boolean = false;
	export let use_symbol_sign: boolean = false;

	$: shared_rt_time = show_arrivals ? event.realtime_arrival : event.realtime_departure;

	$: shared_scheduled_time = show_arrivals ? event.scheduled_arrival : event.scheduled_departure;
</script>

<div class={`flex ${vertical ? 'flex-col items-end' : 'flex-row'}`}>
	{#if event.trip_cancelled}
		<div class="flex flex-row w-full">
			<span class="text-red-500 font-semibold">{$_('cancelled')}</span>
			<div class="ml-auto line-through opacity-70">
				<Clock
					{timezone}
					time_seconds={shared_scheduled_time}
					{show_seconds}
				/>
			</div>
		</div>
	{:else if event.trip_deleted}
		<div class="flex flex-row w-full">
			<span class="text-red-500 font-semibold">{$_('deleted')}</span>
			<div class="ml-auto line-through opacity-70">
				<Clock
					{timezone}
					time_seconds={shared_scheduled_time}
					{show_seconds}
				/>
			</div>
		</div>
	{:else if event.stop_cancelled}
		<div class="flex flex-row w-full">
			<span class="text-red-500 font-semibold">{$_('stop_cancelled')}</span>
			<div class="ml-auto line-through opacity-70">
				<Clock
					{timezone}
					time_seconds={shared_scheduled_time}
					{show_seconds}
				/>
			</div>
		</div>
	{:else}
		
		{#if !vertical}
			<TimeDiff
				large={false}
				show_brackets={false}
				{show_seconds}
				diff={(shared_rt_time || shared_scheduled_time) - current_time / 1000}
			/>
		{/if}

		{#if !vertical}
			<span class="ml-1">
				{#if shared_rt_time}
					{#if shared_scheduled_time}
						<DelayDiff diff={shared_rt_time - shared_scheduled_time} {show_seconds} {use_symbol_sign} />
					{/if}
				{/if}
			</span>
		{/if}

		{#if shared_rt_time}
			<div class="ml-auto flex flex-col items-end">
				{#if vertical}
					<!-- Vertical Mode: Scheduled -> Delay -> Realtime -->
					{#if shared_rt_time != shared_scheduled_time}
						<span class="text-gray-600 dark:text-gray-400 line-through text-xs">
							<Clock
								{timezone}
								time_seconds={shared_scheduled_time}
								{show_seconds}
							/>
						</span>
						{#if shared_scheduled_time}
							<!-- Only show if significant delay or not minimizing -->
							<DelayDiff diff={shared_rt_time - shared_scheduled_time} {show_seconds} {use_symbol_sign} />
						{/if}
						<span
							class={`text-seashore dark:text-seashoredark font-medium ${shared_rt_time < current_time / 1000 ? 'opacity-70' : ''}`}
						>
							<Clock
								{timezone}
								time_seconds={shared_rt_time}
								{show_seconds}
							/>
						</span>
					{:else}
						<!-- On Time (Vertical) -->
						<span
							class={`text-seashore dark:text-seashoredark font-medium ${shared_rt_time < current_time / 1000 ? 'opacity-70' : ''}`}
						>
							<Clock
								{timezone}
								time_seconds={shared_rt_time}
								{show_seconds}
							/>
						</span>
					{/if}
				{:else}
					<!-- Horizontal Mode -->
					<div class="flex flex-row items-center">
						{#if shared_rt_time == shared_scheduled_time}
							<BullseyeArrow class_name="w-4 h-4 inline-block align-middle text-[#58A738]" />
						{/if}
						{#if shared_rt_time != shared_scheduled_time}
							<span class="text-gray-600 dark:text-gray-400 line-through mr-1">
								<Clock
									{timezone}
									time_seconds={shared_scheduled_time}
									{show_seconds}
								/>
							</span>
						{/if}
						<span
							class={`text-seashore dark:text-seashoredark font-medium ${shared_rt_time < current_time / 1000 ? 'opacity-70' : ''}`}
						>
							<Clock
								{timezone}
								time_seconds={shared_rt_time}
								{show_seconds}
							/>
						</span>
					</div>
				{/if}
			</div>
		{:else}
			<div class={`ml-auto ${shared_scheduled_time < current_time / 1000 ? 'opacity-70' : ''}`}>
				<Clock
					{timezone}
					time_seconds={shared_scheduled_time}
					{show_seconds}
				/>
			</div>
		{/if}

		{#if vertical}
			<div class="mt-1">
				<TimeDiff
					large={false}
					show_brackets={false}
					{show_seconds}
					diff={(shared_rt_time || shared_scheduled_time) - current_time / 1000}
				/>
			</div>
		{/if}
	{/if}
</div>
