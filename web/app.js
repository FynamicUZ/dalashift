/* DalaShift static site: renders web/data.json (exported by scripts/export_static.py with the same
   engine and formatting as the Streamlit app). No framework, no server.
   Map: Leaflet 1.9.4 (cdnjs) with OpenStreetMap tiles. */
(function () {
  'use strict';
  var D = null;
  var S = { lang: 'uz', tab: 'farmer', d: 'Karshi', budget: 8000, must: false, plan: 'balanced' };
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
    satellite: "<path d='m13.5 6.5-3.148-3.148a1.205 1.205 0 0 0-1.704 0L6.352 5.648a1.205 1.205 0 0 0 0 1.704L9.5 10.5'/><path d='M16.5 7.5 19 5'/><path d='m17.5 10.5 3.148 3.148a1.205 1.205 0 0 1 0 1.704l-2.296 2.296a1.205 1.205 0 0 1-1.704 0L13.5 14.5'/><path d='M9 21a6 6 0 0 0-6-6'/><path d='M9.352 10.648a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l4.296-4.296a1.205 1.205 0 0 0 0-1.704l-2.296-2.296a1.205 1.205 0 0 0-1.704 0z'/>",
    locate: "<line x1='2' x2='5' y1='12' y2='12'/><line x1='19' x2='22' y1='12' y2='12'/><line x1='12' x2='12' y1='2' y2='5'/><line x1='12' x2='12' y1='19' y2='22'/><circle cx='12' cy='12' r='7'/><circle cx='12' cy='12' r='3'/>"
  };
  function icon(n, color, size) {
    size = size || 18;
    return "<svg xmlns='http://www.w3.org/2000/svg' width='" + size + "' height='" + size + "' viewBox='0 0 24 24' fill='none' stroke='" +
      (color || C.green) + "' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" + ICON[n] + "</svg>";
  }
  // farmer-tab texts (short on purpose; explanations live in "?" tooltips)
  var F = {
    where: { uz: 'Dalangiz qayerda?', en: 'Where is your field?' },
    locate: { uz: 'Mening joylashuvim', en: 'My location' },
    locating: { uz: 'Joylashuv aniqlanmoqda…', en: 'Finding your location…' },
    nearest: { uz: 'Sizga eng yaqin: {d} (~{k} km)', en: 'Nearest to you: {d} (~{k} km)' },
    denied: { uz: 'Joylashuvga ruxsat berilmadi — tumanni qoʻlda tanlang.', en: 'Location not allowed — pick your district by hand.' },
    nogeo: { uz: 'Bu brauzer joylashuvni aniqlay olmaydi.', en: 'This browser cannot find your location.' },
    hot: { uz: 'Jazirama kunlar yiliga', en: 'Very hot days a year' },
    hot_tip: { uz: 'Harorat 35 °C dan oshgan kunlar. 1991–2005 va 2011–2026 yillar oʻrtachasi, NASA POWER.', en: 'Days above 35 °C. Average of 1991–2005 vs 2011–2026, NASA POWER.' },
    rain: { uz: 'Mavsumda yomgʻir', en: 'Season rain' },
    rain_tip: { uz: 'Aprel–oktabr yogʻingarchiligi, 1991–2005 va 2011–2026, NASA POWER.', en: 'April–October rain, 1991–2005 vs 2011–2026, NASA POWER.' },
    soil: { uz: 'Yozda tuproq {p} % quriydi', en: 'Soil dries {p} % by summer' },
    green: { uz: 'Eng yashil oy: {m}', en: 'Greenest month: {m}' },
    plan_h: { uz: 'Keyingi besh yil uchun reja', en: 'Plan for the next five years' },
    water: { uz: 'Suvingiz', en: 'Your water' },
    water_tip: { uz: 'Dalangizga bir yilda keladigan sugʻorish suvi, gektariga. Kam / Oʻrtacha / Koʻp = 6 000 / 8 000 / 12 000 m³/ga.', en: 'Irrigation water your field gets in a year, per hectare. Little / Medium / Plenty = 6,000 / 8,000 / 12,000 m³/ha.' },
    k_t: { uz: 'm³/ga', en: 'm³/ha' },   // water unit on farmer screens (never tonnes)
    must: { uz: 'Paxta/bugʻdoy majburiy', en: 'Cotton/wheat required' },
    must_tip: { uz: 'Davlat buyurtmasi boʻlsa yoqing: rejada 5 yildan kamida 2 yil paxta va 2 yil bugʻdoy boʻladi.', en: 'Switch on if you have a state order: at least 2 years of cotton and 2 of wheat in 5.' },
    goal: { uz: 'Maqsad', en: 'Goal' },
    income: { uz: 'Daromad, gektariga yiliga', en: 'Income per hectare per year' },
    income_tip: { uz: 'Ehtiyotkor taxmin: ±15 % oraliqning pastki chegarasi. Xarajatlar taxminiy.', en: 'Cautious estimate: the low end of a ±15 % range. Costs are estimates.' },
    usual_tip: { uz: 'Odatiy = Oʻzbekistonda keng tarqalgan kuzgi bugʻdoy ↔ paxta almashlab ekish.', en: 'Usual = winter wheat ↔ cotton, the common rotation in Uzbekistan.' },
    risk_tip: { uz: 'Gullash paytidagi jazirama kunlar va sovuq tufayli hosil kamayish ehtimoli.', en: 'Chance of yield loss from very hot days at flowering and from frost.' },
    why: { uz: 'Nega bu reja?', en: 'Why this plan?' },
    note: { uz: 'Taxminiy hisob. Agronomingiz bilan maslahatlashing.', en: 'Estimates only. Talk to your agronomist.' },
    calc_title: { uz: 'Reja hisoblanmoqda', en: 'Building your plan' },
    calc_skip: { uz: 'Oʻtkazib yuborish', en: 'Skip' },
    s1: { uz: 'NASA POWER: 35 yillik iqlim maʼlumotlari', en: 'NASA POWER: 35 years of daily climate' },
    s2: { uz: 'NASA SMAP: tuproq namligi', en: 'NASA SMAP: soil moisture' },
    s3: { uz: 'NASA HLS: dala yashilligi', en: 'NASA HLS: field greenness' },
    s4: { uz: '5 yillik ketma-ketliklar tekshirilmoqda', en: 'Checking 5-year sequences' },
    s5: { uz: 'Suv balansi va daromad', en: 'Water balance and income' },
    days: { uz: 'kun', en: 'days' }, years: { uz: 'yil', en: 'years' },
    months: { uz: ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr'],
              en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'] }
  };
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
    limits: { uz: 'Cheklovlar', en: 'Limits' }, hls: { uz: 'NASA/USGS HLS: yashillik (NDVI), haftalik', en: 'NASA/USGS HLS: greenness (NDVI), weekly' },
    smap: { uz: 'NASA SMAP: ildiz qatlami tuproq namligi (m³/m³), haftalik', en: 'NASA SMAP: root-zone soil moisture (m³/m³), weekly' }, et0: { uz: 'ET0 tuzatmasi', en: 'ET0 correction' },
    deck: { uz: 'Taqdimotni ochish', en: 'Open the pitch deck' }, budget: { uz: 'Suv byudjeti', en: 'Water budget' },
    low: { uz: 'past', en: 'low' }, medium: { uz: 'oʻrta', en: 'medium' }, high: { uz: 'yuqori', en: 'high' }
  };
  function t(k) { return D.ui[k][S.lang]; }
  function f(k) { return F[k][S.lang]; }
  function x(k) { return X[k][S.lang]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmt(n) { var s = (Math.round(n * 10) / 10).toString(); return S.lang === 'uz' ? s.replace('.', ',') : s; }
  function thousands(n) { return Math.round(n).toLocaleString('en-US').replace(/,/g, S.lang === 'uz' ? ' ' : ','); }
  function tip(text) { return "<span class='tip' tabindex='0' role='note' aria-label='" + esc(text) + "'>?<span class='tipbox'>" + esc(text) + '</span></span>'; }

  function seg(id, items, value, label) {
    return "<div class='seg' data-seg='" + id + "'>" + items.map(function (it) {
      return "<button data-v='" + it + "' class='" + (String(it) === String(value) ? 'on' : '') + "'>" + esc(label(it)) + '</button>';
    }).join('') + '</div>';
  }
  function scenario() { return D.districts[S.d].scenarios[S.budget + '|' + (S.must ? 1 : 0)]; }
  function currentPlan(sc) { return sc.status === 'ok' ? sc.plans[S.plan] : sc.plans.least_harm; }
  function levelOf(b) { var lv = D.water_levels; return Object.keys(lv).filter(function (k) { return lv[k] === b; })[0] || null; }

  // ------------------------------------------------------------------ map (Leaflet, kept alive across renders)
  var mapEl = null, map = null, marker = null;
  function ensureMap() {
    if (!window.L) { return null; }
    if (!mapEl) {
      mapEl = document.createElement('div');
      mapEl.className = 'mapbox loading';
      mapEl.innerHTML = "<div class='skeleton'></div><div id='leaflet' style='height:100%'></div>";
    }
    return mapEl;
  }
  function placeMap() {
    var slot = document.getElementById('mapslot');
    if (!slot) { return; }
    var el = ensureMap();
    if (!el) { slot.innerHTML = "<div class='mapbox'><div class='skeleton'></div></div>"; return; }
    slot.appendChild(el);
    var dist = D.districts[S.d];
    if (!map) {
      map = L.map(el.querySelector('#leaflet'), { zoomControl: true, attributionControl: true, scrollWheelZoom: false });
      var tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 13, attribution: '© OpenStreetMap' });
      tiles.on('load', function () { el.classList.remove('loading'); });
      tiles.addTo(map);
      marker = L.circleMarker([dist.lat, dist.lon], { radius: 9, color: '#fff', weight: 3, fillColor: C.green, fillOpacity: 1 }).addTo(map);
    }
    map.setView([dist.lat, dist.lon], 8);
    marker.setLatLng([dist.lat, dist.lon]);
    setTimeout(function () { map.invalidateSize(); }, 50);
  }

  // ------------------------------------------------------------------ geolocation
  var geoMsg = '';
  function km(a, b, c, d) {
    var r = Math.PI / 180, x1 = (d - b) * r * Math.cos((a + c) / 2 * r), y1 = (c - a) * r;
    return 6371 * Math.sqrt(x1 * x1 + y1 * y1);
  }
  function locate() {
    if (!navigator.geolocation) { geoMsg = f('nogeo'); render(); return; }
    geoMsg = f('locating'); render();
    navigator.geolocation.getCurrentPosition(function (pos) {
      var best = null, bestKm = 1e9;
      Object.keys(D.districts).forEach(function (k) {
        var dd = km(pos.coords.latitude, pos.coords.longitude, D.districts[k].lat, D.districts[k].lon);
        if (dd < bestKm) { bestKm = dd; best = k; }
      });
      S.d = best;
      geoMsg = f('nearest').replace('{d}', D.districts[best].short[S.lang]).replace('{k}', Math.round(bestKm));
      render();
    }, function () { geoMsg = f('denied'); render(); }, { timeout: 10000, maximumAge: 600000 });
  }

  // ------------------------------------------------------------------ farmer view
  var calc = null;   // running calculation animation
  function renderFarmer() {
    var dist = D.districts[S.d], fc = dist.facts;
    var dh = fc.hot_now - fc.hot_then, dr = fc.rain_now - fc.rain_then;
    var h = "<div class='h' style='margin-top:18px'>" + f('where') + '</div>';
    h += "<div class='where'>" + seg('d', Object.keys(D.districts), S.d, function (k) { return D.districts[k].short[S.lang]; }) +
      "<button class='locbtn' data-act='locate'>" + icon('locate', C.green, 16) + ' ' + f('locate') + '</button></div>' +
      (geoMsg ? "<div class='geomsg'>" + esc(geoMsg) + '</div>' : '');
    h += "<div class='grid2'><div class='card'><div class='district'>" + icon('pin', C.green, 20) + ' ' + esc(dist.name[S.lang]) + '</div>' +
      "<div class='facts2'>" +
      "<div class='fact'><div class='l'>" + icon('thermo', C.muted, 15) + ' ' + f('hot') + ' ' + tip(f('hot_tip')) + "</div><div class='v'>" + fc.hot_then + ' → ' + fc.hot_now +
      " <span class='d' style='color:" + (dh > 0 ? C.bad : C.ok) + "'>" + (dh > 0 ? '+' : '') + dh + '</span></div></div>' +
      "<div class='fact'><div class='l'>" + icon('rain', C.muted, 15) + ' ' + f('rain') + ' ' + tip(f('rain_tip')) + "</div><div class='v'>" + fc.rain_then + ' → ' + fc.rain_now + ' mm' +
      " <span class='d' style='color:" + (dr < 0 ? C.bad : C.ok) + "'>" + (dr > 0 ? '+' : '') + dr + '</span></div></div></div>';
    if (dist.smap || dist.hls) {
      h += "<div class='sat'>";
      if (dist.smap) { h += '<span>' + icon('satellite', C.muted, 14) + ' ' + f('soil').replace('{p}', dist.smap.drop_pct) + ' ' + tip(t('smap').replace('{p}', dist.smap.drop_pct).replace('{y}', dist.smap.year)) + '</span>'; }
      if (dist.hls) { h += '<span>' + icon('sprout', C.muted, 14) + ' ' + f('green').replace('{m}', F.months[S.lang][dist.hls.peak_month - 1]) + ' ' + tip(dist.hls_line[S.lang]) + '</span>'; }
      h += '</div>';
    }
    h += "</div><div id='mapslot'></div></div>";

    // plan: controls + result in ONE card so they clearly belong together
    var sc = scenario(), plan = currentPlan(sc), lv = levelOf(S.budget);
    h += "<div class='h' style='margin-top:22px'>" + f('plan_h') + '</div>';
    h += "<div class='card plancard'><div class='controls2'>" +
      "<div class='ctl'><div class='lbl'>" + icon('drop', C.muted, 14) + ' ' + f('water') + ' ' + tip(f('water_tip')) + "</div>" +
      seg('lvl', Object.keys(D.water_levels), lv, function (k) { return t('w_' + k); }) +
      "<div class='slider'><input type='range' id='budget' min='" + D.budgets[0] + "' max='" + D.budgets[D.budgets.length - 1] + "' step='500' value='" + S.budget + "'>" +
      "<span class='bval'>" + thousands(S.budget) + ' ' + f('k_t') + '</span></div></div>' +
      "<div class='ctl'><div class='lbl'>" + f('goal') + '</div>' + (sc.status === 'ok' ? seg('plan', D.plans, S.plan, function (k) { return t('plan_' + k); }) : '') +
      "<label class='switch'><input type='checkbox' id='must'" + (S.must ? ' checked' : '') + "><span class='knob'></span><span>" + f('must') + '</span> ' + tip(f('must_tip')) + '</label></div>' +
      '</div>';
    h += "<div id='planbody'>" + planBody(sc, plan) + '</div></div>';
    if (plan) {
      h += "<details class='whybox'><summary>" + f('why') + "</summary><p>" + esc(plan.why[S.lang]) + '</p></details>';
    }
    h += "<p class='note2'>" + f('note') + '</p>';
    document.getElementById('farmer').innerHTML = h;
    placeMap();
    if (calc) { showCalc(); }   // re-render during a run (e.g. language switch): same run continues
  }
  function planBody(sc, plan) {
    var h = '';
    if (sc.status !== 'ok') { h += "<div class='alert'>" + esc(sc.error[S.lang]) + '</div>'; }
    if (!plan) { return h; }
    h += "<div class='steps'>" + plan.years.map(function (y) {
      return "<div class='step'><div class='dot' style='background:" + y.dot + "'></div><div class='y'>" +
        (S.lang === 'uz' ? y.year + '-yil' : 'Year ' + y.year) + "</div><div class='c'>" + esc(y.name[S.lang]) + "</div><div class='m'>" +
        esc(y.months[S.lang]) + "</div><div class='wbar'><div style='width:" + (Math.min(y.water / S.budget, 1) * 100).toFixed(0) +
        '%;background:' + (y.water <= 0.8 * S.budget ? C.ok : y.water <= S.budget ? C.warn : C.bad) + "'></div></div></div>";
    }).join('') + '</div>';
    var c = plan.cmp;
    h += "<div class='result'><div class='inc'><div class='lbl'>" + f('income') + ' ' + tip(f('income_tip')) + "</div><div class='money'>≈ " + fmt(plan.income_low) + ' ' + t('mln') + '</div></div>' +
      "<div class='cmp3'>" +
      "<div><div class='l'>" + icon('coins', C.muted, 14) + ' ' + t('c_income') + ' ' + tip(f('usual_tip')) + "</div><div class='v' style='color:" + c.income_color + "'>" + esc(c.income[S.lang]) + '</div></div>' +
      "<div><div class='l'>" + icon('drop', C.muted, 14) + ' ' + t('c_water') + ' ' + tip(f('usual_tip')) + "</div><div class='v' style='color:" + c.water_color + "'>" + esc(c.water[S.lang]) + '</div></div>' +
      "<div><div class='l'>" + icon('shield', C.muted, 14) + ' ' + t('c_risk') + ' ' + tip(f('risk_tip')) + "</div><div class='v' style='color:" + c.risk_color + "'>" + esc(c.risk[S.lang]) +
      "</div><div class='rr'>" + esc(c.risk_reason[S.lang]) + '</div></div></div></div>';
    if (S.must && plan.must_note) { h += "<div class='info'>" + esc(plan.must_note[S.lang]) + '</div>'; }
    return h;
  }

  // ------------------------------------------------------------------ "calculating" animation (real numbers from the engine)
  var calcRun = 0;
  function startCalc() {
    var sc = scenario();
    calcRun += 1;   // cancels any previous run
    calc = { id: calcRun, t0: Date.now(), dur: 5000, n: sc.n_sequences || 0, k: sc.n_options || 0 };
    showCalc();
  }
  function showCalc() {
    var body = document.getElementById('planbody');
    if (!body || !calc) { return; }
    body.querySelectorAll('.calc').forEach(function (c) { c.remove(); });
    body.classList.remove('reveal');
    body.classList.add('calcing');
    var steps = ['s1', 's2', 's3', 's4', 's5'];
    var el = document.createElement('div');
    el.className = 'calc';
    el.innerHTML = "<div class='ctitle'><span class='spin'></span>" + f('calc_title') + "</div><ol>" + steps.map(function (s) {
      return "<li data-s='" + s + "'><span class='st'></span>" + f(s) + "<span class='cnt'></span></li>"; }).join('') +
      "</ol><div class='cbar'><div></div></div>";
    body.appendChild(el);
    var id = calc.id;
    requestAnimationFrame(function () { tickCalc(id); });
  }
  function tickCalc(id) {
    if (!calc || calc.id !== id) { return; }   // a newer run took over
    var el = document.querySelector('#planbody .calc');
    if (!el) { return; }
    var p = Math.min((Date.now() - calc.t0) / calc.dur, 1);
    el.querySelector('.cbar div').style.width = (p * 100).toFixed(1) + '%';
    var items = el.querySelectorAll('li');
    items.forEach(function (li, i) {
      var a = i / items.length, b = (i + 1) / items.length;
      li.className = p >= b ? 'done' : p >= a ? 'run' : '';
      var cnt = li.querySelector('.cnt');
      var q = Math.max(0, Math.min((p - a) / (b - a), 1));
      if (li.dataset.s === 's1') { cnt.textContent = ' · ' + Math.round(q * 35) + ' ' + f('years'); }
      if (li.dataset.s === 's4') { cnt.textContent = ' · ' + thousands(q * calc.n) + ' / ' + thousands(calc.n); }
    });
    if (p >= 1) { endCalc(); return; }
    requestAnimationFrame(function () { tickCalc(id); });
  }
  function endCalc() {
    calc = null;
    var body = document.getElementById('planbody');
    if (body) { body.classList.remove('calcing'); body.querySelectorAll('.calc').forEach(function (c) { c.remove(); }); body.classList.add('reveal'); }
  }

  // ------------------------------------------------------------------ expert view (dense, data-focused)
  var EC = { hot: '#a5533f', smap: '#3d6e8f', ndvi: '#6b8a3a', ref: '#8a8f8b', grid: '#ecebe6' };
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
      return "<option value='" + it + "'" + (String(it) === String(value) ? ' selected' : '') + '>' + esc(label(it)) + '</option>';
    }).join('') + '</select>';
  }
  function renderExpert() {
    var dist = D.districts[S.d], fc = dist.facts, sc = scenario(), budget = S.budget, uz = S.lang === 'uz';
    var h = "<div class='xhead'><h2>" + esc(dist.name[S.lang]) + "</h2><div class='xctl'>" +
      sel('d', Object.keys(D.districts), S.d, function (k) { return D.districts[k].short[S.lang]; }) +
      sel('budget', D.budgets, S.budget, function (b) { return thousands(b) + ' m³/ha'; }) +
      '</div></div>';
    var rows = [[uz ? 'Jazirama kunlar (>35 °C), kun/yil' : 'Days > 35 °C, per year', fc.hot_then, fc.hot_now, 'NASA POWER'],
      [uz ? 'Mavsumdagi yomgʻir (apr–okt), mm' : 'Season rain (Apr–Oct), mm', fc.rain_then, fc.rain_now, 'NASA POWER']];
    h += "<section class='xcard'><h3>" + (uz ? 'Asosiy koʻrsatkichlar' : 'Key numbers') + "</h3><div class='tablewrap'><table class='xt'><tr><th></th><th class='num'>1991–2005</th><th class='num'>2011–2026</th><th>" + (uz ? 'Manba' : 'Source') + '</th></tr>' +
      rows.map(function (r) { return '<tr><td>' + r[0] + "</td><td class='num'>" + r[1] + "</td><td class='num'>" + r[2] + '</td><td>' + r[3] + '</td></tr>'; }).join('') +
      (dist.smap ? '<tr><td>' + (uz ? 'Ildiz qatlami namligi, bahor → yoz, m³/m³' : 'Root-zone soil moisture, spring → summer, m³/m³') + "</td><td class='num'>" + dist.smap.spring + "</td><td class='num'>" + dist.smap.summer + ' (−' + dist.smap.drop_pct + ' %, ' + dist.smap.year + ')</td><td>NASA SMAP L4</td></tr>' : '') +
      (dist.hls ? '<tr><td>' + (uz ? 'NDVI choʻqqisi' : 'NDVI peak') + "</td><td class='num'>–</td><td class='num'>" + dist.hls.peak + ' (' + dist.hls.peak_date + ')</td><td>NASA/USGS HLS</td></tr>' : '') +
      (dist.et0_correction ? '<tr><td>' + x('et0') + "</td><td class='num'>–</td><td class='num'>× " + dist.et0_correction.factor + '</td><td>' + esc(dist.et0_correction.label) + '</td></tr>' : '') +
      (sc.n_sequences ? '<tr><td>' + (uz ? 'Tekshirilgan 5 yillik rejalar' : '5-year plans checked') + "</td><td class='num'>–</td><td class='num'>" + thousands(sc.n_sequences) + '</td><td>DalaShift</td></tr>' : '') +
      '</table></div></section>';
    h += "<div class='xgrid'>";
    var yrs = fc.years, i0 = yrs.indexOf(1991), i1 = yrs.indexOf(2005), j0 = yrs.indexOf(2011), j1 = yrs.length - 1;
    h += chartCard(x('climate'), lineChart({ title: x('climate'), dates: yrs, values: fc.hot_series, color: EC.hot, ylabel: uz ? 'kun/yil' : 'days/yr', yearStep: 5,
      refs: [{ i0: i0, i1: i1, y: fc.hot_then, color: EC.ref, label: '1991–2005: ' + fc.hot_then }, { i0: j0, i1: j1, y: fc.hot_now, color: EC.hot, label: '2011–2026: ' + fc.hot_now }] }),
      ['NASA POWER daily (MERRA-2), T2M_MAX > 35 °C. ' + (uz ? 'Mavsumdagi yomgʻir ' : 'Season rain ') + fc.rain_then + ' → ' + fc.rain_now + ' mm.']);
    if (dist.smap) {
      h += chartCard(x('smap'), lineChart({ title: 'SMAP', dates: dist.smap.weekly_dates, values: dist.smap.weekly, color: EC.smap, ylabel: 'm³/m³', digits: 2 }), [esc(D.smap_note[S.lang])]);
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
          "</td><td class='num'>" + thousands(p.water_per_year) + "</td><td class='num'>" + p.health + "/10</td><td>" + esc(p.cmp.income[S.lang]) + ' · ' + esc(p.cmp.water[S.lang]) + '</td></tr>';
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
    document.getElementById('foot').innerHTML = esc(D.credits[S.lang]) + ' · Team KarPS · NASA Space Apps 2026' +
      " · <a href='https://t.me/dalashiftbot' rel='noopener'>Telegram: @dalashiftbot</a>";
    save();
  }
  function planChanged() { calc = null; render(); if (S.tab === 'farmer') { startCalc(); } }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) { return; }
    if (b.dataset.act === 'locate') { locate(); return; }
    var group = b.closest('[data-seg]');
    if (b.closest('#lang')) { S.lang = b.dataset.v; geoMsg = ''; render(); return; }
    if (b.closest('#tabs')) { S.tab = b.dataset.v; render(); return; }
    if (!group) { return; }
    var key = group.dataset.seg;
    if (key === 'lvl') { S.budget = D.water_levels[b.dataset.v]; planChanged(); return; }
    if (key === 'd') { S.d = b.dataset.v; geoMsg = ''; planChanged(); return; }
    S[key] = b.dataset.v;
    planChanged();
  });
  // tooltips: flip below / shift sideways when there is no room
  function placeTip(e) {
    var tp = e.target.closest && e.target.closest('.tip');
    if (!tp) { return; }
    var r = tp.getBoundingClientRect(), vw = window.innerWidth;
    tp.classList.toggle('below', r.top < 170);
    tp.classList.toggle('edge-r', r.right > vw - 140);
    tp.classList.toggle('edge-l', r.left < 140);
  }
  document.addEventListener('mouseover', placeTip);
  document.addEventListener('focusin', placeTip);
  document.addEventListener('input', function (e) {
    if (e.target.id === 'budget') {   // live label while dragging; plan recomputed on release
      var v = document.querySelector('.bval'); if (v) { v.textContent = thousands(+e.target.value) + ' ' + f('k_t'); }
    }
  });
  document.addEventListener('change', function (e) {
    if (e.target.id === 'must') { S.must = e.target.checked; planChanged(); }
    else if (e.target.id === 'budget') { S.budget = +e.target.value; planChanged(); }
    else if (e.target.dataset && e.target.dataset.sel) {
      S[e.target.dataset.sel] = e.target.dataset.sel === 'budget' ? +e.target.value : e.target.value; render();
    }
  });

  fetch('data.json').then(function (r) { return r.json(); }).then(function (data) {
    D = data;
    if (!D.districts[S.d]) { S.d = 'Karshi'; }
    if (D.plans.indexOf(S.plan) < 0) { S.plan = 'balanced'; }
    if (D.budgets.indexOf(+S.budget) < 0) { S.budget = 8000; }
    render();   // no animation on first load
  }).catch(function () {
    document.getElementById('farmer').innerHTML = "<div class='alert'>data.json could not be loaded. Open this site through a web server (e.g. Netlify), not as a local file.</div>";
  });
})();
