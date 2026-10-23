# SailPoint IIQ – HR Authoritative Source (Delimited File / CSV)

| Item | Value |
|---|---|
| Application name | `HR Authoritative CSV` |
| Connector | Delimited File (`sailpoint.connector.DelimitedFileConnector`) |
| Delimiter | `|` (pipe) |
| Date format | `DD-MM-YYYY` |
| Account ID / correlation key | `employeeNumber` |

## Layout

```
ldif/ApacheDS-ou-people-and-groups.ldif                  creates ou=people, ou=groups and the role groups in ApacheDS
data/HR_Employees.csv                                    sample HR feed (16 rows)
config/init-HR-CSV.xml                                   imports everything in order
config/Rule/Rule-HR_CSV-Customization.xml                trims values, checks dates, works out status + inactive
config/Rule/Rule-HR_CSV-Correlation.xml                  account -> identity on employeeNumber
config/Rule/Rule-HR_CSV-ManagerCorrelation.xml           managerId -> manager identity
config/Rule/Rule-HR_CSV-IdentityCreation.xml             name, displayName, first/last name, identity type
config/Application/Application-HR_Authoritative_CSV.xml  app, schema, Create Account policy
config/TaskDefinition/TaskDefinition-HR_CSV-Aggregation.xml
config/Rule/Rule-HR_CSV-SetupIdentityMappings.xml        adds the identity mappings + status attribute (run once)
config/Rule/Rule-HR_Lifecycle-StatusAttribute.xml        global rule: calculates identity "status"
config/Rule/Rule-HR_CSV-DisplayName.xml                  global rule: displayName = "firstName lastName" from HR
config/Rule/Rule-HR_CSV-ShowOnIdentityPage.xml           shows HR attributes on View Identity (run once)
config/Rule/Rule-HR_CSV-Diagnose.xml                     read-only troubleshooting report
config/Rule/Rule-HR_Lifecycle-SendTestEmail.xml          prints mail settings and sends one test email
config/EmailTemplate/EmailTemplate-HR_Lifecycle-StatusChange.xml
config/Workflow/Workflow-HR_Lifecycle-StatusChange.xml   sends the status-change email
config/IdentityTrigger/IdentityTrigger-HR_Lifecycle-StatusChange.xml   lifecycle event on "status" change
config/TaskDefinition/TaskDefinition-HR_Lifecycle-DailyRefresh.xml    refresh + process events (schedule daily)
```

## CSV columns

`employeeNumber|firstName|lastName|startDate|endDate|managerId|jobDescription|country|employeeType|isManager`

- `endDate` and `managerId` may be blank. Ashok Kumar (1000) is at the top and has no manager.
- `isManager` is `Y` or `N`. A blank or invalid value is treated as `N`.
- In the sample data, every other user reports to Ashok Kumar (1000), and he is the only one with `isManager = Y`.
- `employeeType` is one of `Employee`, `Contractor` or `Intern`.

## Calculated attributes (Customization rule)

| status | Condition | inactive |
|---|---|---|
| Terminated | endDate is earlier than today (still Active on the end date) | true |
| PreHire | startDate is later than today | true |
| Active | otherwise | false |

## Deploy

1. Copy `data/HR_Employees.csv` to the IIQ server, then update the `file` entry in the Application XML
   (default: `C:/SailPoint/hrfeed/HR_Employees.csv`).
2. Import the objects. In the IIQ console run `import <path>/config/init-HR-CSV.xml`, or import each file
   through **Global Settings > Import from File**. Import the rules first.
3. Add the identity mappings by running the setup rule once, from the IIQ console:
   `rule "HR CSV - Setup Identity Mappings"` (or from **Debug > Rule > Run**).
   The rule adds the HR mappings to your existing Identity ObjectConfig without replacing it,
   and you can run it again safely. Afterwards, check **Global Settings > Identity Mappings**.
   The `manager` identity attribute must be sourced from `managerId` so that manager correlation works.
4. Run **HR Authoritative CSV - Account Aggregation** twice on the first load, then run **Refresh Identity Cube**.
   Managers are resolved only when the manager's identity already exists, so the first run can miss some managers.

## Create Account policy

The policy is `ProvisioningForms > Form type="Create"` in the Application XML. Each field reads its value
from the Identity cube. `startDate` and `endDate` have validation scripts that enforce `DD-MM-YYYY`, and
`employeeType` is restricted to Employee, Contractor or Intern.

