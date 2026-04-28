<script setup>
import { ref, onMounted } from 'vue'
import { version } from 'klinecharts'
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

  chartingLibraryVersion.value = version()
})
</script>

<template>
  <ul class="versions">
    <li class="electron-version">Electron v{{ electronVersion }}</li>
    <li class="chrome-version">Chromium v{{ chromeVersion }}</li>
    <li class="node-version">Node v{{ nodeVersion }}</li>
    <li class="node-version">KLineChart v{{ chartingLibraryVersion }}</li>
  </ul>
</template>
