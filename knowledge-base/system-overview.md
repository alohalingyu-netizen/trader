# A股市场数据服务

## 系统定位

本系统是一个 A 股市场数据的采集、存储和查询服务。它从 Tushare Pro 同步历史数据到本地 MySQL，并通过 REST API 对外提供查询能力。

**不做**交易决策、回测、策略执行等任何业务逻辑。它只提供数据。

## 服务地址

默认运行在 `http://localhost:8000`

## 可用数据

### 股票基础信息
- `GET /api/market/stocks?market=主板|创业板|科创板` — 全部上市股票基本信息（代码、名称、行业、主营业务等）

### 日线行情
- `GET /api/market/daily/{ts_code}?start_date=YYYYMMDD&end_date=YYYYMMDD` — 个股日线（OHLCV + 换手率、市盈率、市净率、市值等）
- `GET /api/market/daily-with-ma/{ts_code}?start_date=YYYYMMDD&end_date=YYYYMMDD` — 个股日线 + MA5/7/10/17/30/60/250 均线（推荐，一次拿全）

### 技术指标
- `POST /api/market/calculate-ma?ts_code=000001.SZ&start_date=YYYYMMDD&end_date=YYYYMMDD` — 计算并存储移动均线（需先调用，才能查到 MA 数据）
- `GET /api/market/technical-indicators/{ts_code}?start_date=YYYYMMDD&end_date=YYYYMMDD` — 单独查询 MA 指标

### 涨跌停数据
- `GET /api/market/limit-list?trade_date=YYYYMMDD&limit_type=涨停池|连扳池|冲刺涨停|炸板池|跌停池` — 涨跌停榜单
- `GET /api/market/limit-step?trade_date=YYYYMMDD` — 连板天梯
- `GET /api/market/limit-concept?trade_date=YYYYMMDD` — 涨停最强板块

### 板块数据（东财）
- `GET /api/market/dc-index?trade_date=YYYYMMDD&idx_type=行业板块|概念板块|地域板块` — 板块指数
- `GET /api/market/dc-index-range?start_date=YYYYMMDD&end_date=YYYYMMDD&idx_type=...` — 板块指数（日期范围）
- `GET /api/market/dc-daily/{ts_code}?start_date=YYYYMMDD&end_date=YYYYMMDD` — 板块指数日线
- `GET /api/market/dc-concept?trade_date=YYYYMMDD` — 概念题材每日快照

### 大盘指数
- `GET /api/market/index-daily/{ts_code}?start_date=YYYYMMDD&end_date=YYYYMMDD` — 上证(000001.SH)、深证(399001.SZ)、创业板(399006.SZ)日线

### 市场统计
- `GET /api/market/breadth-stats?trade_date=YYYYMMDD` — 全市场涨跌家数、涨停数、总成交量/额
- `GET /api/market/daily-info?trade_date=YYYYMMDD&ts_code=SH_MARKET|SZ_MARKET|...` — 沪深市场每日交易统计

### 交易日历
- `GET /api/market/trade-cal?start_date=YYYYMMDD&end_date=YYYYMMDD&is_open=0|1` — 交易日历

## 数据范围

- 时间：默认从 2024-01-01 起
- 交易日历：2024 ~ 2027
- 数据量：总计约 650~900 MB

## 典型用法示例

```bash
# 查某只股票近期日线 + 均线
GET /api/market/daily-with-ma/000001.SZ?start_date=20240101&end_date=20241231

# 查某天涨停池
GET /api/market/limit-list?trade_date=20240315&limit_type=涨停池

# 查某天概念板块涨幅排名
GET /api/market/dc-index?trade_date=20240315&idx_type=概念板块

# 查某天全市场涨跌家数
GET /api/market/breadth-stats?trade_date=20240315
```
