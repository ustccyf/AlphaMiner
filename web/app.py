import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, render_template, request

from src.data.data_source import BaostockDataSource
from src.data.data_feed import DailyBarFeed
from src.broker.broker import Broker
from src.broker.commission import CommissionModel
from src.broker.slippage import SlippageModel
from src.core.engine import BacktestEngine
from src.portfolio.portfolio import Portfolio
from src.strategy.examples.ma_crossover import MACrossoverStrategy
from src.analysis.performance import PerformanceAnalyzer
from src.utils.logger import setup_logger

setup_logger("WARNING")

app = Flask(__name__)

from config.settings import BENCHMARKS

DEFAULT_SYMBOLS = ["600519.SH", "000858.SZ", "000333.SZ", "601318.SH", "600036.SH"]


def parse_symbols(raw: str):
    if not raw or not raw.strip():
        return DEFAULT_SYMBOLS
    return [s.strip() for s in raw.split(",") if s.strip()]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/backtest", methods=["POST"])
def run_backtest():
    data = request.get_json()
    strategy_name = data.get("strategy", "ma_crossover")
    symbols = parse_symbols(data.get("symbols", ""))
    start_str = data.get("start", "20240101")
    end_str = data.get("end", "20241231")
    cash = float(data.get("cash", 1_000_000))
    fast = int(data.get("fast", 5))
    slow = int(data.get("slow", 20))
    benchmarks_selected = data.get("benchmarks", ["hs300"])

    start_dt = datetime.strptime(start_str, "%Y%m%d")
    end_dt = datetime.strptime(end_str, "%Y%m%d")

    source = BaostockDataSource()
    data_feed = DailyBarFeed(source, symbols, start_dt.date(), end_dt.date())

    if strategy_name == "ma_crossover":
        strategy = MACrossoverStrategy(symbols, fast=fast, slow=slow, data_feed=data_feed)
    else:
        from src.factors.composite import MultiFactorModel
        from src.factors.technical import MomentumFactor, VolumeRatioFactor
        from src.strategy.examples.multi_factor import MultiFactorStrategy
        model = MultiFactorModel([
            (MomentumFactor(20), 0.6),
            (VolumeRatioFactor(20), 0.4),
        ])
        strategy = MultiFactorStrategy(symbols, model, data_feed=data_feed)

    portfolio = Portfolio(initial_cash=cash)
    broker = Broker(
        commission=CommissionModel(rate=0.00025, min_per_trade=5.0, stamp_duty_rate=0.0005),
        slippage=SlippageModel(method="percent", value=0.001),
    )

    engine = BacktestEngine(
        data_feed=data_feed, strategy=strategy,
        portfolio=portfolio, broker=broker,
    )
    result = engine.run()

    # Fetch all selected benchmarks
    benchmark_data = {}
    benchmark_metrics = {}
    for bm_key in benchmarks_selected:
        if bm_key in BENCHMARKS:
            bm_code, bm_name = BENCHMARKS[bm_key]
            bm_df = source.load_symbol(bm_code, start_dt.date(), end_dt.date())
            bm_df = bm_df.reset_index()[["date", "close"]]
            bm_df["date"] = bm_df["date"].dt.strftime("%Y-%m-%d")
            benchmark_data[bm_key] = {
                "name": bm_name,
                "data": bm_df.to_dict(orient="records"),
            }
            analyzer_bm = PerformanceAnalyzer(result.equity_curve, result.trades, bm_df)
            s = analyzer_bm.summary()
            benchmark_metrics[bm_key] = {
                "name": bm_name,
                "benchmark_return_pct": s.get("benchmark_return_pct", 0),
                "excess_return_pct": s.get("excess_return_pct", 0),
                "annualized_excess_pct": s.get("annualized_excess_pct", 0),
                "information_ratio": s.get("information_ratio", 0),
                "tracking_error_pct": s.get("tracking_error_pct", 0),
            }

    analyzer = PerformanceAnalyzer(result.equity_curve, result.trades)
    summary = analyzer.summary()

    equity_data = []
    for ep in result.equity_curve:
        equity_data.append({
            "time": ep.time.strftime("%Y-%m-%d"),
            "equity": round(ep.total, 2),
            "returns": round(ep.returns, 6),
        })

    trades_data = []
    for t in result.trades:
        trades_data.append({
            "time": t.time.strftime("%Y-%m-%d"),
            "symbol": t.symbol,
            "direction": t.direction,
            "quantity": t.quantity,
            "price": round(t.price, 2),
            "pnl": round(t.pnl, 2),
        })

    return jsonify({
        "summary": summary,
        "equity_curve": equity_data,
        "trades": trades_data,
        "benchmarks": benchmark_data,
        "benchmark_metrics": benchmark_metrics,
    })


if __name__ == "__main__":
    print("\n  A-Share Quant Backtest Web UI")
    print("  Open http://localhost:5000 in your browser\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