Note: the Delimited File connector is read-only. A Create request on this application becomes a manual
work item unless you add a provisioning integration. To reuse the policy on a target application such as AD,
copy the `<Form>` into that application and rename the fields to match its schema.

## Lifecycle status and email notification

The identity attribute **Status** (`status`) is calculated on every identity refresh by the
global rule `HR Lifecycle - Status Attribute`, from the HR `startDate` and `endDate`:

| Status | When |
|---|---|
| PreHire | today is before startDate |
| Active | from startDate up to and including endDate |
| Terminated | the day after endDate onwards |

When `status` changes (for example PreHire -> Active, or Active -> Terminated), the lifecycle event
**HR Lifecycle - Status Change** starts the workflow **HR Lifecycle - Status Change Notification**.
The workflow emails `ashokhearts@gmail.com`; to change the address, edit the `notifyEmail` variable
in the workflow. The first time `status` is set on an identity there is no previous value, so no email is sent.

Setup:

1. Import `config/init-HR-CSV.xml`.
2. Run `rule "HR CSV - Setup Identity Mappings"` in the IIQ console, then
   `rule "HR CSV - Show Attributes On Identity Page"` so Status, Start Date, End Date etc.
   appear on the View Identity > Attributes tab (log out and back in afterwards).
3. Configure mail in **Global Settings > IdentityIQ Configuration > Mail Settings**. For Gmail use
   `smtp.gmail.com`, port 587, TLS, and a Google *app password* (not your normal password).
   To test without SMTP, set the email notifier to write to a file instead.
4. Run **HR Authoritative CSV - Account Aggregation**, then **HR Lifecycle - Daily Identity Refresh**.
   This first refresh only sets the initial status, so no emails are sent.
5. Schedule **HR Lifecycle - Daily Identity Refresh** to run every day just after midnight,
   so people move between states on the right day even when the CSV has not changed.

To test: change a user's `endDate` in the CSV to yesterday's date, then run the aggregation and
the daily refresh. Their status changes to Terminated and an email is sent.

## LDAP (ApacheDS) - role-based provisioning

| Item | Value |
|---|---|
| Application | `LDAP ApacheDS` (LDAP connector) |
| Server | `localhost:10389`, bind `uid=admin,ou=system` / `secret` (ApacheDS defaults) |
| Users | `uid=<firstname.lastname>,ou=people,dc=example,dc=com` |
| Groups | `groupOfUniqueNames` in `ou=groups,dc=example,dc=com`, member attribute `uniqueMember` |
| Initial password | `Welcome@<employeeNumber>` (lab only) |

LDAP access is granted only through roles. Birthright **business roles** are assigned automatically by
their assignment rules, and each requires an **IT role** that grants one LDAP group. If the identity has
no LDAP account yet, IIQ creates it first with the application's Create Account policy.

| Business role | Assigned when | IT role | LDAP group |
|---|---|---|---|
| Birthright - All Active Users | status = Active | LDAP - All Employees | cn=AllEmployees |
| Birthright - Contractors | status = Active and employeeType = Contractor | LDAP - Contractors | cn=Contractors |
| Birthright - Managers | status = Active and isManager = Y | LDAP - Managers | cn=Managers |

The roles are evaluated by **HR Lifecycle - Daily Identity Refresh** (refresh attributes, process events,
refresh roles, provision assignments). When someone stops matching, for example their status becomes
Terminated, the role is removed and the group membership is taken away. The LDAP account itself stays.

Files:

- `ldif/ApacheDS-ou-people-and-groups.ldif`: `ou=people`, `ou=groups` and the three groups
- `config/Application/Application-LDAP_ApacheDS.xml`: connection, account and group schema, **Create Account policy**
- `config/Rule/Rule-LDAP_ApacheDS-Correlation.xml`: links LDAP accounts to identities by employeeNumber
- `config/Rule/Rule-LDAP_ApacheDS-Library.xml`: shared LDAP (JNDI) functions for group membership
- `config/Rule/Rule-LDAP_ApacheDS-BeforeProvisioning.xml`: takes `groups` out of the LDAP request
- `config/Rule/Rule-LDAP_ApacheDS-AfterProvisioning.xml`: adds/removes the user in each group's `uniqueMember`
- `config/Rule/Rule-LDAP_ApacheDS-Customization.xml`: reads each account's groups during aggregation
- `config/Bundle/Bundle-LDAP_ApacheDS-ITRoles.xml`: the three IT roles
- `config/Bundle/Bundle-Birthright-BusinessRoles.xml`: the three business roles with assignment rules
- `config/TaskDefinition/TaskDefinition-LDAP_ApacheDS-Aggregation.xml`

