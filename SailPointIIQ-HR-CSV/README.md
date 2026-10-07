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
2. Run `rule "HR CSV - Setup Identity Mappings"` in the IIQ console.
3. Configure mail in **Global Settings > IdentityIQ Configuration > Mail Settings**. For Gmail use
   `smtp.gmail.com`, port 587, TLS, and a Google *app password* (not your normal password).
   To test without SMTP, set the email notifier to write to a file instead.
4. Run **HR Authoritative CSV - Account Aggregation**, then **HR Lifecycle - Daily Identity Refresh**.
   This first refresh only sets the initial status, so no emails are sent.
5. Schedule **HR Lifecycle - Daily Identity Refresh** to run every day just after midnight,
   so people move between states on the right day even when the CSV has not changed.

To test: change a user's `endDate` in the CSV to yesterday's date, then run the aggregation and
the daily refresh. Their status changes to Terminated and an email is sent.

