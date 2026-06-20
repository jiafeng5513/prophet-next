# Vegas Channel 自定义技术指标开发计划

## 1. 背景与简介

Vegas Channel 是由交易员 Vegas 提出的一套基于 EMA 的趋势通道指标，专为小时级及更高周期设计。  
它由 **5 条 EMA** 组成，形成两个"通道带"，用于判断趋势方向、支撑/压力区间和入场时机。

| 指标线 | 参数 | 视觉角色 |
|--------|------|----------|
| EMA12  | 12   | 快速均线，趋势先行信号 |
| EMA144 | 144  | Vegas 通道下沿（窄带） |
| EMA169 | 169  | Vegas 通道上沿（窄带） |
| EMA576 | 576  | Vegas 通道下沿（宽带） |
| EMA676 | 676  | Vegas 通道上沿（宽带） |

### 通道逻辑
- **窄带**（EMA144 ~ EMA169）：短期支撑/压力带，价格在此区间震荡或突破
- **宽带**（EMA576 ~ EMA676）：长期趋势核心区，是强趋势行情中的回踩区域
- **EMA12**：快速信号线，与通道的相对位置决定多空偏向

---

## 2. 技术方案

### 2.1 整体架构

```
TVChartContainer.vue
└── widgetOptions.custom_indicators_getter
    └── Vegas Channel (CustomIndicator)
        ├── metainfo: 5 个 plot（line 类型）+ 2 个 filledAreas
        └── constructor.main(): 用 PineJS.Std.ema() 计算 5 条线
```

**纯前端实现**：所有计算在 JS `main()` 中逐 K 线完成，无需调用 Python 后端，利用 TradingView 内置 `PineJS.Std.ema()` 函数。

### 2.2 计算方式

TradingView `custom_indicators_getter` 提供 `PineJS.Std.ema(source, length, context)`：

```js
// 每根 K 线调用一次 main()
this.main = function(ctx, inputCallback) {
  this._context = ctx
  this._input = inputCallback
  const close = PineJS.Std.close(ctx)
  const ema12  = PineJS.Std.ema(close, 12,  ctx)
  const ema144 = PineJS.Std.ema(close, 144, ctx)
  const ema169 = PineJS.Std.ema(close, 169, ctx)
  const ema576 = PineJS.Std.ema(close, 576, ctx)
  const ema676 = PineJS.Std.ema(close, 676, ctx)
  return [ema12, ema144, ema169, ema576, ema676]
}
```

### 2.3 视觉设计

| Plot ID     | 颜色（十六进制） | 线宽 | 说明 |
|-------------|-----------------|------|------|
| `ema12`     | `#FF6B35`       | 1    | 橙红色，快速信号线 |
| `ema144`    | `#00BCD4`       | 2    | 青色，窄带下沿 |
| `ema169`    | `#00BCD4`       | 2    | 青色，窄带上沿 |
| `ema576`    | `#7E57C2`       | 2    | 紫色，宽带下沿 |
| `ema676`    | `#7E57C2`       | 2    | 紫色，宽带上沿 |

**填充区域（filledAreas）**：
- 窄带填充：EMA144 ~ EMA169，`#00BCD4` 透明度 15%
- 宽带填充：EMA576 ~ EMA676，`#7E57C2` 透明度 15%

---

## 3. 开发任务拆解

### Phase 1：核心指标实现（TVChartContainer.vue）

- [ ] **T1.1** 在 `widgetOptions` 中添加 `custom_indicators_getter` 属性
- [ ] **T1.2** 定义 Vegas Channel 的 `metainfo`
  - 5 个 `plots`（line 类型）
  - 5 个 `palettes` / `styles`（颜色、线宽）
  - 2 个 `filledAreas`（窄带填充、宽带填充）
  - `is_price_study: true`（叠加在主图）
  - `shortDescription` / `fullName`
- [ ] **T1.3** 实现 `constructor`，编写 `main()` 函数
  - 用 `PineJS.Std.ema()` 计算 5 条 EMA
  - 返回 `[ema12, ema144, ema169, ema576, ema676]`
- [ ] **T1.4** 将指标注册到 `chartWidget`，验证图表上正确显示 5 条线 + 2 个填充区

### Phase 2：参数可配置化

- [ ] **T2.1** 在 `metainfo.inputs` 中添加 5 个 integer 类型输入
  - `length12`（默认 12）
  - `length144`（默认 144）
  - `length169`（默认 169）
  - `length576`（默认 576）
  - `length676`（默认 676）
- [ ] **T2.2** `main()` 通过 `inputCallback()` 读取用户参数

### Phase 3：样式优化与集成

