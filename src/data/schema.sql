-- ============================================================
-- evolving_trader MySQL Schema
-- 所有表使用 IF NOT EXISTS，可重复执行（幂等）
-- 日期字段统一用 CHAR(8) 存 YYYYMMDD 格式
-- ============================================================

-- ------------------------------------------------------------
-- 0. sync_log  同步进度追踪
--    记录每个表每个批次的同步状态，支持断点续跑
--    batch_key 格式示例:
--      stock_daily   -> '202401'（年月）
--      limit_list_ths -> 'U_202401' / 'D_202401'
--      dc_index      -> 'I_202401' / 'C_202401' / 'G_202401'（idx_type）
--      stock_basic / trade_cal / index_daily -> 'full'（一次性）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_log (
    id           BIGINT        NOT NULL AUTO_INCREMENT,
    table_name   VARCHAR(50)   NOT NULL COMMENT '同步目标表名',
    batch_key    VARCHAR(50)   NOT NULL COMMENT '批次标识',
    status       VARCHAR(10)   NOT NULL DEFAULT 'pending' COMMENT 'pending/done/error',
    rows_written INT           COMMENT '本批次写入行数',
    started_at   DATETIME      COMMENT '批次开始时间',
    finished_at  DATETIME      COMMENT '批次完成时间',
    error_msg    TEXT          COMMENT '失败时的错误信息',
    PRIMARY KEY (id),
    UNIQUE KEY uk_table_batch (table_name, batch_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同步进度追踪（支持断点续跑）';

-- ------------------------------------------------------------
-- 1. stock_basic  股票基本信息 + 公司信息
--    数据来源: stock_basic + stock_company
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_basic (
    ts_code         VARCHAR(20)   NOT NULL COMMENT 'TS代码',
    symbol          VARCHAR(10)   COMMENT '股票代码',
    name            VARCHAR(50)   COMMENT '股票名称',
    area            VARCHAR(50)   COMMENT '地域',
    industry        VARCHAR(50)   COMMENT '所属行业',
    fullname        VARCHAR(100)  COMMENT '股票全称',
    enname          VARCHAR(200)  COMMENT '英文全称',
    cnspell         VARCHAR(20)   COMMENT '拼音缩写',
    market          VARCHAR(20)   COMMENT '市场类型',
    exchange        VARCHAR(10)   COMMENT '交易所代码',
    curr_type       VARCHAR(10)   COMMENT '交易货币',
    list_status     VARCHAR(5)    COMMENT '上市状态 L上市 D退市 P暂停上市',
    list_date       CHAR(8)       COMMENT '上市日期',
    delist_date     CHAR(8)       COMMENT '退市日期',
    is_hs           VARCHAR(5)    COMMENT '是否沪深港通标的 N否 H沪股通 S深股通',
    act_name        VARCHAR(100)  COMMENT '实际控制人名称',
    act_ent_type    VARCHAR(50)   COMMENT '实际控制人企业性质',
    main_business   TEXT          COMMENT '主营业务（来自stock_company）',
    business_scope  TEXT          COMMENT '经营范围（来自stock_company）',
    PRIMARY KEY (ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息';

-- ------------------------------------------------------------
-- 2. trade_cal  交易日历
--    数据来源: trade_cal (2024-01-01 ~ 2027-01-01)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trade_cal (
    exchange        VARCHAR(10)   NOT NULL COMMENT '交易所 SSE上交所 SZSE深交所',
    cal_date        CHAR(8)       NOT NULL COMMENT '日历日期',
    is_open         TINYINT(1)    COMMENT '是否交易日 0休市 1交易',
    pretrade_date   CHAR(8)       COMMENT '上一交易日',
    PRIMARY KEY (cal_date, exchange)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易日历';

-- ------------------------------------------------------------
-- 3. stock_daily  A股日线行情（daily + daily_basic 合并）
--    数据来源: daily + daily_basic，按月分批，20240101起
--    daily_basic 剔除 ts_code/trade_date/close 后拼接
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_daily (
    ts_code         VARCHAR(20)   NOT NULL COMMENT 'TS代码',
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    -- daily 字段
    open            DOUBLE        COMMENT '开盘价',
    high            DOUBLE        COMMENT '最高价',
    low             DOUBLE        COMMENT '最低价',
    close           DOUBLE        COMMENT '收盘价',
    pre_close       DOUBLE        COMMENT '昨收价',
    `change`        DOUBLE        COMMENT '涨跌额',
    pct_chg         DOUBLE        COMMENT '涨跌幅（%）',
    vol             DOUBLE        COMMENT '成交量（手）',
    amount          DOUBLE        COMMENT '成交额（千元）',
    -- daily_basic 字段（排除 ts_code/trade_date/close）
    turnover_rate   DOUBLE        COMMENT '换手率（%）',
    turnover_rate_f DOUBLE        COMMENT '换手率（自由流通股）',
    volume_ratio    DOUBLE        COMMENT '量比',
    pe              DOUBLE        COMMENT '市盈率（总市值/净利润）',
    pe_ttm          DOUBLE        COMMENT '市盈率（TTM）',
    pb              DOUBLE        COMMENT '市净率',
    ps              DOUBLE        COMMENT '市销率',
    ps_ttm          DOUBLE        COMMENT '市销率（TTM）',
    dv_ratio        DOUBLE        COMMENT '股息率（%）',
    dv_ttm          DOUBLE        COMMENT '股息率（TTM）（%）',
    total_share     DOUBLE        COMMENT '总股本（万股）',
    float_share     DOUBLE        COMMENT '流通股本（万股）',
    free_share      DOUBLE        COMMENT '自由流通股本（万）',
    total_mv        DOUBLE        COMMENT '总市值（万元）',
    circ_mv         DOUBLE        COMMENT '流通市值（万元）',
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A股日线行情（daily+daily_basic合并）';

-- ------------------------------------------------------------
-- 4. limit_list_ths  涨跌停列表（同花顺版）
--    数据来源: limit_list_ths，按月×2类型，20240101起
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS limit_list_ths (
    trade_date          CHAR(8)       NOT NULL COMMENT '交易日期',
    ts_code             VARCHAR(20)   NOT NULL COMMENT 'TS代码',
    limit_type          VARCHAR(20)   NOT NULL COMMENT '板单类别（涨停池/连扳池/冲刺涨停/炸板池/跌停池）',
    name                VARCHAR(50)   COMMENT '股票名称',
    price               DOUBLE        COMMENT '收盘价（元）',
    pct_chg             DOUBLE        COMMENT '涨跌幅%',
    open_num            INT           COMMENT '打开次数',
    lu_desc             VARCHAR(200)  COMMENT '涨停原因',
    tag                 VARCHAR(100)  COMMENT '涨停标签',
    status              VARCHAR(20)   COMMENT '涨停状态（N连板/一字板）',
    first_lu_time       VARCHAR(20)   COMMENT '首次涨停时间',
    last_lu_time        VARCHAR(20)   COMMENT '最后涨停时间',
    first_ld_time       VARCHAR(20)   COMMENT '首次跌停时间',
    last_ld_time        VARCHAR(20)   COMMENT '最后跌停时间',
    limit_order         DOUBLE        COMMENT '封单量（元）',
    limit_amount        DOUBLE        COMMENT '封单额（元）',
    turnover_rate       DOUBLE        COMMENT '换手率%',
    free_float          DOUBLE        COMMENT '实际流通（元）',
    lu_limit_order      DOUBLE        COMMENT '最大封单（元）',
    limit_up_suc_rate   DOUBLE        COMMENT '近一年涨停封板率',
    turnover            DOUBLE        COMMENT '成交额',
    rise_rate           DOUBLE        COMMENT '涨速',
    sum_float           DOUBLE        COMMENT '总市值（亿元）',
    market_type         VARCHAR(10)   COMMENT '股票类型（HS/GEM/STAR）',
    PRIMARY KEY (ts_code, trade_date, limit_type),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='涨跌停榜单（同花顺版）';

-- ------------------------------------------------------------
-- 5. limit_step  连板天梯
--    数据来源: limit_step，按月，20240101起
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS limit_step (
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    ts_code         VARCHAR(20)   NOT NULL COMMENT 'TS代码',
    name            VARCHAR(50)   COMMENT '股票名称',
    nums            VARCHAR(10)   COMMENT '连板天数',
    PRIMARY KEY (trade_date, ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='连板天梯';

-- ------------------------------------------------------------
-- 6. limit_cpt_list  涨停最强板块统计
--    数据来源: limit_cpt_list，按月，20240101起
--    注：唯一键字段待首次同步后根据实际字段确认
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS limit_cpt_list (
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    ts_code         VARCHAR(20)   NOT NULL COMMENT '概念代码',
    name            VARCHAR(100)  COMMENT '概念名称',
    days            INT           COMMENT '持续天数',
    up_stat         VARCHAR(20)   COMMENT '涨停统计描述',
    cons_nums       VARCHAR(10)   COMMENT '连板数',
    up_nums         INT           COMMENT '上涨数量',
    pct_chg         DOUBLE        COMMENT '涨跌幅',
    `rank`          INT           COMMENT '排名',
    PRIMARY KEY (trade_date, ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='涨停最强板块统计';

-- ------------------------------------------------------------
-- 7. dc_index  东财概念/行业/地域板块指数
--    数据来源: dc_index，按月×3种idx_type，20240101起
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dc_index (
    ts_code         VARCHAR(20)   NOT NULL COMMENT '概念代码',
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    idx_type        VARCHAR(20)   NOT NULL COMMENT '板块类型（行业板块/概念板块/地域板块）',
    name            VARCHAR(100)  COMMENT '概念名称',
    `leading`       VARCHAR(50)   COMMENT '领涨股票名称',
    leading_code    VARCHAR(20)   COMMENT '领涨股票代码',
    pct_change      DOUBLE        COMMENT '涨跌幅',
    leading_pct     DOUBLE        COMMENT '领涨股票涨跌幅',
    total_mv        DOUBLE        COMMENT '总市值（万元）',
    turnover_rate   DOUBLE        COMMENT '换手率',
    up_num          INT           COMMENT '上涨家数',
    down_num        INT           COMMENT '下降家数',
    level           VARCHAR(20)   COMMENT '行业层级',
    PRIMARY KEY (ts_code, trade_date, idx_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='东财概念板块（行业/概念/地域）';

-- ------------------------------------------------------------
-- 8. dc_daily  东财概念/行业/地域指数日线行情
--    数据来源: dc_daily，按月，20240101起
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dc_daily (
    ts_code         VARCHAR(20)   NOT NULL COMMENT '指数代码',
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    close           DOUBLE        COMMENT '收盘点位',
    open            DOUBLE        COMMENT '开盘点位',
    high            DOUBLE        COMMENT '最高点位',
    low             DOUBLE        COMMENT '最低点位',
    `change`        DOUBLE        COMMENT '涨跌额',
    pct_change      DOUBLE        COMMENT '涨跌幅（%）',
    vol             DOUBLE        COMMENT '成交量（手）',
    amount          DOUBLE        COMMENT '成交额（元）',
    swing           DOUBLE        COMMENT '振幅（%）',
    turnover_rate   DOUBLE        COMMENT '换手率（%）',
    category        VARCHAR(20)   COMMENT '板块类型',
    PRIMARY KEY (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='东财指数日线行情';

-- ------------------------------------------------------------
-- 9. dc_concept  东财概念题材每日快照
--    数据来源: dc_concept，按月，20240101起
--    ts_code = 概念代码
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dc_concept (
    theme_code              VARCHAR(20)   NOT NULL COMMENT '概念代码',
    trade_date              CHAR(8)       NOT NULL COMMENT '交易日期',
    name                    VARCHAR(100)  COMMENT '概念名称',
    pct_change              VARCHAR(20)   COMMENT '涨跌幅',
    hot                     VARCHAR(20)   COMMENT '热度',
    `sort`                  VARCHAR(20)   COMMENT '排序值',
    strength                VARCHAR(20)   COMMENT '强度',
    z_t_num                 VARCHAR(10)   COMMENT '涨停数',
    main_change             VARCHAR(30)   COMMENT '主力净流入',
    lead_stock              VARCHAR(50)   COMMENT '领涨股名称',
    lead_stock_code         VARCHAR(20)   COMMENT '领涨股代码',
    lead_stock_pct_change   VARCHAR(20)   COMMENT '领涨股涨跌幅',
    PRIMARY KEY (theme_code, trade_date),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='东财概念题材每日快照';

-- ------------------------------------------------------------
-- 10. index_daily  指数日线行情（上证/深证/创业板）
--     数据来源: index_daily，对3个指数分别调用，20240101起
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS index_daily (
    ts_code         VARCHAR(20)   NOT NULL COMMENT 'TS代码',
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    close           DOUBLE        COMMENT '收盘点位',
    open            DOUBLE        COMMENT '开盘点位',
    high            DOUBLE        COMMENT '最高点位',
    low             DOUBLE        COMMENT '最低点位',
    pre_close       DOUBLE        COMMENT '昨日收盘点',
    `change`        DOUBLE        COMMENT '涨跌额',
    pct_chg         DOUBLE        COMMENT '涨跌幅（%）',
    vol             DOUBLE        COMMENT '成交量（手）',
    amount          DOUBLE        COMMENT '成交额（千元）',
    PRIMARY KEY (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指数日线行情';

-- ------------------------------------------------------------
-- 11. daily_info  沪深市场每日交易统计
--     数据来源: daily_info，按年×5市场类型，20240101起
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_info (
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    ts_code         VARCHAR(20)   NOT NULL COMMENT '市场代码',
    ts_name         VARCHAR(50)   COMMENT '市场名称',
    com_count       INT           COMMENT '挂牌数',
    total_share     DOUBLE        COMMENT '总股本',
    float_share     DOUBLE        COMMENT '流通股本',
    total_mv        DOUBLE        COMMENT '总市值',
    float_mv        DOUBLE        COMMENT '流通市值',
    amount          DOUBLE        COMMENT '成交额',
    vol             DOUBLE        COMMENT '成交量',
    trans_count     DOUBLE        COMMENT '成交笔数',
    pe              DOUBLE        COMMENT '市盈率',
    tr              DOUBLE        COMMENT '换手率',
    exchange        VARCHAR(10)   COMMENT '交易所',
    PRIMARY KEY (trade_date, ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='沪深市场每日交易统计';

-- ------------------------------------------------------------
-- 12. stock_technical_indicators  股票技术指标
--     计算并存储的技术指标（移动平均线等）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_technical_indicators (
    ts_code         VARCHAR(20)   NOT NULL COMMENT 'TS代码',
    trade_date      CHAR(8)       NOT NULL COMMENT '交易日期',
    ma5             DOUBLE        COMMENT '5日均线',
    ma7             DOUBLE        COMMENT '7日均线',
    ma10            DOUBLE        COMMENT '10日均线',
    ma17            DOUBLE        COMMENT '17日均线',
    ma30            DOUBLE        COMMENT '30日均线',
    ma60            DOUBLE        COMMENT '60日均线',
    ma250           DOUBLE        COMMENT '250日均线',
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票技术指标';
