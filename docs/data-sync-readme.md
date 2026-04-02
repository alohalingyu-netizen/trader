# Tushare 数据同步工具

将 Tushare 历史数据同步到本地 MySQL，支持 11 张表、断点续跑、幂等写入。

## 前置条件

- Python >= 3.11
- MySQL 5.7+ / 8.0+
- Tushare Pro 账户（积分 >= 6000，部分接口如 `dc_index` 需要 6000 积分）

## 安装

```bash
pip install -e .
```

## 配置

### 1. 创建 MySQL 数据库

```sql
CREATE DATABASE evolving_trader DEFAULT CHARSET utf8mb4;
```

### 2. 编辑 `config/settings.yaml`

```yaml
tushare:
  token: "你的tushare_token"
  rate_limit_per_min: 200

mysql:
  host: localhost
  port: 3306
  user: root
  password: ""
  database: evolving_trader
```

也可以通过环境变量覆盖：

```bash
export TUSHARE_TOKEN=你的token
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=yourpassword
export MYSQL_DATABASE=evolving_trader
```

## 使用

```bash
# 全量同步（默认 20240101 ~ 今日，11 张表）
python main.py sync

# 指定日期范围
python main.py sync --start-date 20240101 --end-date 20240331

# 只同步指定表
python main.py sync --table stock_daily
python main.py sync --table stock_daily --table dc_index

# 强制重跑（忽略已完成的批次记录）
python main.py sync --start-date 20240101 --end-date 20240131 --force
```

## 数据表说明

| 表名 | 数据来源 | 批次方式 | 说明 |
|------|---------|---------|------|
| `stock_basic` | stock_basic + stock_company | 按 market 分批 | 上市股票基本信息 |
| `trade_cal` | trade_cal | 一次性全量 | 交易日历（2024~2027） |
| `stock_daily` | daily + daily_basic | 按月 | A股日线行情（合并基础指标） |
| `limit_list_ths` | limit_list_ths | 按月 x 2类型(U/D) | 涨跌停榜单（同花顺版） |
| `limit_step` | limit_step | 按月 | 连板天梯 |
| `limit_cpt_list` | limit_cpt_list | 按月 | 涨停最强板块统计 |
| `dc_index` | dc_index | 按月 x 3种idx_type | 东财板块指数（行业/概念/地域） |
| `dc_daily` | dc_daily | 按月 | 东财板块指数日线行情 |
| `dc_concept` | dc_concept | 按月 | 东财概念题材每日快照 |
| `index_daily` | index_daily | 按指数代码分3次 | 大盘指数日线（上证/深证/创业板） |
| `daily_info` | daily_info | 按年 x 5市场 | 沪深市场每日交易统计 |

## 同步机制

- **幂等**：使用 `INSERT IGNORE`，重复运行不产生重复数据
- **断点续跑**：`sync_log` 表记录每个批次状态（pending/done/error），已完成的批次自动跳过
- **限速**：滑动窗口限速器，默认 200 次/分钟，遵守 Tushare 接口限制
- **`--force`**：跳过 sync_log 检查，强制重跑指定范围内所有批次

## 数据规模参考

| 表 | 预估行数 |
|----|---------|
| stock_daily | ~195 万 |
| dc_daily | ~30 万 |
| dc_concept | ~20 万 |
| 其余表合计 | < 20 万 |
| **总存储** | **650~900 MB** |

全量同步预计耗时 30~60 分钟（取决于网络和 Tushare 限速）。

## 注意事项

- Tushare 数据仅限个人学习和研究使用，商业用途请自行联系数据提供方
- `stock_basic` 和 `trade_cal` 不受 `--start-date` / `--end-date` 影响，始终全量拉取
- 同步失败的批次会记录在 `sync_log` 中（status=error），重跑时会自动重试
