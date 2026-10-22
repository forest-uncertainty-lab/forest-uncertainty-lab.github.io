/* Responsive chart primitives. Domain calculations belong to the data adapter. */
(() => {
  const observers = new WeakMap();
  const number = (value, lang='en', digits=1) => value==null ? '—' : Number(value).toLocaleString(lang==='id'?'id-ID':'en-GB',{maximumFractionDigits:digits});
  function responsive(host, draw) {
    let entry = observers.get(host);
    if (!entry) {
      entry = {width:0,draw}; observers.set(host,entry);
      if (window.ResizeObserver) {
        entry.observer = new ResizeObserver(() => {
          const width = Math.round(host.getBoundingClientRect().width);
          if (width>0 && width!==entry.width) { entry.width=width; entry.draw(width); }
        });
        entry.observer.observe(host);
      }
    }
    entry.draw = draw;
    entry.width = Math.max(260,Math.round(host.getBoundingClientRect().width));
    draw(entry.width);
  }
  function bars(host, records, options) {
    responsive(host,width => {
      const {lang='en',selected,reference=0,unit='',onSelect} = options, left=12,right=15,rh=65,top=9,height=records.length*rh+43;
      const value = options.value, label = options.label;
      const max = Math.max(1,reference,...records.map(r=>Number.isFinite(r[value])?r[value]:0))*1.08;
      const x=d3.scaleLinear().domain([0,max]).range([left,width-right]);
      const svg=d3.create('svg').attr('viewBox',`0 0 ${width} ${height}`).attr('role','group').attr('aria-label',unit);
      svg.append('title').text(unit);
      if(reference>0) svg.append('line').attr('x1',x(reference)).attr('x2',x(reference)).attr('y1',top).attr('y2',height-37).attr('stroke','var(--muted)').attr('stroke-dasharray','3 3');
      records.forEach((r,i)=>{
        const y=top+i*rh,v=r[value],g=svg.append('g');
        if(onSelect) {
          g.attr('id','comparison-chart-'+r.key).attr('role','button').attr('tabindex',0).attr('aria-label',`${label(r)} · ${number(v,lang)} ${unit}`)
            .on('click',()=>onSelect(r)).on('keydown',ev=>{if(['Enter',' '].includes(ev.key)){ev.preventDefault();onSelect(r);}});
        }
        g.append('rect').attr('x',1).attr('y',y).attr('width',width-2).attr('height',rh-5).attr('fill',selected===r.key?'var(--surface-soft)':'transparent').attr('rx',4);
        g.append('text').attr('x',left).attr('y',y+17).attr('fill','var(--text)').attr('font-size',14).attr('font-weight',selected===r.key?700:500).text(label(r));
        g.append('text').attr('x',width-right).attr('y',y+17).attr('text-anchor','end').attr('fill','var(--text)').attr('font-size',14).text(number(v,lang));
        g.append('line').attr('x1',left).attr('x2',width-right).attr('y1',y+42).attr('y2',y+42).attr('stroke','var(--line)');
        if(v!=null && Number.isFinite(v)) {
          g.append('rect').attr('x',left).attr('y',y+29).attr('width',Math.max(0,x(v)-left)).attr('height',21).attr('fill',selected===r.key?'var(--fire)':'var(--muted)').attr('rx',2);
          if(v===0)g.append('circle').attr('cx',left).attr('cy',y+40).attr('r',3).attr('fill','var(--fire)');
        }
        g.append('title').text(`${label(r)} · ${number(v,lang)} ${unit}`);
      });
      const axis=svg.append('g').attr('transform',`translate(0,${height-31})`).call(d3.axisBottom(x).ticks(Math.max(2,Math.floor(width/110))).tickFormat(v=>number(v,lang)));
      axis.attr('color','var(--muted)').attr('font-size',11);axis.select('.domain').remove();
      host.replaceChildren(svg.node());
    });
  }
  function days(host, records, {lang='en',title=''}) {
    responsive(host,width=>{
      const height=220,m={left:12,right:12,top:35,bottom:30},x=d3.scaleBand().domain(records.map(r=>r.day)).range([m.left,width-m.right]).padding(.22),y=d3.scaleLinear().domain([0,24]).range([height-m.bottom,m.top]);
      const svg=d3.create('svg').attr('viewBox',`0 0 ${width} ${height}`).attr('role','img').attr('aria-label',title);
      svg.append('title').text(title);
      const pattern=svg.append('defs').append('pattern').attr('id','method-fill-hatch').attr('width',5).attr('height',5).attr('patternUnits','userSpaceOnUse').attr('patternTransform','rotate(45)');
      pattern.append('line').attr('x1',0).attr('x2',0).attr('y1',0).attr('y2',5).attr('stroke','var(--text)').attr('stroke-width',1);
      records.forEach(r=>{
        const value=r.value,px=x(r.day),h=value==null?4:height-m.bottom-y(value),py=height-m.bottom-h;
        svg.append('rect').attr('x',px).attr('y',py).attr('width',x.bandwidth()).attr('height',h).attr('fill',value==null?'none':r.kind==='estimate'?'var(--band)':'var(--fire)').attr('stroke',r.kind==='observed'?'none':r.kind==='estimate'?'var(--model)':'var(--muted)').attr('stroke-dasharray',r.kind==='observed'?'':'4 3');
        if(r.kind==='filled') svg.append('rect').attr('x',px).attr('y',py).attr('width',x.bandwidth()).attr('height',h).attr('fill','url(#method-fill-hatch)');
        svg.append('text').attr('x',px+x.bandwidth()/2).attr('y',py-8).attr('text-anchor','middle').attr('fill','var(--text)').attr('font-size',12).text(value==null?'?':number(value,lang));
        svg.append('text').attr('x',px+x.bandwidth()/2).attr('y',height-10).attr('text-anchor','middle').attr('fill','var(--muted)').attr('font-size',11).text((lang==='id'?'Hari ':'Day ')+r.day);
      });
      host.replaceChildren(svg.node());
    });
  }
  window.ChartKit = {number,bars,days};
})();