- [ ] **T3.1** 调整颜色与透明度，与深色主题（`#151517`）协调
- [ ] **T3.2** 在指标列表对话框中验证指标可被用户手动添加/删除
- [ ] **T3.3** 验证在不同周期（1H / 4H / 1D）下指标计算正确

### Phase 4（可选）：默认自动加载

- [ ] **T4.1** 图表 `onChartReady` 后自动调用 `chart.createStudy('VegasChannel@tv-basicstudies-1')`
- [ ] **T4.2** 支持通过设置页面开关"是否默认显示 Vegas Channel"

---

## 4. 关键 API 参考

### `custom_indicators_getter` 入口

```js
custom_indicators_getter: function(PineJS) {
  return Promise.resolve([
    {
      name: 'VegasChannel',
      metainfo: { /* ... */ },
      constructor: function() { /* ... */ }
    }
  ])
}
```

### metainfo 最小结构

```js
metainfo: {
  _metainfoVersion: 51,
  id: 'VegasChannel@tv-basicstudies-1',
  name: 'VegasChannel',
  description: 'Vegas Channel',
  shortDescription: 'Vegas',
  is_price_study: true,        // 叠加主图
  isCustomIndicator: true,
  plots: [
    { id: 'ema12',  type: 'line' },
    { id: 'ema144', type: 'line' },
    { id: 'ema169', type: 'line' },
    { id: 'ema576', type: 'line' },
    { id: 'ema676', type: 'line' },
  ],
  filledAreas: [
    {
      id: 'narrowBand',
      objAId: 'ema144', objBId: 'ema169',
      type: 'plot_plot',
      title: 'Narrow Band',
      palette: 'narrowBandPalette'
    },
    {
      id: 'wideBand',
      objAId: 'ema576', objBId: 'ema676',
      type: 'plot_plot',
      title: 'Wide Band',
      palette: 'wideBandPalette'
    }
  ],
  defaults: {
    styles: {
      ema12:  { linestyle: 0, linewidth: 1, plottype: 0, color: '#FF6B35' },
      ema144: { linestyle: 0, linewidth: 2, plottype: 0, color: '#00BCD4' },
      ema169: { linestyle: 0, linewidth: 2, plottype: 0, color: '#00BCD4' },
      ema576: { linestyle: 0, linewidth: 2, plottype: 0, color: '#7E57C2' },
      ema676: { linestyle: 0, linewidth: 2, plottype: 0, color: '#7E57C2' },
    },
    filledAreasStyle: {
      narrowBand: { color: '#00BCD4', transparency: 85, visible: true },
      wideBand:   { color: '#7E57C2', transparency: 85, visible: true },
    },
    inputs: { length12: 12, length144: 144, length169: 169, length576: 576, length676: 676 }
  },
  inputs: [
    { id: 'length12',  name: 'EMA12 Length',  type: 'integer', defval: 12,  min: 1, max: 2000 },
    { id: 'length144', name: 'EMA144 Length', type: 'integer', defval: 144, min: 1, max: 2000 },
    { id: 'length169', name: 'EMA169 Length', type: 'integer', defval: 169, min: 1, max: 2000 },
    { id: 'length576', name: 'EMA576 Length', type: 'integer', defval: 576, min: 1, max: 2000 },
    { id: 'length676', name: 'EMA676 Length', type: 'integer', defval: 676, min: 1, max: 2000 },
  ]
}
```

### constructor 完整示例

```js
constructor: function() {
  this.main = function(ctx, inputCallback) {
    this._context = ctx
    this._input = inputCallback

    const len12  = this._input(0)
    const len144 = this._input(1)
    const len169 = this._input(2)
    const len576 = this._input(3)
    const len676 = this._input(4)

    const close = PineJS.Std.close(this._context)

    return [
      PineJS.Std.ema(close, len12,  this._context),
      PineJS.Std.ema(close, len144, this._context),
      PineJS.Std.ema(close, len169, this._context),
      PineJS.Std.ema(close, len576, this._context),
      PineJS.Std.ema(close, len676, this._context),
    ]
  }
}
```

---

## 5. 文件改动清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `src/renderer/src/components/TVChartContainer.vue` | 修改 | 在 `widgetOptions` 中添加 `custom_indicators_getter` |

仅需修改 **1 个文件**，无需后端改动。

---

## 6. 验证标准

1. 图表主图上出现 5 条 EMA 线，颜色符合设计
2. EMA144/EMA169 之间有青色半透明填充
3. EMA576/EMA676 之间有紫色半透明填充
4. 打开"指标设置"可修改各 EMA 参数
5. 切换 symbol 或 timeframe 后指标自动重算
6. 长周期（EMA676）需等待至少 676 根 K 线才完全稳定（前期显示 NaN 为正常）
