# Phase 1 — 数据基座夯实（详细开发计划）

> 目标：构建统一的行情数据层、新闻采集管线、标的元数据管理体系，为上层 Agent 分析和 K 线图展示提供稳定的数据源支持。

---

## 目录
1. [数据源清单](#数据源清单)
2. [Module A: 统一行情数据层](#module-a-统一行情数据层)
3. [Module C: 新闻资讯采集与数据集化](#module-c-新闻资讯采集与数据集化)
4. [Module F: 全局标的管理](#module-f-全局标的管理)
5. [开发时间线与优先级](#开发时间线与优先级)
6. [技术决策与风险](#技术决策与风险)

---

## 数据源清单

> **原则**: ① 尽可能利用所有已有数据源 ② 优先使用 TickFlow ③ 加密货币优先使用 Binance

### 所有可用数据源一览

| # | 数据源 | 类型 | 覆盖市场 | 成本 | 集成状态 |
|---|--------|------|---------|------|---------|
| 1 | **TickFlow** ✨ | 付费 API | A股/港股/美股/ETF/指数 | 已购 | 🔧 扩展中（当前仅市场宽度） |
| 2 | **akshare** | 开源库 | A股/港股/美股/ETF | 免费 | ✅ 已集成 |
| 3 | **tushare** | 社区 API | A股/指数/基金 | 免费(积分制) | ✅ 已集成 |
| 4 | **baostock** | 开源库 | A股 | 免费 | ✅ 已集成 |
| 5 | **efinance** | 开源库 | A股/ETF | 免费 | ✅ 已集成 |
| 6 | **pytdx** | 通达信协议 | A股实时/分笔 | 免费 | ✅ 已集成 |
| 7 | **longbridge** | 券商 API | 港股/美股 | 免费(有限额) | ✅ 已集成 |
| 8 | **yfinance** | Yahoo Finance | 美股/港股/期货/ETF | 免费 | ✅ 已集成 |
| 9 | **binance** | 交易所 API | 加密货币 | 免费 | ✅ 已集成 |
| 10 | **okx** | 交易所 API | 加密货币 | 免费 | ✅ 已集成 |

### TickFlow 能力矩阵（付费，已购）

**文档**: https://docs.tickflow.org/zh-Hans

| 功能 | 支持市场 | 说明 |
|------|---------|------|
| **日线 K线** (1d/1w/1M/1Q/1Y) | A股/港股/美股 | 全市场覆盖 |
| **分钟线** (1m/5m/15m/30m/60m) | **仅 A股** | 美股/港股不支持分钟线 |
| **当日分钟K线** | A股 | 批量查询当日分时数据 |
| **实时行情快照** | A股/港股/美股 | 最新价/涨跌/量 |
| **市场深度** (五档行情) | A股 | 买卖五档盘口 |
| **WebSocket 实时推送** | A股/港股/美股 | quotes + depth 频道 |
| **除权因子** | A股/港股 | 用于前/后复权计算 |
| **标的元数据** | 全市场 | 名称/交易所/类型等 |
| **标的池 (Universe)** | 全市场 | CN_Equity_A / US_Equity / HK_Equity 等 |
| **财务数据** | A股 | 利润表/资产负债表/现金流/股本/核心指标 |
| 逐笔 tick 数据 | ❌ | **不支持** |

### 数据源优先级路由表（按市场×数据类型）

#### A股

| 数据类型 | 优先级 1 | 优先级 2 | 优先级 3 | 优先级 4 | 优先级 5 |
|---------|---------|---------|---------|---------|---------|
| **日线 K线** | tickflow | akshare | tushare | baostock | efinance |
| **分钟线** (1m~60m) | tickflow | pytdx | — | — | — |
| **实时行情快照** | tickflow | pytdx | akshare | efinance | — |
| **五档盘口** | tickflow | pytdx | — | — | — |
| **WebSocket 推送** | tickflow WS | pytdx | — | — | — |
| **除权因子** | tickflow | tushare | akshare | — | — |
| **基本面/财务** | tickflow | akshare | tushare | — | — |
| **标的元数据** | tickflow | akshare | tushare | — | — |
| **市场宽度统计** | tickflow | akshare | — | — | — |

#### 港股

| 数据类型 | 优先级 1 | 优先级 2 | 优先级 3 | 优先级 4 |
|---------|---------|---------|---------|---------|
| **日线 K线** | tickflow | longbridge | yfinance | akshare |
| **分钟线** | longbridge | — | — | — |
| **实时行情快照** | tickflow | longbridge | yfinance | — |
| **WebSocket 推送** | tickflow WS | longbridge WS | — | — |
| **除权因子** | tickflow | longbridge | — | — |
| **标的元数据** | tickflow | longbridge | yfinance | — |

#### 美股

| 数据类型 | 优先级 1 | 优先级 2 | 优先级 3 | 优先级 4 |
|---------|---------|---------|---------|---------|
| **日线 K线** | tickflow | yfinance | longbridge | akshare |
| **分钟线** | yfinance | longbridge | — | — |
| **实时行情快照** | tickflow | yfinance | longbridge | — |
| **WebSocket 推送** | tickflow WS | — | — | — |
| **标的元数据** | tickflow | yfinance | longbridge | — |

#### 加密货币

| 数据类型 | 优先级 1 | 优先级 2 | 备注 |
|---------|---------|---------|------|
| **K线** (1m~1M) | **binance** | okx | Binance 优先 |
| **实时行情** | **binance** | okx | — |
| **WebSocket 推送** | **binance WS** | okx WS | 已有实现 |
| **逐笔成交** | **binance WS** | okx WS | trade stream |
| **深度行情** | **binance** | okx | orderbook |
| **标的元数据** | **binance** | okx | exchangeInfo |

#### 大宗商品期货

| 数据类型 | 优先级 1 | 优先级 2 | 备注 |
|---------|---------|---------|------|
| **日线 K线** | yfinance | — | GC=F / CL=F / SI=F 等 |
| **实时行情** | yfinance | — | 延迟 15min |
| **标的元数据** | yfinance | — | — |

### 各数据源职责总结

| 数据源 | 主要职责 | 次要职责 |
|--------|---------|---------|
| **tickflow** ✨ | A股/港股/美股 K线 + 实时 + 财务 + 元数据 | 市场宽度、除权因子 |
| **akshare** | A股 K线备用、基本面补充 | 港股/美股日线备用 |
| **tushare** | A股日线备用、除权因子备用 | 指数成分股信息 |
| **baostock** | A股日线第四备用 | 历史数据回补 |
| **efinance** | A股日线第五备用、实时备用 | ETF 数据 |
| **pytdx** | A股分钟线备用、五档盘口备用 | A股实时行情备用 |
| **longbridge** | 港股分钟线 + 实时(WS) | 美股日线/分钟线备用 |
| **yfinance** | 美股分钟线、期货K线 | 港股/美股日线备用 |
| **binance** | 加密货币全套 (K线/实时/WS/深度) | — |
| **okx** | 加密货币备用 | — |

### 故障转移策略

```
请求到达 DataFetcherManager:
  │
  ├─ 按照上表优先级依次尝试
  ├─ 单源超时: 10s → 自动切换下一源
  ├─ 单源连续失败 3 次 → 熔断 5min
  ├─ 全部源失败 → 返回缓存数据（标记 stale）
  └─ 成功后记录来源（用于数据质量追踪）
```

---

## Module A: 统一行情数据层

### A.1 统一数据模型（UnifiedBar）

创建 `backend/src/schemas/unified_bar.py`：

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional

class MarketType(str, Enum):
    A_SHARE = "A_SHARE"          # A股
    HK = "HK"                    # 港股
    US = "US"                    # 美股
    CRYPTO = "CRYPTO"            # 加密货币
    FUTURES = "FUTURES"          # 大宗商品期货

class PeriodType(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    M1_PERIOD = "1M"

@dataclass
class UnifiedBar:
    """统一行情数据格式"""
    symbol: str                   # 统一编码: "600519.SH" / "AAPL" / "BTC-USDT" / "GC=F"
    market: MarketType            # 市场类型
    timestamp: datetime           # UTC 时间戳
    period: PeriodType            # 时间周期
    
    # OHLCV 数据
    open: Decimal                 # 开盘价
    high: Decimal                 # 最高价
    low: Decimal                  # 最低价
    close: Decimal                # 收盘价
    volume: Decimal               # 成交量（股数/张数/枚数）
    
    # 可选字段
    turnover: Optional[Decimal] = None    # 成交额（仅 A股/港股）
    amount: Optional[Decimal] = None      # 成交额（同 turnover，兼容性）
    vwap: Optional[Decimal] = None        # 成交均价
    
    # 数据质量标记
    data_source: str = ""                 # 数据来源: "akshare" / "tickflow" / "tushare"
    data_quality: str = "high"            # "high" / "medium" / "low"
    is_adjusted: bool = False             # 是否已复权
    adjustment_factor: Optional[Decimal] = None  # 复权因子
    
    # 异常标记
    anomaly_flag: bool = False            # 异常值标记
    anomaly_reason: Optional[str] = None  # 异常原因描述

    def pct_change(self) -> Optional[Decimal]:
        """涨跌幅 (%)"""
        if not self.open or self.open == 0:
            return None
        return (self.close - self.open) / self.open * 100
```

**Pydantic 变体** (`backend/src/schemas/bar.py`):

```python
from pydantic import BaseModel, Field
from typing import Optional

class BarSchema(BaseModel):
    """API 返回用 Pydantic 模型"""
    symbol: str
    market: str
    timestamp: str  # ISO 8601
    period: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: Optional[float] = None
    data_source: str = ""
    data_quality: str = "high"
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "600519.SH",
                "market": "A_SHARE",
                "timestamp": "2026-05-19T00:00:00Z",
                "period": "1d",
                "open": 1234.56,
                "high": 1245.67,
                "low": 1223.45,
                "close": 1240.12,
                "volume": 1000000,
                "turnover": 1234560000,
            }
        }
```

### A.2 数据源编码映射表

创建 `backend/src/data/symbol_mapping.py`：

```python
"""
符号映射和市场识别逻辑
"""

# A股
ASHARE_SUFFIXES = {
    "SH": "SSE",          # 上交所
    "SZ": "SZSE",         # 深交所
}

# 港股
HK_SUFFIX = "HK"

# 美股
US_SYMBOLS = ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", ...]  # 常见美股代码

# 加密货币
CRYPTO_SYMBOLS = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    # ...
}

# 期货
FUTURES_SYMBOLS = {
    "GC=F": "Gold Futures",
    "CL=F": "Crude Oil",
    # ...
}

class SymbolNormalizer:
    """将各数据源的符号格式统一为标准格式"""
    
    @staticmethod
    def normalize_symbol(symbol: str, market: MarketType) -> str:
        """
        将任意格式的符号转为标准格式
        
        示例:
        - tushare "600519" -> "600519.SH"
        - akshare "sh600519" -> "600519.SH"
        - tickflow "SH600519" -> "600519.SH"
        - yfinance "AAPL" -> "AAPL"
        - binance "BTCUSDT" -> "BTC-USDT"
        """
        # 实现统一归一化逻辑
        pass
    
    @staticmethod
    def denormalize_for_source(symbol: str, source: str) -> str:
        """
        将标准符号转为特定数据源要求的格式
        
        示例:
        - symbol="600519.SH", source="tushare" -> "600519"
        - symbol="600519.SH", source="tickflow" -> "SH600519"
        - symbol="600519.SH", source="akshare" -> "sh600519"
        """
        pass
```

### A.3 扩展 TickFlowFetcher（现有的弱功能）

重点改造 `backend/data_provider/tickflow_fetcher.py`：

**当前状态**：仅支持市场宽度统计，不支持日常 K线 数据拉取。

**改造方向**：

1. **扩展方法**
   ```python
   class TickFlowFetcher(BaseFetcher):
       name = "TickFlowFetcher"
       priority = 50  # 调整优先级
       
       async def get_bars(
           self,
           symbol: str,
           period: str = "1d",
           start_date: Optional[str] = None,
           end_date: Optional[str] = None,
           limit: int = 500,
       ) -> List[UnifiedBar]:
           """获取历史 K线数据"""
           # 使用 TickFlow 的 query_kline 接口
           # 统一转换为 UnifiedBar 格式
           pass
       
       async def get_latest_bar(self, symbol: str) -> Optional[UnifiedBar]:
           """获取最新 bar（用于实时行情缓存）"""
           pass
       
       async def get_market_breadth(self, market: MarketType) -> Dict:
           """获取市场宽度统计（当前已实现）"""
           pass
       
       async def get_index_quote(self, symbols: List[str]) -> List[Dict]:
           """获取主要指数实时行情"""
           pass
   ```

2. **流控和重试策略**
   - 利用 TickFlow 50+ 并发支持
   - 批量拉取优化：单次 request 最多 50 个 symbol
   - 指数退避重试（3 次）

3. **集成到 DataFetcherManager**
   ```python
   # backend/data_provider/base.py 中的 DataFetcherManager
   
   FETCHER_PRIORITY_MAP = {
       ("A_SHARE", "1d"): ["tickflow", "akshare", "tushare"],
       ("HK", "1d"): ["tickflow", "longbridge", "yfinance"],
       ("US", "1d"): ["tickflow", "yfinance", "longbridge"],
       ("CRYPTO", "1d"): ["binance", "okx"],
   }
   ```

### A.4 行情数据缓存层

改造 `backend/src/data/cache_manager.py`（SQLite）：

```python
"""
行情数据本地缓存管理
"""

class BarCacheManager:
    """K线数据缓存"""
    
    def __init__(self, db_path: str = "backend/data/market_cache.db"):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """创建表结构"""
        # 主表：按 (symbol, period) 分表存储
        # bar_600519_sh_1d, bar_aapl_1d, bar_btc_usdt_1h 等
        
        # 元数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS bar_metadata (
                symbol TEXT NOT NULL,
                period TEXT NOT NULL,
                market TEXT NOT NULL,
                last_update DATETIME,
                min_timestamp DATETIME,
                max_timestamp DATETIME,
                record_count INTEGER,
                PRIMARY KEY (symbol, period)
            )
        """)
        
        # 单个 bar 表（样例）
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS bar_{symbol}_{period} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL UNIQUE,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                turnover REAL,
                data_source TEXT,
                data_quality TEXT,
                anomaly_flag INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def get_or_fetch(
        self,
        symbol: str,
        period: str,
        start_date: datetime,
        end_date: datetime,
        fetcher_manager: DataFetcherManager,
    ) -> List[UnifiedBar]:
        """
        先查本地缓存，缺失区间才远程拉取并回填
        """
        # 1. 查询本地已有的数据区间
        existing_ranges = self._query_existing_ranges(symbol, period)
        
        # 2. 计算缺失区间
        missing_ranges = self._calculate_missing_ranges(
            start_date, end_date, existing_ranges
        )
        
        # 3. 为缺失区间远程拉取
        if missing_ranges:
            for miss_start, miss_end in missing_ranges:
                bars = fetcher_manager.get_bars(
                    symbol, period, miss_start, miss_end
                )
                self._insert_bars(symbol, period, bars)
        
        # 4. 合并返回（本地 + 新拉取）
        return self._query_bars(symbol, period, start_date, end_date)
    
    def _insert_bars(self, symbol: str, period: str, bars: List[UnifiedBar]):
        """插入 bar 数据"""
        table_name = self._get_table_name(symbol, period)
        for bar in bars:
            self.db.execute(f"""
                INSERT OR REPLACE INTO {table_name}
                (timestamp, open, high, low, close, volume, turnover, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bar.timestamp, bar.open, bar.high, bar.low,
                bar.close, bar.volume, bar.turnover, bar.data_source
            ))
        self.db.commit()
        self._update_metadata(symbol, period)
```

### A.5 增量更新与数据质量检查

创建 `backend/src/services/data_quality_service.py`：

```python
"""
数据质量检查和异常检测
"""

class DataQualityService:
    
    @staticmethod
    def detect_anomalies(bars: List[UnifiedBar]) -> List[UnifiedBar]:
        """
        检测异常值：
        1. 涨跌幅 > 阈值 → 标记 anomaly_flag
        2. 成交量异常稀疏
        3. gap > 某个比例
        """
        for bar in bars:
            pct = bar.pct_change()
            if pct and abs(pct) > 20:  # 涨跌幅 > 20% 为异常（可配置）
                bar.anomaly_flag = True
                bar.anomaly_reason = f"pct_change {pct:.2f}% > 20%"
        return bars
    
    @staticmethod
    def fill_missing_bars(
        symbol: str,
        period: str,
        bars: List[UnifiedBar],
    ) -> List[UnifiedBar]:
        """
        补全缺失 bar（节假日、停牌等）
        """
        # 按 period 计算应有的时间间隔
        # 如果缺少某个时间点，标记为 data_quality="missing"
        pass
    
    @staticmethod
    def validate_adjustment_factor(
        symbol: str,
        market: MarketType,
        bars: List[UnifiedBar],
    ) -> List[UnifiedBar]:
        """
        复权因子验证和应用（A股/港股需要）
        """
        if market not in [MarketType.A_SHARE, MarketType.HK]:
            return bars
        
        # 查询复权因子表
        adjustment_factors = fetch_adjustment_factors(symbol)
        
        # 应用复权
        for bar in bars:
            factor = get_factor_at_date(adjustment_factors, bar.timestamp)
            if factor:
                bar.open *= factor
                bar.high *= factor
                bar.low *= factor
                bar.close *= factor
                bar.is_adjusted = True
                bar.adjustment_factor = factor
        
        return bars
```

### A.6 开发任务清单 (Module A)

| # | 任务 | 优先级 | 估时 | 依赖 |
|----|------|-------|------|------|
| A1 | 创建 UnifiedBar 和 BarSchema | P0 | 2h | — |
| A2 | 实现 SymbolNormalizer（各源符号转换） | P0 | 3h | A1 |
| A3 | 改造 TickFlowFetcher（支持 K线拉取） | P0 | 5h | A2，TickFlow 文档 |
| A4 | 实现 BarCacheManager（SQLite 缓存） | P0 | 4h | A1 |
| A5 | 集成 TickFlowFetcher 到 DataFetcherManager | P0 | 3h | A3, A4 |
| A6 | 实现 DataQualityService（异常检测 + 复权） | P0 | 4h | A1 |
| A7 | 单元测试（各数据源覆盖） | P0 | 5h | A1-A6 |
| A8 | 文档编写（API 文档 + 使用指南） | P1 | 2h | A1-A7 |

**小计**: ~28h（~3.5 个工作日）

---

## Module C: 新闻资讯采集与数据集化

### C.1 新闻数据模型

创建 `backend/src/schemas/news_item.py`：

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

class NewsSentiment(str, Enum):
    STRONGLY_POSITIVE = "strongly_positive"  # +1.0
    POSITIVE = "positive"                    # +0.5
    NEUTRAL = "neutral"                      # 0.0
    NEGATIVE = "negative"                    # -0.5
    STRONGLY_NEGATIVE = "strongly_negative"  # -1.0

class NewsImportance(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class NewsTag(str, Enum):
    EARNINGS = "earnings"        # 财报
    MACRO = "macro"              # 宏观经济
    INSIDER = "insider"          # 内幕交易
    MERGER_ACQUISITION = "M&A"   # 并购
    BANKRUPTCY = "bankruptcy"    # 破产
    DIVIDEND = "dividend"        # 分红
    POLICY = "policy"            # 政策
    ANNOUNCEMENT = "announcement" # 公告

@dataclass
class NewsItem:
    id: str                       # UUID
    source: str                   # "eastmoney" / "xueqiu" / "reuters" / "sina"
    source_url: str               # 原始 URL（去重键）
    title: str
    content: str                  # 全文或摘要
    publish_time: datetime        # 新闻发布时间
    crawl_time: datetime          # 爬虫采集时间
    
    # 关联信息
    symbols: List[str]            # 关联标的 ["600519.SH", "AAPL"]
    markets: List[str]            # 市场类型 ["A_SHARE", "US"]
    tags: List[str]               # 标签列表
    
    # LLM 处理结果
    summary: Optional[str] = None # 单句摘要
    sentiment_score: Optional[float] = None  # -1.0 ~ 1.0
    sentiment_label: Optional[NewsSentiment] = None
    importance: Optional[NewsImportance] = None
    
    # 元数据
    language: str = "zh"          # "zh" / "en"
    author: Optional[str] = None
    view_count: Optional[int] = None
    comment_count: Optional[int] = None
    
    # 数据库字段
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_processed: bool = False    # 是否已 LLM 处理
```

### C.2 新闻采集源定义

创建 `backend/src/services/news/sources/` 目录：

```
backend/src/services/news/
├── sources/
│   ├── base_crawler.py          # 基类
│   ├── eastmoney_crawler.py     # 东方财富
│   ├── xueqiu_crawler.py        # 雪球
│   ├── reuters_crawler.py       # Reuters
│   └── sina_crawler.py          # 新浪财经
├── news_scheduler.py            # 调度器
├── news_processor.py            # LLM 处理管线
└── news_repository.py           # 数据访问层
```

**基类** (`base_crawler.py`):

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class BaseCrawler(ABC):
    """新闻爬虫基类"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.last_crawl_cursor = None  # 增量采集游标
    
    @abstractmethod
    async def fetch_news(
        self,
        limit: int = 50,
        keywords: Optional[List[str]] = None,
    ) -> List[NewsItem]:
        """
        抓取新闻
        
        Args:
            limit: 返回条数
            keywords: 关键词过滤（可选）
        
        Returns:
            新闻列表
        """
        pass
    
    @abstractmethod
    def extract_symbols(self, text: str) -> List[str]:
        """从文本提取股票代码"""
        pass
    
    def deduplicate_key(self, news: NewsItem) -> str:
        """
        生成去重键
        
        默认: (source, source_url) 作为唯一键
        """
        return f"{self.source_name}#{news.source_url}"
```

**具体实现示例** (`eastmoney_crawler.py`):

```python
class EasmoneyNewsCrawler(BaseCrawler):
    """东方财富新闻爬虫"""
    
    def __init__(self):
        super().__init__("eastmoney")
        self.api_endpoint = "https://newsapi.eastmoney.com/kuaixun"
    
    async def fetch_news(
        self,
        limit: int = 50,
        keywords: Optional[List[str]] = None,
    ) -> List[NewsItem]:
        """从东方财富爬取财经快讯"""
        
        # 使用 httpx 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_endpoint,
                params={
                    "pageIndex": 1,
                    "pageSize": limit,
                    "showType": 1,  # 1=快讯, 2=公告
                },
                timeout=10,
            )
            data = response.json()
        
        news_list = []
        for item in data.get("result", []):
            news = NewsItem(
                id=uuid.uuid4().hex,
                source="eastmoney",
                source_url=item.get("link", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                publish_time=datetime.fromisoformat(item.get("ctime")),
                crawl_time=datetime.utcnow(),
                symbols=self.extract_symbols(item.get("content", "")),
                markets=[],
                tags=[],
            )
            news_list.append(news)
        
        return news_list
    
    def extract_symbols(self, text: str) -> List[str]:
        """从文本提取股票代码（正则表达式）"""
        import re
        
        # A股：600xxx / 000xxx / 300xxx
        ashare_pattern = r'([036]\d{5}(?:\.\w{2})?)'
        # 美股：大写字母 2-5 个
        us_pattern = r'\b([A-Z]{2,5})\b'
        
        symbols = []
        for match in re.finditer(ashare_pattern, text):
            symbols.append(match.group(1))
        for match in re.finditer(us_pattern, text):
            symbols.append(match.group(1))
        
        return list(set(symbols))
```

### C.3 新闻采集调度器

创建 `backend/src/services/news/news_scheduler.py`：

```python
import asyncio
from typing import List, Dict
from datetime import datetime
from src.services.news.sources import (
    EasmoneyNewsCrawler,
    XueqiuCrawler,
    ReutersCrawler,
)

class NewsScheduler:
    """后台定时新闻采集"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.crawlers = [
            EasmoneyNewsCrawler(),
            XueqiuCrawler(),
            ReutersCrawler(),
        ]
        self.crawl_interval_minutes = 15  # 配置项
    
    async def start(self):
        """启动调度循环"""
        while True:
            try:
                await self.crawl_all()
                await asyncio.sleep(self.crawl_interval_minutes * 60)
            except Exception as e:
                logger.error(f"新闻采集失败: {e}")
                await asyncio.sleep(60)  # 异常时等待 1 分钟后重试
    
    async def crawl_all(self):
        """并行采集所有源"""
        tasks = [
            self._crawl_single_source(crawler)
            for crawler in self.crawlers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"本轮采集完成: {success_count}/{len(self.crawlers)} 源成功")
    
    async def _crawl_single_source(self, crawler: BaseCrawler) -> bool:
        """采集单个源，处理异常和去重"""
        try:
            news_items = await crawler.fetch_news(limit=50)
            
            # 去重：检查 (source, source_url) 是否已存在
            for news in news_items:
                dedupe_key = crawler.deduplicate_key(news)
                if not self._exists(dedupe_key):
                    news.created_at = datetime.utcnow()
                    self._insert_news(news)
            
            logger.info(f"{crawler.source_name} 采集成功，新增 {len(news_items)} 条")
            return True
        except Exception as e:
            logger.error(f"{crawler.source_name} 采集失败: {e}")
            return False
    
    def _exists(self, dedupe_key: str) -> bool:
        """查询去重键是否存在"""
        result = self.db.query(
            "SELECT 1 FROM news WHERE dedupe_key = ?",
            (dedupe_key,)
        )
        return result is not None
    
    def _insert_news(self, news: NewsItem):
        """插入新闻到数据库"""
        self.db.execute(
            """
            INSERT INTO news 
            (id, source, source_url, title, content, publish_time, 
             crawl_time, symbols, created_at, is_processed, dedupe_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                news.id, news.source, news.source_url, news.title,
                news.content, news.publish_time, news.crawl_time,
                json.dumps(news.symbols), news.created_at, False,
                f"{news.source}#{news.source_url}"
            ),
        )
```

### C.4 LLM 增强处理管线

创建 `backend/src/services/news/news_processor.py`：

```python
"""
使用 LLM 增强新闻处理：摘要、情感、重要性分级
"""

class NewsProcessor:
    
    def __init__(self, llm_client):
        self.llm = llm_client  # LiteLLM 客户端
        self.quick_think_model = "deepseek-v3"  # 快速模型
    
    async def process_news_batch(
        self,
        news_items: List[NewsItem],
        batch_size: int = 10,
    ) -> List[NewsItem]:
        """批量处理新闻"""
        
        for i in range(0, len(news_items), batch_size):
            batch = news_items[i : i + batch_size]
            
            # 并行处理
            tasks = [self.process_single_news(news) for news in batch]
            processed = await asyncio.gather(*tasks)
            
            # 保存处理结果
            for news in processed:
                self.save_processed_news(news)
    
    async def process_single_news(self, news: NewsItem) -> NewsItem:
        """处理单条新闻"""
        
        # 1. 摘要生成
        summary_prompt = f"""
        将以下新闻摘要为一句话（10-20 字）：
        
        标题：{news.title}
        内容：{news.content[:500]}
        """
        news.summary = await self.llm.generate(
            summary_prompt,
            model=self.quick_think_model,
            max_tokens=50,
        )
        
        # 2. 情感分析
        sentiment_prompt = f"""
        分析以下新闻的情感倾向（-1 = 强烈负面，0 = 中立，1 = 强烈正面），
        仅返回数字：
        
        {news.title}
        {news.content[:300]}
        """
        sentiment_str = await self.llm.generate(
            sentiment_prompt,
            model=self.quick_think_model,
            max_tokens=5,
        )
        try:
            sentiment_score = float(sentiment_str.strip())
            news.sentiment_score = max(-1, min(1, sentiment_score))
            news.sentiment_label = self._score_to_label(sentiment_score)
        except:
            news.sentiment_score = 0.0
            news.sentiment_label = NewsSentiment.NEUTRAL
        
        # 3. 重要性分级
        importance_prompt = f"""
        判断以下新闻的重要性（high/medium/low），仅返回一个单词：
        
        {news.title}
        {news.content[:300]}
        """
        importance_str = await self.llm.generate(
            importance_prompt,
            model=self.quick_think_model,
            max_tokens=10,
        )
        news.importance = NewsImportance(importance_str.strip().lower())
        
        # 4. 更新处理标记
        news.is_processed = True
        news.updated_at = datetime.utcnow()
        
        return news
    
    def _score_to_label(self, score: float) -> NewsSentiment:
        """数值转标签"""
        if score >= 0.75:
            return NewsSentiment.STRONGLY_POSITIVE
        elif score >= 0.25:
            return NewsSentiment.POSITIVE
        elif score > -0.25:
            return NewsSentiment.NEUTRAL
        elif score > -0.75:
            return NewsSentiment.NEGATIVE
        else:
            return NewsSentiment.STRONGLY_NEGATIVE
    
    def save_processed_news(self, news: NewsItem):
        """保存处理结果"""
        self.db.execute(
            """
            UPDATE news SET 
            summary = ?, sentiment_score = ?, sentiment_label = ?,
            importance = ?, is_processed = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                news.summary, news.sentiment_score,
                news.sentiment_label.value, news.importance.value,
                True, datetime.utcnow(), news.id
            ),
        )
