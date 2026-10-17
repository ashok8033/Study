# Task Status Dashboard – IdentityIQ Plugin

Shows the **last run status of every scheduled task** in SailPoint IdentityIQ on one page.

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green | Success | Last run completed successfully |
| 🔴 Red | Failed | Last run ended in Error, Terminated or TempError |
| 🟠 Amber | Warning | Last run completed with warnings |
| 🔵 Blue | Running | Task is running right now |
| ⚪ Grey | Never Run | Schedule has no task result yet |

Features: summary counters (click to filter), search, failures listed first, first error
message shown per task, next scheduled run, auto-refresh every 60 seconds.

## Layout

```
manifest.xml                      Plugin definition (full page + REST resource)
import/install/*.xml              SPRight + Capability created on install
src/.../TaskStatusResource.java   REST: GET /identityiq/plugin/rest/taskstatus/schedules
ui/page.xhtml                     Full-page UI
ui/js/taskstatus.js               Fetches + renders the table
ui/css/taskstatus.css             Green/red styling
build.xml                         Ant build -> dist/TaskStatusDashboard-1.0.0.zip
```

## Build

Requires JDK 8+ and Ant. Point `iiq.home` at your exploded IdentityIQ webapp
(the folder containing `WEB-INF/lib/identityiq.jar`):

```
cd TaskStatusDashboard
ant -Diiq.home=/opt/tomcat/webapps/identityiq
```

## Install

1. IdentityIQ → **Gear → Plugins → New** → upload `dist/TaskStatusDashboard-1.0.0.zip`.
2. Give users access: assign the **Task Status Dashboard Viewer** capability
   (System Administrators already have access).
3. Open: `https://<host>/identityiq/plugins/pluginPage.jsf?pn=TaskStatusDashboard`
   (also reachable from the plugin's entry in the Plugins menu).

## How the status is determined

For each `TaskSchedule`, the newest `TaskResult` whose `schedule` equals the schedule
name is used. If none is found, the newest result of the schedule's `TaskDefinition`
is used instead. The result's `completionStatus` is mapped to the colors above.
