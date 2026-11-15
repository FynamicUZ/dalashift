/* DalaShift static site: renders web/data.json (exported by scripts/export_static.py with the same
   engine and formatting as the Streamlit app). No framework, no server. */
(function () {
  'use strict';
  var D = null;
  var S = { lang: 'uz', tab: 'farmer', d: 'Karshi', water: 'normal', must: false, plan: 'balanced' };
  try { var saved = JSON.parse(localStorage.getItem('dalashift') || '{}'); Object.assign(S, saved); } catch (e) { /* storage off */ }
  function save() { try { localStorage.setItem('dalashift', JSON.stringify(S)); } catch (e) { /* ignore */ } }

  var C = { ok: '#2e7d4f', warn: '#c98a1b', bad: '#c0442f', muted: '#6b716d', green: '#1f5f3f' };
  var ICON = {
    pin: "<path d='M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z'/><circle cx='12' cy='10' r='3'/>",
    thermo: "<path d='M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z'/>",
    rain: "<path d='M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242'/><path d='M16 14v6'/><path d='M8 14v6'/><path d='M12 16v6'/>",
    drop: "<path d='M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z'/>",
    coins: "<circle cx='8' cy='8' r='6'/><path d='M18.09 10.37A6 6 0 1 1 10.34 18'/><path d='M7 6h1v4'/>",
    shield: "<path d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/>",
    sprout: "<path d='M7 20h10'/><path d='M10 20c5.5-2.5.8-6.4 3-10'/><path d='M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z'/><path d='M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z'/>",
    alert: "<path d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z'/><path d='M12 9v4'/><path d='M12 17h.01'/>",
    map: "<path d='M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z'/><path d='M15 5.764v15'/><path d='M9 3.236v15'/>"
  };
  function icon(n, color, size) {
    size = size || 18;
    return "<svg xmlns='http://www.w3.org/2000/svg' width='" + size + "' height='" + size + "' viewBox='0 0 24 24' fill='none' stroke='" +
      (color || C.green) + "' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" + ICON[n] + "</svg>";
  }
  var X = { // expert-tab labels
    climate: { uz: 'Jazirama kunlar (Tmax > 35 °C), 1991–2026', en: 'Very hot days (Tmax > 35 °C), 1991–2026' },
    crops: { uz: 'Ekinlarning sof sugʻorish ehtiyoji (FAO-56, ET0 tuzatmasi bilan)', en: 'Net irrigation need per crop (FAO-56, with ET0 correction)' },
    crop: { uz: 'Ekin', en: 'Crop' }, need: { uz: 'm³/ga', en: 'm³/ha' }, fit: { uz: 'Iqlimga mos', en: 'Climate fit' },
    season: { uz: 'Ekish → yigʻim', en: 'Sow → harvest' }, heat: { uz: 'Issiqlik xavfi', en: 'Heat risk' },
    yes: { uz: 'ha', en: 'yes' }, no: { uz: 'yoʻq', en: 'no' },
    plans: { uz: 'Rejalar (tanlangan suv va majburiyat bilan)', en: 'Plans (with the selected water and obligation)' },
    plan: { uz: 'Reja', en: 'Plan' }, seq: { uz: '5 yil', en: '5 years' },
    usd: { uz: 'Foyda, USD/ga/yil (±15 %)', en: 'Profit, USD/ha/yr (±15 %)' }, water: { uz: 'Suv, m³/ga/yil', en: 'Water, m³/ha/yr' },
    health: { uz: 'Salomatlik', en: 'Health' }, vsusual: { uz: 'Bugʻdoy ↔ paxtaga nisbatan', en: 'vs wheat ↔ cotton' },
    limits: { uz: 'Cheklovlar', en: 'Limits' }, hls: { uz: 'NASA/USGS HLS: yashillik (NDVI), haftalik', en: 'NASA/USGS HLS: greenness (NDVI), weekly' }, smap: { uz: 'NASA SMAP: ildiz qatlami tuproq namligi (m³/m³), haftalik', en: 'NASA SMAP: root-zone soil moisture (m³/m³), weekly' }, et0: { uz: 'ET0 tuzatmasi', en: 'ET0 correction' },
    deck: { uz: 'Taqdimotni ochish', en: 'Open the pitch deck' }, budget: { uz: 'Suv byudjeti', en: 'Water budget' },
    low: { uz: 'past', en: 'low' }, medium: { uz: 'oʻrta', en: 'medium' }, high: { uz: 'yuqori', en: 'high' }
  };
  function t(k) { return D.ui[k][S.lang]; }
  function x(k) { return X[k][S.lang]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmt(n) { var s = (Math.round(n * 10) / 10).toString(); return S.lang === 'uz' ? s.replace('.', ',') : s; }
  function thousands(n) { return Math.round(n).toLocaleString('en-US').replace(/,/g, S.lang === 'uz' ? ' ' : ','); }

  function seg(id, items, value, label) {
    return "<div class='seg' data-seg='" + id + "'>" + items.map(function (it) {
      return "<button data-v='" + it + "' class='" + (it === value ? 'on' : '') + "'>" + esc(label(it)) + '</button>';
    }).join('') + '</div>';
  }
  function sparkline(vals, w, h) {
    vals = vals.filter(function (v) { return v !== null; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals), span = (hi - lo) || 1;
    var pts = vals.map(function (v, i) { return (i * w / (vals.length - 1)).toFixed(1) + ',' + (h - 2 - (v - lo) / span * (h - 4)).toFixed(1); }).join(' ');
    return "<svg width='" + w + "' height='" + h + "' viewBox='0 0 " + w + ' ' + h + "' style='margin-top:4px'><polyline points='" + pts +
      "' fill='none' stroke='" + C.bad + "' stroke-width='1.5' stroke-linejoin='round'/></svg>";
  }
  function scenario() { return D.districts[S.d].scenarios[S.water + '|' + (S.must ? 1 : 0)]; }
  function currentPlan(sc) { return sc.status === 'ok' ? sc.plans[S.plan] : sc.plans.least_harm; }

  // ------------------------------------------------------------------ farmer view
  function renderFarmer() {
    var dist = D.districts[S.d], f = dist.facts, budget = D.water_levels[S.water];
    var dh = f.hot_now - f.hot_then, dr = f.rain_now - f.rain_then;
    var h = '';
    h += "<div class='eyebrow'>" + t('eyebrow1') + "</div><div class='h'>" + t('step1') + '</div>';
    h += seg('d', Object.keys(D.districts), S.d, function (k) { return D.districts[k].short[S.lang]; });
    h += "<div class='grid2'><div class='card'><div class='district'>" + icon('pin', C.green, 20) + ' ' + esc(dist.name[S.lang]) + '</div>' +
      "<div class='sub'>" + t('since') + "</div><div class='facts'>" +
      "<div class='fact'><div class='l'>" + icon('thermo', C.muted, 15) + ' ' + t('hot') + "</div><div class='v'>" + f.hot_then + ' → ' + f.hot_now +
      " <span class='d' style='color:" + (dh > 0 ? C.bad : C.ok) + "'>" + (dh > 0 ? '+' : '') + dh + '</span></div>' + sparkline(f.hot_series, 130, 26) + '</div>' +
      "<div class='fact'><div class='l'>" + icon('rain', C.muted, 15) + ' ' + t('rain') + "</div><div class='v'>" + f.rain_then + ' → ' + f.rain_now + ' ' + t('mm') +
      " <span class='d' style='color:" + (dr < 0 ? C.bad : C.ok) + "'>" + (dr > 0 ? '+' : '') + dr + '</span></div></div>' +
      "<div class='fact'><div class='l'>" + icon('drop', C.muted, 15) + ' ' + t('budget') + "</div><div class='v'>" + fmt(budget / 1000) + ' ' + t('k_tonnes') + '</div></div>' +
      '</div>' + (dist.smap ? "<div class='smap'>" + icon('drop', C.green, 15) + '<div>' +
        esc(t('smap').replace('{p}', dist.smap.drop_pct).replace('{y}', dist.smap.year)) + '</div></div>' : '') +
      (dist.hls ? "<div class='smap'>" + icon('sprout', C.green, 15) + '<div>' + esc(dist.hls_line[S.lang]) + '</div></div>' : '') + '</div>';
    h += "<div class='controls'><div class='lbl'>" + t('q_water') + '</div>' +
      seg('water', Object.keys(D.water_levels), S.water, function (k) { return t('w_' + k); }) +
      "<label class='switch'><input type='checkbox' id='must'" + (S.must ? ' checked' : '') + "><span class='knob'></span><span>" + t('q_must') + '</span></label>' +
      "<div class='help'>" + t('must_help') + '</div>' +
      "<a class='maplink' target='_blank' rel='noopener' href='https://www.openstreetmap.org/?mlat=" + dist.lat + '&mlon=' + dist.lon + '#map=9/' + dist.lat + '/' + dist.lon + "'>" +
      icon('map', C.green, 16) + ' ' + (S.lang === 'uz' ? 'Xaritada koʻrish' : 'Show on map') + '</a></div></div>';

    var sc = scenario(), plan = currentPlan(sc);
    h += "<div class='eyebrow'>" + t('eyebrow2') + "</div><div class='h'>" + t('plan_h') + '</div>';
    if (sc.status !== 'ok') { h += "<div class='alert'>" + esc(sc.error[S.lang]) + '</div>'; }
    else {
      h += "<div class='sub' style='margin-bottom:6px'>" + t('q_goal') + '</div>' +
        seg('plan', D.plans, S.plan, function (k) { return t('plan_' + k); });
    }
    if (plan) {
      h += "<div class='card' style='margin-top:12px'><div class='steps'>" + plan.years.map(function (y) {
        return "<div class='step'><div class='dot' style='background:" + y.dot + "'></div><div class='y'>" +
          (S.lang === 'uz' ? y.year + '-yil' : 'Year ' + y.year) + "</div><div class='c'>" + esc(y.name[S.lang]) + "</div><div class='m'>" +
          esc(y.months[S.lang]) + "</div><div class='wbar' title='" + thousands(y.water) + "'><div style='width:" + (y.share * 100).toFixed(0) +
          '%;background:' + y.water_color + "'></div></div></div>";
      }).join('') + '</div>';
      h += "<div style='margin-top:18px'><div class='sub'>" + t('income') + "</div><div class='money'>≈ " + fmt(plan.income_low) + ' ' + t('mln') +
        "</div><div class='sub'>" + t('conservative') + ' · ' + (S.lang === 'uz' ? 'oraliq' : 'range') + ' ±15 %: ' + fmt(plan.band_lo) + '–' + fmt(plan.band_hi) + ' mln</div></div>';
      var c = plan.cmp;
      h += "<div class='cmp'><div><div class='l'>" + t('vs_usual') + "</div><div class='v' style='font-size:.95rem'>" + esc(c.usual[S.lang]) + '</div>' +
        (c.usual_short ? "<div class='short'>" + esc(c.usual_short[S.lang]) + '</div>' : '') + '</div>' +
        "<div><div class='l'>" + icon('coins', C.muted, 14) + ' ' + t('c_income') + "</div><div class='v' style='font-size:1rem;color:" + c.income_color + "'>" + esc(c.income[S.lang]) + '</div></div>' +
        "<div><div class='l'>" + icon('drop', C.muted, 14) + ' ' + t('c_water') + "</div><div class='v' style='font-size:1rem;color:" + c.water_color + "'>" + esc(c.water[S.lang]) + '</div></div>' +
        "<div><div class='l'>" + icon('shield', C.muted, 14) + ' ' + t('c_risk') + "</div><div class='v' style='color:" + c.risk_color + "'>" + esc(c.risk[S.lang]) + "</div><div class='sub' style='font-size:.78rem'>" + esc(c.risk_reason[S.lang]) + '</div></div></div></div>';
      if (S.must && plan.must_note) { h += "<div class='info'>" + esc(plan.must_note[S.lang]) + '</div>'; }
      h += "<div class='eyebrow'>" + t('why') + "</div><div class='card why'>" + esc(plan.why[S.lang]) + '</div>';
    }
    h += "<div class='note'>" + icon('alert', C.warn, 18) + '<div>' + t('disclaimer') + "</div></div>";
    document.getElementById('farmer').innerHTML = h;
  }

  // ------------------------------------------------------------------ expert view (dense, data-focused)
  var EC = { hot: '#a5533f', smap: '#3d6e8f', ndvi: '#6b8a3a', ref: '#8a8f8b', grid: '#ecebe6' };
  // line chart with y-axis title, year ticks and optional dashed reference segments
  function lineChart(o) {
    var w = 640, hh = 230, l = 46, r = 12, t0 = 12, b = 34, v = o.values, n = v.length;
    var good = v.filter(function (q) { return q !== null; });
    var lo = o.lo !== undefined ? o.lo : Math.min.apply(null, good), hi = o.hi !== undefined ? o.hi : Math.max.apply(null, good);
    var pad = (o.lo !== undefined) ? 0 : ((hi - lo) * 0.08 || 1); lo -= pad; hi += pad;
    function X_(i) { return l + i * (w - l - r) / (n - 1); }
    function Y_(q) { return t0 + (hi - q) / (hi - lo) * (hh - t0 - b); }
    var s = "<svg class='chart' viewBox='0 0 " + w + ' ' + hh + "' width='100%' role='img' aria-label='" + esc(o.title) + "'>";
    for (var k = 0; k <= 4; k++) {
      var q = lo + (hi - lo) * k / 4;
      s += "<line x1='" + l + "' x2='" + (w - r) + "' y1='" + Y_(q).toFixed(1) + "' y2='" + Y_(q).toFixed(1) + "' stroke='" + EC.grid + "'/>" +
        "<text x='" + (l - 6) + "' y='" + (Y_(q) + 4).toFixed(1) + "' text-anchor='end'>" + q.toFixed(o.digits || 0) + '</text>';
    }
    var lastYear = null;
    o.dates.forEach(function (d, i) {
      var y = String(d).slice(0, 4);
      if (y !== lastYear && (!o.yearStep || i === 0 || (+y) % o.yearStep === 0)) {
        s += "<line x1='" + X_(i).toFixed(1) + "' x2='" + X_(i).toFixed(1) + "' y1='" + (hh - b) + "' y2='" + (hh - b + 4) + "' stroke='" + EC.ref + "'/>" +
          "<text x='" + X_(i).toFixed(1) + "' y='" + (hh - b + 16) + "' text-anchor='middle'>" + y + '</text>';
      }
      lastYear = y;
    });
    s += "<line x1='" + l + "' x2='" + (w - r) + "' y1='" + (hh - b) + "' y2='" + (hh - b) + "' stroke='" + EC.ref + "'/>";
    s += "<text transform='rotate(-90)' x='" + (-(t0 + (hh - b)) / 2) + "' y='12' text-anchor='middle' class='ax'>" + esc(o.ylabel) + '</text>';
    (o.refs || []).forEach(function (rf) {
      s += "<line x1='" + X_(rf.i0) + "' x2='" + X_(rf.i1) + "' y1='" + Y_(rf.y) + "' y2='" + Y_(rf.y) + "' stroke='" + rf.color + "' stroke-width='2' stroke-dasharray='5 4'/>" +
        "<text x='" + (X_(rf.i0) + 4) + "' y='" + (Y_(rf.y) - 6) + "' class='lbl' style='fill:" + rf.color + "'>" + esc(rf.label) + '</text>';
    });
    var pts = v.map(function (q, i) { return q === null ? null : X_(i).toFixed(1) + ',' + Y_(q).toFixed(1); }).filter(Boolean).join(' ');
    s += "<polyline points='" + pts + "' fill='none' stroke='" + o.color + "' stroke-width='1.8' stroke-linejoin='round'/>";
    return s + '</svg>';
  }
  function chartCard(title, chart, notes) {
    return "<section class='xcard'><h3>" + esc(title) + '</h3>' + chart + notes.map(function (nt) { return "<p class='xnote'>" + nt + '</p>'; }).join('') + '</section>';
  }
  function sel(id, items, value, label) {
    return "<select data-sel='" + id + "'>" + items.map(function (it) {
      return "<option value='" + it + "'" + (it === value ? ' selected' : '') + '>' + esc(label(it)) + '</option>';
    }).join('') + '</select>';
  }
  function renderExpert() {
    var dist = D.districts[S.d], f = dist.facts, sc = scenario(), budget = D.water_levels[S.water], uz = S.lang === 'uz';
    var h = "<div class='xhead'><h2>" + esc(dist.name[S.lang]) + "</h2><div class='xctl'>" +
      sel('d', Object.keys(D.districts), S.d, function (k) { return D.districts[k].short[S.lang]; }) +
      sel('water', Object.keys(D.water_levels), S.water, function (k) { return t('w_' + k) + ' · ' + thousands(D.water_levels[k]) + ' m³/ha'; }) +
      '</div></div>';
    var rows = [[uz ? 'Jazirama kunlar (>35 °C), kun/yil' : 'Days > 35 °C, per year', f.hot_then, f.hot_now, 'NASA POWER'],
      [uz ? 'Mavsumdagi yomgʻir (apr–okt), mm' : 'Season rain (Apr–Oct), mm', f.rain_then, f.rain_now, 'NASA POWER']];
    h += "<section class='xcard'><h3>" + (uz ? 'Asosiy koʻrsatkichlar' : 'Key numbers') + "</h3><div class='tablewrap'><table class='xt'><tr><th></th><th class='num'>1991–2005</th><th class='num'>2011–2026</th><th>" + (uz ? 'Manba' : 'Source') + '</th></tr>' +
      rows.map(function (r) { return '<tr><td>' + r[0] + "</td><td class='num'>" + r[1] + "</td><td class='num'>" + r[2] + '</td><td>' + r[3] + '</td></tr>'; }).join('') +
      (dist.smap ? '<tr><td>' + (uz ? 'Ildiz qatlami namligi, bahor → yoz, m³/m³' : 'Root-zone soil moisture, spring → summer, m³/m³') + "</td><td class='num'>" + dist.smap.spring + "</td><td class='num'>" + dist.smap.summer + ' (−' + dist.smap.drop_pct + ' %, ' + dist.smap.year + ')</td><td>NASA SMAP L4</td></tr>' : '') +
      (dist.hls ? '<tr><td>' + (uz ? 'NDVI choʻqqisi' : 'NDVI peak') + "</td><td class='num'>–</td><td class='num'>" + dist.hls.peak + ' (' + dist.hls.peak_date + ')</td><td>NASA/USGS HLS</td></tr>' : '') +
      (dist.et0_correction ? '<tr><td>' + x('et0') + "</td><td class='num'>–</td><td class='num'>× " + dist.et0_correction.factor + '</td><td>' + esc(dist.et0_correction.label) + '</td></tr>' : '') +
      '</table></div></section>';
    h += "<div class='xgrid'>";
    var yrs = f.years, i0 = yrs.indexOf(1991), i1 = yrs.indexOf(2005), j0 = yrs.indexOf(2011), j1 = yrs.length - 1;
    h += chartCard(x('climate'), lineChart({ title: x('climate'), dates: yrs, values: f.hot_series, color: EC.hot, ylabel: uz ? 'kun/yil' : 'days/yr', yearStep: 5,
      refs: [{ i0: i0, i1: i1, y: f.hot_then, color: EC.ref, label: '1991–2005: ' + f.hot_then }, { i0: j0, i1: j1, y: f.hot_now, color: EC.hot, label: '2011–2026: ' + f.hot_now }] }),
      ['NASA POWER daily (MERRA-2), T2M_MAX > 35 °C. ' + (uz ? 'Mavsumdagi yomgʻir ' : 'Season rain ') + f.rain_then + ' → ' + f.rain_now + ' mm.']);
    if (dist.smap) {
      h += chartCard(x('smap'), lineChart({ title: 'SMAP', dates: dist.smap.weekly_dates, values: dist.smap.weekly, color: EC.smap, ylabel: 'm³/m³', digits: 2 }),
        [esc(D.smap_note[S.lang])]);
    }
    if (dist.hls) {
      h += chartCard(x('hls'), lineChart({ title: 'NDVI', dates: dist.hls.weekly_dates, values: dist.hls.weekly, color: EC.ndvi, ylabel: 'NDVI', digits: 1, lo: 0, hi: 1 }),
        [esc(dist.hls_line[S.lang]), esc(D.hls_note[S.lang])]);
    }
    if (dist.has_ecostress) { h += "<section class='xcard'><h3>NASA ECOSTRESS</h3><p class='xnote'>" + esc(D.ecostress_note[S.lang]) + '</p></section>'; }
    h += '</div>';
    h += "<section class='xcard'><h3>" + x('crops') + "</h3><div class='tablewrap'><table class='xt'><tr><th>" + x('crop') + "</th><th class='num'>" + x('need') + '</th><th>' + x('fit') + '</th><th>' + x('season') + '</th><th>' + x('heat') + '</th></tr>' +
      dist.crops.slice().sort(function (a, b) { return a.need - b.need; }).map(function (c) {
        return '<tr><td>' + esc(D.crop_names[c.crop][S.lang]) + "</td><td class='num" + (c.need > budget ? ' over' : '') + "'>" + thousands(c.need) +
          "</td><td class='" + (c.fits ? 'yes' : 'no') + "'>" + x(c.fits ? 'yes' : 'no') + '</td><td>' + esc(c.sow + ' → ' + c.harvest) + '</td><td>' + x(c.heat_risk) + '</td></tr>';
      }).join('') + "</table></div><p class='xnote'>FAO-56 · " + (uz ? 'qizil: suv byudjetidan koʻp' : 'red: above the water budget') + ' (' + thousands(budget) + ' m³/ha)</p></section>';
    h += "<section class='xcard'><h3>" + x('plans') + "</h3><div class='tablewrap'><table class='xt'><tr><th>" + x('plan') + '</th><th>' + x('seq') +
      "</th><th class='num'>" + x('usd') + "</th><th class='num'>" + x('water') + "</th><th class='num'>" + x('health') + '</th><th>' + x('vsusual') + '</th></tr>' +
      Object.keys(sc.plans).map(function (k) {
        var p = sc.plans[k];
        return '<tr><td>' + (k === 'least_harm' ? (uz ? 'Eng kam zararli' : 'Least harmful') : t('plan_' + k)) + '</td><td>' +
          p.years.map(function (y) { return esc(y.name[S.lang]); }).join(' → ') + "</td><td class='num'>" + thousands(p.usd_per_year[0]) + '–' + thousands(p.usd_per_year[1]) +
          "</td><td class='num'>" + thousands(p.water_per_year) + "</td><td class='num'>" + p.health + "/10</td><td class='num'>" + esc(p.cmp.income[S.lang]) + ' · ' + esc(p.cmp.water[S.lang]) + '</td></tr>';
      }).join('') + '</table></div>' + (sc.status !== 'ok' ? "<p class='xnote' style='color:" + C.bad + "'>" + esc(sc.error[S.lang]) + '</p>' : '') +
      "<p class='xnote'>" + (uz ? 'Barcha 5 yillik ketma-ketliklar tekshirilgan; foyda ±15 % taxminiy; bugʻdoy ↔ paxtaga nisbatan.' : 'Every 5-year sequence checked; profit ±15 % estimate; compared with wheat ↔ cotton.') + '</p></section>';
    h += "<section class='xcard limits'><h3>" + x('limits') + '</h3>' + D.limits[S.lang] + '</section>';
    h += "<p class='xnote'><a href='deck/index.html'>" + x('deck') + " →</a> · <a href='https://github.com/FynamicUZ/dalashift'>GitHub</a></p>";
    document.getElementById('expert').innerHTML = h;
  }

  // ------------------------------------------------------------------ shell
  function render() {
    document.documentElement.lang = S.lang;
    document.querySelectorAll('#lang button').forEach(function (b) { b.classList.toggle('on', b.dataset.v === S.lang); });
    document.querySelectorAll('#tabs button, #tabs a').forEach(function (b) {
      if (b.dataset[S.lang]) { b.textContent = b.dataset[S.lang]; }
      if (b.dataset.v) { b.classList.toggle('on', b.dataset.v === S.tab); }
    });
    document.getElementById('farmer').hidden = S.tab !== 'farmer';
    document.getElementById('expert').hidden = S.tab !== 'expert';
    if (S.tab === 'farmer') { renderFarmer(); } else { renderExpert(); }
    document.getElementById('foot').textContent = D.credits[S.lang] + ' · Team KarPS · NASA Space Apps 2026';
    save();
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) { return; }
    var group = b.closest('[data-seg]');
    if (b.closest('#lang')) { S.lang = b.dataset.v; }
    else if (b.closest('#tabs')) { S.tab = b.dataset.v; }
    else if (group) { S[group.dataset.seg] = b.dataset.v; }
    else { return; }
    render();
  });
  document.addEventListener('change', function (e) {
    if (e.target.id === 'must') { S.must = e.target.checked; render(); }
    else if (e.target.dataset && e.target.dataset.sel) { S[e.target.dataset.sel] = e.target.value; render(); }
  });

  fetch('data.json').then(function (r) { return r.json(); }).then(function (data) {
    D = data;
    if (!D.districts[S.d]) { S.d = 'Karshi'; }
    if (D.plans.indexOf(S.plan) < 0) { S.plan = 'balanced'; }
    render();
  }).catch(function () {
    document.getElementById('farmer').innerHTML = "<div class='alert'>data.json could not be loaded. Open this site through a web server (e.g. Netlify), not as a local file.</div>";
  });
})();
