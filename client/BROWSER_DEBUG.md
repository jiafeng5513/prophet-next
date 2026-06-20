# 浏览器调试模式使用说明

## 概述

现在您可以在浏览器中直接调试这个 Electron 应用，而不需要启动桌面客户端。这大大提高了开发效率，特别是在调试前端界面和逻辑时。

## 使用方法

### 启动浏览器模式

```bash
npm run dev:browser
```

这个命令会：
1. 启动一个纯 Vite 开发服务器（不包含 Electron）
2. 自动在浏览器中打开应用（默认端口 5173）
3. 加载模拟的 Electron API，使应用可以在浏览器中正常运行

### 访问地址

- 主应用：http://localhost:5173/
- Home 页面：http://localhost:5173/home.html
- Chart 页面：http://localhost:5173/chart.html
- Python 编辑器：http://localhost:5173/python.html
- 设置页面：http://localhost:5173/settings.html

## 功能说明

### 已实现的功能

✅ **标签页管理**
- 创建/关闭标签页
- 切换标签页
- 标签页加载状态显示
- 标签页标题更新

✅ **页面导航**
- Home 页面
- Chart 页面（TradingView 图表）
- Python 编辑器
- 设置页面

✅ **Electron API 模拟**
- 所有主要的 Electron IPC 通信都已模拟
- 事件监听器系统正常工作
- 标签页生命周期管理

### 浏览器模式 vs Electron 模式

| 功能 | 浏览器模式 | Electron 模式 |
|------|-----------|--------------|
| 开发速度 | ⚡ 快速（热重载） | 较慢（需要重启 Electron） |
| 调试工具 | 🌐 浏览器 DevTools | Electron DevTools |
| 标签页实现 | iframe | WebContentsView |
| 文件系统访问 | ❌ 受限 | ✅ 完整访问 |
| 系统集成 | ❌ 无 | ✅ 完整集成 |

## 技术实现

### 核心文件

1. **`src/renderer/src/browser-mock.js`**
   - 模拟 Electron API
   - 实现浏览器模式的标签页管理器
   - 使用 iframe 来显示不同的页面

2. **`vite.browser.config.mjs`**
   - 纯 Vite 配置（不包含 Electron）
   - 配置了所有入口 HTML 文件
   - 设置了路径别名

3. **`src/renderer/index.html`**
   - 自动检测运行环境
   - 在浏览器模式下加载模拟 API
   - 在 Electron 模式下使用真实的 Electron API

## 调试技巧

### 使用浏览器开发者工具

1. **打开 DevTools**
   - 按 `F12` 或 `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows/Linux)
   - 右键点击页面 → 检查

2. **调试标签页**
   - 每个标签页都是独立的 iframe
   - 可以在 DevTools 中切换到不同的 iframe 上下文进行调试

3. **网络请求**
   - 可以在 Network 面板中查看所有 API 请求
   - 方便调试数据源连接（Binance、OKX 等）

4. **控制台日志**
   - 所有 `console.log` 都会显示在浏览器控制台
   - 可以看到 "🌐 浏览器模式已启用" 的提示

### 热重载

浏览器模式支持完整的 Vite 热重载：
- 修改 Vue 组件 → 自动更新
- 修改 CSS → 自动更新
- 修改 JavaScript → 自动更新（可能需要手动刷新）

## 注意事项

⚠️ **限制**

1. **文件系统访问**
   - 浏览器模式无法访问本地文件系统
   - 某些需要文件操作的功能可能不可用

2. **系统集成**
   - 无法使用 Electron 的系统级功能
   - 窗口管理、菜单等功能不可用

3. **跨域限制**
   - iframe 中的页面可能受到跨域限制
   - 某些 API 调用可能需要 CORS 配置

4. **存储隔离**
   - 浏览器模式使用浏览器本地存储
   - 与 Electron 模式的存储是分离的

## 切换回 Electron 模式

如果需要测试 Electron 特定功能，使用：

```bash
npm run dev
```

这会启动完整的 Electron 应用。

## 故障排除

### 端口被占用

如果 5173 端口被占用，Vite 会自动尝试下一个可用端口。或者可以修改 `vite.browser.config.mjs` 中的端口配置。

### 页面无法加载

1. 检查控制台是否有错误
2. 确认所有 HTML 文件都在 `src/renderer/` 目录下
3. 检查路径别名配置是否正确

### 标签页不显示

1. 打开浏览器控制台查看错误
2. 确认 `browser-mock.js` 已正确加载
3. 检查 iframe 的 src 路径是否正确

## 开发建议

- 🚀 **日常开发**：使用 `npm run dev:browser` 进行快速迭代
- 🧪 **功能测试**：使用 `npm run dev` 测试 Electron 特定功能
- 🐛 **调试问题**：优先在浏览器模式中调试，利用强大的浏览器 DevTools
- 📦 **构建前**：确保在 Electron 模式下进行最终测试
