<script setup>
import { ref, onMounted } from 'vue'
import { version } from '@tradingview/trading_platform/charting_library'
const nodeVersion = ref('')
const chromeVersion = ref('')
const electronVersion = ref('')
const chartingLibraryVersion = ref('')
onMounted(() => {
  if (window.electronAPI) {
    nodeVersion.value = window.electronAPI.getVersion().node
    chromeVersion.value = window.electronAPI.getVersion().chrome
    electronVersion.value = window.electronAPI.getVersion().electron
  }

  var array = version().match(/(\d+)[.](\d+)[.](\d+)/g);
  chartingLibraryVersion.value = array[0]
})
</script>

<template>
  <ul class="versions">
    <li class="electron-version">Electron v{{ electronVersion }}</li>
    <li class="chrome-version">Chromium v{{ chromeVersion }}</li>
    <li class="node-version">Node v{{ nodeVersion }}</li>
    <li class="node-version">charting library v{{ chartingLibraryVersion }}</li>
  </ul>
</template>
