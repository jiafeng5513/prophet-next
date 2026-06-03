/**
 * Vegas
 * 自定义技术指标
 */

/**
 * @param {object} PineJS - TradingView PineJS 运行时对象
 * @returns {object} CustomIndicator
 */
export function create(PineJS) {
  return {
    name: 'Vegas',

    metainfo: {
      _metainfoVersion: 53,
      id: 'Vegas@tv-basicstudies-1',
      name: 'Vegas',
      description: 'Vegas',
      shortDescription: 'Vegas',
      is_price_study: true,
      isCustomIndicator: true,
      linkedToSeries: true,
      format: { type: 'inherit' },

      plots: [
        { id: 'plot0', type: 'line' }
      ],

      defaults: {
        styles: {
          plot0: { linestyle: 0, linewidth: 2, plottype: 2, trackPrice: false, transparency: 0, color: '#2196F3', visible: true }
        },
        inputs: {
          length: 20
        }
      },

      styles: {
        plot0: { title: 'Value', histogramBase: 0 }
      },

      inputs: [
        { id: 'length', name: 'Length', type: 'integer', defval: 20, min: 1, max: 500 }
      ]
    },

    constructor: function () {
      this.main = function (context, inputCallback) {
        this._context = context
        this._input = inputCallback

        var length = this._input(0)
        var close = this._context.new_var(PineJS.Std.close(this._context))

        return [
          PineJS.Std.sma(close, length, this._context)
        ]
      }
    }
  }
}
