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
data/HR_Employees.csv                                    sample HR feed (15 rows)
config/init-HR-CSV.xml                                   imports everything in order
config/Rule/Rule-HR_CSV-Customization.xml                trims values, checks dates, works out status + inactive
config/Rule/Rule-HR_CSV-Correlation.xml                  account -> identity on employeeNumber
config/Rule/Rule-HR_CSV-ManagerCorrelation.xml           managerId -> manager identity
config/Rule/Rule-HR_CSV-IdentityCreation.xml             name, displayName, first/last name, identity type
config/Application/Application-HR_Authoritative_CSV.xml  app, schema, Create Account policy
config/TaskDefinition/TaskDefinition-HR_CSV-Aggregation.xml
config/Rule/Rule-HR_CSV-SetupIdentityMappings.xml        adds the identity mappings (run once)
```

## CSV columns

`employeeNumber|firstName|lastName|startDate|endDate|managerId|jobDescription|country|employeeType`

- `endDate` and `managerId` may be blank (for example, the CEO has no manager).
- `employeeType` is one of `Employee`, `Contractor` or `Intern`.

## Calculated attributes (Customization rule)

| status | Condition | inactive |
|---|---|---|
| Terminated | endDate is earlier than today | true |
| Pre-Hire | startDate is later than today | true |
| Active | otherwise | false |

## Deploy

1. Copy `data/HR_Employees.csv` to the IIQ server, then update the `file` entry in the Application XML
   (default: `/opt/sailpoint/hrfeed/HR_Employees.csv`).
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