```

### C.5 新闻数据库表设计

```sql
-- 新闻主表
CREATE TABLE news (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    
    publish_time DATETIME NOT NULL,
    crawl_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    
    -- LLM 处理结果
    sentiment_score REAL,
    sentiment_label TEXT,
    importance TEXT,
    is_processed INTEGER DEFAULT 0,
    
    -- 去重键
    dedupe_key TEXT UNIQUE,
    
    -- 索引
    FOREIGN KEY (source) REFERENCES news_sources(name)
);

CREATE INDEX idx_news_source ON news(source);
CREATE INDEX idx_news_publish_time ON news(publish_time DESC);
CREATE INDEX idx_news_importance ON news(importance);
CREATE INDEX idx_news_is_processed ON news(is_processed);

-- 新闻-标的关联表
CREATE TABLE news_symbol_mapping (
    news_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT,
    PRIMARY KEY (news_id, symbol),
    FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE
);

CREATE INDEX idx_symbol_news ON news_symbol_mapping(symbol);

-- 新闻源配置表
CREATE TABLE news_sources (
    name TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    last_crawl_time DATETIME,
    crawl_interval_minutes INTEGER DEFAULT 15,
    last_cursor TEXT,  -- 增量采集游标
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### C.6 新闻数据导出能力

创建 `backend/src/services/news/news_exporter.py`：

```python
import csv
import json
from pathlib import Path
from typing import List

class NewsExporter:
    """新闻数据导出"""
    
    @staticmethod
    def export_to_csv(
        news_items: List[NewsItem],
        output_path: str,
    ):
        """导出为 CSV（用于 backtest 框架）"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'id', 'publish_time', 'symbol', 'title',
                'summary', 'sentiment_score', 'importance'
            ])
            writer.writeheader()
            for news in news_items:
                for symbol in news.symbols:
                    writer.writerow({
                        'id': news.id,
                        'publish_time': news.publish_time.isoformat(),
                        'symbol': symbol,
                        'title': news.title,
                        'summary': news.summary,
                        'sentiment_score': news.sentiment_score,
                        'importance': news.importance,
                    })
    
    @staticmethod
    def export_to_parquet(
        news_items: List[NewsItem],
        output_path: str,
    ):
        """导出为 Parquet（压缩、列式存储）"""
        import pyarrow as pa
        import pyarrow.parquet as pq
        
        rows = []
        for news in news_items:
            for symbol in news.symbols:
                rows.append({
                    'id': news.id,
                    'publish_time': news.publish_time,
                    'symbol': symbol,
                    'title': news.title,
                    'sentiment_score': news.sentiment_score,
                })
        
        table = pa.Table.from_pylist(rows)
        pq.write_table(table, output_path, compression='snappy')
```

### C.7 开发任务清单 (Module C)

| # | 任务 | 优先级 | 估时 | 依赖 |
|----|------|-------|------|------|
| C1 | 创建 NewsItem 和新闻数据模型 | P0 | 2h | — |
| C2 | 实现 BaseCrawler 基类 | P0 | 2h | — |
| C3 | 实现 EasmoneyNewsCrawler（第一源） | P0 | 4h | C2 |
| C4 | 实现 NewsScheduler（采集调度） | P0 | 3h | C2, C3 |
| C5 | 实现 NewsProcessor（LLM 处理） | P0 | 4h | C1，LiteLLM |
| C6 | 新闻数据库表设计 + 迁移脚本 | P0 | 2h | C1 |
| C7 | 实现第二个爬虫源（XueqiuCrawler 或 SinaCrawler） | P1 | 4h | C2, C3 |
| C8 | 实现新闻导出能力（CSV / Parquet） | P1 | 2h | C1 |
| C9 | 单元测试 + 集成测试 | P0 | 4h | C1-C8 |
| C10 | 文档编写 | P1 | 1h | C1-C9 |

**小计**: ~28h（~3.5 个工作日）

---

## Module F: 全局标的管理

### F.1 标的元数据模型

创建 `backend/src/schemas/symbol_info.py`：

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SymbolInfo(BaseModel):
    """标的元数据"""
    symbol: str                   # 统一符号 "600519.SH"
    name: str                    # "贵州茅台"
    market: str                  # "A_SHARE" / "US" / "HK" / "CRYPTO"
    exchange: str                # "SSE" / "NASDAQ" / "HKEX" / "Binance"
    
    # 基本信息
    sector: Optional[str] = None  # 行业
    industry: Optional[str] = None  # 细分行业
    list_date: Optional[str] = None  # 上市日期 YYYY-MM-DD
    
    # 交易信息
    currency: str = "CNY"        # 交易货币
    lot_size: int = 1            # 最小交易单位
    trading_hours: str = ""      # 交易时段描述
    time_zone: str = "UTC+8"     # 时区
    
    # 特殊标记
    is_tradeable: bool = True    # 是否可交易
    is_suspended: bool = False   # 是否停牌
    is_st: bool = False          # 是否 ST 股
    
    # 关联关系
    related_indices: List[str] = []  # 所属指数 ["000300.SH", "000688.SH"]
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "market": "A_SHARE",
                "exchange": "SSE",
                "sector": "食品饮料",
                "currency": "CNY",
                "lot_size": 1,
                "trading_hours": "09:30-11:30 / 13:00-15:00",
                "is_tradeable": True,
                "list_date": "2001-08-27",
            }
        }
