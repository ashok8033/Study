(function () {
    'use strict';

    var REFRESH_MS = 60000;

    // label + css class for each status the REST endpoint returns
    var STATUS = {
        Success:  { label: 'Success',   css: 'tsd-success' },
        Failed:   { label: 'Failed',    css: 'tsd-failed' },
        Warning:  { label: 'Warning',   css: 'tsd-warning' },
        Running:  { label: 'Running',   css: 'tsd-running' },
        NeverRun: { label: 'Never Run', css: 'tsd-never' }
    };
    var ORDER = ['Failed', 'Warning', 'Running', 'Success', 'NeverRun'];

    var rows = [];
    var activeFilter = null;
    var timer = null;

    function $(id) { return document.getElementById(id); }

    function esc(value) {
        if (value === null || value === undefined) { return ''; }
        return String(value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function fmtDate(ms) {
        return ms ? new Date(ms).toLocaleString() : '-';
    }

    function fmtDuration(start, end) {
        if (!start) { return '-'; }
        var secs = Math.max(0, Math.round(((end || Date.now()) - start) / 1000));
        var h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), s = secs % 60;
        return (h ? h + 'h ' : '') + (h || m ? m + 'm ' : '') + s + 's';
    }

    function restUrl(path) {
        if (window.PluginHelper && PluginHelper.getPluginRestUrl) {
            return PluginHelper.getPluginRestUrl(path);
        }
        return (window.SailPoint ? SailPoint.CONTEXT_PATH : '/identityiq') + '/plugin/rest/' + path;
    }

    function load() {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', restUrl('taskstatus/schedules'), true);
        xhr.setRequestHeader('Accept', 'application/json');
        if (window.PluginHelper && PluginHelper.getCsrfToken) {
            xhr.setRequestHeader('X-XSRF-TOKEN', PluginHelper.getCsrfToken());
        }
        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) {
                $('tsd-error').style.display = 'none';
                rows = JSON.parse(xhr.responseText) || [];
                $('tsd-updated').textContent = 'Last updated: ' + new Date().toLocaleString();
                render();
            } else {
                showError('Failed to load task status (HTTP ' + xhr.status + ').');
            }
        };
        xhr.onerror = function () { showError('Network error while loading task status.'); };
        xhr.send();
    }

    function showError(msg) {
        var el = $('tsd-error');
        el.textContent = msg;
        el.style.display = 'block';
    }

    function renderSummary() {
        var counts = {};
        rows.forEach(function (r) { counts[r.status] = (counts[r.status] || 0) + 1; });

        var html = '<button type="button" class="tsd-card tsd-all' + (activeFilter ? '' : ' tsd-active') +
            '" data-status="">All<span>' + rows.length + '</span></button>';
        ORDER.forEach(function (key) {
            html += '<button type="button" class="tsd-card ' + STATUS[key].css +
                (activeFilter === key ? ' tsd-active' : '') + '" data-status="' + key + '">' +
                STATUS[key].label + '<span>' + (counts[key] || 0) + '</span></button>';
        });
        $('tsd-summary').innerHTML = html;
    }

    function render() {
        renderSummary();

        var term = ($('tsd-search').value || '').toLowerCase();
        var visible = rows.filter(function (r) {
            if (activeFilter && r.status !== activeFilter) { return false; }
            if (!term) { return true; }
            return (r.scheduleName || '').toLowerCase().indexOf(term) >= 0 ||
                   (r.taskDefinition || '').toLowerCase().indexOf(term) >= 0;
        });

        // failures first, then alphabetical
        visible.sort(function (a, b) {
            var d = ORDER.indexOf(a.status) - ORDER.indexOf(b.status);
            return d !== 0 ? d : (a.scheduleName || '').localeCompare(b.scheduleName || '');
        });

        if (!visible.length) {
            $('tsd-rows').innerHTML = '<tr><td colspan="8" class="tsd-empty">No scheduled tasks found.</td></tr>';
            return;
        }

        $('tsd-rows').innerHTML = visible.map(function (r) {
            var st = STATUS[r.status] || STATUS.NeverRun;
            return '<tr class="' + st.css + '-row">' +
                '<td><span class="tsd-badge ' + st.css + '"><i></i>' + st.label + '</span></td>' +
                '<td>' + esc(r.scheduleName) + '</td>' +
                '<td>' + esc(r.taskDefinition || '-') + '</td>' +
                '<td>' + fmtDate(r.launched) + '</td>' +
                '<td>' + fmtDate(r.completed) + '</td>' +
                '<td>' + (r.launched ? fmtDuration(r.launched, r.completed) : '-') + '</td>' +
                '<td>' + fmtDate(r.nextExecution) + '</td>' +
                '<td class="tsd-msg" title="' + esc(r.message) + '">' + esc(r.message || '') + '</td>' +
                '</tr>';
        }).join('');
    }

    function scheduleRefresh() {
        if (timer) { clearInterval(timer); timer = null; }
        if ($('tsd-autorefresh').checked) { timer = setInterval(load, REFRESH_MS); }
    }

    function init() {
        $('tsd-refresh').addEventListener('click', load);
        $('tsd-search').addEventListener('input', render);
        $('tsd-autorefresh').addEventListener('change', scheduleRefresh);
        $('tsd-summary').addEventListener('click', function (e) {
            var btn = e.target.closest('.tsd-card');
            if (!btn) { return; }
            activeFilter = btn.getAttribute('data-status') || null;
            render();
        });
        load();
        scheduleRefresh();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
