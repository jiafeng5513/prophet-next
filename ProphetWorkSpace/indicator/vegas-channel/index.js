/**
 * Vegas Channel 自定义技术指标
 *
 * 由 5 条 EMA 组成，形成两个趋势通道带：
 *   - EMA12          快速信号线（橙红色）
 *   - EMA144 / EMA169  窄带（青色）
 *   - EMA576 / EMA676  宽带（紫色）
 */

/**
 * @param {object} PineJS - TradingView PineJS 运行时对象
 * @returns {object} CustomIndicator
 */
export function create(PineJS) {
  return {
    name: 'VegasChannel',

    metainfo: {
      _metainfoVersion: 53,
      id: 'VegasChannel@tv-basicstudies-1',
      name: 'VegasChannel',
      description: 'Vegas Channel',
      shortDescription: 'Vegas',
      is_price_study: true,
      isCustomIndicator: true,
      linkedToSeries: true,
      format: { type: 'inherit' },

      plots: [
        { id: 'ema12', type: 'line' },
        { id: 'ema144', type: 'line' },
        { id: 'ema169', type: 'line' },
        { id: 'ema576', type: 'line' },
        { id: 'ema676', type: 'line' }
      ],

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

      defaults: {
        styles: {
          ema12: { linestyle: 0, linewidth: 1, plottype: 2, trackPrice: false, transparency: 0, color: '#FF6B35', visible: true },
          ema144: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#00BCD4', visible: true },
          ema169: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#00BCD4', visible: true },
          ema576: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#7E57C2', visible: true },
          ema676: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#7E57C2', visible: true }
        },
        filledAreasStyle: {
          narrowBandFill: { color: '#00BCD4', transparency: 85, visible: true },
          wideBandFill: { color: '#7E57C2', transparency: 85, visible: true }
        },
        inputs: {
          length12: 12,
          length144: 144,
          length169: 169,
          length576: 576,
          length676: 676
        }
      },

      styles: {
        ema12: { title: 'EMA 12', histogramBase: 0 },
        ema144: { title: 'EMA 144', histogramBase: 0 },
        ema169: { title: 'EMA 169', histogramBase: 0 },
        ema576: { title: 'EMA 576', histogramBase: 0 },
        ema676: { title: 'EMA 676', histogramBase: 0 }
      },

      inputs: [
        { id: 'length12', name: 'EMA12 Length', type: 'integer', defval: 12, min: 1, max: 2000 },
        { id: 'length144', name: 'EMA144 Length', type: 'integer', defval: 144, min: 1, max: 2000 },
        { id: 'length169', name: 'EMA169 Length', type: 'integer', defval: 169, min: 1, max: 2000 },
        { id: 'length576', name: 'EMA576 Length', type: 'integer', defval: 576, min: 1, max: 2000 },
        { id: 'length676', name: 'EMA676 Length', type: 'integer', defval: 676, min: 1, max: 2000 }
      ]
    },

    constructor: function () {
      this.main = function (context, inputCallback) {
        this._context = context
        this._input = inputCallback

        var len12 = this._input(0)
        var len144 = this._input(1)
        var len169 = this._input(2)
        var len576 = this._input(3)
        var len676 = this._input(4)

        var closeSeries = this._context.new_var(PineJS.Std.close(this._context))

        return [
          PineJS.Std.ema(closeSeries, len12, this._context),
          PineJS.Std.ema(closeSeries, len144, this._context),
          PineJS.Std.ema(closeSeries, len169, this._context),
          PineJS.Std.ema(closeSeries, len576, this._context),
          PineJS.Std.ema(closeSeries, len676, this._context)
        ]
      }
    }
  }
}
