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
    limits: { uz: 'Cheklovlar', en: 'Limits' }, smap: { uz: 'NASA SMAP: ildiz qatlami tuproq namligi (m³/m³), haftalik', en: 'NASA SMAP: root-zone soil moisture (m³/m³), weekly' }, et0: { uz: 'ET0 tuzatmasi', en: 'ET0 correction' },
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
        esc(t('smap').replace('{p}', dist.smap.drop_pct).replace('{y}', dist.smap.year)) + '</div></div>' : '') + '</div>';
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
        "<div><div class='l'>" + icon('coins', C.muted, 14) + ' ' + t('c_income') + "</div><div class='v' style='color:" + c.income_color + "'>" + esc(c.income[S.lang]) + '</div></div>' +
        "<div><div class='l'>" + icon('drop', C.muted, 14) + ' ' + t('c_water') + "</div><div class='v' style='color:" + c.water_color + "'>" + esc(c.water[S.lang]) + '</div></div>' +
        "<div><div class='l'>" + icon('shield', C.muted, 14) + ' ' + t('c_risk') + "</div><div class='v' style='color:" + c.risk_color + "'>" + esc(c.risk[S.lang]) + '</div></div></div></div>';
      if (S.must && plan.must_note) { h += "<div class='info'>" + esc(plan.must_note[S.lang]) + '</div>'; }
      h += "<div class='eyebrow'>" + t('why') + "</div><div class='card why'>" + esc(plan.why[S.lang]) + '</div>';
    }
    h += "<div class='note'>" + icon('alert', C.warn, 18) + '<div>' + t('disclaimer') + "</div></div>";
    document.getElementById('farmer').innerHTML = h;
  }

  // ------------------------------------------------------------------ expert view
  function hotChart(f) {
    var w = 760, hh = 240, pad = 34, vals = f.hot_series, yrs = f.years;
    var good = vals.filter(function (v) { return v !== null; });
    var lo = Math.floor(Math.min.apply(null, good) / 10) * 10, hi = Math.ceil(Math.max.apply(null, good) / 10) * 10;
    function X_(i) { return pad + i * (w - 2 * pad) / (yrs.length - 1); }
    function Y_(v) { return hh - pad - (v - lo) / (hi - lo) * (hh - 2 * pad); }
    var pts = vals.map(function (v, i) { return v === null ? null : X_(i).toFixed(1) + ',' + Y_(v).toFixed(1); }).filter(Boolean).join(' ');
    var i0 = yrs.indexOf(1991), i1 = yrs.indexOf(2005), j0 = yrs.indexOf(2011), j1 = yrs.length - 1;
    var s = "<svg class='chart' viewBox='0 0 " + w + ' ' + hh + "' width='100%' role='img' aria-label='" + x('climate') + "'>";
    [lo, (lo + hi) / 2, hi].forEach(function (v) { s += "<line x1='" + pad + "' x2='" + (w - pad) + "' y1='" + Y_(v) + "' y2='" + Y_(v) + "' stroke='#eee'/><text x='2' y='" + (Y_(v) + 4) + "'>" + v + '</text>'; });
    s += "<polyline points='" + pts + "' fill='none' stroke='" + C.bad + "' stroke-width='2'/>";
    s += "<line x1='" + X_(i0) + "' x2='" + X_(i1) + "' y1='" + Y_(f.hot_then) + "' y2='" + Y_(f.hot_then) + "' stroke='" + C.muted + "' stroke-width='3' stroke-dasharray='6 4'/>";
    s += "<line x1='" + X_(j0) + "' x2='" + X_(j1) + "' y1='" + Y_(f.hot_now) + "' y2='" + Y_(f.hot_now) + "' stroke='" + C.bad + "' stroke-width='3' stroke-dasharray='6 4'/>";
    s += "<text x='" + X_(0) + "' y='" + (hh - 8) + "'>" + yrs[0] + "</text><text x='" + (X_(j1) - 30) + "' y='" + (hh - 8) + "'>" + yrs[j1] + '</text>';
    s += "<text x='" + X_(i0) + "' y='" + (Y_(f.hot_then) - 8) + "'>1991–2005: " + f.hot_then + "</text><text x='" + X_(j0) + "' y='" + (Y_(f.hot_now) - 8) + "' style='fill:" + C.bad + "'>2011–2026: " + f.hot_now + '</text>';
    return s + '</svg>';
  }
  function smapChart(sm) {
    var w = 760, hh = 220, pad = 34, v = sm.weekly, n = v.length;
    var lo = Math.floor(Math.min.apply(null, v) * 50) / 50, hi = Math.ceil(Math.max.apply(null, v) * 50) / 50;
    function X_(i) { return pad + i * (w - 2 * pad) / (n - 1); }
    function Y_(y) { return hh - pad - (y - lo) / (hi - lo) * (hh - 2 * pad); }
    var s = "<svg class='chart' viewBox='0 0 " + w + ' ' + hh + "' width='100%' role='img' aria-label='SMAP'>";
    [lo, (lo + hi) / 2, hi].forEach(function (y) { s += "<line x1='" + pad + "' x2='" + (w - pad) + "' y1='" + Y_(y) + "' y2='" + Y_(y) + "' stroke='#eee'/><text x='0' y='" + (Y_(y) + 4) + "'>" + y.toFixed(2) + '</text>'; });
    s += "<polyline points='" + v.map(function (y, i) { return X_(i).toFixed(1) + ',' + Y_(y).toFixed(1); }).join(' ') + "' fill='none' stroke='" + C.green + "' stroke-width='2'/>";
    s += "<text x='" + pad + "' y='" + (hh - 8) + "'>" + sm.weekly_dates[0] + "</text><text x='" + (w - pad - 70) + "' y='" + (hh - 8) + "'>" + sm.weekly_dates[n - 1] + '</text>';
    return s + "</svg><div class='sub'>" + (S.lang === 'uz' ? 'Bahor (mart–aprel) ' : 'Spring (Mar–Apr) ') + sm.spring + ' → ' + (S.lang === 'uz' ? 'yoz (iyul–avgust) ' : 'summer (Jul–Aug) ') + sm.summer + ' m³/m³, ' + sm.year + ' (−' + sm.drop_pct + ' %)</div>';
  }
  function renderExpert() {
    var dist = D.districts[S.d], f = dist.facts, sc = scenario(), budget = D.water_levels[S.water];
    var h = "<div class='eyebrow'>DalaShift</div><div class='h'>" + esc(dist.name[S.lang]) + '</div>';
    h += seg('d', Object.keys(D.districts), S.d, function (k) { return D.districts[k].short[S.lang]; });
    h += " <div style='margin-top:8px'>" + seg('water', Object.keys(D.water_levels), S.water, function (k) { return t('w_' + k) + ' · ' + thousands(D.water_levels[k]) + ' m³/ha'; }) + '</div>';
    h += "<div class='card' style='margin-top:14px'><b>" + x('climate') + '</b>' + hotChart(f) +
      "<div class='sub'>NASA POWER (MERRA-2) · " + (S.lang === 'uz' ? 'mavsumdagi yomgʻir' : 'season rain') + ' ' + f.rain_then + ' → ' + f.rain_now + ' mm</div></div>';
    if (dist.smap) { h += "<div class='card' style='margin-top:14px'><b>" + x('smap') + '</b>' + smapChart(dist.smap) + "<div class='sub'>" + esc(D.smap_note[S.lang]) + '</div></div>'; }
    var et = dist.et0_correction;
    h += "<div class='card' style='margin-top:14px'><b>" + x('crops') + '</b>' + (et ? "<div class='sub'>" + x('et0') + ': × ' + et.factor + ' · ' + esc(et.label) + '</div>' : '') +
      "<div class='tablewrap'><table><tr><th>" + x('crop') + "</th><th class='num'>" + x('need') + '</th><th>' + x('fit') + '</th><th>' + x('season') + '</th><th>' + x('heat') + '</th></tr>' +
      dist.crops.slice().sort(function (a, b) { return a.need - b.need; }).map(function (c) {
        return '<tr><td>' + esc(D.crop_names[c.crop][S.lang]) + "</td><td class='num' style='color:" + (c.need > budget ? C.bad : 'inherit') + "'>" + thousands(c.need) +
          "</td><td class='" + (c.fits ? 'yes' : 'no') + "'>" + x(c.fits ? 'yes' : 'no') + '</td><td>' + esc(c.sow + ' → ' + c.harvest) + '</td><td>' + x(c.heat_risk) + '</td></tr>';
      }).join('') + '</table></div></div>';
    h += "<div class='card' style='margin-top:14px'><b>" + x('plans') + '</b> · ' + x('budget') + ' ' + thousands(budget) + " m³/ha<div class='tablewrap'><table><tr><th>" + x('plan') + '</th><th>' + x('seq') +
      "</th><th class='num'>" + x('usd') + "</th><th class='num'>" + x('water') + "</th><th class='num'>" + x('health') + '</th><th>' + x('vsusual') + '</th></tr>' +
      Object.keys(sc.plans).map(function (k) {
        var p = sc.plans[k];
        return '<tr><td>' + (k === 'least_harm' ? (S.lang === 'uz' ? 'Eng kam zararli' : 'Least harmful') : t('plan_' + k)) + '</td><td>' +
          p.years.map(function (y) { return esc(y.name[S.lang]); }).join(' → ') + "</td><td class='num'>" + thousands(p.usd_per_year[0]) + '–' + thousands(p.usd_per_year[1]) +
          "</td><td class='num'>" + thousands(p.water_per_year) + "</td><td class='num'>" + p.health + '/10</td><td>' + esc(p.cmp.income[S.lang]) + ' · ' + esc(p.cmp.water[S.lang]) + '</td></tr>';
      }).join('') + '</table></div>' + (sc.status !== 'ok' ? "<div class='alert'>" + esc(sc.error[S.lang]) + '</div>' : '') + '</div>';
    h += "<div class='card limits' style='margin-top:14px'><b>" + x('limits') + '</b>' + D.limits[S.lang] + '</div>';
    h += "<p><a class='maplink' href='deck/index.html'>" + x('deck') + ' →</a></p>';
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
  document.addEventListener('change', function (e) { if (e.target.id === 'must') { S.must = e.target.checked; render(); } });

  fetch('data.json').then(function (r) { return r.json(); }).then(function (data) {
    D = data;
    if (!D.districts[S.d]) { S.d = 'Karshi'; }
    if (D.plans.indexOf(S.plan) < 0) { S.plan = 'balanced'; }
    render();
  }).catch(function () {
    document.getElementById('farmer').innerHTML = "<div class='alert'>data.json could not be loaded. Open this site through a web server (e.g. Netlify), not as a local file.</div>";
  });
})();
