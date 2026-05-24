# A-Share Quant System

A股量化交易系统，包含事件驱动回测引擎和多因子选股策略框架。

## 架构

```
stock/
├── src/
│   ├── core/          # 回测引擎、事件系统、数据类型
│   ├── data/          # 数据源(Cache→Baostock/AkShare→DailyBarFeed)
│   │   └── data_source.py  # 支持OHLCV + PE/PB/换手率(peTTM,pbMRQ,turn)
│   ├── broker/        # 券商模拟：T+1、涨跌停、佣金、印花税、滑点
│   ├── portfolio/     # 资金管理、持仓跟踪、风控
│   ├── strategy/      # 策略基类 + 示例策略
│   │   ├── timing.py       # MarketTimer（MA择时）+ TimingMultiFactorStrategy
│   │   └── examples/
│   │       ├── advanced.py  # ICWeightedStrategy / MLFactorStrategy
│   │       └── alpha.py     # 业界Alpha策略（微盘/价值/反转/低波/低换手）
│   ├── factors/       # 因子框架
│   │   ├── base.py         # Factor抽象基类（winsorize、standardize）
│   │   ├── technical.py    # 8个技术因子（动量、量比、RSI、波动率等）
│   │   ├── fundamental.py  # 基本面因子（价值PE+PB、换手率、反转、市值代理）
│   │   ├── composite.py    # MultiFactorModel（固定权重合成）
│   │   ├── ic_weighted.py  # ICWeightedModel（滚动IC动态权重）
│   │   └── ml_composite.py # MLFactorModel（Ridge回归合成）
│   └── analysis/      # 绩效分析、图表报告
├── web/               # Web界面（Flask + ECharts）
├── config/            # 配置：费率、股票池（多级universe）
├── scripts/           # 批量回测脚本
│   ├── compare_strategies.py
│   ├── backtest_alpha.py
│   └── build_universe.py
├── tests/             # 测试
├── data/cache/        # Parquet本地缓存
└── outputs/           # 图表输出 + 回测报告
```

## 回测引擎

事件驱动架构，逐日循环：

```
DataFeed.next()  →  Strategy.next(bars)  →  Portfolio.on_signal()
    →  Broker.execute()  →  Portfolio.on_fill()  →  Portfolio.update()
```

### A股规则

| 规则 | 实现 |
|------|------|
| T+1 | Broker跟踪当日买入量，当日不可卖出 |
| 涨跌停 | ±10%（主板）/ ±5%（ST）价格钳位 |
| 佣金 | 万2.5，最低5元/笔 |
| 印花税 | 卖出0.05%，买入免收 |
| 最小单位 | 100股（1手） |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 构建股票池
python scripts/build_universe.py

# 命令行回测
python src/main.py --start 20240101 --end 20241231 --strategy reversal

