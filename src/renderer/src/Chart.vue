<script setup>
import TVChartContainer from '@renderer/components/TVChartContainer.vue'
</script>

<template>
  <div class="app">
    <TVChartContainer />
  </div>
</template>

<style scoped>
.app {
  text-align: center;
}

.app_header {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
  background-color: #222;
  color: #fff;
  height: 60px;
  max-height: 60px;
  padding: 10px;
}

.app_title {
  display: block;
  font-size: 1.25em;
}
</style>
