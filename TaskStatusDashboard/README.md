# Task Status Dashboard – IdentityIQ Plugin

A SailPoint IdentityIQ plugin that shows the **last run status of every scheduled task** on
one page, color coded so failures stand out, and can email the same report on demand.

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green | Success | Last run completed successfully |
| 🔴 Red | Failed | Last run ended in Error, Terminated or TempError |
| 🟠 Amber | Warning | Last run completed with warnings |
| 🔵 Blue | Running | Task is running right now |
| ⚪ Grey | Never Run | Schedule has no task result yet |

**Contents**

- [Features](#features)
- [Requirements](#requirements)
- [Build](#build)
- [Install](#install)
- [Upgrade](#upgrade)
- [Using the dashboard](#using-the-dashboard)
- [Email report](#email-report)
- [Access control](#access-control)
- [Configuration](#configuration)
- [How the status is determined](#how-the-status-is-determined)
- [REST API](#rest-api)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Version history](#version-history)

## Features

- One row per scheduled task with status, task definition, last start/end time, duration,
  next scheduled run and the first error message.
- Summary counters per status; click a counter to show only those tasks.
- Search by schedule or task definition name.
- Failed tasks listed first, then Warning, Running, Success, Never Run.
- Auto-refresh every 60 seconds (can be switched off) plus a manual **Refresh** button.
- **Email Report** button that sends the current status as a formatted HTML email.
- **Scheduled Task Status** quick link.
- Access limited by a dedicated right and capability.

## Requirements

| Item | Version |
|------|---------|
| IdentityIQ | 8.0 or later (used on 8.5) |
| JDK (to build) | 8 or later; use the same major version as the IdentityIQ server where possible (8.5: JDK 17) |
| Apache Ant (to build) | 1.9 or later |
| IdentityIQ mail settings | Only needed for the Email Report button |

Plugins must be enabled in IdentityIQ (`plugins.enabled=true` in `WEB-INF/classes/iiq.properties`,
the default).

## Build

The build compiles the Java code against IdentityIQ's own libraries and packages everything
into a zip. It runs on any machine that has Java, Ant and a copy of the IdentityIQ `WEB-INF/lib`
folder; the IdentityIQ server itself is simplest.

1. Get the code:
   ```
   git clone https://github.com/ashok8033/Study.git
   cd Study/TaskStatusDashboard
   ```
2. Find the IdentityIQ webapp folder: the folder containing `WEB-INF/lib/identityiq.jar`, e.g.
   - Windows: `C:\Program Files\Apache Software Foundation\Tomcat 9.0\webapps\identityiq`
   - Linux: `/opt/tomcat/webapps/identityiq`

   To search for it on Windows (PowerShell):
   ```powershell
   Get-ChildItem -Path C:\ -Filter identityiq.jar -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
   ```
3. Run Ant, passing that folder as `iiq.home`:
   ```
   ant -Diiq.home="C:\Program Files\Apache Software Foundation\Tomcat 9.0\webapps\identityiq"
   ```
   On success it prints `Plugin built: dist/TaskStatusDashboard-<version>.zip`.

`iiq.home` is only read from, never modified. The build writes to `build/` (temporary) and
`dist/` (the zip) inside the plugin folder; neither is committed to git.

What the build does (`build.xml`):

| Target | Result |
|--------|--------|
| `compile` | `src/**/*.java` → `build/classes` |
| `jar` | `build/stage/lib/TaskStatusDashboard.jar` |
| `dist` (default) | Copies `manifest.xml`, `ui/`, `import/` next to the jar and zips it to `dist/` |

The zip must have `manifest.xml`, `lib/`, `ui/` and `import/` at its top level. A zip of the
repository or source folder (e.g. GitHub's "Download ZIP") is **not** a valid plugin package;
always upload the zip from `dist/`.

## Install

1. Log in to IdentityIQ as an administrator (e.g. `spadmin`).
2. **Gear → Plugins → New**, drop in `dist/TaskStatusDashboard-<version>.zip`, click **Install**.
3. Log out and back in (quick links are loaded at login).
4. Open the dashboard from the **Scheduled Task Status** quick link, or directly:
   ```
   http://<host>:<port>/identityiq/plugins/pluginPage.jsf?pn=TaskStatusDashboard
   ```

On install the plugin imports `import/install/*.xml`, creating:

| Object | Name |
|--------|------|
| SPRight | `ViewTaskStatusDashboard` |
| Capability | `TaskStatusDashboardViewer` ("Task Status Dashboard Viewer") |
| DynamicScope (Quicklink Population) | `Task Status Dashboard Viewers` |
| QuickLink | `Task Status Dashboard` (shown as "Scheduled Task Status", category `Tasks`) |

## Upgrade

1. Raise the version in **both** `manifest.xml` (`version`) and `build.xml` (`plugin.version`).
2. Build and upload the new zip as in [Install](#install). IdentityIQ replaces the old version.
   Check **Configure** afterwards that the Report recipients setting is still as expected.

On upgrade IdentityIQ imports `import/upgrade/*.xml` instead of `import/install/*.xml`. Any object
added after 1.0.0 must be placed in both folders so fresh installs and upgrades both get it.
`minUpgradableVersion` in `manifest.xml` is the oldest version that can upgrade in place (1.0.0).

## Using the dashboard

```
┌ Scheduled Task Status ──────────── [Search…] [✓ Auto-refresh] [Refresh] [Email Report] ┐
│ [All 7] [Failed 1] [Warning 0] [Running 0] [Success 6] [Never Run 0]                  │
│ Last updated: 20/10/2026, 21:29:42                                                     │
│ Status    Schedule        Task Definition  Started  Completed  Duration  Next Run  Msg  │
│ ● Failed  AD Aggregation  Aggregate AD     …        …          1m 5s     …         …    │
│ ● Success Full Refresh    Full Refresh     …        …          7s        …              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Counters** – click one to filter the table; click **All** to clear.
- **Search** – filters by schedule or task definition name as you type.
- **Auto-refresh** – reloads data every 60 seconds while ticked.
- **Message** – the first error of the last run; hover to see the full text.
- Times are shown in the browser's local time zone.

## Email report

**Email Report** sends the current status to the configured recipients. The email contains:

- Subject: `IdentityIQ Scheduled Task Status - <n> failed`
- Colored summary tiles with the count per status.
- One block per task (failures first) with a colored stripe and status badge, followed by
  task definition, started, completed, duration and next run; errors on a separate red line.
- Times in the IdentityIQ server's time zone (stated in the email header).

The page shows "Report sent to …" on success, or the error message on failure.

Prerequisites:

- **Gear → Global Settings → IdentityIQ Configuration → Mail Settings** must have a working SMTP
  host, port and From address. For Gmail: `smtp.gmail.com`, port 587, TLS, and a Gmail
  [app password](https://support.google.com/accounts/answer/185833).
- Recipients set in [Configuration](#configuration).

The email is laid out with `div`/`span` only: on IdentityIQ 8.5 table tags were stripped from the
sent mail, collapsing a table layout into one run of text.

## Access control

| Who | Dashboard page & REST API | Quick link |
|-----|---------------------------|------------|
| System Administrators | ✅ | ✅ |
| Identities with the **Task Status Dashboard Viewer** capability | ✅ | ✅ |
| Everyone else | ❌ (HTTP 403) | Hidden |

To grant access: **Identities → select identity → Attributes → Capabilities**, add
**Task Status Dashboard Viewer**, save.

Both REST endpoints require the `ViewTaskStatusDashboard` right, so the data is protected even if
the quick link is shown more widely.

## Configuration

**Gear → Plugins → Task Status Dashboard → Configure**

| Setting | Default | Description |
|---------|---------|-------------|
| Report recipients (`reportRecipients`) | `ashokhearts@gmail.com` | Comma separated email addresses for the Email Report button |

Code-level settings:

| What | Where |
|------|-------|
| Auto-refresh interval (60 s) | `REFRESH_MS` in `ui/js/taskstatus.js` |
| Status colors (page) | `ui/css/taskstatus.css` |
| Status colors / layout (email) | `STATUS` map in `TaskStatusReport.java` |
| Quick link label, category, audience | `import/*/TaskStatusDashboardQuickLink.xml` |

## How the status is determined

For every `TaskSchedule`:

1. The task definition is read from the schedule's `executor` argument.
2. The newest `TaskResult` (by `launched`) whose `schedule` property equals the schedule name is
   used. If there is none, the newest result of the schedule's `TaskDefinition` is used instead.
3. The result is mapped to a status:

| TaskResult | Status |
|------------|--------|
| No result found | Never Run |
| `completed` is empty | Running |
| `completionStatus` = Success (or empty) | Success |
| `completionStatus` = Warning | Warning |
| `completionStatus` = Error, Terminated, TempError | Failed |

Notes:

- Task results are pruned by IdentityIQ's housekeeping (result expiration / Perform Maintenance).
  A schedule whose results have expired shows as **Never Run**.
- Schedules that fail to read are logged (`com.plugin.taskstatus.rest.TaskStatusResource`) and
  skipped rather than breaking the whole page.

## REST API

Base URL: `/identityiq/plugin/rest/taskstatus`. Both endpoints need an authenticated session with
the `ViewTaskStatusDashboard` right; POST requests also need the `X-XSRF-TOKEN` header
(the page sends it automatically).

### `GET /schedules`

Returns one object per schedule, sorted by schedule name. Dates are epoch milliseconds.

```json
[
  {
    "scheduleName": "Full Identity Refresh",
    "description": null,
    "taskDefinition": "Full Identity Refresh",
    "cron": ["0 25 19 * * ?"],
    "nextExecution": 1792603500000,
    "status": "Success",
    "completionStatus": "Success",
    "resultId": "c0a801a1...",
    "resultName": "Full Identity Refresh",
    "launched": 1792531569000,
    "completed": 1792531576000,
    "host": "Ashokkumar",
    "message": null
  }
]
```

`status` is one of `Success`, `Failed`, `Warning`, `Running`, `NeverRun`.

### `POST /email`

Sends the report to the configured recipients.

| Response | Body |
|----------|------|
| 200 | `{"recipients": "ashokhearts@gmail.com"}` |
| 400 | `{"message": "No recipients configured ..."}` |
| 500 | `{"message": "Failed to send email: <reason>"}` |

## Project layout

```
TaskStatusDashboard/
├── manifest.xml                         Plugin definition: name, version, right, full page,
│                                        REST resource, settings
├── build.xml                            Ant build → dist/TaskStatusDashboard-<version>.zip
├── import/
│   ├── install/                         Imported on fresh install
│   │   ├── TaskStatusDashboardRights.xml     SPRight + Capability
│   │   └── TaskStatusDashboardQuickLink.xml  DynamicScope + QuickLink
│   └── upgrade/                         Imported on upgrade
│       └── TaskStatusDashboardQuickLink.xml
├── src/com/plugin/taskstatus/rest/
│   ├── TaskStatusResource.java          REST endpoints, status logic, email sending
│   └── TaskStatusReport.java            HTML email rendering
└── ui/
    ├── page.xhtml                       Full page markup
    ├── js/taskstatus.js                 Loads data, renders table, filters, email button
    └── css/taskstatus.css               Page styling and status colors
```

## Troubleshooting

### Finding the real error

The IdentityIQ UI only shows a generic message. The details are in:

1. **Syslog** – `http://<host>:<port>/identityiq/debug/debug.jsf` → object type **SyslogEvent**
   → sort by created date, open the newest entry.
2. **Log files** – check `WEB-INF/classes/log4j2.properties` for an active
   `appender.file.fileName`. If it is commented out, output goes to Tomcat's `logs` folder
   (Windows service: `tomcat9-stdout.<date>.log`). Search for `TaskStatusDashboard`:
   ```powershell
   Select-String -Path "<Tomcat>\logs\*.log" -Pattern "TaskStatusDashboard|PluginInstaller" | Select-Object -Last 20
   ```
3. **More detail** – add to `log4j2.properties`, then *Reload Logging Configuration* on the debug
   page:
   ```
   logger.plugin.name=sailpoint.plugin
   logger.plugin.level=debug
   logger.tsd.name=com.plugin.taskstatus
   logger.tsd.level=debug
   ```

### Common problems

| Symptom | Cause / fix |
|---------|-------------|
| `ant` fails with `cannot find symbol … sailpoint` | `iiq.home` does not point at the folder containing `WEB-INF/lib`. |
| Install fails: `Attribute "…" must be declared for element type "…"` | An XML file in `import/` uses an attribute IdentityIQ's DTD does not allow (e.g. `description` on `SPRight`). Remove it, rebuild. Check the zip contains the fixed file. |
| Install fails right after a fix | The uploaded zip is an old build. Rebuild from the latest `main` and upload the zip from `dist/`. |
| No Plugins entry under the gear icon | Set `plugins.enabled=true` in `iiq.properties` and restart Tomcat. |
| Page loads but shows "Failed to load task status (HTTP 403)" | User lacks the `ViewTaskStatusDashboard` right – assign the viewer capability. |
| Quick link not visible | IIQ 8.5 shows no category called `Custom`, so the link uses `Tasks`. Re-import `import/install/TaskStatusDashboardQuickLink.xml` from the console if an older copy still says `Custom`. Then log out and back in, and check the user is in the **Task Status Dashboard Viewers** population (Gear → Global Settings → Quicklink Populations). |
| Email Report: "Failed to send email" | IdentityIQ mail settings missing or wrong; see the syslog for the SMTP error. |
| Email arrives as one run of text | You are on a version before 1.0.3 (table-based email). Upgrade. |
| Email not received | Check spam; check the **Report recipients** setting. |
| A task shows Never Run but has run before | Its task results have been pruned by IdentityIQ housekeeping. |

## Version history

| Version | Changes |
|---------|---------|
| 1.0.3 | Email report laid out without tables so it renders correctly in mail clients. |
| 1.0.2 | **Email Report** button and `reportRecipients` setting. |
| 1.0.1 | **Scheduled Task Status** quick link and its population. |
| 1.0.0 | Dashboard page, REST endpoint, right and capability. Install XML fixed to pass IdentityIQ DTD validation. |
