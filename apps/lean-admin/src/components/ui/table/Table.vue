<script setup>
import { cn } from "@/lib/utils";

const props = defineProps({
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
});
</script>

<template>
  <div data-slot="table-container" class="relative w-full">
    <table
      data-slot="table"
      :class="cn('w-full caption-bottom border-separate border-spacing-0 text-sm', props.class)"
    >
      <slot />
    </table>
  </div>
</template>