Setup:

1. In Apache Directory Studio, import `ldif/ApacheDS-ou-people-and-groups.ldif` under `dc=example,dc=com`.
2. Import `config/init-HR-CSV.xml`.
3. Open **Applications > LDAP ApacheDS > Configuration**, re-enter the bind password, and click **Test Connection**.
4. If LDAP accounts already exist, run **LDAP ApacheDS - Account Aggregation** first so IIQ knows about them.
5. Run **HR Lifecycle - Daily Identity Refresh**. Active identities get the roles, an LDAP account and their groups.
6. Run **LDAP ApacheDS - Account Aggregation** to read the accounts and group memberships back.

## Requestable role: Office365 Access

| Role | Type | How it is given | Entitlement |
|---|---|---|---|
| Office365 Access | business | **Request only** (no assignment rule) | via the IT role below |
| LDAP - Office365Access | IT | required by Office365 Access | LDAP ApacheDS `groups` = `cn=Office365Access,ou=groups,dc=example,dc=com` |

Files:

- `ldif/ApacheDS-group-Office365Access.ldif`: the LDAP group (also added to `ApacheDS-ou-people-and-groups.ldif`)
- `config/ManagedAttribute/ManagedAttribute-LDAP_Office365Access.xml`: the entitlement in the catalog, requestable
- `config/Bundle/Bundle-Office365Access.xml`: the IT role and the requestable business role

Setup:

1. Import `ldif/ApacheDS-group-Office365Access.ldif` in Apache Directory Studio.
2. Import `config/ManagedAttribute/ManagedAttribute-LDAP_Office365Access.xml`, then `config/Bundle/Bundle-Office365Access.xml`.
3. Request it: **Manage Access > Request Access**, pick a user, search for *Office365 Access*, submit.
   Requesting needs Lifecycle Manager; without it, assign the role to an identity as an administrator
   (Identities > open the identity > Roles / Entitlements, or Setup > Roles).
4. After approval the user is added to `cn=Office365Access`. Run **LDAP ApacheDS - Account Aggregation** to read it back.

## LDAP account status

During **LDAP ApacheDS - Account Aggregation** the Customization rule reads ApacheDS's password-policy and
operational attributes for each account and adds:

| IIQ account attribute | From ApacheDS | Value |
|---|---|---|
| `accountStatus` | `pwdAccountLockedTime` | `Active` (not set), `Disabled` (`000001010000Z`, admin lock), `Locked` (any other time: failed logins) |
| `pwdAccountLockedTime` | same | the raw ApacheDS value (`000001010000Z`, a timestamp, or empty) |
| `IIQDisabled` / `IIQLocked` | same | IIQ's own disabled/locked flags, so the account shows as disabled or locked in the UI |
| `lockedTime` | `pwdAccountLockedTime` | when it was locked by failed logins |
| `lastFailedLogin` | `pwdFailureTime` | last failed login |
| `passwordLastChanged` | `pwdChangedTime` | last password change |
| `createdOn` / `modifiedOn` | `createTimestamp` / `modifyTimestamp` | entry created / last changed |

Times are shown as `DD-MM-YYYY HH:mm:ss UTC`.

To test, disable an account in Apache Directory Studio by adding
`pwdAccountLockedTime: 000001010000Z` to it, run the LDAP aggregation, and the account shows as Disabled in IIQ.
Remove the attribute and aggregate again to make it Active.

## Display Name

The identity attribute **Display Name** (`displayName`) is calculated by the global rule
`HR CSV - Display Name` on every refresh:

```
displayName = firstName + " " + lastName      (from the HR Authoritative CSV account)
```

It is pushed to the **LDAP ApacheDS** account attribute `displayName` through an attribute sync target.
The daily refresh has *Synchronize attributes* on, so when the HR name changes the LDAP
`displayName` is updated on the next refresh. New LDAP accounts already get it from the Create Account policy.

Setup:

1. Import `Rule-HR_CSV-DisplayName.xml`, `Rule-HR_CSV-SetupIdentityMappings.xml`, `Rule-HR_CSV-ShowOnIdentityPage.xml`
   and `TaskDefinition-HR_Lifecycle-DailyRefresh.xml`.