```

### F.2 标的元数据数据库

```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    market TEXT NOT NULL,
    exchange TEXT NOT NULL,
    
    sector TEXT,
    industry TEXT,
    list_date DATE,
    
    currency TEXT DEFAULT 'CNY',
    lot_size INTEGER DEFAULT 1,
    trading_hours TEXT,
    time_zone TEXT DEFAULT 'UTC+8',
    
    is_tradeable INTEGER DEFAULT 1,
    is_suspended INTEGER DEFAULT 0,
    is_st INTEGER DEFAULT 0,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    
    INDEX idx_market (market),
    INDEX idx_exchange (exchange),
    INDEX idx_sector (sector),
    INDEX idx_name (name)
);

-- 标的与指数关联表
CREATE TABLE symbol_index_mapping (
    symbol TEXT NOT NULL,
    index_symbol TEXT NOT NULL,
    PRIMARY KEY (symbol, index_symbol),
    FOREIGN KEY (symbol) REFERENCES symbols(symbol),
    FOREIGN KEY (index_symbol) REFERENCES symbols(symbol)
);

-- 用户自定义 Watchlist
CREATE TABLE user_watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name)
);

CREATE TABLE watchlist_symbols (
    watchlist_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (watchlist_id, symbol),
    FOREIGN KEY (watchlist_id) REFERENCES user_watchlists(id) ON DELETE CASCADE,
    FOREIGN KEY (symbol) REFERENCES symbols(symbol)
);
```

### F.3 标的元数据服务

创建 `backend/src/services/symbol_service.py`：

```python
from typing import List, Optional
from src.schemas.symbol_info import SymbolInfo

