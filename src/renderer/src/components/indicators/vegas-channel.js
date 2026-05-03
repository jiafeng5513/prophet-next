/**
 * Vegas Channel 自定义技术指标
 *
 * 由 5 条 EMA 组成，形成两个趋势通道带：
 *   - EMA12          快速信号线（橙红色）
 *   - EMA144 / EMA169  窄带（青色）
 *   - EMA576 / EMA676  宽带（紫色）
 *
 * 语言：JavaScript (ES5 兼容)
 * 运行环境：TradingView Charting Library custom_indicators_getter
 *
 * 使用方式：
 *   import { vegasChannelIndicator } from './indicators/vegas-channel.js'
 *   custom_indicators_getter: (PineJS) => Promise.resolve([vegasChannelIndicator(PineJS)])
 */

/**
 * 工厂函数，接收 PineJS 工具对象，返回符合 CustomIndicator 接口的指标对象。
 * @param {object} PineJS - TradingView 注入的 PineJS 工具对象
 * @returns {object} CustomIndicator
 */
export function vegasChannelIndicator(PineJS) {
  return {
    // 指标的内部唯一名称（不显示在 UI）
    name: 'VegasChannel',

    metainfo: {
      // 当前文档建议使用版本 53
      _metainfoVersion: 53,

      // id 格式固定为 '<name>@tv-basicstudies-1'，必须全局唯一
      id: 'VegasChannel@tv-basicstudies-1',
      name: 'VegasChannel',

      // description 显示在指标对话框和图例中
      description: 'Vegas Channel',
      // shortDescription 显示在图例标签和样式设置标题
      shortDescription: 'Vegas',

      // true = 叠加在主图（K线图）上，false = 显示在独立副图
      is_price_study: true,
      isCustomIndicator: true,

      // 与主图绑定，不允许移动到其他 pane
      linkedToSeries: true,

      // 继承主图的价格格式（小数位数等）
      format: { type: 'inherit' },

      // -----------------------------------------------------------------
      // plots：定义指标由哪些绘图元素组成
      // 每个 plot 对应 main() 返回数组中的一个元素，顺序一致
      // -----------------------------------------------------------------
      plots: [
        { id: 'ema12',  type: 'line' },
        { id: 'ema144', type: 'line' },
        { id: 'ema169', type: 'line' },
        { id: 'ema576', type: 'line' },
        { id: 'ema676', type: 'line' }
      ],

      // -----------------------------------------------------------------
      // filledAreas：在两条 plot 线之间绘制填充色区域
      // objAId / objBId 对应 plots 中的 id
      // -----------------------------------------------------------------
      filledAreas: [
        {
          id: 'narrowBandFill',
          objAId: 'ema144',
          objBId: 'ema169',
          type: 'plot_plot',
          title: 'Narrow Band Fill'
        },
        {
          id: 'wideBandFill',
          objAId: 'ema576',
          objBId: 'ema676',
          type: 'plot_plot',
          title: 'Wide Band Fill'
        }
      ],

      // -----------------------------------------------------------------
      // defaults：指标首次加载时的默认样式和参数值
      // 用户可在"设置"对话框中修改，并可通过"恢复默认"还原
      // -----------------------------------------------------------------
      defaults: {
        styles: {
          // plottype 2 = Line（折线），0 = Histogram
          ema12:  { linestyle: 0, linewidth: 1, plottype: 2, trackPrice: false, transparency: 0, color: '#FF6B35', visible: true },
          ema144: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#00BCD4', visible: true },
          ema169: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#00BCD4', visible: true },
          ema576: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#7E57C2', visible: true },
          ema676: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#7E57C2', visible: true }
        },
        filledAreasStyle: {
          narrowBandFill: { color: '#00BCD4', transparency: 85, visible: true },
          wideBandFill:   { color: '#7E57C2', transparency: 85, visible: true }
        },
        inputs: {
          length12:  12,
          length144: 144,
          length169: 169,
          length576: 576,
          length676: 676
        }
      },

      // -----------------------------------------------------------------
      // styles：每个 plot 在图例 / 样式面板中显示的名称（用户不可修改）
      // -----------------------------------------------------------------
      styles: {
        ema12:  { title: 'EMA 12',  histogramBase: 0 },
        ema144: { title: 'EMA 144', histogramBase: 0 },
        ema169: { title: 'EMA 169', histogramBase: 0 },
        ema576: { title: 'EMA 576', histogramBase: 0 },
        ema676: { title: 'EMA 676', histogramBase: 0 }
      },

      // -----------------------------------------------------------------
      // inputs：用户可在"输入"选项卡中调整的参数
      // 顺序决定 inputCallback(index) 的 index
      // -----------------------------------------------------------------
      inputs: [
        { id: 'length12',  name: 'EMA12 Length',  type: 'integer', defval: 12,  min: 1, max: 2000 },
        { id: 'length144', name: 'EMA144 Length', type: 'integer', defval: 144, min: 1, max: 2000 },
        { id: 'length169', name: 'EMA169 Length', type: 'integer', defval: 169, min: 1, max: 2000 },
        { id: 'length576', name: 'EMA576 Length', type: 'integer', defval: 576, min: 1, max: 2000 },
        { id: 'length676', name: 'EMA676 Length', type: 'integer', defval: 676, min: 1, max: 2000 }
      ]
    },

    // -----------------------------------------------------------------
    // constructor：ES5 构造函数，库通过 new 实例化
    // main() 在每根 K 线上被调用一次，返回值对应 plots 数组的顺序
    // -----------------------------------------------------------------
    constructor: function () {
      this.main = function (context, inputCallback) {
        this._context = context
        this._input = inputCallback

        // 读取用户输入的参数（顺序与 inputs 数组一致）
        var len12  = this._input(0)
        var len144 = this._input(1)
        var len169 = this._input(2)
        var len576 = this._input(3)
        var len676 = this._input(4)

        // PineJS.Std.close() 返回当前 bar 的收盘价标量
        // new_var() 将其包装为 series（可回溯历史的序列），ema() 需要此类型
        var closeSeries = this._context.new_var(PineJS.Std.close(this._context))

        // 每次调用 ema() 时库会根据调用位置自动维护各自的 EMA 内部状态
        return [
          PineJS.Std.ema(closeSeries, len12,  this._context),
          PineJS.Std.ema(closeSeries, len144, this._context),
          PineJS.Std.ema(closeSeries, len169, this._context),
          PineJS.Std.ema(closeSeries, len576, this._context),
          PineJS.Std.ema(closeSeries, len676, this._context)
        ]
      }
    }
  }
}
