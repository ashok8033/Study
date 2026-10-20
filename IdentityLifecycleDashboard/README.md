# Identity Lifecycle Dashboard – IdentityIQ Plugin

A live KPI dashboard that checks every identity's **lifecycle status** against the **status of its
application accounts**, so you can see at a glance whether identities and their accounts agree.

- An **inactive** identity (Terminated, PreHire) should have only **disabled** accounts.
- An **active** identity should have **enabled** accounts.

The defaults match this repository's HR/LDAP setup (`SailPointIIQ-HR-CSV`, see
[Lifecycle in this environment](#lifecycle-in-this-environment)); other setups only need the
plugin settings changed.

Anything else is a **mismatch**:

| Mismatch | Color | Why it matters |
|----------|-------|----------------|
| Inactive identity, **enabled** account | 🔴 Red | Access risk: a leaver can still log in |
| Active identity, **disabled** account | 🟠 Amber | The user may be missing access they need |

**Contents**

- [What the dashboard shows](#what-the-dashboard-shows)
- [How "real time" works](#how-real-time-works)
- [Requirements](#requirements)
- [Build](#build)
- [Install](#install)
- [Configuration](#configuration)
- [Lifecycle in this environment](#lifecycle-in-this-environment)
- [How statuses are compared](#how-statuses-are-compared)
- [Access control](#access-control)
- [REST API](#rest-api)
- [Performance](#performance)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [Version history](#version-history)

## What the dashboard shows

**KPI tiles**

| Tile | Meaning |
|------|---------|
| Identities | All identities (workgroups excluded), split into active / inactive |
| Accounts | Accounts in scope, split into enabled / disabled |
| Compliance | % of accounts whose state matches their identity (green ≥ 99%, amber ≥ 95%, red below) |
| Mismatched accounts | Total mismatches and how many identities they affect |
| Inactive identity, enabled account | Red mismatches |
| Active identity, disabled account | Amber mismatches |
| Locked accounts | Informational; locked is not counted as a mismatch |
| Identities without accounts | Identities with no account in scope |

**Account compliance bar** – in-sync vs red vs amber across all accounts.

**By lifecycle status** – one row per status value: the expected account state (Enabled/Disabled),
identities, accounts, enabled, disabled, mismatches and a sync bar with the in-sync percentage.

**By application** – one row per application: accounts, enabled, disabled, locked, mismatches and
sync bar, worst application first. Click a row to filter the mismatch list to that application.

**Mismatched accounts** – every mismatched account (red first) with identity, identity status,
application, account and account status. Filter by issue type, application or text, and
**Export CSV** for remediation.

## How "real time" works

- Every page load and every auto-refresh (every **30 seconds** while **Live** is ticked) asks the
  server for current numbers, calculated directly from the IdentityIQ database.
- To protect the database when several people have the page open, the server reuses a computed
  snapshot for **Cache seconds** (default 30). **Refresh now** always recalculates.
- The header shows when the data was calculated, how long it took and whether it came from cache.
- The dashboard reflects what IdentityIQ knows. Account enabled/disabled state is updated by
  **account aggregation**; identity status by your HR aggregation / identity refresh. A change made
  directly in a target system appears here after the next aggregation of that application.

## Requirements

| Item | Version |
|------|---------|
| IdentityIQ | 8.0 or later (built for 8.5) |
| JDK (to build) | 8 or later; ideally the server's version (8.5: JDK 17) |
| Apache Ant (to build) | 1.9 or later |

## Build

Same process as the Task Status Dashboard plugin:

```
cd Study/IdentityLifecycleDashboard
ant -Diiq.home="C:\Program Files\Apache Software Foundation\Tomcat 9.0\webapps\identityiq"
```

`iiq.home` is the folder containing `WEB-INF/lib/identityiq.jar`. The result is
`dist/IdentityLifecycleDashboard-<version>.zip`; upload that zip, not a zip of the source folder.

## Install

1. **Gear → Plugins → New**, upload `dist/IdentityLifecycleDashboard-<version>.zip`, **Install**.
2. Optional: **Gear → Plugins → Identity Lifecycle Dashboard → Configure**. The defaults already
   match the `SailPointIIQ-HR-CSV` setup (`status` attribute, Terminated/PreHire inactive).
3. Open:
   ```
   http://<host>:<port>/identityiq/plugins/pluginPage.jsf?pn=IdentityLifecycleDashboard
   ```

Installing creates the SPRight `ViewIdentityLifecycleDashboard` and the capability
`IdentityLifecycleDashboardViewer` ("Identity Lifecycle Dashboard Viewer").

## Configuration

**Gear → Plugins → Identity Lifecycle Dashboard → Configure.** Changes apply on the next refresh.

| Setting | Default | Description |
|---------|---------|-------------|
| Identity status attribute | `status` | Identity attribute holding the lifecycle status (here: PreHire / Active / Terminated). Blank = use the IdentityIQ **Inactive** flag (statuses *Active* / *Inactive*). |
| Inactive status values | `Terminated,PreHire` | Status values whose accounts should be **disabled**. Comma separated, case-insensitive. Every other value means accounts should be **enabled**. |
| Excluded applications | *(blank)* | Comma separated application names to leave out (e.g. applications without a disable concept). Case-insensitive. |
| Include authoritative applications | `false` | Authoritative (HR) sources are skipped by default because their accounts are not disabled the way target accounts are. |
| Cache seconds | `30` | How long a snapshot is reused. `0` = recalculate on every request. |
| Max mismatch rows | `2000` | Maximum mismatches sent to the page. KPI counts are always complete; the page notes when the list is cut off. |

Example for a different environment: identities have `employeeStatus` = `Active`, `LOA`,
`Terminated`, `Retired`. Set *Identity status attribute* = `employeeStatus` and *Inactive status
values* = `Terminated,Retired`. `Active` and `LOA` identities are then expected to have enabled accounts.

## Lifecycle in this environment

From `SailPointIIQ-HR-CSV` (branch `claude/determined-gates-e23l4w`):

- Identity attribute **`status`** is calculated on every refresh by the global rule
  `HR Lifecycle - Status Attribute` from the HR account's `startDate` / `endDate` (`DD-MM-YYYY`):

  | `status` | When | IIQ Inactive flag |
  |----------|------|-------------------|
  | PreHire | today is before `startDate` | true |
  | Active | `startDate` up to and including `endDate` | false |
  | Terminated | the day after `endDate` onwards | true |

- **LDAP ApacheDS** accounts are created only for Active identities (birthright roles need
  `status = Active`). On Terminated the workflow `HR Lifecycle - Status Change Notification` disables
  the account (`pwdAccountLockedTime: 000001010000Z` → `IIQDisabled`); on rehire it re-enables it.
  Accounts locked by failed logins get `IIQLocked` only, which the dashboard counts as *Locked*, not
  as a mismatch.
- **HR Authoritative CSV** is authoritative and skipped by default.

What the dashboard expects, and what a mismatch means here:

| Identity `status` | LDAP account should be | 🔴 / 🟠 mismatch means |
|-------------------|------------------------|------------------------|
| Active | Enabled | 🟠 disabled: rehire not re-enabled, or disabled directly in ApacheDS |
| Terminated | Disabled | 🔴 enabled: leaver not disabled (workflow failed, or terminated before the disable logic existed – run `rule "LDAP ApacheDS - Disable Terminated Users"`) |
| PreHire | Disabled / none | 🔴 enabled: access before the start date |

Data freshness: `status` changes on **HR Lifecycle - Daily Identity Refresh**; LDAP account state on
**LDAP ApacheDS - Account Aggregation** (or immediately when the workflow changes it).

## How statuses are compared

For each identity (workgroups excluded):

1. **Lifecycle status**
   - Attribute configured → the attribute value. Values are grouped case-insensitively.
     Empty → `(not set)`.
   - No attribute configured → `Inactive` if the Inactive flag is set, otherwise `Active`.
2. **Expected account state**
   - Status is in *Inactive status values* → accounts should be **disabled**.
   - Status is `(not set)` → falls back to the Inactive flag.
   - Otherwise → accounts should be **enabled**.
3. **Each account** (excluded and, by default, authoritative applications skipped) is compared:
   - Expected disabled, account enabled → 🔴 *Inactive identity, enabled account*
   - Expected enabled, account disabled → 🟠 *Active identity, disabled account*
   - Otherwise in sync. Locked accounts are counted but not treated as mismatches.

Account state is IdentityIQ's view of the account (`Link.isDisabled()` / `isLocked()`), as set by
the last aggregation or provisioning.

## Access control

| Who | Page & REST API |
|-----|-----------------|
| System Administrators | ✅ |
| Identities with the **Identity Lifecycle Dashboard Viewer** capability | ✅ |
| Everyone else | ❌ (HTTP 403) |

The page shows identity names and account IDs; grant the capability only to people allowed to see that.

## REST API

`GET /identityiq/plugin/rest/identitylifecycle/snapshot[?refresh=true]`

Requires the `ViewIdentityLifecycleDashboard` right. `refresh=true` bypasses the cache.

```json
{
  "generatedAt": 1792525305449,
  "durationMs": 842,
  "cached": false,
  "kpis": {
    "identities": 4620, "identitiesExpectEnabled": 4105, "identitiesExpectDisabled": 515,
    "identitiesWithMismatch": 52, "identitiesWithoutAccounts": 37,
    "accounts": 10540, "enabledAccounts": 9844, "disabledAccounts": 696, "lockedAccounts": 17,
    "mismatchedAccounts": 59, "inactiveIdentityEnabledAccounts": 35, "activeIdentityDisabledAccounts": 24,
    "compliancePct": 99.4
  },
  "lifecycle": [
    { "status": "Terminated", "expectEnabled": false, "identities": 470, "identitiesWithMismatch": 28,
      "accounts": 420, "enabled": 30, "disabled": 390, "locked": 0,
      "mismatches": 30, "inactiveEnabled": 30, "activeDisabled": 0 }
  ],
  "applications": [
    { "application": "Active Directory", "accounts": 4210, "enabled": 3890, "disabled": 320, "locked": 12,
      "mismatches": 27, "inactiveEnabled": 18, "activeDisabled": 9 }
  ],
  "mismatches": [
    { "issue": "InactiveIdentityEnabledAccount", "identityId": "…", "identity": "a.kumar",
      "identityDisplayName": "A Kumar", "identityStatus": "Terminated", "application": "Active Directory",
      "account": "a.kumar", "nativeIdentity": "CN=a.kumar,OU=Users,DC=corp",
      "accountStatus": "Enabled", "locked": false }
  ],
  "mismatchTotal": 59,
  "mismatchTruncated": false,
  "config": { "statusAttribute": "employeeStatus", "inactiveStatusValues": ["Terminated", "Leaver"],
              "excludedApplications": [], "includeAuthoritativeApps": false, "cacheSeconds": 30 }
}
```

`issue` is `InactiveIdentityEnabledAccount` or `ActiveIdentityDisabledAccount`.

## Performance

Each calculation reads every identity and its accounts once, releasing them from memory every
100 identities. Time grows with the number of accounts; the header shows how long each calculation
took (`… ms`). If it gets slow:

- Raise **Cache seconds** (e.g. 120 or 300) so viewers share one calculation.
- Untick **Live** and use **Refresh now** when needed.
- Add applications you don't need to **Excluded applications**.

Only one calculation runs at a time; other requests wait for it and then share the result.

## Project layout

```
IdentityLifecycleDashboard/
├── manifest.xml                          Plugin definition, REST resource, settings
├── build.xml                             Ant build → dist/IdentityLifecycleDashboard-<version>.zip
├── import/install/
│   └── IdentityLifecycleDashboardRights.xml   SPRight + Capability
├── src/com/plugin/identitylifecycle/rest/
│   ├── IdentityLifecycleResource.java    REST endpoint, settings, snapshot cache
│   └── LifecycleSnapshotBuilder.java     Walks identities/accounts, computes KPIs and mismatches
└── ui/
    ├── page.xhtml                        Page markup
    ├── js/lifecycle.js                   Loads snapshot, renders tiles/tables/bars, filters, CSV export
    └── css/lifecycle.css                 Styling
```

## Troubleshooting

See the Task Status Dashboard README's [Troubleshooting](../TaskStatusDashboard/README.md#troubleshooting)
section for finding errors (SyslogEvent on the debug page, Tomcat logs). To log this plugin in detail:

```
logger.ild.name=com.plugin.identitylifecycle
logger.ild.level=debug
```

| Symptom | Cause / fix |
|---------|-------------|
| Every identity shows `(not set)` | The `status` attribute isn't populated: run `rule "HR CSV - Setup Identity Mappings"` and **HR Lifecycle - Daily Identity Refresh**. Elsewhere: the *Identity status attribute* name is wrong – use the attribute **name**, not its display name. |
| Terminated users counted as Active | Their status value isn't in *Inactive status values* (check spelling). |
| HR application missing from the table | Authoritative applications are excluded by default; enable *Include authoritative applications*. |
| An application shows many amber mismatches | It may not support or report disable status (its accounts always look disabled/enabled). Add it to *Excluded applications*. |
| Account fixed in the target but still listed | Account state updates on the next aggregation of that application. |
| Page slow to load | See [Performance](#performance). |
| HTTP 403 | User lacks the viewer capability. |

## Version history

| Version | Changes |
|---------|---------|
| 1.0.1 | `minUpgradableVersion` moved to the `<Plugin>` element so upgrades are accepted. |
| 1.0.0 | Defaults for the `SailPointIIQ-HR-CSV` lifecycle (`status`; Terminated/PreHire inactive). KPI tiles, compliance bar, breakdown by lifecycle status and application, mismatch list with filters and CSV export, live refresh with server cache, configurable status attribute. |
