/* Builder Agent for Divi admin screen. Talks to the plugin's REST API; measures computed styles on the front end
   through a same-origin iframe (the browser is the only place a computed style can be read). */
(function () {
	'use strict';
	var D = window.wpbaData || {};
	var app = document.getElementById('wpba-app');
	if (!app) { return; }

	// ---- helpers ------------------------------------------------------------------------------------
	function api(path, method, body) {
		return window.wp.apiFetch({ path: 'wpba/v1' + path, method: method || 'GET', data: body })
			.catch(function (e) {
				var msg = (e && e.error) || (e && e.message) || 'Request failed';
				var err = new Error(msg); err.data = e && e.data; throw err;
			});
	}
	function h(tag, attrs, children) {
		var el = document.createElement(tag);
		Object.keys(attrs || {}).forEach(function (k) {
			if (k === 'html') { el.innerHTML = attrs[k]; }
			else if (k === 'text') { el.textContent = attrs[k]; }
			else if (k.indexOf('on') === 0) { el.addEventListener(k.slice(2), attrs[k]); }
			else { el.setAttribute(k, attrs[k]); }
		});
		(children || []).forEach(function (c) { if (c) { el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); } });
		return el;
	}
	function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
	function pretty(o) { return typeof o === 'string' ? o : JSON.stringify(o, null, 2); }
	function out(el, data, cls) { el.textContent = pretty(data); el.className = 'wpba-out' + (cls ? ' ' + cls : ''); }
	function busy(card, on) { card.classList.toggle('wpba-busy', !!on); }
	function confirmField() {
		return h('label', { 'class': 'wpba-confirm' }, ['Type the site name to confirm (' + D.site + ')', h('input', { type: 'text', 'class': 'wpba-confirm-input', placeholder: D.site, autocomplete: 'off' })]);
	}
	function confirmValue(card) { var i = card.querySelector('.wpba-confirm-input'); return i ? i.value.trim() : ''; }
	function runLink(id) { return h('a', { href: '#runs', text: 'run ' + id, onclick: function (e) { e.preventDefault(); showTab('runs'); loadRun(id); } }); }

	// ---- front-end measurement via iframe -------------------------------------------------------------
	function loadFrame(path) {
		return new Promise(function (resolve, reject) {
			var holder = document.getElementById('wpba-iframes');
			holder.innerHTML = '';
			var url = D.home.replace(/\/$/, '') + path + (path.indexOf('?') >= 0 ? '&' : '?') + 'wpagent=' + Date.now();
			var f = h('iframe', { src: url });
			var t = setTimeout(function () { reject(new Error('Timed out loading ' + path)); }, 60000);
			f.addEventListener('load', function () { clearTimeout(t); setTimeout(function () { resolve(f); }, 800); });
			holder.appendChild(f);
		});
	}
	function measure(checks) {
		var results = [], current = null, frame = null;
		return checks.reduce(function (p, c) {
			return p.then(function () {
				var step = (c.page !== current) ? loadFrame(c.page).then(function (f) { frame = f; current = c.page; }) : Promise.resolve();
				return step.then(function () {
					var actual = null;
					try {
						var doc = frame.contentDocument;
						var el = doc && doc.querySelector(c.selector);
						if (el) { actual = frame.contentWindow.getComputedStyle(el).getPropertyValue(c.css_property || c.property); }
					} catch (e) { actual = null; }
					results.push({ page: c.page, selector: c.selector, property: c.css_property || c.property, expected: c.expected, actual: actual });
				});
			});
		}, Promise.resolve()).then(function () { document.getElementById('wpba-iframes').innerHTML = ''; return results; });
	}
	function renderResults(results) {
		var t = h('table', { 'class': 'wpba-table' }, [h('tr', {}, ['Page', 'Selector', 'Property', 'Expected', 'Actual', 'Result'].map(function (x) { return h('th', { text: x }); }))]);
		results.forEach(function (r) {
			t.appendChild(h('tr', {}, [h('td', { text: r.page }), h('td', { text: r.selector }), h('td', { text: r.property }), h('td', { text: r.expected }), h('td', { text: r.actual == null ? '(not found)' : r.actual }), h('td', { 'class': r.pass ? 'wpba-ok' : 'wpba-fail', text: r.pass ? 'PASS' : 'FAIL' })]));
		});
		return t;
	}

	// ---- tabs ------------------------------------------------------------------------------------------
	var panels = document.getElementById('wpba-panels');
	var tabs = {};
	function showTab(id) {
		app.querySelectorAll('.nav-tab').forEach(function (a) { a.classList.toggle('nav-tab-active', a.dataset.tab === id); });
		Object.keys(tabs).forEach(function (k) { tabs[k].classList.toggle('active', k === id); });
		if (id === 'runs') { loadRuns(); }
		if (id === 'pages' || id === 'sitewide') { loadPages(); }
		try { window.history.replaceState(null, '', '#' + id); } catch (e) {}
	}
	app.querySelectorAll('.nav-tab').forEach(function (a) { a.addEventListener('click', function (e) { e.preventDefault(); showTab(a.dataset.tab); }); });

	// ---- Plan & apply ----------------------------------------------------------------------------------
	function planPanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-plan' });
		var card = h('div', { 'class': 'wpba-card' });
		var task = h('input', { type: 'text', 'class': 'wpba-wide', placeholder: 'e.g. make all buttons #ff8a3d with 6px radius' });
		var o = h('div', { 'class': 'wpba-out' });
		var planBox = h('div', {});
		var state = { runId: null, plan: null, applyRunId: null };
		var apply = h('div', { 'class': 'wpba-card', style: 'display:none' });

		function renderPlan(plan, runId) {
			planBox.innerHTML = '';
			var dl = h('dl', { 'class': 'wpba-plan' });
			function add(k, v) { dl.appendChild(h('dt', { text: k })); dl.appendChild(h('dd', {}, [typeof v === 'string' ? document.createTextNode(v) : v])); }
			add('Run', runLink(runId));
			add('Feasible', plan.feasible ? 'yes' : 'no' + (plan.blocked_reason ? ' - ' + plan.blocked_reason : ''));
			if (plan.rung) { add('Edit rung', plan.rung); }
			if (plan.skipped_rungs.length) { add('Skipped rungs', h('ul', {}, plan.skipped_rungs.map(function (s) { return h('li', { text: s }); }))); }
			if (plan.changes.length) { add('Changes', h('ul', {}, plan.changes.map(function (c) { return h('li', { html: '<code>' + esc(c.setting) + '</code>: <code>' + esc(c.old_value) + '</code> → <code>' + esc(c.new_value) + '</code> <span class="wpba-muted">' + esc(c.reason) + '</span>' }); }))); }
			if (plan.side_effects.length) { add('Side effects', h('ul', {}, plan.side_effects.map(function (s) { return h('li', { text: s }); }))); }
			if (plan.verify.length) { add('Will verify', h('ul', {}, plan.verify.map(function (v) { return h('li', { html: esc(v.page) + ' <code>' + esc(v.selector) + '</code> ' + esc(v.css_property) + ' == <code>' + esc(v.expected) + '</code>' }); }))); }
			planBox.appendChild(dl);
			apply.style.display = plan.feasible ? '' : 'none';
		}
		card.appendChild(h('h2', { text: '1. Plan (read-only)' }));
		card.appendChild(h('p', { 'class': 'wpba-muted', text: 'The agent reads Theme Options and every page layout, asks Claude for a plan using the edit ladder, and validates it. Nothing is changed.' }));
		card.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Task', task]), h('button', { 'class': 'button button-primary', text: 'Make plan', onclick: function () {
			busy(card, true); out(o, 'Planning… this calls Claude and can take a minute.');
			api('/plan', 'POST', { task: task.value }).then(function (r) {
				state.runId = r.runId || r.run_id; state.plan = r.plan; renderPlan(r.plan, state.runId); out(o, r.note + (r.usage && r.usage[0] ? '  (Claude: $' + r.usage[0].usd + ')' : ''));
			}).catch(function (e) {
				if (e.data && e.data.plan) { renderPlan(e.data.plan, e.data.run_id); apply.style.display = 'none'; }
				out(o, 'Error: ' + e.message, 'wpba-fail');
			}).then(function () { busy(card, false); });
		} })]));
		card.appendChild(planBox); card.appendChild(o);

		var ao = h('div', { 'class': 'wpba-out' });
		var vbox = h('div', {});
		apply.appendChild(h('h2', { text: '2. Apply, verify, roll back' }));
		apply.appendChild(h('p', { 'class': 'wpba-muted', text: 'Apply backs up the whole Theme Options record, writes the approved values, clears caches, then measures the front end in your browser.' }));
		apply.appendChild(h('div', { 'class': 'wpba-row' }, [confirmField(), h('button', { 'class': 'button button-primary', text: 'Apply this plan', onclick: function () {
			busy(apply, true); out(ao, 'Measuring current front-end values…');
			measure(state.plan.verify).then(function (before) {
				out(ao, 'Applying…');
				return api('/apply', 'POST', { run_id: state.runId, confirm_site: confirmValue(apply), before: before });
			}).then(function (r) {
				state.applyRunId = r.run_id; out(ao, 'Applied (run ' + r.run_id + '). Caches cleared: ' + r.cleared.join(', ') + '. Verifying…');
				return measure(r.verify).then(function (res) { return api('/verify', 'POST', { run_id: r.run_id, results: res }); });
			}).then(function (v) {
				vbox.innerHTML = ''; vbox.appendChild(renderResults(v.results));
				out(ao, v.pass ? 'Verification: PASS (' + v.results.length + ' checks). Rollback is available below.' : 'Verification: FAIL. Roll back if this is not what you wanted.', v.pass ? 'wpba-ok' : 'wpba-fail');
				rb.style.display = '';
			}).catch(function (e) { out(ao, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(apply, false); });
		} })]));
		var rb = h('div', { 'class': 'wpba-row', style: 'display:none' }, [h('button', { 'class': 'button', text: 'Roll back this apply', onclick: function () {
			busy(apply, true); out(ao, 'Rolling back…');
			api('/rollback', 'POST', { run_id: state.applyRunId, confirm_site: confirmValue(apply) }).then(function (r) {
				out(ao, 'Rolled back (run ' + r.run_id + '). Verifying the old values are back…');
				return measure(r.verify).then(function (res) { return api('/verify', 'POST', { run_id: r.run_id, results: res }); });
			}).then(function (v) { vbox.innerHTML = ''; vbox.appendChild(renderResults(v.results)); out(ao, v.pass ? 'Rollback verified.' : 'Rollback verification FAILED; check the run log.', v.pass ? 'wpba-ok' : 'wpba-fail'); })
			.catch(function (e) { out(ao, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(apply, false); });
		} })]);
		apply.appendChild(rb); apply.appendChild(vbox); apply.appendChild(ao);

		var snap = h('div', { 'class': 'wpba-card' });
		var so = h('div', { 'class': 'wpba-out' });
		snap.appendChild(h('h2', { text: 'Snapshot (read-only backup)' }));
		snap.appendChild(h('p', { 'class': 'wpba-muted', text: 'Records Theme Options, global colours, Custom CSS and every published page layout into one run you can restore from by hand.' }));
		snap.appendChild(h('div', { 'class': 'wpba-row' }, [h('button', { 'class': 'button', text: 'Take snapshot', onclick: function () {
			busy(snap, true); api('/snapshot', 'POST', {}).then(function (r) { out(so, r); }).catch(function (e) { out(so, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(snap, false); });
		} })]));
		snap.appendChild(so);
		p.appendChild(card); p.appendChild(apply); p.appendChild(snap);
		return p;
	}

	// ---- Pages: clone / rebuild / go live -------------------------------------------------------------
	var pagesCache = null;
	function loadPages() {
		if (pagesCache) { return Promise.resolve(pagesCache); }
		return api('/pages').then(function (r) { pagesCache = r; app.querySelectorAll('select.wpba-pages').forEach(fillPages); return r; });
	}
	function fillPages(sel) {
		var want = sel.dataset.status || '';
		var cur = sel.value; sel.innerHTML = '';
		sel.appendChild(h('option', { value: '', text: '— choose —' }));
		(pagesCache || []).forEach(function (p) {
			if (want && p.status !== want) { return; }
			sel.appendChild(h('option', { value: p.id, text: p.id + ' · ' + p.title + ' (' + p.status + ')' }));
		});
		if (cur) { sel.value = cur; }
	}
	function pageSelect(status) { var s = h('select', { 'class': 'wpba-pages', 'data-status': status || '' }); fillPages(s); return s; }

	function pagesPanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-pages' });

		var rb = h('div', { 'class': 'wpba-card' }); var ro = h('div', { 'class': 'wpba-out' });
		var src = pageSelect('publish'), draft = pageSelect('draft'), specOnly = h('input', { type: 'checkbox' });
		rb.appendChild(h('h2', { text: 'Rebuild a Code-module page as native Divi modules' }));
		rb.appendChild(h('p', { 'class': 'wpba-muted', text: 'Reads the page\'s Code module, asks Claude for a layout spec (sections, rows, Text/Button/Image/Blurb/Toggle modules, one JSON-LD Code module), validates it (safe HTML only, images from the media library, every original passage present), renders Divi\'s own layout format and saves it into a draft. Costs about $0.30 in Claude usage for a long page.' }));
		rb.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Source page', src]), h('label', {}, ['Draft to write into (blank = new draft)', draft]), h('label', {}, [h('span', {}, [specOnly, ' Spec only (touch nothing)'])]), confirmField(), h('button', { 'class': 'button button-primary', text: 'Rebuild', onclick: function () {
			busy(rb, true); out(ro, 'Designing the page with Claude… a long page takes a few minutes.');
			api('/rebuild', 'POST', { source_id: src.value, draft_id: draft.value, confirm_site: confirmValue(rb), spec_only: specOnly.checked }).then(function (r) {
				pagesCache = null; out(ro, (r.note || '') + '\nModules: ' + JSON.stringify(r.modules) + (r.notes && r.notes.length ? '\nNotes:\n - ' + r.notes.join('\n - ') : '') + (r.preview_url ? '\nPreview: ' + r.preview_url + '\nEdit: ' + r.edit_url : ''));
			}).catch(function (e) { out(ro, 'Error: ' + e.message + (e.data && e.data.missing ? '\nMissing text:\n - ' + e.data.missing.join('\n - ') : ''), 'wpba-fail'); }).then(function () { busy(rb, false); });
		} })]));
		rb.appendChild(ro);

		var cl = h('div', { 'class': 'wpba-card' }); var co = h('div', { 'class': 'wpba-out' }); var clSrc = pageSelect('');
		cl.appendChild(h('h2', { text: 'Clone a page into a new draft' }));
		cl.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Page', clSrc]), confirmField(), h('button', { 'class': 'button', text: 'Clone', onclick: function () {
			busy(cl, true); api('/clone', 'POST', { page_id: clSrc.value, confirm_site: confirmValue(cl) }).then(function (r) { pagesCache = null; loadPages(); out(co, r.note + '\nEdit: ' + r.edit_url); }).catch(function (e) { out(co, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(cl, false); });
		} })]));
		cl.appendChild(co);

		var gl = h('div', { 'class': 'wpba-card' }); var go = h('div', { 'class': 'wpba-out' }); var live = pageSelect('publish'), dr = pageSelect('draft');
		gl.appendChild(h('h2', { text: 'Go live: put a verified draft onto the live page' }));
		gl.appendChild(h('p', { 'class': 'wpba-muted', text: 'The live page\'s old layout is backed up in the run; the draft goes to Trash (restorable for 30 days).' }));
		gl.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Live page', live]), h('label', {}, ['Draft', dr]), confirmField(), h('button', { 'class': 'button button-primary', text: 'Go live', onclick: function () {
			if (!window.confirm('Replace the live page layout with the draft?')) { return; }
			busy(gl, true); api('/golive', 'POST', { live_id: live.value, draft_id: dr.value, confirm_site: confirmValue(gl) }).then(function (r) { pagesCache = null; loadPages(); out(go, r.note + '\n' + r.url); }).catch(function (e) { out(go, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(gl, false); });
		} })]));
		gl.appendChild(go);
		p.appendChild(rb); p.appendChild(cl); p.appendChild(gl);
		return p;
	}

	// ---- Site-wide: header glow, restyle ------------------------------------------------------------
	function resultsTable(rows) {
		var t = h('table', { 'class': 'wpba-table' }, [h('tr', {}, ['ID', 'Path', 'Status', 'Changes', 'Verified'].map(function (x) { return h('th', { text: x }); }))]);
		rows.forEach(function (r) { t.appendChild(h('tr', {}, [h('td', { text: r.id }), h('td', { text: r.path }), h('td', { text: r.status }), h('td', { text: r.changes != null ? r.changes : '' }), h('td', { text: r.verified == null ? '' : (r.verified ? 'yes' : 'NO') })])); });
		return t;
	}
	function sitewidePanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-sitewide' });
		function tool(title, desc, extra, path, body) {
			var c = h('div', { 'class': 'wpba-card' }); var o = h('div', { 'class': 'wpba-out' }); var tb = h('div', {});
			var only = h('input', { type: 'text', placeholder: 'e.g. 12, 340', 'class': 'wpba-wide' });
			c.appendChild(h('h2', { text: title })); c.appendChild(h('p', { 'class': 'wpba-muted', text: desc }));
			var run = function (liveMode) {
				busy(c, true); out(o, liveMode ? 'Applying…' : 'Dry run…');
				var b = body(); b.only = only.value.split(',').map(function (s) { return s.trim(); }).filter(Boolean); if (liveMode) { b.confirm_site = confirmValue(c); }
				api(path, 'POST', b).then(function (r) { tb.innerHTML = ''; tb.appendChild(resultsTable(r.results)); out(o, r.note + ' (run ' + r.run_id + ')'); }).catch(function (e) { out(o, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(c, false); });
			};
			c.appendChild(h('div', { 'class': 'wpba-row' }, extra.concat([h('label', {}, ['Only these page ids (blank = all published)', only]), h('button', { 'class': 'button', text: 'Dry run', onclick: function () { run(false); } }), confirmField(), h('button', { 'class': 'button button-primary', text: 'Apply', onclick: function () { run(true); } })])));
			c.appendChild(tb); c.appendChild(o);
			return c;
		}
		p.appendChild(tool('Header glow', 'Adds the site profile\'s hero glow (Divi native circular gradient) to the first section of every page with a dark header. Live mode works page by page: backup, write, clear cache, check the gradient is on the front end, stop at the first failure.', [], '/header-glow', function () { return {}; }));
		var theme = h('select', {}); (D.themes || []).forEach(function (t) { theme.appendChild(h('option', { value: t, text: t })); });
		p.appendChild(tool('Restyle by role', 'Changes colour and radius settings by what they are used for (backgrounds, borders, text, icons, button radius). Only shortcode attributes change; module content, Code-module HTML and visible text never do. Pages whose visible text would change are skipped.', [h('label', {}, ['Theme', theme])], '/restyle', function () { return { theme: theme.value }; }));
		return p;
	}

	// ---- CSS & components ---------------------------------------------------------------------------
	function cssPanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-css' });
		var comp = h('div', { 'class': 'wpba-card' }); var co = h('div', { 'class': 'wpba-out' }); var list = h('div', {});
		comp.appendChild(h('h2', { text: 'Component library' }));
		comp.appendChild(h('p', { 'class': 'wpba-muted', text: 'Small CSS classes for things Divi 4 has no native module for (pill tags, numbered steps, KPI cards). Installing writes one marked block into Theme Options > Custom CSS; re-installing replaces that block and leaves your other CSS alone.' }));
		api('/components').then(function (r) {
			r.catalogue.forEach(function (c) { list.appendChild(h('p', { html: '<strong>' + esc(c.file) + '</strong> ' + c.classes.map(function (x) { return '<span class="wpba-pill">' + esc(x) + '</span>'; }).join('') + (c.usage ? '<br><span class="wpba-muted">' + esc(c.usage) + '</span>' : '') })); });
			list.appendChild(h('p', { 'class': 'wpba-muted', text: 'Site-specific components the designer creates are saved to ' + r.site_folder }));
		});
		comp.appendChild(list);
		comp.appendChild(h('div', { 'class': 'wpba-row' }, [confirmField(), h('button', { 'class': 'button button-primary', text: 'Install / update bundle in Custom CSS', onclick: function () {
			busy(comp, true); api('/components/install', 'POST', { confirm_site: confirmValue(comp) }).then(function (r) { out(co, r); }).catch(function (e) { out(co, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(comp, false); });
		} })]));
		comp.appendChild(co);

		var css = h('div', { 'class': 'wpba-card' }); var o = h('div', { 'class': 'wpba-out' });
		var ta = h('textarea', { rows: 8, placeholder: '/* wp-builder-agent: reusable components ... */\n.rd-thing{...}\n/* end wp-builder-agent components */' });
		var reason = h('input', { type: 'text', 'class': 'wpba-wide', placeholder: 'Why no native Divi setting can do this (logged)' });
		css.appendChild(h('h2', { text: 'Theme Custom CSS (last resort)' }));
		css.appendChild(h('p', { 'class': 'wpba-muted', text: 'Bottom rung of the edit ladder. Needs a reason, backs up the existing Custom CSS, and checks the class is served on the front end afterwards.' }));
		css.appendChild(ta);
		css.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Reason', reason]), confirmField(), h('button', { 'class': 'button', text: 'Save CSS block', onclick: function () {
			busy(css, true); api('/theme-css', 'POST', { css: ta.value, reason: reason.value, confirm_site: confirmValue(css) }).then(function (r) { out(o, r, r.saved ? 'wpba-ok' : ''); }).catch(function (e) { out(o, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(css, false); });
		} })]));
		css.appendChild(o);
		p.appendChild(comp); p.appendChild(css);
		return p;
	}

	// ---- Runs ---------------------------------------------------------------------------------------
	var runsList, runDetail;
	function runsPanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-runs' });
		runsList = h('div', { 'class': 'wpba-card' }); runDetail = h('div', { 'class': 'wpba-card', style: 'display:none' });
		p.appendChild(runsList); p.appendChild(runDetail);
		return p;
	}
	function loadRuns() {
		runsList.innerHTML = ''; runsList.appendChild(h('h2', { text: 'Runs' }));
		Promise.all([api('/runs'), api('/usage')]).then(function (rr) {
			var runs = rr[0], usage = rr[1];
			runsList.appendChild(h('p', { 'class': 'wpba-muted', text: 'Claude usage so far: $' + usage.total_usd.toFixed(4) }));
			var t = h('table', { 'class': 'wpba-table' }, [h('tr', {}, ['ID', 'Command', 'Status', 'Date (UTC)', ''].map(function (x) { return h('th', { text: x }); }))]);
			runs.forEach(function (r) { t.appendChild(h('tr', {}, [h('td', { text: r.id }), h('td', { text: r.command }), h('td', { text: r.status }), h('td', { text: r.date }), h('td', {}, [h('a', { href: '#', text: 'open', onclick: function (e) { e.preventDefault(); loadRun(r.id); } })])])); });
			runsList.appendChild(t);
		});
	}
	function loadRun(id) {
		runDetail.style.display = ''; runDetail.innerHTML = ''; runDetail.appendChild(h('h2', { text: 'Run ' + id }));
		api('/runs/' + id).then(function (r) {
			runDetail.appendChild(h('p', { html: '<strong>' + esc(r.command) + '</strong> · ' + esc(r.status) + ' · ' + esc(r.date) + (r.backups.length ? ' · backups: ' + r.backups.map(esc).join(', ') : '') }));
			var ev = h('div', { 'class': 'wpba-out' }); ev.textContent = r.events.map(function (e) { return e.t + '  ' + e.type + '  ' + JSON.stringify(Object.keys(e).filter(function (k) { return k !== 't' && k !== 'type'; }).reduce(function (a, k) { a[k] = e[k]; return a; }, {})); }).join('\n');
			runDetail.appendChild(h('h3', { text: 'Events' })); runDetail.appendChild(ev);
			Object.keys(r.files).forEach(function (name) { runDetail.appendChild(h('h3', { text: name })); var f = h('div', { 'class': 'wpba-out' }); f.textContent = pretty(r.files[name]); runDetail.appendChild(f); });
			if (r.files.plan && r.command === 'plan') {
				runDetail.appendChild(h('p', { 'class': 'wpba-muted', text: 'Apply from the Plan & apply tab, or: wp wpagent apply ' + id + ' --confirm-site=' + D.site }));
			}
		}).catch(function (e) { runDetail.appendChild(h('p', { 'class': 'wpba-fail', text: e.message })); });
	}

	// ---- Settings -----------------------------------------------------------------------------------
	function settingsPanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-settings' });
		var s = D.settings || {};
		var c = h('div', { 'class': 'wpba-card' }); var o = h('div', { 'class': 'wpba-out' });
		var key = h('input', { type: 'password', 'class': 'wpba-wide', placeholder: s.api_key_source === 'wp-config' ? 'Set in wp-config.php (WPBA_ANTHROPIC_API_KEY)' : (s.api_key_masked || 'sk-ant-…'), autocomplete: 'new-password' });
		if (s.api_key_source === 'wp-config') { key.disabled = true; }
		var model = h('select', {}); (D.models || []).forEach(function (m) { model.appendChild(h('option', { value: m, text: m })); }); model.value = s.model;
		var effort = h('select', {}); (D.efforts || []).forEach(function (m) { effort.appendChild(h('option', { value: m, text: m })); }); effort.value = s.effort;
		var fb = h('input', { type: 'checkbox' }); fb.checked = !!s.fallbacks;
		var css = h('input', { type: 'checkbox' }); css.checked = !!s.allow_css;
		var staging = h('input', { type: 'checkbox' }); staging.checked = !!s.is_staging;
		var pages = h('input', { type: 'text', 'class': 'wpba-wide', value: (s.pages || ['/']).join(', ') });
		c.appendChild(h('h2', { text: 'Settings' }));
		c.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Anthropic API key (' + s.api_key_source + ')', key]), h('label', {}, ['Model', model]), h('label', {}, ['Effort', effort])]));
		c.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, [h('span', {}, [fb, ' Server-side refusal fallback (re-runs a declined request on Anthropic\'s recommended fallback model)'])])]));
		c.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, [h('span', {}, [css, ' Allow plans on the CSS rungs (module_custom_css, theme_custom_css)'])]), h('label', {}, [h('span', {}, [staging, ' This is a staging site'])])]));
		c.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['Pages to inspect when planning (comma-separated paths)', pages])]));
		c.appendChild(h('div', { 'class': 'wpba-row' }, [h('button', { 'class': 'button button-primary', text: 'Save settings', onclick: function () {
			var body = { model: model.value, effort: effort.value, fallbacks: fb.checked, allow_css: css.checked, is_staging: staging.checked, pages: pages.value, keep_key: true };
			if (!key.disabled && key.value) { body.api_key = key.value; }
			busy(c, true); api('/settings', 'POST', body).then(function (r) { D.settings = r; key.value = ''; out(o, 'Saved.', 'wpba-ok'); }).catch(function (e) { out(o, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(c, false); });
		} })]));
		c.appendChild(o);

		var pc = h('div', { 'class': 'wpba-card' }); var po = h('div', { 'class': 'wpba-out' });
		var ta = h('textarea', { rows: 18 }); ta.value = JSON.stringify(D.profile || {}, null, 2);
		pc.appendChild(h('h2', { text: 'Site profile' }));
		pc.appendChild(h('p', { 'class': 'wpba-muted', text: 'Learned, non-secret facts about this site: design tokens, hero glow (used by header glow and rebuilds), dark header colours, component notes. Fed to the planner and designer as context.' }));
		pc.appendChild(ta);
		pc.appendChild(h('div', { 'class': 'wpba-row' }, [h('button', { 'class': 'button', text: 'Save profile', onclick: function () {
			var data; try { data = JSON.parse(ta.value); } catch (e) { out(po, 'Not valid JSON: ' + e.message, 'wpba-fail'); return; }
			busy(pc, true); api('/profile', 'POST', { profile: data }).then(function (r) { D.profile = r; out(po, 'Saved.', 'wpba-ok'); }).catch(function (e) { out(po, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(pc, false); });
		} })]));
		pc.appendChild(po);
		p.appendChild(c); p.appendChild(pc);
		return p;
	}

	// ---- Connect Claude ------------------------------------------------------------------------------
	function connectPanel() {
		var p = h('div', { 'class': 'wpba-panel', id: 'wpba-connect' });
		var c = h('div', { 'class': 'wpba-card' }); var o = h('div', { 'class': 'wpba-out' }); var lists = h('div', {});
		c.appendChild(h('h2', { text: 'Connect Claude to this site' }));
		c.appendChild(h('p', { html: 'The plugin is an <strong>MCP server</strong>. Add it to Claude once and the Claude you talk to does the planning and the page design itself, through the same validators and guard rails. No API key is needed in this mode.' }));
		c.appendChild(h('p', { html: 'MCP URL: <code id="wpba-mcp-url">' + esc(D.mcp_url) + '</code>' }));
		var steps = h('ol', {}, [
			h('li', { html: '<strong>claude.ai, Claude Desktop, Cowork:</strong> Customize &rsaquo; Connectors &rsaquo; Add custom connector. Paste the MCP URL. Choose <em>Sign in</em> (Claude registers itself and you approve on a WordPress consent screen), or choose fixed credentials and add a header <code>Authorization: Bearer &lt;token&gt;</code> with a connection token from below. Team and Enterprise: an Owner adds it under Organization settings &rsaquo; Connectors.' }),
			h('li', { html: '<strong>Claude Code:</strong> <code>claude mcp add --transport http builder-agent-for-divi ' + esc(D.mcp_url) + '</code> then <code>/mcp</code> to sign in, or append <code>--header "Authorization: Bearer &lt;token&gt;"</code>.' }),
			h('li', { html: '<strong>Then ask Claude</strong>, e.g. "Check my site status and make all buttons 6px rounded." It will read, propose, ask you to confirm the site name <code>' + esc(D.site) + '</code>, apply and verify.' })
		]);
		c.appendChild(steps);
		if (D.mcp_url.indexOf('https://') !== 0) { c.appendChild(h('p', { 'class': 'wpba-fail', text: 'This site is not on HTTPS. Claude\'s connectors need a public HTTPS URL; local or http sites only work with Claude Code on the same machine.' })); }
		c.appendChild(h('p', { 'class': 'wpba-muted', text: 'WordPress Application Passwords (Users > Profile) also work as Basic auth for Claude Code. The Authorization header must reach PHP: some Apache hosts need the standard "RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]" line; the X-WPBA-Token header is accepted as a fallback.' }));
		var label = h('input', { type: 'text', placeholder: 'Label, e.g. Claude Desktop' });
		c.appendChild(h('div', { 'class': 'wpba-row' }, [h('label', {}, ['New connection token', label]), h('button', { 'class': 'button button-primary', text: 'Create token', onclick: function () {
			busy(c, true); api('/tokens', 'POST', { label: label.value }).then(function (r) { out(o, 'Copy it now, it is shown once:\n\n' + r.token + '\n\nHeader:  Authorization: Bearer ' + r.token + '\nClaude Code:  claude mcp add --transport http builder-agent-for-divi ' + D.mcp_url + ' --header "Authorization: Bearer ' + r.token + '"'); refresh(); }).catch(function (e) { out(o, 'Error: ' + e.message, 'wpba-fail'); }).then(function () { busy(c, false); });
		} })]));
		c.appendChild(o);
		function refresh() {
			api('/connect').then(function (r) {
				lists.innerHTML = '';
				var t = h('table', { 'class': 'wpba-table' }, [h('tr', {}, ['Type', 'Label / client', 'User', 'Created', 'Expires', 'Last used', ''].map(function (x) { return h('th', { text: x }); }))]);
				r.tokens.forEach(function (k) { t.appendChild(h('tr', {}, [h('td', { text: k.type }), h('td', { text: (k.label || k.client_id) + (k.prefix ? ' (' + k.prefix + '…)' : '') }), h('td', { text: k.user }), h('td', { text: k.created }), h('td', { text: k.expires }), h('td', { text: k.last_used }), h('td', {}, [h('a', { href: '#', text: 'revoke', onclick: function (e) { e.preventDefault(); api('/tokens', 'DELETE', { hash: k.hash }).then(refresh); } })])])); });
				lists.appendChild(h('h3', { text: 'Tokens (' + r.tokens.length + ')' })); lists.appendChild(t);
				var ct = h('table', { 'class': 'wpba-table' }, [h('tr', {}, ['Client', 'Client id', 'Redirects to', 'Registered', ''].map(function (x) { return h('th', { text: x }); }))]);
				r.clients.forEach(function (k) { ct.appendChild(h('tr', {}, [h('td', { text: k.client_name }), h('td', { text: k.client_id }), h('td', { text: k.redirect_uris.join(', ') }), h('td', { text: k.created }), h('td', {}, [h('a', { href: '#', text: 'disconnect', onclick: function (e) { e.preventDefault(); api('/oauth/clients', 'DELETE', { client_id: k.client_id }).then(refresh); } })])])); });
				lists.appendChild(h('h3', { text: 'Connected apps (' + r.clients.length + ')' })); lists.appendChild(ct);
				lists.appendChild(h('p', { 'class': 'wpba-muted', text: 'Tools exposed: ' + r.tools.join(', ') }));
			});
		}
		refresh();
		c.appendChild(lists);
		p.appendChild(c);
		return p;
	}

	// ---- boot ---------------------------------------------------------------------------------------
	panels.innerHTML = '';
	tabs.connect = connectPanel(); tabs.plan = planPanel(); tabs.pages = pagesPanel(); tabs.sitewide = sitewidePanel(); tabs.css = cssPanel(); tabs.runs = runsPanel(); tabs.settings = settingsPanel();
	Object.keys(tabs).forEach(function (k) { panels.appendChild(tabs[k]); });
	var initial = (window.location.hash || '#plan').slice(1);
	showTab(tabs[initial] ? initial : 'connect');
})();