class SymbolService:
    """标的管理服务"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """获取标的元数据"""
        row = self.db.query(
            "SELECT * FROM symbols WHERE symbol = ?",
            (symbol,)
        )
        if row:
            return self._row_to_symbol_info(row)
        return None
    
    def search_symbols(
        self,
        keyword: str,
        market: Optional[str] = None,
        limit: int = 20,
    ) -> List[SymbolInfo]:
        """搜索标的"""
        query = "SELECT * FROM symbols WHERE (symbol LIKE ? OR name LIKE ?)"
        params = [f"%{keyword}%", f"%{keyword}%"]
        
        if market:
            query += " AND market = ?"
            params.append(market)
        
        query += " LIMIT ?"
        params.append(limit)
        
        rows = self.db.query_all(query, tuple(params))
        return [self._row_to_symbol_info(row) for row in rows]
    
    def get_watchlist(
        self,
        user_id: str,
        watchlist_name: str = "default",
    ) -> List[SymbolInfo]:
        """获取用户 watchlist"""
        query = """
            SELECT s.* FROM symbols s
            JOIN watchlist_symbols ws ON s.symbol = ws.symbol
            JOIN user_watchlists uw ON ws.watchlist_id = uw.id
            WHERE uw.user_id = ? AND uw.name = ?
            ORDER BY ws.added_at DESC
        """
        rows = self.db.query_all(query, (user_id, watchlist_name))
        return [self._row_to_symbol_info(row) for row in rows]
    
    def add_to_watchlist(
        self,
        user_id: str,
        symbol: str,
        watchlist_name: str = "default",
    ) -> bool:
        """添加到 watchlist"""
        # 确保 watchlist 存在
        self._ensure_watchlist_exists(user_id, watchlist_name)
        
        # 获取 watchlist_id
        wl_id = self.db.query(
            "SELECT id FROM user_watchlists WHERE user_id = ? AND name = ?",
            (user_id, watchlist_name)
        )[0]
        
        # 插入符号
        try:
            self.db.execute(
                "INSERT INTO watchlist_symbols (watchlist_id, symbol) VALUES (?, ?)",
                (wl_id, symbol)
            )
            return True
        except:
            return False
    
    def _ensure_watchlist_exists(self, user_id: str, name: str):
        """确保 watchlist 存在"""
        existing = self.db.query(
            "SELECT id FROM user_watchlists WHERE user_id = ? AND name = ?",
            (user_id, name)
        )
        if not existing:
            self.db.execute(
                "INSERT INTO user_watchlists (user_id, name) VALUES (?, ?)",
                (user_id, name)
            )
    
    def _row_to_symbol_info(self, row: tuple) -> SymbolInfo:
        """数据库行转 SymbolInfo"""
        # 实现转换逻辑
        pass
```

### F.4 初始元数据导入

创建 `backend/scripts/import_symbol_metadata.py`：

```python
"""
初始化导入标的元数据
"""

import asyncio
from src.services.symbol_service import SymbolService

async def import_ashare_symbols():
    """导入 A股标的元数据"""
    # 从 akshare 或 tushare 获取
    symbols = await fetch_ashare_list()
    
    for symbol_data in symbols:
        db.execute(
            """
            INSERT OR REPLACE INTO symbols 
            (symbol, name, market, exchange, sector, currency)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                symbol_data['symbol'],
                symbol_data['name'],
                'A_SHARE',
                'SSE' if symbol_data['symbol'].endswith('SH') else 'SZSE',
                symbol_data.get('sector'),
                'CNY',
            )
        )