# Alpha策略批量对比
python scripts/backtest_alpha.py --start 20260223 --end 20260522
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start` | 20240101 | 开始日期 |
| `--end` | 20241231 | 结束日期 |
| `--cash` | 1000000 | 初始资金 |
| `--strategy` | ma_crossover | 见策略列表 |
| `--benchmark` | hs300 | 基准: hs300 / sz50 / zz500 / zz1000 / cyb / kc50 / szcz |
| `--symbols` | 5只蓝筹 | 股票代码列表 |

## 数据源

| 数据源 | 数据 | 说明 |
|--------|------|------|
| Baostock（默认） | OHLCV + PE(TTM) + PB(MRQ) + 换手率 | 免费，无需注册 |
| AkShare | OHLCV | 免费，依赖东方财富API |

数据自动缓存到 `data/cache/` 目录（Parquet格式）。

## 绩效指标

- 总收益率、年化收益率、年化波动率
- Sharpe比率、Calmar比率、最大回撤
- **超额收益** — 策略 vs 基准指数收益差
- **信息比率** — 单位跟踪误差的超额收益
- 胜率、盈亏比、交易次数

---

## 业界Alpha策略库

### 策略分类

| 类别 | 策略 | 选股逻辑 | 数据需求 | 实现状态 |
|------|------|---------|---------|---------|
| 规模 | **微盘股** | 做多最小市值/最低成交额股票 | 市值代理(成交额) | ✅ |
| 价值 | **价值(低PE/PB)** | 做多低PE、低PB股票，1/PE+1/PB等权 | Baostock peTTM/pbMRQ | ✅ |
| 动量 | **动量** | 做多20日涨幅最强 | OHLCV | ✅ |
| 反转 | **短期反转** | 做多5日跌幅最大（反转效应） | OHLCV | ✅ |
| 低波 | **低波动** | 做多20日波动率最低 | OHLCV | ✅ |
| 流动性 | **低换手率** | 做多换手率最低的股票 | Baostock turn | ✅ |
| 质量 | ROE/利润率 | 做多高ROE、高利润率 | 季报数据 | ❌ 待实现 |
| 红利 | 高股息 | 做多股息率最高 | 年报分红数据 | ❌ 待实现 |
| 成长 | 营收/利润增速 | 做多高增长 | 季报数据 | ❌ 待实现 |
| 轮动 | 大小盘轮动 | 大小盘相对强弱轮动 | OHLCV | ❌ 待实现 |

### 股票池

| Universe | 来源 | 股票数 | 说明 |
|----------|------|--------|------|
| 大盘 | 沪深300前15只 | 15 | 最大市值 |
| 中盘 | 中证500（排除沪深300重叠） | 15 | 中等市值 |
| 微盘 | 中证500偏小市值 | 15 | 偏小市值（市值代理） |

---

## 回测结果排名（最近3个月 2026-02-23 ~ 2026-05-22）

> 基准：沪深300(+2.92%) | 调仓周期：20日 | Top 5持仓

### 全部策略按超额收益排名

| 排名 | 策略 | Universe | 总收益 | 超额收益 | Sharpe | 最大回撤 | 胜率 |
|------|------|----------|--------|----------|--------|----------|------|
| 1 | **中盘价值(低PE/PB)** | 中盘 | +3.88% | **+0.96%** | 1.14 | -2.85% | 100% |
| 2 | 中盘反转 | 中盘 | +3.12% | **+0.20%** | 0.88 | -3.18% | 71% |
| 3 | 振幅_20日(单因子) | 大盘 | +2.76% | -0.16% | 1.02 | -2.88% | 83% |
| 4 | 大盘反转 | 大盘 | -0.11% | -3.03% | -0.22 | -4.86% | 57% |
| 5 | 微盘股(小市值因子) | 微盘 | -0.28% | -3.20% | -0.24 | -3.91% | 67% |
| 6 | 大盘低换手率 | 大盘 | -0.33% | -3.25% | -0.13 | -5.51% | 100% |
| 7 | 大盘低波 | 大盘 | -0.41% | -3.33% | -0.59 | -2.91% | 17% |
| 8 | 中盘低波 | 中盘 | -1.24% | -4.16% | -0.66 | -5.32% | 67% |
| 9 | 中盘基准(动量+量比) | 中盘 | -1.44% | -4.36% | -0.80 | -5.13% | 29% |
| 10 | 微盘低波 | 微盘 | -1.84% | -4.76% | -1.11 | -3.74% | 20% |
| 11 | 大盘基准(动量+量比) | 大盘 | -2.36% | -5.28% | -1.40 | -4.29% | 0% |
| 12 | 微盘反转 | 微盘 | -3.05% | -5.97% | -0.73 | -10.34% | 60% |
| 13 | 微盘基准(动量+量比) | 微盘 | -3.91% | -6.84% | -2.03 | -6.17% | 14% |
| 14 | 大盘价值(低PE/PB) | 大盘 | -4.78% | -7.70% | -2.89 | -7.23% | 100% |

### 关键发现

1. **中盘价值(+0.96%超额)** 是唯一显著正超额的策略：中盘股估值分化大，低PE/PB选股有效
2. **中盘反转(+0.20%)** 也实现正超额：中盘股均值回复效应强于大盘
3. **大盘价值反而亏损(-7.70%)**：大盘股估值差异小，价值因子失效
4. **微盘策略无超额**：近3个月大盘风格主导，微盘股整体跑输
5. **单因子中振幅(低振幅)最优**，超额仅 -0.16%，Sharpe 1.02

### 综合策略对比

| 策略 | 总收益 | 超额收益 | Sharpe | 说明 |
|------|--------|----------|--------|------|
| 中盘价值 | +3.88% | +0.96% | 1.14 | 低PE/PB选股 |
| 中盘反转 | +3.12% | +0.20% | 0.88 | 5日反转效应 |
| 固定权重(动量+量比) | +1.65% | -1.27% | 0.89 | 基线策略 |
| IC动态权重 | -0.97% | -3.89% | -0.58 | 8因子IC动态 |
| 择时+固定权重 | -2.61% | -5.53% | -2.89 | MA20择时 |
| Ridge回归 | -5.90% | -8.83% | -4.68 | ML合成 |

---

## 策略CLI参考

```bash
# 单因子Alpha策略
python src/main.py --strategy low_vol --start 20260223 --end 20260522
python src/main.py --strategy reversal --start 20260223 --end 20260522
python src/main.py --strategy micro_cap --start 20260223 --end 20260522
python src/main.py --strategy value --start 20260223 --end 20260522
python src/main.py --strategy low_turnover --start 20260223 --end 20260522
python src/main.py --strategy small_reversal --start 20260223 --end 20260522

# 组合策略
python src/main.py --strategy multi_factor --start 20260223 --end 20260522
python src/main.py --strategy timing_multi_factor --start 20260223 --end 20260522
python src/main.py --strategy ic_weighted --start 20260223 --end 20260522
python src/main.py --strategy ml_factor --start 20260223 --end 20260522

# 批量对比
python scripts/backtest_alpha.py --start 20260223 --end 20260522 --benchmark hs300
```

## 更新日志

- **2026-05-24** — Alpha策略库 + 数据扩展
  - 扩展 Baostock 数据源支持 PE(TTM)、PB(MRQ)、换手率
  - 新增 `src/factors/fundamental.py`：价值(PE+PB)、换手率、短期反转、市值代理因子
  - 新增 `src/strategy/examples/alpha.py`：6个业界Alpha策略类
  - 新增 `scripts/backtest_alpha.py`：14策略 × 3股票池 批量对比
  - 新增 `scripts/build_universe.py`：从 Baostock 构建大盘/中盘/微盘股票池
  - **首次实现正超额：中盘价值 +0.96%、中盘反转 +0.20%**

- **2026-05-23** — 策略增强
  - 新增择时多因子、IC动态权重、Ridge回归策略
  - 新增 `src/strategy/timing.py`、`src/factors/ic_weighted.py`、`src/factors/ml_composite.py`
  - 修复 Sharpe/Calmar/IR 除零边界处理

## 依赖

```
pandas, numpy, baostock, pyarrow, matplotlib, loguru, scipy, scikit-learn, flask
```
