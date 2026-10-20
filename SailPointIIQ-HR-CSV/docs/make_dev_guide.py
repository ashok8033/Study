"""Builds the Developer Guide PDF: a walkthrough of the source code for developers.

Usage:  python3 docs/make_dev_guide.py docs
"""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

from make_docs import (AUTHOR, H1, H2, bullets, code, cover, footer, glue_headings, p, table)


def build(path):
    s = cover("Developer Guide", "How the source code works - read this before changing it")

    # ------------------------------------------------------------ 1
    s += [p("1. Who this guide is for", H1),
          p("This guide explains the source code of the SailPoint IdentityIQ (IIQ) HR CSV and LDAP ApacheDS "
            "implementation so a developer can understand it, debug it and extend it safely. It assumes you know "
            "Java; it explains the IIQ and BeanShell concepts you need along the way. The HLD and LLD describe "
            "<i>what</i> the solution does; this guide explains <i>how the code does it</i>."),
          p("<b>Read in this order</b>"),
          *bullets(["Section 2-3: what is in the repository and the IIQ concepts used.",
                    "Section 4: when IIQ runs each piece of code (the most important section).",
                    "Sections 5-9: walk-through of every file, with the key code.",
                    "Sections 10-12: how to extend it, coding conventions, debugging."]),

          # -------------------------------------------------------- 2
          p("2. Repository layout", H1),
          code("SailPointIIQ-HR-CSV/\n"
               "  README.md                       setup notes, kept in step with the code\n"
               "  data/HR_Employees.csv           sample HR feed (copy to C:/SailPoint/hrfeed/)\n"
               "  ldif/                           ApacheDS entries: OUs and groups\n"
               "  docs/                           HLD, LLD, this guide and their generator scripts\n"
               "  config/\n"
               "    init-HR-CSV.xml               master import file - imports everything in order\n"
               "    Application/                  HR Authoritative CSV, LDAP ApacheDS\n"
               "    Rule/                         all BeanShell code (18 rules)\n"
               "    Bundle/                       roles (business + IT)\n"
               "    ManagedAttribute/             the Office365Access entitlement\n"
               "    Workflow/  IdentityTrigger/  EmailTemplate/   lifecycle event, workflow, email\n"
               "    TaskDefinition/               aggregation and refresh tasks"),
          p("<b>Naming convention.</b> Every file is <font face='Courier'>&lt;ObjectType&gt;-&lt;Area&gt;-&lt;Name&gt;.xml</font> "
            "and the object inside is named <font face='Courier'>&lt;Area&gt; - &lt;Name&gt;</font>, for example "
            "<font face='Courier'>Rule-HR_CSV-Correlation.xml</font> holds the rule <b>HR CSV - Correlation</b>. "
            "Areas: <b>HR CSV</b> (the HR source), <b>HR Lifecycle</b> (status and events), <b>LDAP ApacheDS</b> (the target)."),
          p("<b>Every file is a SailPoint XML object.</b> Each starts with <font face='Courier'>&lt;!DOCTYPE &lt;Root&gt; PUBLIC \"sailpoint.dtd\" \"sailpoint.dtd\"&gt;</font>; "
            "files holding several objects use the root <font face='Courier'>&lt;sailpoint&gt;</font>. IIQ validates "
            "the XML against its DTD on import, so element names and nesting must match exactly."),

          # -------------------------------------------------------- 3
          p("3. IIQ concepts used in the code", H1),
          table([["Concept", "What it is", "Where you see it"],
                 ["Application", "Connection to a system + its account schema", "HR Authoritative CSV, LDAP ApacheDS"],
                 ["ResourceObject", "One account as read from the source, before IIQ stores it", "Customization rules (object)"],
                 ["Link", "An account stored in IIQ, attached to an identity", "Set Account Status, Display Name rule"],
                 ["Identity", "A person (the 'identity cube')", "Every identity rule, workflow"],
                 ["ObjectConfig 'Identity'", "Definition of identity attributes and their sources / targets", "Setup Identity Mappings"],
                 ["Rule", "BeanShell script IIQ calls at a defined point (by type)", "config/Rule"],
                 ["ProvisioningPlan", "List of changes to make on target accounts (AccountRequest / AttributeRequest)", "Before / After Provisioning"],
                 ["Bundle", "A role: business (assigned / requested) or IT (holds entitlements)", "config/Bundle"],
                 ["IdentityTrigger", "Lifecycle event: fires when something about an identity changes", "HR Lifecycle - Status Change"],
                 ["Workflow", "Steps run on an event; steps can call rules", "HR Lifecycle - Status Change Notification"],
                 ["SailPointContext", "The API handle every rule receives as 'context'", "context.getObjectByName(...), context.saveObject(...)"]],
                [36, 70, 64]),
          p("<b>BeanShell.</b> Rules are written in BeanShell: Java syntax, interpreted at run time. Things that differ from Java:"),
          *bullets(["Variables can be untyped; a missing variable can be tested with <font face='Courier'>void == name</font>.",
                    "Inputs (context, log, identity, object ...) are injected as variables - the &lt;Signature&gt; only documents them.",
                    "A <b>library rule</b> holds shared functions; other rules include it with &lt;ReferencedRules&gt; and call its functions directly.",
                    "Errors surface at run time only, so test every change by running the rule (see section 12)."]),

          # -------------------------------------------------------- 4
          p("4. When does each piece of code run?", H1),
          p("Most confusion comes from not knowing when IIQ calls a rule. Three processes drive everything."),
          p("4.1 HR aggregation (task: HR Authoritative CSV - Account Aggregation)", H2),
          code("for each row in HR_Employees.csv:\n"
               "  1. DelimitedFileConnector parses the row      -> ResourceObject\n"
               "  2. HR CSV - Customization                      trim, validate dates, status, IIQDisabled\n"
               "  3. HR CSV - Correlation                        which identity owns it? (identityName = employeeNumber)\n"
               "  4. HR CSV - Identity Creation                  ONLY if no identity found: create it\n"
               "  5. Link saved; identity attributes promoted    (mappings from ObjectConfig Identity)\n"
               "  6. HR CSV - Manager Correlation                managerId -> manager identity"),
          p("4.2 Identity refresh (task: HR Lifecycle - Daily Identity Refresh)", H2),
          code("for each identity:\n"
               "  1. promoteAttributes      sources + global rules:\n"
               "                              HR Lifecycle - Status Attribute  -> status\n"
               "                              HR CSV - Display Name             -> displayName\n"
               "  2. processTriggers        status changed? -> IdentityTrigger -> Workflow (section 8)\n"
               "  3. correlateEntitlements  detect roles already met by LDAP groups\n"
               "  4. provision              run birthright assignment rules; add / remove roles;\n"
               "                            build a ProvisioningPlan for missing access (section 4.3)\n"
               "  5. synchronizeAttributes  push displayName to the LDAP account (attribute target)"),
          p("4.3 Provisioning to LDAP (inside the refresh, or after an approved request)", H2),
          code("ProvisioningPlan for LDAP ApacheDS\n"
               "  1. Create Account Policy fills a new account (uid, dn, cn, mail, password ...)\n"
               "  2. LDAP ApacheDS - Before Provisioning   take 'groups' out, save as hrGroupsAdd / hrGroupsRemove\n"
               "  3. LDAPConnector                         ADD or MODIFY the account entry\n"
               "  4. LDAP ApacheDS - After Provisioning    add / remove uniqueMember on each group (JNDI)"),
          p("4.4 LDAP aggregation (task: LDAP ApacheDS - Account Aggregation)", H2),
          code("for each inetOrgPerson under ou=people:\n"
               "  1. LDAPConnector reads it                -> ResourceObject\n"
               "  2. LDAP ApacheDS - Customization         add groups + account status (JNDI)\n"
               "  3. LDAP ApacheDS - Correlation           identityName = employeeNumber"),

          # -------------------------------------------------------- 5
          p("5. HR source code", H1),
          p("5.1 HR CSV - Customization (ResourceObjectCustomization)", H2),
          p("Input <font face='Courier'>object</font> is the parsed CSV row; whatever it returns is what IIQ stores. "
            "It never throws: bad data is logged and defaulted, so one bad row cannot stop the aggregation."),
          code('// 1. trim every String attribute; "" becomes null\n'
               '// 2. parse startDate / endDate with SimpleDateFormat("dd-MM-yyyy"), setLenient(false)\n'
               '// 3. isManager -> "Y" / "N" (blank or invalid -> "N", logged)\n'
               '// 4. status, compared by WHOLE DAY (midnight today):\n'
               'if (end != null && end.before(today))         status = "Terminated";\n'
               'else if (start != null && start.after(today)) status = "PreHire";\n'
               'else                                          status = "Active";\n'
               'object.setAttribute("status", status);\n'
               'object.setAttribute("inactive", !"Active".equals(status));\n'
               'object.setAttribute("IIQDisabled", Boolean.valueOf("Terminated".equals(status)));'),
          p("<b>IIQDisabled</b> is a reserved attribute name: IIQ uses it to mark the account (Link) disabled, which "
            "drives the red/green icon on Application Accounts."),
          p("5.2 HR CSV - Correlation and Manager Correlation", H2),
          p("Both return a Map telling IIQ which identity to use. Returning <font face='Courier'>identityName</font> "
            "matches on the identity's name, which is always searchable."),
          code('Map result = new HashMap();\n'
               'String empNo = account.getStringAttribute("employeeNumber");\n'
               'if (empNo != null && empNo.trim().length() > 0) result.put("identityName", empNo.trim());\n'
               'return result;      // empty map = no match -> Identity Creation rule runs'),
          p("<b>Why not identityAttributeName = employeeNumber?</b> That needs employeeNumber to be a <i>searchable</i> "
            "identity attribute (database column). It is not, and the first version failed with "
            "<font face='Courier'>could not resolve property: employeeNumber</font>. Naming identities after the employee "
            "number avoids the schema change."),
          p("5.3 HR CSV - Identity Creation (IdentityCreation)", H2),
          p("Runs once, only for a new identity. It sets the name - this is what makes correlation work - and first values."),
          code('identity.setName(empNo);                     // identity name = employeeNumber\n'
               'identity.setFirstname(first); identity.setLastname(last);\n'
               'identity.setDisplayName(first + " " + last);  // later kept current by HR CSV - Display Name\n'
               'identity.setType("Employee".equalsIgnoreCase(type) ? "employee" : "contractor");'),

          # -------------------------------------------------------- 6
          p("6. Identity attributes and calculated values", H1),
          p("6.1 Global rules (IdentityAttribute)", H2),
          p("A global rule calculates an identity attribute on every refresh. IIQ passes "
            "<font face='Courier'>identity</font> and <font face='Courier'>oldValue</font>; the return value becomes the "
            "new value. Both global rules read the <b>HR link</b> rather than other identity attributes, because the "
            "order in which attributes are promoted is not guaranteed."),
          code('Application app = context.getObjectByName(Application.class, "HR Authoritative CSV");\n'
               'Link hr = (app == null) ? null : identity.getLink(app);\n'
               'Object startValue = (hr != null) ? hr.getAttribute("startDate") : identity.getAttribute("startDate");\n'
               '...\n'
               'if (start == null && end == null) return oldValue;   // no data: keep what we had'),
          table([["Rule", "Returns"],
                 ["HR Lifecycle - Status Attribute", "PreHire / Active / Terminated (same day logic as section 5.1)"],
                 ["HR CSV - Display Name", "firstName + ' ' + lastName from the HR link"]],
                [60, 110]),
          p("6.2 HR CSV - Setup Identity Mappings (one-time setup rule)", H2),
          p("Creates the identity attributes in ObjectConfig <b>Identity</b> through the API instead of importing XML, "
            "because importing an ObjectConfig replaces the whole object. It is <b>idempotent</b>: it checks before "
            "it adds, so running it again is safe."),
          code('String[][] MAPPINGS = {   // { identity attribute, display name, type, HR attribute }\n'
               '    { "employeeNumber", "Employee Number", "string", "employeeNumber" },\n'
               '    { "manager", null, "sailpoint.object.Identity", "managerId" }, ... };\n'
               'ObjectAttribute oa = oc.getObjectAttribute(idAttr);          // create if missing\n'
               'AttributeSource src = new AttributeSource(); src.setApplication(app); src.setName(appAttr);\n'
               'statusAttr.setRule(statusRule);                             // global rule\n'
               'AttributeTarget t = new AttributeTarget(); t.setApplication(ldapApp); t.setName("displayName");\n'
               'context.saveObject(oc); context.commitTransaction();'),
          p("<b>To add a new HR attribute:</b> add a column to the CSV, an AttributeDefinition to the HR application "
            "schema, one line to MAPPINGS, then re-run the setup rule and a refresh."),

          # -------------------------------------------------------- 7
          p("7. LDAP ApacheDS code", H1),
          p("7.1 Why the LDAP rules exist", H2),
          p("IIQ treats <font face='Courier'>groups</font> as an <i>entitlement</i> on the account. The LDAP connector "
            "sent it to ApacheDS as an LDAP attribute, which ApacheDS rejected "
            "(<font face='Courier'>NO_SUCH_ATTRIBUTE ... groups</font>). Group membership is therefore done by rules "
            "that talk to ApacheDS directly with <b>JNDI</b> (javax.naming). The same connection code also reads and "
            "sets account status, which the connector does not support for ApacheDS."),
          p("7.2 LDAP ApacheDS - Library (shared functions)", H2),
          table([["Function", "What it does"],
                 ["ldapConnect(context, app)", "Opens a JNDI connection with the application's host, port, user and (decrypted) password"],
                 ["ldapSetMember(ldap, groupDn, userDn, add)", "ADD / REMOVE uniqueMember; 'already member' / 'not member' count as success"],
                 ["ldapSetDisabled(ldap, userDn, disable)", "REPLACE pwdAccountLockedTime = 000001010000Z, or REMOVE it"],
                 ["ldapGroupsOf(ldap, userDn)", "Search ou=groups for (uniqueMember=userDn); returns group DNs"],
                 ["ldapReadAttributes(ldap, dn, attrIds)", "Read named attributes - needed for operational ones like pwdAccountLockedTime"],
                 ["ldapFormatTime(value)", "20261013101500Z -> 13-10-2026 10:15:00 UTC"]],
                [65, 105]),
          p("Rules that use it declare:"),
          code('<ReferencedRules>\n'
               '  <Reference class="sailpoint.object.Rule" name="LDAP ApacheDS - Library"/>\n'
               '</ReferencedRules>'),
          p("7.3 Before / After Provisioning - how group changes travel", H2),
          p("The two rules hand data to each other through the <b>arguments</b> of the AccountRequest, which survive "
            "from before to after the connector call."),
          code('// BEFORE: remove "groups" so ApacheDS accepts the request; remember the change\n'
               'if ("groups".equals(req.getName())) {\n'
               '    (Remove ? removes : adds).addAll(values);\n'
               '    it.remove();\n'
               '}\n'
               'args.put("hrGroupsAdd", adds);  args.put("hrGroupsRemove", removes);\n\n'
               '// AFTER: only if the account request did not fail\n'
               'if (r != null && r.isFailed()) continue;\n'
               'String userDn = acct.getNativeIdentity();     // or the "dn" attribute request on a Create\n'
               'for (g : adds)    ldapSetMember(ldap, g, userDn, true);\n'
               'for (g : removes) ldapSetMember(ldap, g, userDn, false);'),
          p("Both are attached as <b>application attributes</b>, not elements (the Application DTD has no "
            "&lt;BeforeProvisioningRule&gt; element):"),
          code('<entry key="beforeProvisioningRule" value="LDAP ApacheDS - Before Provisioning"/>\n'
               '<entry key="afterProvisioningRule"  value="LDAP ApacheDS - After Provisioning"/>'),
          p("7.4 LDAP ApacheDS - Customization (read-back)", H2),
          p("Runs for every account during LDAP aggregation. It keeps one JNDI connection in the aggregation "
            "<font face='Courier'>state</font> map so it does not reconnect for every account."),
          code('DirContext ldap = (DirContext) state.get("hrLdapContext");\n'
               'if (ldap == null) { ldap = ldapConnect(context, application); state.put("hrLdapContext", ldap); }\n'
               'object.setAttribute("groups", ldapGroupsOf(ldap, dn));\n'
               'String locked = ldapReadAttributes(ldap, dn, STATUS_ATTRS).get("pwdAccountLockedTime");\n'
               'status = locked == null ? "Active" : ("000001010000Z".equals(locked) ? "Disabled" : "Locked");\n'
               'object.setAttribute("IIQDisabled", "Disabled".equals(status));\n'
               'object.setAttribute("IIQLocked",   "Locked".equals(status));'),
          p("7.5 LDAP ApacheDS - Set Account Status", H2),
          p("Called by the workflow (and by the catch-up rule) with <font face='Courier'>identityName</font> and "
            "<font face='Courier'>action</font> = Disable / Enable. It changes ApacheDS, then updates the Link at once "
            "so the UI is right without waiting for the next aggregation."),
          code('ldapSetDisabled(ldap, link.getNativeIdentity(), disable);\n'
               'link.setAttribute("accountStatus", disable ? "Disabled" : "Active");\n'
               'link.setAttribute("pwdAccountLockedTime", disable ? "000001010000Z" : null);\n'
               'link.setAttribute("IIQDisabled", Boolean.valueOf(disable));\n'
               'context.saveObject(link); context.commitTransaction();'),
          p("7.6 Create Account Policy", H2),
          p("Lives inside the LDAP application (&lt;ProvisioningForms&gt;, Form type=\"Create\"). Each Field has a "
            "Script; <font face='Courier'>identity</font> is available. A field can use another field's value as a "
            "variable when it declares <font face='Courier'>dependencies=\"uid\"</font> - that is how dn and mail are "
            "built from uid. uid is made unique by counting existing LDAP links with the same DN."),

          # -------------------------------------------------------- 8
          p("8. Lifecycle event and workflow", H1),
          p("The IdentityTrigger fires during a refresh with <i>processTriggers</i> when <b>status</b> changes, and "
            "starts the workflow with <font face='Courier'>identityName</font>, <font face='Courier'>event</font> "
            "(IdentityChangeEvent: old and new identity) and <font face='Courier'>trigger</font>."),
          code('Start -> Collect Details\n'
               '         | newStatus == Terminated and oldStatus != Terminated  -> Disable LDAP\n'
               '         | oldStatus == Terminated and newStatus == Active      -> Enable LDAP\n'
               '         | otherwise                                            -> Check Notify\n'
               'Disable LDAP / Enable LDAP: action="rule:LDAP ApacheDS - Set Account Status"\n'
               '                            resultVariable="ldapResult"  -> Check Notify\n'
               'Check Notify: oldStatus and newStatus set and different -> Send Email, else Stop\n'
               'Send Email:   action="call:sendEmail", template "HR Lifecycle - Status Change"'),
          *bullets(["<b>explicitTransitions=\"true\"</b>: the first Transition whose script returns true is taken; "
                    "a Transition without a script is the default and must come last.",
                    "Workflow variables are plain BeanShell variables in transition scripts; a step script sets them with "
                    "<font face='Courier'>workflow.put(\"name\", value)</font>.",
                    "Each &lt;Arg&gt; of the sendEmail step becomes a Velocity variable in the template ($!oldStatus ...). "
                    "<font face='Courier'>$!</font> prints nothing instead of the literal name when the value is null.",
                    "No email the first time status is set (oldStatus null) - otherwise the first refresh would email everyone."]),

          # -------------------------------------------------------- 9
          p("9. Roles, entitlements and tasks", H1),
          p("Roles are data, not code. A business role either has a <b>Selector</b> (assignment rule) or none "
            "(requestable). It points to an IT role through &lt;Requirements&gt;; the IT role's Profile holds the LDAP group."),
          code('<Selector><IdentitySelector><MatchExpression and="true">\n'
               '  <MatchTerm name="status" value="Active"/>\n'
               '  <MatchTerm name="employeeType" value="Contractor"/>\n'
               '</MatchExpression></IdentitySelector></Selector>\n\n'
               '<Profile> ... <Filter operation="CONTAINS_ALL" property="groups">\n'
               '  <Value><List><String>cn=Contractors,ou=groups,dc=example,dc=com</String></List></Value>\n'
               '</Filter></Profile>'),
          table([["Task option (Daily Identity Refresh)", "Effect"],
                 ["promoteAttributes", "Run sources and global rules (status, displayName)"],
                 ["processTriggers", "Fire lifecycle events (the workflow)"],
                 ["correlateEntitlements", "Detect IT roles already satisfied by LDAP groups"],
                 ["provision", "Evaluate assignment rules and provision / deprovision roles"],
                 ["synchronizeAttributes", "Push attributes that have targets (displayName -> LDAP)"]],
                [70, 100]),

          # -------------------------------------------------------- 10
          p("10. How to extend", H1),
          table([["Change", "Files to touch"],
                 ["New HR column", "data CSV header; HR application schema; MAPPINGS in Setup Identity Mappings; "
                                   "ShowOnIdentityPage ADD list; re-run both setup rules + refresh"],
                 ["New calculated identity attribute", "New IdentityAttribute rule; attach with setRule() in Setup Identity Mappings"],
                 ["New birthright LDAP group", "LDIF entry; IT role (Profile with the group DN); business role with a Selector; refresh"],
                 ["New requestable access", "LDIF group; ManagedAttribute (requestable=\"true\"); IT role; business role without Selector"],
                 ["Sync another attribute to LDAP", "LDAP schema attribute; AttributeTarget on the identity attribute (like displayName)"],
                 ["New lifecycle action", "Add a step + Transition in the workflow; put the logic in a rule, call it with action=\"rule:...\""],
                 ["Different OU / directory layout", "dn field + uniqueness DN in the Create policy; searchDN entries; group DNs in "
                                                      "IT roles, ManagedAttribute, Library (ldapGroupsOf); LDIF"],
                 ["Another target system", "New Application XML; correlation rule; IT roles with its entitlements"]],
                [55, 115]),

          # -------------------------------------------------------- 11
          p("11. Coding conventions and gotchas", H1),
          *bullets(["<b>Never import ObjectConfig, UIConfig or Configuration objects wholesale</b> - they replace everything. "
                    "Change them with an idempotent setup rule (see Setup Identity Mappings / ShowOnIdentityPage).",
                    "<b>Every file needs a DOCTYPE</b> whose root matches the root element, or the import fails.",
                    "<b>Follow the DTD.</b> Examples that bit us: HandlerParameters must wrap its Map in &lt;Attributes&gt;; "
                    "provisioning rules are application attributes, not elements.",
                    "<b>Correlate on identity name</b> unless an attribute is made searchable.",
                    "<b>Rules must not throw during aggregation</b> - catch, log with a clear prefix ('HR CSV' / 'LDAP ApacheDS:') and continue.",
                    "<b>Make utility rules idempotent</b> and print a report of what they did; they are run by hand.",
                    "<b>Dates:</b> DD-MM-YYYY strings everywhere, parsed with setLenient(false), compared by whole day.",
                    "<b>Close JNDI connections</b> in finally, except the aggregation-scoped one kept in state.",
                    "<b>Commit after saving</b> outside the normal pipeline: context.saveObject(x); context.commitTransaction();",
                    "<b>Keep README, init-HR-CSV.xml and these docs in step</b> with any new file."]),

          # -------------------------------------------------------- 12
          p("12. Debugging toolkit", H1),
          table([["Tool", "Use it to"],
                 ["rule \"HR CSV - Diagnose\"", "See mappings (database vs memory), the HR link, the identity values and the status rule result for one identity"],
                 ["rule \"Aggregate Single Account\"", "Re-read one account (APP_NAME / ACCOUNT_ID) and print what the source returned"],
                 ["rule \"HR Lifecycle - Send Test Email\"", "Check mail settings and send one email"],
                 ["Debug page (/identityiq/debug)", "View raw XML of any object: Identity, Link, Rule, Workflow, IdentityTrigger"],
                 ["IIQ console: get Identity 1000", "Same as above from the command line"],
                 ["log4j2.properties", "Raise a logger to debug, e.g. sailpoint.connector.DelimitedFileConnector; reload logging from Debug"],
                 ["Task Results", "Counts (created / updated) and errors of aggregations and refreshes"],
                 ["Apache Directory Studio", "Check entries; enable 'Fetch operational attributes' to see pwdAccountLockedTime"]],
                [58, 112]),
          p("<b>Edit - import - test loop:</b> change the XML, check it is well formed, import that one file in the "
            "console (<font face='Courier'>import config/Rule/&lt;file&gt;.xml</font>), run the smallest thing that "
            "exercises it (a utility rule or Aggregate Single Account), read the output and the log.")]

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title="Developer Guide - SailPoint IIQ HR CSV and LDAP", author=AUTHOR)
    doc.build(glue_headings(s), onFirstPage=footer("Developer Guide"), onLaterPages=footer("Developer Guide"))


if __name__ == "__main__":
    build(f"{sys.argv[1]}/SailPointIIQ_HR_LDAP_Developer_Guide.pdf")
    print("done")