async def import_us_symbols():
    """导入美股标的元数据"""
    # 可选：从 Yahoo Finance 或其他源获取
    pass

async def import_hk_symbols():
    """导入港股标的元数据"""
    # 从 longbridge 或其他源获取
    pass
```

### F.5 开发任务清单 (Module F)

| # | 任务 | 优先级 | 估时 | 依赖 |
|----|------|-------|------|------|
| F1 | 创建 SymbolInfo 数据模型 | P0 | 1h | — |
| F2 | 标的元数据数据库表设计 + 迁移 | P0 | 2h | F1 |
| F3 | 实现 SymbolService | P0 | 3h | F1, F2 |
| F4 | 初始元数据导入脚本（A股） | P0 | 3h | F3 |
| F5 | 初始元数据导入脚本（美股） | P1 | 2h | F4 |
| F6 | 初始元数据导入脚本（港股） | P1 | 2h | F4 |
| F7 | API 端点：搜索 + watchlist 管理 | P0 | 3h | F3 |
| F8 | 前端集成（标的搜索、watchlist UI） | P1 | 5h | F7 |
| F9 | 单元测试 | P0 | 2h | F1-F8 |
| F10 | 文档编写 | P1 | 1h | F1-F9 |

**小计**: ~24h（~3 个工作日）

---

## 开发时间线与优先级

### Phase 1 总体规划

```
总估时：28h (A) + 28h (C) + 24h (F) = 80h ≈ 10 个工作日

