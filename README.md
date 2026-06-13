# A-Share Quant System

A股量化交易系统，包含事件驱动回测引擎和多因子选股策略框架。

## 架构

```
├── src/
│   ├── core/          # 回测引擎、事件系统、数据类型
│   ├── data/          # 数据源(Cache→Baostock→DailyBarFeed), 支持OHLCV+PE/PB/换手率
│   ├── broker/        # 券商模拟：T+1、涨跌停、佣金、印花税、滑点
│   ├── portfolio/     # 资金管理、持仓跟踪、风控
│   ├── strategy/      # 策略基类 + 示例策略
│   │   ├── timing.py       # MarketTimer（MA择时）+ TimingMultiFactorStrategy
│   │   └── examples/
│   │       ├── advanced.py # ICWeightedStrategy / MLFactorStrategy
│   │       └── alpha.py    # Alpha策略（微盘/价值/反转/低波/低换手）
│   ├── factors/       # 因子框架
│   │   ├── base.py         # Factor基类（winsorize、standardize）
│   │   ├── technical.py    # 8个技术因子
│   │   ├── fundamental.py  # 基本面因子（价值PE+PB、换手率、反转、市值代理）
│   │   ├── composite.py    # MultiFactorModel（固定权重合成）
│   │   ├── ic_weighted.py  # ICWeightedModel（滚动IC动态权重）
│   │   ├── ml_composite.py # MLFactorModel（Ridge回归合成）
│   │   ├── templates.py    # 因子模板引擎（20个模板→134个候选因子）
│   │   ├── evaluator.py    # 批量因子评估器（IC/ICIR/胜率）
│   │   └── miner.py        # 因子挖掘引擎（筛选+去相关+组合）
│   ├── pipeline.py     # Self-improving 流水线编排器
│   └── analysis/      # 绩效分析、图表报告
├── config/            # 配置：费率、股票池（大盘/中盘/微盘三级universe）
├── scripts/           # 批量回测脚本
│   ├── compare_strategies.py
│   ├── backtest_alpha.py
│   ├── build_universe.py
│   └── run_pipeline.py  # Self-improving pipeline CLI
└── outputs/           # 图表 + 回测报告
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
pip install -r requirements.txt

# 构建股票池（从Baostock获取指数成分股）
python scripts/build_universe.py

# 运行回测
python src/main.py --start 20260223 --end 20260522 --strategy value --benchmark hs300

# Alpha策略批量对比
python scripts/backtest_alpha.py --start 20260223 --end 20260522
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start` | 20240101 | 开始日期 YYYYMMDD |
| `--end` | 20241231 | 结束日期 YYYYMMDD |
| `--cash` | 1000000 | 初始资金 |
| `--strategy` | ma_crossover | 见策略列表 |
| `--benchmark` | hs300 | hs300 / sz50 / zz500 / zz1000 / cyb / kc50 / szcz |
| `--symbols` | 5只蓝筹 | 股票代码列表 |

## 数据源

| 数据源 | 数据字段 | 说明 |
|--------|---------|------|
| Baostock（默认） | OHLCV + peTTM + pbMRQ + turn(换手率) | 免费，无需注册 |
| AkShare | OHLCV | 免费，依赖东方财富API |

数据自动缓存到 `data/cache/` 目录（Parquet格式）。

---

## 业界Alpha策略库

| 类别 | 策略 | 选股逻辑 | 数据 | 状态 |
|------|------|---------|------|------|
| 规模 | **微盘股** | 做多成交额最小的股票（市值代理） | OHLCV | ✅ |
| 价值 | **价值(低PE/PB)** | 做多PE、PB最低，1/PE+1/PB等权 | Baostock PE/PB | ✅ |
| 动量 | **动量** | 做多20日涨幅最强 | OHLCV | ✅ |
| 反转 | **短期反转** | 做多5日跌幅最大 | OHLCV | ✅ |
| 低波 | **低波动** | 做多20日波动率最低 | OHLCV | ✅ |
| 流动性 | **低换手率** | 做多换手率最低 | Baostock 换手率 | ✅ |
| 质量 | ROE/利润率 | 做多高ROE、高利润率 | 季报数据 | ❌ |
| 红利 | 高股息 | 做多股息率最高 | 年报分红 | ❌ |
| 成长 | 营收/利润增速 | 做多高增长 | 季报数据 | ❌ |
| 轮动 | 大小盘轮动 | 大小盘相对强弱轮动 | OHLCV | ❌ |

### 股票池

| Universe | 来源 | 数量 | 说明 |
|----------|------|------|------|
| 大盘 | 沪深300成分股 | 50 | 最大市值 |
| 中盘 | 中证500成分股（排除沪深300重叠） | 50 | 中等市值 |
| 微盘 | 中证500偏小市值成分股 | 50 | 偏小市值 |

---

## 回测结果：全部策略超额收益排名

> 回测区间：2026-02-23 ~ 2026-05-22 | 基准：沪深300(+2.92%) | 调仓周期：20日 | Top 5持仓

### 完整排名（单因子 + 组合策略 + Alpha策略 + 多级Universe）

| 排名 | 策略 | Universe | 类型 | 总收益 | 超额收益 | Sharpe | 最大回撤 | 胜率 |
|------|------|----------|------|--------|----------|--------|----------|------|
| 1 | **中盘价值(低PE/PB)** | 中盘 | Alpha | +3.88% | **+0.96%** | 1.14 | -2.85% | 100% |
| 2 | **中盘反转** | 中盘 | Alpha | +3.12% | **+0.20%** | 0.88 | -3.18% | 71% |
| 3 | 振幅_20日 | 大盘 | 单因子 | +2.76% | -0.16% | 1.02 | -2.88% | 83% |
| 4 | 固定权重(动量+量比) | 大盘 | 组合 | +1.65% | -1.27% | 0.89 | -1.81% | 33% |
| 5 | 均线偏离_20日 | 大盘 | 单因子 | +0.45% | -2.47% | 0.04 | -3.21% | 43% |
| 6 | 价格位置_20日 | 大盘 | 单因子 | +0.25% | -2.67% | -0.06 | -3.26% | 33% |
| 7 | 大盘反转 | 大盘 | Alpha | -0.11% | -3.03% | -0.22 | -4.86% | 57% |
| 8 | 微盘股(小市值因子) | 微盘 | Alpha | -0.28% | -3.20% | -0.24 | -3.91% | 67% |
| 9 | 大盘低换手率 | 大盘 | Alpha | -0.33% | -3.25% | -0.13 | -5.51% | 100% |
| 10 | 大盘低波 | 大盘 | Alpha | -0.41% | -3.33% | -0.59 | -2.91% | 17% |
| 11 | IC动态权重 | 大盘 | 组合 | -0.97% | -3.89% | -0.58 | -4.40% | 57% |
| 12 | 波动率_20日 | 大盘 | 单因子 | -1.08% | -4.01% | -0.67 | -4.47% | 71% |
| 13 | 中盘低波 | 中盘 | Alpha | -1.24% | -4.16% | -0.66 | -5.32% | 67% |
| 14 | 量比_20日 | 大盘 | 单因子 | -1.28% | -4.20% | -0.79 | -4.66% | 42% |
| 15 | 中盘基准(动量+量比) | 中盘 | Alpha | -1.44% | -4.36% | -0.80 | -5.13% | 29% |
| 16 | 微盘低波 | 微盘 | Alpha | -1.84% | -4.76% | -1.11 | -3.74% | 20% |
| 17 | 动量_20日 | 大盘 | 单因子 | -2.14% | -5.06% | -1.07 | -5.49% | 50% |
| 18 | 大盘基准(动量+量比) | 大盘 | Alpha | -2.36% | -5.28% | -1.40 | -4.29% | 0% |
| 19 | 择时+固定权重 | 大盘 | 组合 | -2.61% | -5.53% | -2.89 | -4.68% | 20% |
| 20 | 微盘反转 | 微盘 | Alpha | -3.05% | -5.97% | -0.73 | -10.34% | 60% |
| 21 | RSI_14 | 大盘 | 单因子 | -3.17% | -6.09% | -2.41 | -4.65% | 29% |
| 22 | 微盘基准(动量+量比) | 微盘 | Alpha | -3.91% | -6.84% | -2.03 | -6.17% | 14% |
| 23 | 大盘价值(低PE/PB) | 大盘 | Alpha | -4.78% | -7.70% | -2.89 | -7.23% | 100% |
| 24 | 成交额_20日 | 大盘 | 单因子 | -4.91% | -7.84% | -2.06 | -8.17% | 100% |
| 25 | Ridge回归 | 大盘 | 组合 | -5.90% | -8.83% | -4.68 | -6.26% | 0% |

### 关键发现