2. Run `rule "HR CSV - Setup Identity Mappings"` (prints `displayName -> LDAP ApacheDS:displayName (sync target)`).
3. Run `rule "HR CSV - Show Attributes On Identity Page"`, then log out and back in.
4. Run the HR aggregation and **HR Lifecycle - Daily Identity Refresh**.

## Aggregating a single account

`config/Rule/Rule-Aggregate-Single-Account.xml` re-reads **one** account and runs it through the normal
aggregation (customization rule, correlation, attribute promotion). It works for both applications:
LDAP fetches the account directly; for the HR CSV the file is read and only the matching row is used.

Edit `APP_NAME` and `ACCOUNT_ID` at the top of the rule (defaults: `HR Authoritative CSV` / `1000`), then:

```
rule "Aggregate Single Account"
```

Account IDs: HR CSV = employeeNumber (`1000`); LDAP = DN (`uid=ashok.kumar,ou=people,dc=example,dc=com`).
For LDAP you can also use the refresh icon on the account in Identity > Application Accounts.
Afterwards run **HR Lifecycle - Daily Identity Refresh** if roles or LDAP sync should follow.

## Leaver / rehire: LDAP account disable and enable

| Status change | LDAP ApacheDS account | HR account in IIQ |
|---|---|---|
| ... -> **Terminated** | **disabled**: `pwdAccountLockedTime: 000001010000Z` | shown disabled (`IIQDisabled`) |
| Terminated -> **Active** (rehire) | **enabled**: `pwdAccountLockedTime` removed | shown active |

The lifecycle workflow *HR Lifecycle - Status Change Notification* calls the rule
`LDAP ApacheDS - Set Account Status`, which changes ApacheDS directly and updates the IIQ account straight away.
The birthright roles are removed by the daily refresh, which also takes the person out of the LDAP groups.
The LDAP result is included in the status-change email.

For people who were already Terminated before this was added, run once:

```
rule "LDAP ApacheDS - Disable Terminated Users"
```

The lock only stops logins if the ApacheDS password policy is enabled (Apache Directory Studio >
server configuration > Password Policy).

## Design documents

- `docs/SailPointIIQ_HR_LDAP_HLD.pdf` - High-Level Design (scope, architecture, identity and access model, lifecycle, decisions, risks)
- `docs/SailPointIIQ_HR_LDAP_LLD.pdf` - Low-Level Design (applications, schemas, rules, roles, workflow, tasks, runbook, test cases, troubleshooting)
- `docs/SailPointIIQ_HR_LDAP_Developer_Guide.pdf` - Developer Guide: how the source code works (execution order, every rule explained, how to extend, conventions, debugging)

Rebuild them after changes (needs `reportlab`), from the `docs` folder:
`python3 make_docs.py .` (HLD + LLD) and `python3 make_dev_guide.py .` (Developer Guide).

## Email from LDAP

The identity attribute **Email** (`email`) is sourced from the LDAP ApacheDS account attribute `mail`,
which the LDAP Create Account policy generates as `<uid>@example.com`. The setup rule
`HR CSV - Setup Identity Mappings` adds the mapping. The value reaches the identity on the next
**HR Lifecycle - Daily Identity Refresh** (or LDAP aggregation) after the LDAP account exists.
People without an LDAP account (PreHire) have no email yet.


## Emergency Identity Disable / Enable (quick link)

Administrators can disable an identity and all its accounts straight away, and enable it again
later, with the quick link **Emergency Identity Disable / Enable**. It starts the approval-free
workflow **Emergency Identity Status Management Workflow**.

| Item | Value |
|---|---|
| Identity attribute | `emergencyDisable` (Emergency Disable, boolean, editable, set only by the workflow) |
| LCM disabled status | identity `inactive`, calculated by the global rule `Emergency Identity - Inactive Attribute`: `true` while `emergencyDisable = true`, otherwise the HR value |
| Who sees the quick link | DynamicScope `Emergency Identity Administrators`, rule `Emergency Identity - Admin Selector`: capability `SystemAdministrator` or `EmergencyIdentityAdministrator` (direct or through a workgroup) |
| Audit | one `AuditEvent` per request: `EmergencyIdentityDisable`, `EmergencyIdentityEnable` or `EmergencyIdentityDenied` |

How it works:

1. **Form.** Pick an identity. The form fills in the Identity Name, the Current Status
   (`Active` when Emergency Disable is false, `Disabled` when it is true), the Emergency Disable value
   and the HR status. The Action list offers only **Disable** for an active identity and only
   **Enable** for a disabled one. A justification is required, and you cannot pick yourself.
2. **Validate.** The workflow checks again that the requestor is an administrator and that the
   action still matches the identity's current state. If a check fails, nothing is changed and the
   request is audited as `EmergencyIdentityDenied`.
3. **Update the identity.** It sets `emergencyDisable` (`true` for Disable, `false` for Enable) and `inactive`,
   and saves the identity under an identity lock, so the identity record shows the change at once.
4. **Provision** (rule `Emergency Identity - Provision Accounts`), with no approvals:

   | Account | Disable | Enable |
   |---|---|---|
   | HR Authoritative CSV (authoritative) | not changed | not changed |
   | LDAP ApacheDS | admin lock (`LDAP ApacheDS - Set Account Status`) | lock removed |
   | another application whose connector supports `ENABLE` | Disable request through the IIQ provisioner (uses the app's Disable policy) | Enable request (Enable policy) |
   | another application without `ENABLE` | reported as `MANUAL` | reported as `MANUAL` |

   Accounts that are already in the requested state are skipped. **Enable** never re-enables
   accounts while the HR status is `Terminated`.
5. **Audit and result.** The workflow writes the audit event and shows the requestor the result:
   `SUCCESS`, `PARTIAL`, `FAILED`, `NOTHING_TO_DO` or `DENIED`, with one line per account.

Each audit event records the following:

| Field | Content |
|---|---|
| action | `EmergencyIdentityDisable` / `EmergencyIdentityEnable` / `EmergencyIdentityDenied` |
| source | requestor |
| target | target identity |
| created | date and time |
| string1 | workflow execution result |
| string2 | justification |
| string3 | Emergency Disable before -> after |
| string4 | per-account summary; the full list is in the attribute `accounts` |

The same line is written to the server log at WARN level, prefixed with `Emergency Identity:`.
To find the events, use **Advanced Analytics > Audit Search** and search by action, source or target.

The HR lifecycle stays consistent with this feature:

- A refresh never re-activates an emergency-disabled identity, because `inactive` comes from the global rule.
- A rehire (Terminated -> Active) does not re-enable the LDAP account while `emergencyDisable = true`.
- `HR CSV - Setup Identity Mappings` no longer adds a source to an attribute that is calculated by a
  global rule, so running it again does not undo the `inactive` change.

Files:

- `config/QuickLink/QuickLink-Emergency_Identity-DisableEnable.xml`: SPRight, capability, DynamicScope and quick link
- `config/Workflow/Workflow-Emergency_Identity-StatusManagement.xml`: form, validation, update, provisioning, audit, result
- `config/Rule/Rule-Emergency_Identity-ProvisionAccounts.xml`: disables or enables the accounts
- `config/Rule/Rule-Emergency_Identity-Audit.xml`: audit event and log line
- `config/Rule/Rule-Emergency_Identity-InactiveAttribute.xml`: global rule for `inactive`
- `config/Rule/Rule-Emergency_Identity-Setup.xml`: one-time setup
- `config/Rule/Rule-Emergency_Identity-AdminSelector.xml`: who is in the quick link population

Setup:

1. Import `config/init-HR-CSV.xml`.
2. In the IIQ console, run `rule "HR CSV - Setup Identity Mappings"` and then `rule "Emergency Identity - Setup"`.
   The second rule creates `emergencyDisable`, switches `inactive` to the global rule and adds the audit actions.
3. Run `rule "HR CSV - Show Attributes On Identity Page"` so that Emergency Disable shows on View Identity.
4. Give people who are not system administrators the capability **Emergency Identity Administrator**,
   then log out and back in.
5. Run **HR Lifecycle - Daily Identity Refresh** once, so that `inactive` is recalculated by the new rule.

To test:

1. As `spadmin`, open **Quick Links > Emergency Identity Disable / Enable** and pick an active user.
   Only Disable is offered. Submit the form.
2. Check the result: the LDAP account is locked (`pwdAccountLockedTime`), and the identity shows
   Emergency Disable = true and is Inactive.
3. Open the quick link again for the same user. Only Enable is offered. Submit it, and the LDAP account is unlocked.
4. Log in as a user without either capability: the quick link is not shown.
5. Check the audit events in Audit Search, filtered on target = that user.