并行建议：
- Week 1:
  ├─ A1-A4 (TickFlowFetcher 改造 + 缓存系统)
  ├─ C1-C4 (新闻采集基础框架)
  └─ F1-F3 (标的元数据核心)

- Week 2:
  ├─ A5-A7 (测试 + 数据源集成)
  ├─ C5-C6 (LLM 处理 + 第一个爬虫完整)
  └─ F4-F7 (初始数据导入 + API)

- Week 3:
  ├─ A8 (文档)
  ├─ C7-C10 (第二爬虫源 + 导出 + 测试)
  └─ F8-F10 (前端 + 测试 + 文档)
```

### 优先级说明

**P0 (Phase 1 必须)**:
- TickFlowFetcher K线拉取能力
- 统一 Bar 缓存
- 新闻采集基础 + LLM 处理
- 标的元数据 + API

**P1 (Phase 1 可选 / Phase 2 早期)**:
- 第二新闻源、社交媒体采集
- 美股/港股元数据完整导入
- 前端标的搜索 UI

---

## 技术决策与风险

### 数据源优先级决策

| 决策 | 理由 |
|------|------|
| TickFlow 作为 A股 一级 | 付费已购、稳定性高、并发支持多 |
| tushare/akshare 作为备用 | 免费、社区活跃、多功能覆盖 |
| longbridge 作为港股主源 | 用户已有账户，实时性好 |
| yfinance 保留（不主推） | 稳定但限流严格，作为最后手段 |

### 新闻采集架构

| 设计 | 优势 | 风险 |
|------|------|------|
| BaseCrawler 策略模式 | 易扩展新源、代码复用 | 各源差异处理复杂 |
| 异步 + 批处理 | 高效、并行 | 错误传播需仔细 |
| LLM 处理管线 | 统一质量、易调试 | 成本增加（可关闭） |
| 去重 (source, url) | 简单可靠 | 同源多版本无法区分 |

### 数据库选型

| 决策 | 理由 |
|------|------|
| SQLite 主库 | 已有 market_cache.db，现成 |
| 分表存储 K线 | 单表行数控制、查询快 |
| DuckDB 作为可选分析引擎 | 列式存储、OLAP 友好、可选 |

### 复权处理

| 市场 | 策略 |
|------|------|
| A股 | 存储复权因子，按需应用（默认不复权展示） |
| 港股 | 类似 A股 |
| 美股 | yfinance 已自动处理，无需额外处理 |

---

## 完成标志与验收标准

### Module A 验收

- [ ] TickFlowFetcher 支持日线 K线拉取（至少 5 个品种）
- [ ] 统一 Bar 格式通过 pydantic 验证
- [ ] 缓存命中率 > 80%（相同 symbol/period 第二次查询）
- [ ] 异常检测准确率 > 90%（人工抽检）
- [ ] 数据源故障转移正常工作

### Module C 验收

- [ ] 至少 2 个新闻源成功采集（东方财富 + 雪球或新浪）
- [ ] 每日采集 100+ 条新闻
- [ ] 去重率 > 99%（本周期采集数据 vs 历史数据）
- [ ] LLM 处理成功率 > 95%
- [ ] 前端展示最新 20 条新闻（分页）

### Module F 验收

- [ ] 标的搜索支持 500+ 标的（至少 A股常见 100+）
- [ ] Watchlist 支持自定义分组（至少 5 个）
- [ ] API 响应时间 < 200ms
- [ ] 元数据更新周期 ≤ 1 周

---

## 配置项

创建 `backend/.env.phase1`：

```bash
# === TickFlow ===
TICKFLOW_API_KEY=your_key_here
TICKFLOW_TIMEOUT=30
TICKFLOW_BATCH_SIZE=50

# === 新闻采集 ===
NEWS_CRAWL_INTERVAL_MINUTES=15
NEWS_SOURCES_ENABLED=eastmoney,xueqiu,sina
NEWS_RETENTION_DAYS=365
NEWS_BATCH_PROCESS_SIZE=10

# === 数据库 ===
DATABASE_PATH=backend/data/market_cache.db
DATABASE_NEWS_PATH=backend/data/news.db

# === LLM ===
NEWS_PROCESSING_MODEL=deepseek-v3
NEWS_SENTIMENT_ENABLE=true

# === 标的元数据 ===
SYMBOL_METADATA_UPDATE_INTERVAL_DAYS=7
```

---

## 后续补充

待按实际开发进展补充：
- 具体 SQL 迁移脚本
- API 端点详细文档（OpenAPI)
- 单元测试框架和样例
- CI/CD 集成
