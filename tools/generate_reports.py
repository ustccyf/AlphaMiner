"""Generate factor_results.md and factor_results.html from factor_results.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def generate_markdown(results, out_path):
    bm_keys = list(results[0]["benchmarks"].keys())

    lines = []
    lines.append("# A股因子回测结果")
    lines.append("")
    lines.append("> 回测区间：2024-01-01 ~ 2024-12-31 | 股票池：15只沪深龙头 | 调仓周期：20日 | Top 5持仓")
    lines.append("")

    # Summary table
    lines.append("## 因子绩效汇总")
    lines.append("")
    lines.append("| 因子 | 方向 | 总收益 | 年化收益 | Sharpe | 最大回撤 | Calmar | 胜率 | 交易数 |")
    lines.append("|------|------|--------|----------|--------|----------|--------|------|--------|")
    for r in results:
        lines.append(
            f"| {r['factor_name']} | {r['description']} | {r['total_return_pct']}% | "
            f"{r['annualized_return_pct']}% | {r['sharpe_ratio']} | {r['max_drawdown_pct']}% | "
            f"{r['calmar_ratio']} | {r['win_rate_pct']}% | {r['num_trades']} |"
        )
    lines.append("")

    # Benchmark comparison
    lines.append("## 超额收益对比（vs 各基准指数）")
    lines.append("")
    header = "| 因子 |" + "|".join(f" {results[0]['benchmarks'][k]['name']}超额 |" for k in bm_keys) + " 信息比率(vs HS300) |"
    lines.append(header)
    sep = "|------|" + "|".join("-------------|" for _ in bm_keys) + "-------------------|"
    lines.append(sep)
    for r in results:
        bm = r["benchmarks"]
        cols = "|".join(f" {bm[k]['excess_return_pct']}% |" for k in bm_keys)
        ir = bm.get("hs300", {}).get("information_ratio", 0)
        lines.append(f"| {r['factor_name']} |{cols} {ir} |")
    lines.append("")

    # Factor details
    lines.append("## 各因子详解")
    lines.append("")
    for r in results:
        lines.append(f"### {r['factor_name']}")
        lines.append(f"- **选股逻辑**：{r['description']}")
        lines.append(f"- **总收益**：{r['total_return_pct']}%")
        lines.append(f"- **年化收益**：{r['annualized_return_pct']}%")
        lines.append(f"- **Sharpe比率**：{r['sharpe_ratio']}")
        lines.append(f"- **最大回撤**：{r['max_drawdown_pct']}%")
        bm = r['benchmarks']
        best_bm = max(bm.items(), key=lambda x: x[1]['excess_return_pct'])
        worst_bm = min(bm.items(), key=lambda x: x[1]['excess_return_pct'])
        lines.append(f"- **超额收益范围**：{worst_bm[1]['excess_return_pct']}% (vs {worst_bm[1]['name']}) ~ {best_bm[1]['excess_return_pct']}% (vs {best_bm[1]['name']})")
        lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Markdown saved to {out_path}")


def generate_html(results, out_path):
    bm_keys = list(results[0]["benchmarks"].keys())
    bm_names = {k: results[0]["benchmarks"][k]["name"] for k in bm_keys}
    factor_names = [r["factor_name"] for r in results]
    returns_all = [r["total_return_pct"] for r in results]
    sharpes = [r["sharpe_ratio"] for r in results]
    maxdds = [r["max_drawdown_pct"] for r in results]

    # Main metrics rows
    metrics_rows = ""
    for r in results:
        cls_ret = "positive" if r["total_return_pct"] >= 0 else "negative"
        metrics_rows += f"""
        <tr>
          <td><strong>{r['factor_name']}</strong></td>
          <td>{r['description']}</td>
          <td class="{cls_ret}">{r['total_return_pct']}%</td>
          <td>{r['annualized_return_pct']}%</td>
          <td>{r['sharpe_ratio']}</td>
          <td class="negative">{r['max_drawdown_pct']}%</td>
          <td>{r['calmar_ratio']}</td>
          <td>{r['win_rate_pct']}%</td>
          <td>{r['num_trades']}</td>
        </tr>"""

    # Benchmark comparison rows (dynamic)
    bm_header = "<th>因子</th>" + "".join(f"<th>vs {bm_names[k]}</th>" for k in bm_keys) + "<th>信息比率(vs HS300)</th>"
    bm_rows = ""
    for r in results:
        bm = r["benchmarks"]
        cells = "".join(
            f"<td class=\"{'positive' if bm[k]['excess_return_pct'] >= 0 else 'negative'}\">{bm[k]['excess_return_pct']}%</td>"
            for k in bm_keys
        )
        ir = bm.get("hs300", {}).get("information_ratio", 0)
        bm_rows += f"""
        <tr>
          <td><strong>{r['factor_name']}</strong><br><small>{r['description']}</small></td>
          {cells}<td>{ir}</td>
        </tr>"""

    # Build benchmark excess series for chart
    bm_colors = ['#0984e3', '#e17055', '#00b894', '#6c5ce7', '#fdcb6e', '#e84393', '#a29bfe', '#fd79a8']
    bm_series_js = ""
    for i, k in enumerate(bm_keys):
        vals = [r["benchmarks"][k]["excess_return_pct"] for r in results]
        bm_series_js += f"""
    {{ name: 'vs {bm_names[k]}', type: 'bar', data: {json.dumps(vals)},
       itemStyle: {{ color: bmColors[{i}] }},
       label: {{ show: true, position: 'top', fontSize: 9, formatter: p => p.value+'%' }} }},"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股因子回测结果</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f6fa; color: #2d3436; }}
.header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: #fff; padding: 28px 32px; }}
.header h1 {{ font-size: 24px; font-weight: 600; }}
.header p {{ font-size: 13px; opacity: 0.7; margin-top: 6px; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
.chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
@media (max-width: 900px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
.chart-box {{ background: #fff; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.chart-box h3 {{ font-size: 14px; margin-bottom: 12px; }}
.chart {{ width: 100%; height: 420px; }}
.chart-full {{ width: 100%; height: 380px; }}
.table-box {{ background: #fff; padding: 16px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 24px; overflow-x: auto; }}
.table-box h3 {{ font-size: 15px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #eee; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: #f8f9fa; padding: 10px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #dee2e6; white-space: nowrap; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #f1f3f4; }}
tr:hover {{ background: #f8f9ff; }}
.positive {{ color: #00b894; font-weight: 600; }}
.negative {{ color: #d63031; font-weight: 600; }}
.footer {{ text-align: center; padding: 20px; color: #b2bec3; font-size: 12px; }}
</style>
</head>
<body>

<div class="header">
  <h1>A股因子回测结果</h1>
  <p>回测区间：2024-01-01 ~ 2024-12-31 | 股票池：15只沪深龙头 | 调仓周期：20日 | Top 5持仓 | 初始资金100万</p>
</div>

<div class="container">

  <div class="chart-row">
    <div class="chart-box">
      <h3>各因子总收益率对比</h3>
      <div class="chart" id="chart-returns"></div>
    </div>
    <div class="chart-box">
      <h3>各因子Sharpe &amp; 最大回撤</h3>
      <div class="chart" id="chart-sharpe-dd"></div>
    </div>
  </div>

  <div class="chart-box" style="margin-bottom:24px">
    <h3>超额收益对比（vs 全部基准指数）</h3>
    <div class="chart-full" id="chart-excess"></div>
  </div>

  <div class="table-box">
    <h3>因子绩效汇总表</h3>
    <table>
      <thead><tr>
        <th>因子</th><th>选股逻辑</th><th>总收益</th><th>年化收益</th>
        <th>Sharpe</th><th>最大回撤</th><th>Calmar</th><th>胜率</th><th>交易数</th>
      </tr></thead>
      <tbody>{metrics_rows}</tbody>
    </table>
  </div>

  <div class="table-box">
    <h3>超额收益对比表</h3>
    <table>
      <thead><tr>{bm_header}</tr></thead>
      <tbody>{bm_rows}</tbody>
    </table>
  </div>

</div>

<div class="footer">Generated by A-Share Quant System</div>

<script>
(function() {{
  const names = {json.dumps(factor_names, ensure_ascii=False)};
  const returns = {json.dumps(returns_all)};
  const sharpes = {json.dumps(sharpes)};
  const maxdds = {json.dumps(maxdds)};
  const bmColors = {json.dumps(bm_colors)};

  // Chart 1: Returns bar
  const c1 = echarts.init(document.getElementById('chart-returns'));
  c1.setOption({{
    tooltip: {{ trigger: 'axis', formatter: p => p[0].name + '<br/>收益: <b>' + p[0].data + '%</b>' }},
    grid: {{ left: 120, right: 20, top: 10, bottom: 20 }},
    xAxis: {{ type: 'value', axisLabel: {{ formatter: v => v + '%' }} }},
    yAxis: {{ type: 'category', data: names, inverse: true, axisLabel: {{ fontSize: 12 }} }},
    series: [{{
      type: 'bar', data: returns.map(v => ({{ value: v, itemStyle: {{ color: v >= 0 ? '#00b894' : '#d63031' }} }})),
      label: {{ show: true, position: 'right', formatter: p => p.value + '%', fontSize: 11 }}
    }}]
  }});

  // Chart 2: Sharpe + MaxDD
  const c2 = echarts.init(document.getElementById('chart-sharpe-dd'));
  c2.setOption({{
    tooltip: {{ trigger: 'axis' }},
    legend: {{ data: ['Sharpe', '最大回撤%'], bottom: 0 }},
    grid: {{ left: 120, right: 60, top: 20, bottom: 40 }},
    xAxis: {{ type: 'category', data: names, axisLabel: {{ rotate: 30, fontSize: 11 }} }},
    yAxis: [
      {{ type: 'value', name: 'Sharpe', axisLabel: {{ fontSize: 11 }} }},
      {{ type: 'value', name: '回撤%', axisLabel: {{ formatter: v => v + '%' }}, inverse: true }}
    ],
    series: [
      {{ name: 'Sharpe', type: 'bar', data: sharpes, itemStyle: {{ color: '#0984e3' }},
         label: {{ show: true, position: 'top', fontSize: 10 }} }},
      {{ name: '最大回撤%', type: 'line', yAxisIndex: 1, data: maxdds,
         itemStyle: {{ color: '#d63031' }}, lineStyle: {{ width: 2 }},
         label: {{ show: true, position: 'top', fontSize: 10, formatter: p => p.value + '%' }} }}
    ]
  }});

  // Chart 3: Excess returns vs all benchmarks
  const c3 = echarts.init(document.getElementById('chart-excess'));
  const bmSeries = [{bm_series_js[:-1]}
  ];
  c3.setOption({{
    tooltip: {{ trigger: 'axis' }},
    legend: {{ data: bmSeries.map(s => s.name), bottom: 0, type: 'scroll' }},
    grid: {{ left: 120, right: 20, top: 20, bottom: 50 }},
    xAxis: {{ type: 'category', data: names, axisLabel: {{ rotate: 30, fontSize: 11 }} }},
    yAxis: {{ type: 'value', axisLabel: {{ formatter: v => v + '%' }} }},
    series: bmSeries
  }});

  window.addEventListener('resize', () => {{ c1.resize(); c2.resize(); c3.resize(); }});
}})();
</script>
</body>
</html>"""

    with open(out_path, "w") as f:
        f.write(html)
    print(f"HTML saved to {out_path}")


if __name__ == "__main__":
    json_path = Path(__file__).resolve().parent.parent / "outputs" / "factor_results.json"
    if not json_path.exists():
        print(f"Error: {json_path} not found. Run run_factor_backtest.py first.")
        sys.exit(1)

    with open(json_path) as f:
        results = json.load(f)

    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    generate_markdown(results, out_dir / "factor_results.md")
    generate_html(results, out_dir / "factor_results.html")
    print("Done!")
