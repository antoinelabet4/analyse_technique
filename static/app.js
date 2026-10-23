async function main() {
  const res = await fetch("/api/test-candles");
  const candles = await res.json();

  const chart = LightweightCharts.createChart(document.getElementById("chart"), {
    layout: {
      background: { color: "#0d1117" },
      textColor: "#e6edf3",
    },
    grid: {
      vertLines: { color: "#21262d" },
      horzLines: { color: "#21262d" },
    },
    timeScale: {
      timeVisible: false,
      borderColor: "#30363d",
    },
    rightPriceScale: {
      borderColor: "#30363d",
    },
    handleScroll: true,
    handleScale: true,
  });

  const series = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: "#3fb950",
    downColor: "#f85149",
    borderVisible: false,
    wickUpColor: "#3fb950",
    wickDownColor: "#f85149",
  });

  series.setData(candles);
  chart.timeScale().fitContent();

  window.addEventListener("resize", () => {
    chart.applyOptions({
      width: document.getElementById("chart").clientWidth,
      height: document.getElementById("chart").clientHeight,
    });
  });
}

main();
