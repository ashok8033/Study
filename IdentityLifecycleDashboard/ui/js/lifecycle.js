(function () {
    'use strict';

    var REFRESH_MS = 30000;
    var MAX_ROWS_SHOWN = 500;

    var ISSUES = {
        InactiveIdentityEnabledAccount: { label: 'Inactive identity, enabled account', css: 'ild-red' },
        ActiveIdentityDisabledAccount: { label: 'Active identity, disabled account', css: 'ild-amber' }
    };

    var data = null;
    var timer = null;
    var loading = false;

    function $(id) { return document.getElementById(id); }

    function esc(value) {
        if (value === null || value === undefined) { return ''; }
        return String(value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function num(n) { return (n || 0).toLocaleString(); }

    function pct(part, total) { return total ? Math.round(part * 1000 / total) / 10 : 0; }

    function restUrl(path) {
        if (window.PluginHelper && PluginHelper.getPluginRestUrl) {
            return PluginHelper.getPluginRestUrl(path);
        }
        return (window.SailPoint ? SailPoint.CONTEXT_PATH : '/identityiq') + '/plugin/rest/' + path;
    }

    function load(force) {
        if (loading) { return; }
        loading = true;
        $('ild-refresh').disabled = true;

        var xhr = new XMLHttpRequest();
        xhr.open('GET', restUrl('identitylifecycle/snapshot' + (force ? '?refresh=true' : '')), true);
        xhr.setRequestHeader('Accept', 'application/json');
        if (window.PluginHelper && PluginHelper.getCsrfToken) {
            xhr.setRequestHeader('X-XSRF-TOKEN', PluginHelper.getCsrfToken());
        }
        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) {
                $('ild-error').style.display = 'none';
                data = JSON.parse(xhr.responseText);
                render();
            } else {
                showError('Failed to load identity data (HTTP ' + xhr.status + ').');
            }
        };
        xhr.onerror = function () { showError('Network error while loading identity data.'); };
        xhr.onloadend = function () {
            loading = false;
            $('ild-refresh').disabled = false;
        };
        xhr.send();
    }

    function showError(msg) {
        var el = $('ild-error');
        el.textContent = msg;
        el.style.display = 'block';
    }

    // Green = in sync, red = inactive identity with enabled account, amber = active identity with disabled account
    function syncBar(total, red, amber) {
        if (!total) { return '<div class="ild-sync"><div class="ild-bar ild-bar-empty"></div><span>-</span></div>'; }
        var inSync = pct(total - red - amber, total);
        // Non-zero problems get a minimum width so a handful of mismatches is still visible
        var r = red ? Math.max(pct(red, total), 3) : 0, a = amber ? Math.max(pct(amber, total), 3) : 0;
        var g = Math.max(0, 100 - r - a);
        return '<div class="ild-sync" title="In sync ' + inSync + '% | Inactive identity, enabled account: ' + red +
            ' | Active identity, disabled account: ' + amber + '"><div class="ild-bar">' +
            '<span class="ild-green" style="width:' + g + '%"></span>' +
            '<span class="ild-red" style="width:' + r + '%"></span>' +
            '<span class="ild-amber" style="width:' + a + '%"></span></div>' +
            '<span class="' + (red ? 'ild-text-red' : '') + '">' + inSync + '%</span></div>';
    }

    function renderHeader() {
        var c = data.config || {};
        $('ild-config').textContent = 'Lifecycle status from: ' +
            (c.statusAttribute ? 'identity attribute "' + c.statusAttribute + '"' : 'IdentityIQ Inactive flag') +
            '  |  Inactive values: ' + (c.inactiveStatusValues || []).join(', ') +
            (c.includeAuthoritativeApps ? '' : '  |  Authoritative apps excluded') +
            ((c.excludedApplications || []).length ? '  |  Excluded: ' + c.excludedApplications.join(', ') : '');
        $('ild-updated').textContent = 'Data as of ' + new Date(data.generatedAt).toLocaleTimeString() +
            ' (' + data.durationMs + ' ms' + (data.cached ? ', cached' : '') + ')';
    }

    function tile(label, value, css, sub) {
        return '<div class="ild-kpi ' + (css || '') + '"><div class="ild-kpi-label">' + esc(label) + '</div>' +
            '<div class="ild-kpi-value">' + value + '</div>' +
            (sub ? '<div class="ild-kpi-sub">' + sub + '</div>' : '') + '</div>';
    }

    function renderKpis() {
        var k = data.kpis;
        var compCss = k.compliancePct >= 99 ? 'ild-kpi-green' : (k.compliancePct >= 95 ? 'ild-kpi-amber' : 'ild-kpi-red');
        $('ild-kpis').innerHTML =
            tile('Identities', num(k.identities), '',
                 num(k.identitiesExpectEnabled) + ' active · ' + num(k.identitiesExpectDisabled) + ' inactive') +
            tile('Accounts', num(k.accounts), '',
                 num(k.enabledAccounts) + ' enabled · ' + num(k.disabledAccounts) + ' disabled') +
            tile('Compliance', k.compliancePct + '%', compCss, 'accounts in sync') +
            tile('Mismatched accounts', num(k.mismatchedAccounts), k.mismatchedAccounts ? 'ild-kpi-red' : 'ild-kpi-green',
                 num(k.identitiesWithMismatch) + ' identities affected') +
            tile('Inactive identity, enabled account', num(k.inactiveIdentityEnabledAccounts),
                 k.inactiveIdentityEnabledAccounts ? 'ild-kpi-red' : 'ild-kpi-green', 'access risk') +
            tile('Active identity, disabled account', num(k.activeIdentityDisabledAccounts),
                 k.activeIdentityDisabledAccounts ? 'ild-kpi-amber' : 'ild-kpi-green', 'user may lack access') +
            tile('Locked accounts', num(k.lockedAccounts), '', 'informational') +
            tile('Identities without accounts', num(k.identitiesWithoutAccounts), '', 'in scope');

        $('ild-compliance').innerHTML = syncBar(k.accounts, k.inactiveIdentityEnabledAccounts, k.activeIdentityDisabledAccounts) +
            '<div class="ild-legend"><span><i class="ild-green"></i>In sync ' + num(k.accounts - k.mismatchedAccounts) + '</span>' +
            '<span><i class="ild-red"></i>Inactive identity, enabled account ' + num(k.inactiveIdentityEnabledAccounts) + '</span>' +
            '<span><i class="ild-amber"></i>Active identity, disabled account ' + num(k.activeIdentityDisabledAccounts) + '</span></div>';
    }

    function renderLifecycle() {
        var rows = (data.lifecycle || []).slice().sort(function (a, b) { return b.identities - a.identities; });
        if (!rows.length) {
            $('ild-lifecycle').innerHTML = '<tr><td colspan="8" class="ild-empty">No identities found.</td></tr>';
            return;
        }
        $('ild-lifecycle').innerHTML = rows.map(function (r) {
            return '<tr><td><b>' + esc(r.status) + '</b></td>' +
                '<td><span class="ild-badge ' + (r.expectEnabled ? 'ild-green' : 'ild-grey') + '">' +
                (r.expectEnabled ? 'Enabled' : 'Disabled') + '</span></td>' +
                '<td class="num">' + num(r.identities) + '</td><td class="num">' + num(r.accounts) + '</td>' +
                '<td class="num">' + num(r.enabled) + '</td><td class="num">' + num(r.disabled) + '</td>' +
                '<td class="num ' + (r.mismatches ? 'ild-text-red' : '') + '">' + num(r.mismatches) + '</td>' +
                '<td>' + syncBar(r.accounts, r.inactiveEnabled, r.activeDisabled) + '</td></tr>';
        }).join('');
    }

    function renderApps() {
        var rows = (data.applications || []).slice().sort(function (a, b) {
            return b.mismatches - a.mismatches || a.application.localeCompare(b.application);
        });
        if (!rows.length) {
            $('ild-apps').innerHTML = '<tr><td colspan="7" class="ild-empty">No application accounts in scope.</td></tr>';
            return;
        }
        $('ild-apps').innerHTML = rows.map(function (r) {
            return '<tr class="ild-click" data-app="' + esc(r.application) + '"><td><b>' + esc(r.application) + '</b></td>' +
                '<td class="num">' + num(r.accounts) + '</td><td class="num">' + num(r.enabled) + '</td>' +
                '<td class="num">' + num(r.disabled) + '</td><td class="num">' + num(r.locked) + '</td>' +
                '<td class="num ' + (r.mismatches ? 'ild-text-red' : '') + '">' + num(r.mismatches) + '</td>' +
                '<td>' + syncBar(r.accounts, r.inactiveEnabled, r.activeDisabled) + '</td></tr>';
        }).join('');

        // Keep the application filter in step with the data
        var select = $('ild-f-app'), current = select.value;
        select.innerHTML = '<option value="">All applications</option>' + rows.map(function (r) {
            return '<option value="' + esc(r.application) + '">' + esc(r.application) + '</option>';
        }).join('');
        select.value = current;
    }

    function filteredMismatches() {
        var issue = $('ild-f-issue').value, app = $('ild-f-app').value;
        var term = ($('ild-f-search').value || '').toLowerCase();
        return (data.mismatches || []).filter(function (m) {
            if (issue && m.issue !== issue) { return false; }
            if (app && m.application !== app) { return false; }
            if (!term) { return true; }
            return [m.identity, m.identityDisplayName, m.account, m.nativeIdentity].some(function (v) {
                return (v || '').toLowerCase().indexOf(term) >= 0;
            });
        }).sort(function (x, y) {
            // Access risk (inactive identity, enabled account) first, then by application and identity
            var ix = x.issue === 'InactiveIdentityEnabledAccount' ? 0 : 1;
            var iy = y.issue === 'InactiveIdentityEnabledAccount' ? 0 : 1;
            return ix - iy || (x.application || '').localeCompare(y.application || '') ||
                (x.identity || '').localeCompare(y.identity || '');
        });
    }

    function renderMismatches() {
        if (!data) { return; }
        var rows = filteredMismatches();
        var note = num(rows.length) + ' shown';
        if (data.mismatchTruncated) {
            note += ' — list limited to the first ' + num(data.mismatches.length) + ' of ' + num(data.mismatchTotal) +
                ' mismatches (plugin setting "Max mismatch rows")';
        }
        $('ild-mm-count').textContent = note;

        if (!rows.length) {
            $('ild-mismatches').innerHTML = '<tr><td colspan="6" class="ild-empty">' +
                (data.mismatchTotal ? 'No mismatches match the filter.' : 'All accounts are in sync with their identities.') +
                '</td></tr>';
            return;
        }
        $('ild-mismatches').innerHTML = rows.slice(0, MAX_ROWS_SHOWN).map(function (m) {
            var issue = ISSUES[m.issue] || { label: m.issue, css: 'ild-grey' };
            return '<tr><td><span class="ild-badge ' + issue.css + '">' + esc(issue.label) + '</span></td>' +
                '<td><b>' + esc(m.identityDisplayName || m.identity) + '</b><div class="ild-sub">' + esc(m.identity) + '</div></td>' +
                '<td>' + esc(m.identityStatus) + '</td><td>' + esc(m.application) + '</td>' +
                '<td>' + esc(m.account || m.nativeIdentity) +
                (m.account && m.account !== m.nativeIdentity ? '<div class="ild-sub">' + esc(m.nativeIdentity) + '</div>' : '') + '</td>' +
                '<td>' + esc(m.accountStatus) + (m.locked ? ' <span class="ild-badge ild-grey">Locked</span>' : '') + '</td></tr>';
        }).join('') + (rows.length > MAX_ROWS_SHOWN
            ? '<tr><td colspan="6" class="ild-empty">Showing first ' + MAX_ROWS_SHOWN + ' rows. Narrow the filter or export CSV for all.</td></tr>'
            : '');
    }

    function exportCsv() {
        if (!data) { return; }
        var cols = ['issue', 'identity', 'identityDisplayName', 'identityStatus', 'application', 'account', 'nativeIdentity', 'accountStatus', 'locked'];
        var lines = [cols.join(',')].concat(filteredMismatches().map(function (m) {
            return cols.map(function (c) {
                var v = c === 'issue' && ISSUES[m.issue] ? ISSUES[m.issue].label : m[c];
                v = v === null || v === undefined ? '' : String(v);
                return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
            }).join(',');
        }));
        var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'identity-lifecycle-mismatches.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    function render() {
        renderHeader();
        renderKpis();
        renderLifecycle();
        renderApps();
        renderMismatches();
    }

    function scheduleRefresh() {
        if (timer) { clearInterval(timer); timer = null; }
        if ($('ild-autorefresh').checked) { timer = setInterval(function () { load(false); }, REFRESH_MS); }
    }

    function init() {
        $('ild-refresh').addEventListener('click', function () { load(true); });
        $('ild-autorefresh').addEventListener('change', scheduleRefresh);
        $('ild-f-issue').addEventListener('change', renderMismatches);
        $('ild-f-app').addEventListener('change', renderMismatches);
        $('ild-f-search').addEventListener('input', renderMismatches);
        $('ild-export').addEventListener('click', exportCsv);
        $('ild-apps').addEventListener('click', function (e) {
            var row = e.target.closest('.ild-click');
            if (!row) { return; }
            $('ild-f-app').value = row.getAttribute('data-app');
            renderMismatches();
            $('ild-f-app').scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        load(false);
        scheduleRefresh();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
