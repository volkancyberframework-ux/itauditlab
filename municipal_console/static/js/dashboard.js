(() => {
  const source = document.getElementById('dashboard-data');
  if (!source || !window.Chart) return;
  const data = JSON.parse(source.textContent);
  const charts = [];
  const palettes = {responses:['#279d82','#dfa945','#d56869','#8096af','#dce5ed'],evaluations:['#279d82','#dfa945','#d56869','#dce5ed'],risks:['#d56869','#dfa945','#3399ad'],frameworks:['#087d94','#4ea957']};
  const dark = () => document.documentElement.dataset.theme === 'dark';
  const text = () => dark() ? '#a5becf' : '#526c80';
  const grid = () => dark() ? '#294253' : '#e8eef3';
  document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
    const key = canvas.dataset.chart, values = data[key];
    if (!values) return;
    const donut = key === 'responses';
    const options = {
      responsive:true, maintainAspectRatio:false,
      animation:matchMedia('(prefers-reduced-motion: reduce)').matches ? false : {duration:450},
      plugins:{legend:{display:false},tooltip:{backgroundColor:'#18394c',padding:12,callbacks:{label:ctx => `${ctx.label}: ${ctx.raw} kontrol`}}}
    };
    if (donut) options.cutout = '77%';
    else {
      options.indexAxis = 'y';
      options.scales = {
        x:{beginAtZero:true,suggestedMax:Math.max(1,...values.values),ticks:{precision:0,color:text(),font:{size:11}},grid:{color:grid()},border:{display:false}},
        y:{ticks:{color:text(),font:{size:12}},grid:{display:false},border:{display:false}}
      };
    }
    charts.push(new Chart(canvas, {
      type:donut ? 'doughnut' : 'bar',
      data:{labels:values.labels,datasets:[{label:'Kontrol',data:values.values,backgroundColor:palettes[key],borderWidth:0,borderRadius:donut?0:5,barThickness:16,hoverOffset:donut?3:0}]},
      options
    }));
  });
  new MutationObserver(() => charts.forEach(chart => {
    if (chart.options.scales?.x) {
      chart.options.scales.x.ticks.color = text();
      chart.options.scales.y.ticks.color = text();
      chart.options.scales.x.grid.color = grid();
    }
    chart.update('none');
  })).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
})();
