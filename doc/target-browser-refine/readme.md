接下来我们要对标的浏览器进行重构。

要解决的问题
1. 左侧侧边栏作为标的浏览器，可视区域比较小，每行能显示的信息有限
2. 标的浏览器没有排列，筛选等功能

需要的效果
1. 左侧侧边栏留用，用于显示自选
2. 导航栏项目-交易模式中，增加一个tab页面，该页面不可关闭，作为标的浏览器
    标的浏览器分为加密、A股、港股、美股四个板块
3. 导航栏项目-交易模式中，增加一个tab页面，作为首页，该页面不可关闭，程序启动后默认显示
    首页显示上证综指，深证成指，纳斯达克指数，道琼斯指数等宏观数据
4. TradingView的标的浏览器中，每个标的显示的项目，包括商品代码、名称、价格、涨跌、成交量、相对成交量、总市值、P/E、摊薄每股收益、板块、分析师评级等，每列均可以升序和降序，我们要对此进行评估，看能拿到哪些数据

tickflow的api文档
https://docs.tickflow.org/zh-Hans

binance api 文档
https://developers.binance.com/docs/binance-spot-api-docs/rest-api#market-data-endpoints
https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams

