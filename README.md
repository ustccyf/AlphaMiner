# A-Share Quant System

A股量化交易系统，包含事件驱动回测引擎和多因子选股策略框架。

## 架构

```
stock/
├── src/
│   ├── core/          # 回测引擎、事件系统、数据类型
│   ├── data/          # 数据源(Cache→Baostock/AkShare→DailyBarFeed)
│   ├── broker/        # 券商模拟：T+1、涨跌停、佣金、印花税、滑点
│   ├── portfolio/     # 资金管理、持仓跟踪、风控
│   ├── strategy/      # 策略基类 + 示例策略
│   ├── factors/       # 因子框架：动量、RSI、量比、多因子合成
│   └── analysis/      # 绩效分析、图表报告
├── web/               # Web界面（Flask + ECharts）
├── config/            # 配置：费率、股票池
├── tests/             # 测试
├── data/cache/        # Parquet本地缓存
└── outputs/plots/     # 图表输出
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

# 命令行回测
python src/main.py --start 20240101 --end 20241231 --strategy ma_crossover

# Web界面
python web/app.py
# 浏览器打开 http://localhost:5000
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start` | 20240101 | 开始日期 |
| `--end` | 20241231 | 结束日期 |
| `--cash` | 1000000 | 初始资金 |
| `--strategy` | ma_crossover | 策略: ma_crossover / multi_factor |
| `--benchmark` | hs300 | 基准: hs300 / sz50 / zz500 / cyb |
| `--symbols` | 5只蓝筹 | 股票代码列表 |

### Web界面功能

- 在线选择策略、日期范围、股票池
- 实时运行回测，展示绩效指标
- ECharts交互图表：策略 vs 全部基准指数对比
- 超额收益分析、回撤图、交易分布

## 绩效指标

- 总收益率、年化收益率、年化波动率
- Sharpe比率、Calmar比率、最大回撤
- **超额收益** — 策略 vs 基准指数收益差
- **信息比率** — 单位跟踪误差的超额收益
- 胜率、盈亏比、交易次数

## 数据源

| 数据源 | 说明 |
|--------|------|
| Baostock（默认） | 免费，无需注册，独立数据服务 |
| AkShare | 免费，依赖东方财富API |

数据自动缓存到 `data/cache/` 目录（Parquet格式），后续回测无需重新获取。

## 策略

### MA Crossover（均线交叉）
- `fast=5, slow=20` — 5日均线上穿20日均线买入，下穿卖出

### Multi-Factor（多因子选股）
- 动量因子(20日) + 量比因子(20日)，加权打分排名
- 每20个交易日调仓，持有Top 5

## 依赖

```
pandas, numpy, baostock, pyarrow, matplotlib, loguru, scipy, flask
```
