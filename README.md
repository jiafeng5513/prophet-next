<div align=center><img width="100" height="100" src="resources/prophet_logo.png"/></div>
</br>
<div align=center>Prophet-Next</div>
</br>
</br>
</br>
<div align=center><img src="doc/screenshot.png"/></div>


## Develop Environment Setup
1. install with windows package control
    ```powershell
    # installs fnm (Fast Node Manager)
    winget install Schniz.fnm

    # close and restart a new windows shell
    fnm env --use-on-cd | Out-String | Invoke-Expression

    # download and install Node.js
    fnm use --install-if-missing 20

    # verifies the right Node.js version is in the environment
    node -v 

    # verifies the right NPM version is in the environment
    npm -v 

    # optinal: find all available version
    fnm list-remote

    # optinal: find all installed version
    fnm list

    # optinal: install a new version 
    fnm install v22.17.0

    # optinal: select a default version
    fnm default v22.17.0

    # optinal: install nrm to manager npm source
    npm install -g nrm
    # optinal: `nrm ls` to show all avaliable source, `nrm use` to set it
    ```

2. close and restart a new Windows shell, run `npm -v`, it should tell you that the npm is not a valied command or executable, that because the npm env is one-time-drop now. You can try `fnm env --use-on-cd | Out-String | Invoke-Expression` again, and then `npm -v`, and it should work again.

3. to make npm env activate auto start with windows shell, edit the `C:\Users\${username}\Documents\WindowsPowerShell\profile.ps1` which created when install anaconda, edit it as bellow:
    ```powershell
    #region conda initialize
    # !! Contents within this block are managed by 'conda init' !!
    If (Test-Path "C:\ProgramData\anaconda3\Scripts\conda.exe") {
        (& "C:\ProgramData\anaconda3\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | ?{$_} | Invoke-Expression
    }
    #endregion

    #region npm initialize
    fnm env --use-on-cd | Out-String | Invoke-Expression
    #endregion
    ```
4. install vue
    ```shell
    npm i @vue/cli -g
    ```

## Recommended IDE Setup

- [VSCode](https://code.visualstudio.com/) + [ESLint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint) + [Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar)

## Project Setup

### Install

```bash
$ npm install
```

### Development

```bash
$ npm run dev
```

### Build

```bash
# For windows
$ npm run build:win

# For macOS
$ npm run build:mac

# For Linux
$ npm run build:linux
```

## Referemce
1. [electron-vite](https://cn.electron-vite.org/)
2. [清理npm包](https://juejin.cn/post/6997956167473463327)
3. [element-plus 前端组件库](https://element-plus.org/zh-CN/component/overview.html)
4. [UDF API](./UDF-api.md)
5. [Electron + Vue + Vite + Python + FastAPI](https://github.com/hafiidz/electron-vite-vue-fastapi)
6. [TradingView API Reference](https://www.tradingview.com/charting-library-docs/latest/connecting_data/Datafeed-API#getservertime)
7. [Binance WSS API](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)
8. [CCXT: 跨交易所的交易API封装库，为各种交易所提供统一的上层接口，支持python和js](https://docs.ccxt.com/#/README?id=social)
9. [wondertreader](https://wtdocs.readthedocs.io/zh/latest/)
10. [install-redis-on-linux](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/install-redis-on-linux/)

## 开发计划
1. [done]开发模式和交易模式的切换逻辑: 用一个开关手动切换
2. 主logo的UX设计
3. agent窗口和侧边栏开关按钮，模仿vscode右上角
4. 两个模式的UI梳理
5. python指标
6. 数据持久化和本地缓存
7. 工作区模式（程序第一次启动，要询问工作区，持久化数据和python脚本要放进去）
8. binance数据源

## 目前的主要疑惑：
1. K线页面和代码页面显然都有打开多个页面的需求
2. 代码调试的时候可能需要同时显示K线页面
3. 一个工程可能存在多个代码文件，多个策略，多个指标，显然需要一个类似vscode的“资源管理器”
4. Agent在开发模式下能够进行开发辅助，在交易模式下能够直接获得交易信息


## 构想
程序第一次启动，要询问工作区，工作区用于存储持久化数据和python脚本，存放用于python运行的虚拟环境
K线视图里，除了内置的indicators列表，还要有一个自定义指标的列表，其中的指标是工作区中存储的python指标
还应该有一个策略列表，其中的条目是存储工作区中存储的python策略，目前我们只考虑单一策略，未来可以考虑权重式多策略和多策略排行回测


仔细思考后，我决定进行一个较大的UI逻辑更新：
1. 将程序分成交易模式(trading_mode), 开发模式(developing_mode), 新闻模式(news_mode), 市场分析模式(market_analyze_mode)
2. 模式切换按钮放在左侧的侧边栏中，可以使用src\renderer\public中的图标
3. 模式切换按钮不再起到新建tab页面的作用，而是切换不同的模式，不同模式的解释如下：
4. 交易模式显示k线图也就是chart页面，tab栏中的新建页面按钮保留，功能还是新建chart页面
5. 开发模式，显示代码编辑页面，tab栏中无新建页面按钮
6. 新闻模式和市场分析模式目前没有内容，我们日后再进行详细开发，目前只需要显示“正在开发中”即可
7. 从A模式切换到B模式之后，保留A模式打开的所有标签页状态，以便于日后切换回A模式时恢复之前打开的标签页
8. 设置、新闻模式、市场分析模式这三个模式不适用多tab页面，当切换到这个模式时不显示tab栏
