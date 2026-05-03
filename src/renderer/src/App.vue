<script setup>
import Versions from '@renderer/components/Versions.vue'
</script>

<template>
  <img alt="logo" class="logo" src="./assets/hivelogic_logo.png" />
  <div class="creator">HiveLogic</div>
  <div class="text">
    Build With Electron-Vite and
    <span class="vue">Vue</span>
  </div>

  <div class="actions">
    <div class="action">
      <a href="https://electron-vite.org/" target="_blank" rel="noreferrer">Documentation</a>
    </div>
  </div>
  <Versions />
</template>