1. **仅2个策略实现正超额**：中盘价值(+0.96%)、中盘反转(+0.20%)，均为中盘universe
2. **中盘股是Alpha来源**：中盘股估值分化大，低PE/PB选股和反转效应显著
3. **同一因子在不同universe表现差异大**：价值因子在中盘有效(+0.96%)，在大盘反而巨亏(-7.70%)
4. **单因子中低振幅最优**：超额-0.16%，Sharpe 1.02，几乎追平基准
5. **微盘股近3个月无超额**：大盘风格主导，小市值整体跑输
6. **IC/ML组合策略不如简单策略**：15只股票截面太窄，统计显著性和训练样本均不足

---

## Self-Improving Pipeline（多Agent因子挖掘+组合优化）

自动化7阶段流水线，238个候选因子 → IC评估 → 去相关筛选 → 多方法权重优化 → 回测验证。

```bash
# 单个universe完整流水线（~4分钟）
python scripts/overnight_pipeline.py --start 20260223 --end 20260522 --universe large_cap

# 所有universe批量运行
for u in large_cap mid_cap micro_cap; do
    python scripts/overnight_pipeline.py --universe $u --output outputs/overnight_report_${u}.md &
done
```

### Agent 架构

```
Phase 1: Agent A (Param Refiner)      → 134 baseline + 48 refined + 56 composite = 238 factors
Phase 2: Agent C (IC Evaluator)       → Daily rank IC + ICIR + Win Rate
Phase 3: Agent C (Rolling Validator)  → IC stability across time windows
Phase 4: Selector                     → |IC|>0.015 + ICIR>0.2 + stability>0.3 + decorrelate@0.7
Phase 5: Agent D (Weight Optimizer)   → ICIR / Equal / IC / GridSearch
Phase 6: Agent E (Backtest Engine)    → Strategy backtest with mined factors
Phase 7: Agent F (Report Writer)      → Comprehensive markdown report
```

### Overnight 挖掘结果（2026-02-23 ~ 2026-05-22）

| Universe | 候选因子 | 入选 | 最佳方法 | 总收益 | 超额收益 | Sharpe |
|----------|---------|------|---------|--------|----------|--------|
| **大盘** | 238 | 11 | Equal | +12.54% | **+9.62%** | 2.94 |
| **微盘** | 238 | 14 | ICIR | +10.72% | **+7.80%** | 2.45 |
| 中盘 | 238 | 6 | ICIR | -0.73% | -3.65% | -0.81 |

### 大盘最佳因子组合（超额+9.62%）

Pipeline 自动发现的因子（全部是复合因子，非手工编写）：

| Factor | IC Mean | ICIR | 来源 |
|--------|---------|------|------|
| (return(w=15))*(return(w=20)) | +0.146 | 0.88 | 复合(动量×动量) |
| (return(w=10))*(ma_dev(w=10)) | +0.090 | 0.71 | 复合(动量×均线偏离) |
| amount_vol_corr(w=30) | +0.105 | 0.57 | 量价相关性 |
| price_pos(w=5) | +0.079 | 0.54 | 短期价格位置 |
| diff(w=2) | +0.086 | 0.50 | 2日价格差分 |
| hl_ratio(w=30) | +0.062 | 0.45 | 30日高低价比 |
| (return(w=5))*(ma_dev(w=5)) | +0.057 | 0.36 | 复合(短期动量×均线偏离) |

> 完整报告：`outputs/overnight_report_*.md`

---

## 策略列表

| CLI参数 | 策略 | 类型 |
|---------|------|------|
| `ma_crossover` | 均线交叉(5日/20日) | 技术 |
| `multi_factor` | 多因子(动量+量比 固定权重) | 组合 |
| `timing_multi_factor` | 择时多因子(MA20牛熊过滤) | 组合 |
| `ic_weighted` | IC动态权重(8因子) | 组合 |
| `ml_factor` | Ridge回归(8因子) | 组合 |
| `low_vol` | 低波动 | Alpha |
| `reversal` | 短期反转(5日) | Alpha |
| `micro_cap` | 微盘股(市值代理因子) | Alpha |
| `small_reversal` | 小市值+反转 | Alpha |
| `value` | 价值(低PE/PB) | Alpha |
| `low_turnover` | 低换手率 | Alpha |

## 绩效指标

总收益率、年化收益率、年化波动率、Sharpe比率、Calmar比率、最大回撤、超额收益（策略 vs 基准指数收益差）、信息比率（单位跟踪误差的超额收益）、胜率、盈亏比、交易次数。

## 依赖

```
pandas, numpy, baostock, pyarrow, matplotlib, loguru, scipy, scikit-learn, flask
```
# AlphaMinerAgent
