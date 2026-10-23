"""Builds the HLD and LLD PDFs for the SailPoint IIQ HR CSV / LDAP implementation."""
import sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle, Preformatted)

VERSION = "1.1"
DATE = "23-10-2026"
AUTHOR = "Ashok Kumar"

NAVY = colors.HexColor("#1F3A5F")
TEAL = colors.HexColor("#0E7C86")
LIGHT = colors.HexColor("#EEF3F8")
GRID = colors.HexColor("#B8C4D0")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=NAVY, fontSize=16, spaceBefore=10, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=TEAL, fontSize=12.5, spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontSize=9.5, leading=13.5, spaceAfter=5)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.5, leading=11, spaceAfter=0)
CELLB = ParagraphStyle("CellB", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
BUL = ParagraphStyle("Bul", parent=BODY, leftIndent=12, bulletIndent=2)
CODE = ParagraphStyle("Code", parent=ss["Code"], fontSize=7.8, leading=10, backColor=LIGHT,
                      borderPadding=5, leftIndent=4, rightIndent=4, spaceBefore=3, spaceAfter=8)
TITLE = ParagraphStyle("T", parent=ss["Title"], textColor=NAVY, fontSize=24, leading=30, alignment=TA_CENTER)
SUB = ParagraphStyle("S", parent=BODY, fontSize=12, alignment=TA_CENTER, textColor=TEAL)


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(i, BUL, bulletText="\u2022") for i in items]


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), CELLB if (header and r == 0) else CELL) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, GRID),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    for r in range(1 if header else 0, len(rows)):
        if r % 2 == 0:
            style.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def code(text):
    return Preformatted(text.strip("\n"), CODE)


def cover(title, subtitle):
    meta = table([["Document", title], ["Project", "SailPoint IdentityIQ - HR CSV authoritative source, lifecycle and LDAP ApacheDS provisioning"],
                  ["Version", VERSION], ["Date", DATE], ["Author", AUTHOR],
                  ["Source", "github.com/ashok8033/Study - branch main, folder SailPointIIQ-HR-CSV"]],
                 [35, 125], header=False)
    return [Spacer(1, 55 * mm), p(title, TITLE), Spacer(1, 4 * mm), p(subtitle, SUB),
            Spacer(1, 25 * mm), meta, PageBreak()]


def glue_headings(story):
    """Keep each heading on the same page as the element that follows it."""
    out, i = [], 0
    while i < len(story):
        f = story[i]
        is_label = isinstance(f, Paragraph) and f.text.startswith("<b>") and f.text.endswith("</b>")
        if isinstance(f, Paragraph) and (f.style.name in ("H1", "H2") or is_label) and i + 1 < len(story):
            out.append(KeepTogether([f, story[i + 1]]))
            i += 2
        else:
            out.append(f)
            i += 1
    return out


def footer(label):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.grey)
        canvas.drawString(18 * mm, 10 * mm, f"SailPoint IIQ - HR CSV & LDAP ApacheDS | {label} v{VERSION}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


# ---------------------------------------------------------------- diagrams
def box(d, x, y, w, h, title, lines=(), fill=LIGHT, stroke=NAVY):
    d.add(Rect(x, y, w, h, fillColor=fill, strokeColor=stroke, strokeWidth=1, rx=4, ry=4))
    d.add(String(x + w / 2, y + h - 12, title, fontName="Helvetica-Bold", fontSize=8.5,
                 fillColor=NAVY, textAnchor="middle"))
    for i, ln in enumerate(lines):
        d.add(String(x + w / 2, y + h - 24 - i * 10, ln, fontName="Helvetica", fontSize=7,
                     fillColor=colors.black, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, label=None, dy=4):
    d.add(Line(x1, y1, x2, y2, strokeColor=TEAL, strokeWidth=1.2))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    s = 5
    d.add(Polygon([x2, y2, x2 - s * math.cos(a - 0.4), y2 - s * math.sin(a - 0.4),
                   x2 - s * math.cos(a + 0.4), y2 - s * math.sin(a + 0.4)],
                  fillColor=TEAL, strokeColor=TEAL))
    if label:
        d.add(String((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, fontName="Helvetica-Oblique",
                     fontSize=6.8, fillColor=TEAL, textAnchor="middle"))


def architecture():
    d = Drawing(170 * mm, 88 * mm)
    W = 170 * mm
    box(d, 0, 150, 120, 70, "HR CSV file", ["HR_Employees.csv", "pipe delimited", "DD-MM-YYYY dates"])
    box(d, W / 2 - 85, 100, 170, 140, "SailPoint IdentityIQ",
        ["HR Authoritative CSV (DelimitedFile)", "Identity cube + attributes",
         "Status rule: PreHire/Active/Terminated", "Birthright & requestable roles",
         "Lifecycle event + workflow", "LDAP ApacheDS (LDAP connector)", "Rules: customization, provisioning"],
        fill=colors.HexColor("#E3F1F2"))
    box(d, W - 120, 150, 120, 70, "Apache DS", ["dc=example,dc=com", "ou=people / ou=groups", "port 10389"])
    box(d, W - 120, 20, 120, 60, "Mail (SMTP)", ["Gmail smtp.gmail.com:587", "status-change emails"])
    box(d, 0, 20, 120, 60, "Administrators", ["IIQ console & UI", "Apache Directory Studio"])
    arrow(d, 120, 185, W / 2 - 85, 185, "aggregation (read)")
    arrow(d, W / 2 + 85, 195, W - 120, 195, "provision / disable")
    arrow(d, W - 120, 175, W / 2 + 85, 175, "aggregation", dy=-9)
    arrow(d, W / 2 + 85, 120, W - 120, 55, "email")
    arrow(d, 120, 55, W / 2 - 85, 120, "manage")
    return d


def lifecycle():
    d = Drawing(170 * mm, 45 * mm)
    y = 60
    box(d, 0, y, 110, 60, "PreHire", ["today < startDate", "no LDAP access"], fill=colors.HexColor("#FFF5E0"))
    box(d, 175, y, 120, 60, "Active", ["startDate <= today", "<= endDate", "birthright roles + LDAP"],
        fill=colors.HexColor("#E6F4EA"))
    box(d, 360, y, 120, 60, "Terminated", ["today > endDate", "roles removed", "LDAP disabled"],
        fill=colors.HexColor("#FDE8E8"))
    arrow(d, 110, y + 30, 175, y + 30, "start date")
    arrow(d, 295, y + 38, 360, y + 38, "end date")
    arrow(d, 360, y + 18, 295, y + 18, "rehire", dy=-9)
    d.add(String(240, 30, "Every move between states raises the lifecycle event 'HR Lifecycle - Status Change'",
                 fontName="Helvetica", fontSize=7.5, textAnchor="middle", fillColor=NAVY))
    d.add(String(240, 18, "-> workflow: LDAP disable/enable + email to ashokhearts@gmail.com",
                 fontName="Helvetica", fontSize=7.5, textAnchor="middle", fillColor=NAVY))
    return d


# ---------------------------------------------------------------- HLD
def build_hld(path):
    s = cover("High-Level Design (HLD)", "SailPoint IdentityIQ: HR authoritative source, joiner / mover / leaver and LDAP provisioning")

    s += [p("1. Purpose and scope", H1),
          p("This document describes the overall design of a SailPoint IdentityIQ (IIQ) lab implementation that "
            "uses an HR CSV file as the authoritative source of identities, calculates a lifecycle status for every "
            "person, and grants, changes and removes access in an Apache Directory Server (ApacheDS) LDAP directory "
            "through roles. Detailed configuration is in the companion Low-Level Design (LLD)."),
          p("<b>In scope</b>"),
          *bullets(["Aggregation of employees, contractors and interns from a pipe-delimited HR CSV file.",
                    "Identity attributes, manager hierarchy and a calculated lifecycle <b>Status</b> (PreHire / Active / Terminated, or Disabled by an emergency disable).",
                    "Joiner, mover, leaver and rehire handling with email notification.",
                    "LDAP ApacheDS accounts and groups: creation, group membership by birthright and requestable roles, "
                    "display-name synchronisation, account status read-back and disable / enable.",
                    "Emergency Identity Disable / Enable: an administrator-only quick link that disables or re-enables "
                    "an identity and its accounts at once, without approval, fully audited.",
                    "Operational tooling: diagnostics, single-account aggregation, catch-up rules."]),
          p("<b>Out of scope</b>"),
          *bullets(["Production hardening (SSL/LDAPS, HA, secrets vault), password management and self-service.",
                    "Other target systems (Active Directory, Office 365 itself - Office365Access is an LDAP group only)."]),

          p("2. Solution overview", H1),
          p("IIQ reads the HR file, builds an identity for each employee and keeps it current. A global rule works out "
            "each person's lifecycle Status from their start and end dates. Roles decide what LDAP access a person "
            "should have; IIQ provisions it to ApacheDS. When the Status changes, a lifecycle event runs a workflow "
            "that disables or re-enables the LDAP account and sends an email."),
          architecture(),
          p("Figure 1 - Logical architecture", ParagraphStyle("cap", parent=BODY, alignment=TA_CENTER, fontSize=8, textColor=colors.grey)),

          p("3. Systems and components", H1),
          table([["Component", "Role", "Technology / settings"],
                 ["HR CSV file", "Authoritative source of people", "C:/SailPoint/hrfeed/HR_Employees.csv, delimiter |, header row, dates DD-MM-YYYY"],
                 ["SailPoint IdentityIQ", "Identity governance and provisioning", "Tomcat on Windows, http://localhost:8080/identityiq"],
                 ["HR Authoritative CSV", "IIQ application for the HR file", "DelimitedFile connector, authoritative, account ID = employeeNumber"],
                 ["LDAP ApacheDS", "IIQ application for the directory", "LDAP connector, localhost:10389, bind uid=admin,ou=system"],
                 ["Apache Directory Server", "Target directory", "dc=example,dc=com, users in ou=people, groups (groupOfUniqueNames) in ou=groups"],
                 ["SMTP (Gmail)", "Notification email", "smtp.gmail.com:587 TLS, app password; recipient ashokhearts@gmail.com"]],
                [38, 50, 82]),

          p("4. Identity model", H1),
          p("Every HR row becomes one identity named after its <b>employeeNumber</b> (for example 1000). Ashok Kumar "
            "(1000, now Ashokkumar Chidambaram) is the top manager; every other person reports to him."),
          table([["Identity attribute", "Source"],
                 ["Name (user name)", "employeeNumber (set by the Identity Creation rule)"],
                 ["First name, Last name, Manager", "HR firstName, lastName, managerId"],
                 ["Display Name", "Calculated: firstName + ' ' + lastName (global rule)"],
                 ["Status", "Calculated from startDate / endDate (global rule); Disabled while Emergency Disable is set"],
                 ["Start / End Date, Job Description, Country, Employee Type, Is Manager, Employee Number", "HR columns of the same name"],
                 ["Inactive (LCM disabled status)", "Calculated: true while Emergency Disable is set, otherwise HR status is not Active (global rule)"],
                 ["Emergency Disable", "Set only by the Emergency Identity Status Management Workflow (true / false)"],
                 ["Email", "LDAP ApacheDS mail (generated when the LDAP account is created)"]],
                [70, 100]),

          p("5. Lifecycle (joiner / mover / leaver)", H1),
          lifecycle(),
          p("Figure 2 - Lifecycle states", ParagraphStyle("cap2", parent=BODY, alignment=TA_CENTER, fontSize=8, textColor=colors.grey)),
          table([["Event", "Trigger", "What happens"],
                 ["Joiner", "Status becomes Active", "Birthright roles assigned; LDAP account created (Create Account policy) and added to groups"],
                 ["Mover", "employeeType / isManager / name changes", "Roles re-evaluated (groups added or removed); Display Name pushed to LDAP"],
                 ["Leaver", "Status becomes Terminated", "Roles removed (groups removed); LDAP account disabled; HR account shown disabled; email"],
                 ["Rehire", "Terminated -> Active", "LDAP account re-enabled; birthright roles assigned again; email"],
                 ["Access request", "Office365 Access requested", "User added to LDAP group cn=Office365Access"],
                 ["Emergency disable", "Administrator, quick link", "Emergency Disable = true; Status Disabled; identity inactive; LDAP account disabled; birthright groups removed on the next refresh; audited"],
                 ["Emergency enable", "Administrator, quick link", "Emergency Disable = false; Status and inactive from HR; LDAP account enabled unless Terminated; groups back on the next refresh; audited"]],
                [24, 46, 100]),

          p("6. Access model (roles)", H1),
          table([["Business role", "How assigned", "IT role", "LDAP group"],
                 ["Birthright - All Active Users", "status = Active", "LDAP - All Employees", "cn=AllEmployees"],
                 ["Birthright - Contractors", "Active and employeeType = Contractor", "LDAP - Contractors", "cn=Contractors"],
                 ["Birthright - Managers", "Active and isManager = Y", "LDAP - Managers", "cn=Managers"],
                 ["Office365 Access", "Requestable only", "LDAP - Office365Access", "cn=Office365Access"]],
                [45, 50, 40, 35]),

          p("7. Integration flows", H1),
          table([["#", "Flow", "Direction", "Schedule"],
                 ["1", "HR account aggregation", "HR CSV -> IIQ", "After each HR file drop"],
                 ["2", "Daily identity refresh (attributes, events, roles, provisioning, attribute sync)", "IIQ -> ApacheDS", "Daily, just after midnight"],
                 ["3", "LDAP account aggregation (accounts, groups, status)", "ApacheDS -> IIQ", "After refresh / daily"],
                 ["4", "Lifecycle workflow (disable / enable, email)", "IIQ -> ApacheDS, SMTP", "On Status change (during refresh)"],
                 ["5", "Emergency Identity Status Management Workflow (disable / enable accounts)", "IIQ -> ApacheDS (and other ENABLE-capable apps)", "On demand, from the quick link"]],
                [8, 82, 40, 40]),

          p("8. Emergency identity disable / enable", H1),
          p("Administrators can cut off a person immediately - for example after a security incident - and restore "
            "access later, independently of the HR dates. The quick link <b>Emergency Identity Disable / Enable</b> "
            "starts the approval-free <b>Emergency Identity Status Management Workflow</b>."),
          table([["Aspect", "Design"],
                 ["Who", "Only identities with the SystemAdministrator or EmergencyIdentityAdministrator capability see the "
                         "quick link (DynamicScope); the workflow checks the capability again before changing anything"],
                 ["Form", "Identity selector; shows name, status (Active / Disabled), Emergency Disable value and HR status. "
                          "Only the valid action is offered: Disable for an active identity, Enable for a disabled one. "
                          "Justification required; requestors cannot target themselves"],
                 ["Identity", "Emergency Disable set to true / false; Inactive (LCM disabled status) recalculated at once and "
                              "kept in step on every refresh by a global rule"],
                 ["Accounts", "Disabled / enabled without approval: LDAP ApacheDS by the admin lock, other applications whose "
                              "connector supports ENABLE through the IIQ provisioner; HR (authoritative) is never changed. "
                              "Enable never re-enables accounts of an HR-Terminated identity"],
                 ["Audit", "One AuditEvent per request (also refused ones): requestor, target, action, date and time, "
                           "workflow result, justification, per-account outcome; plus a server log line"]],
                [25, 145]),
          p("The HR lifecycle respects the flag: a refresh never re-activates an emergency-disabled identity, and a "
            "rehire does not re-enable its LDAP account while Emergency Disable is set."),

          p("9. Key design decisions", H1),
          table([["Decision", "Reason"],
                 ["Identity name = employeeNumber; correlation on name", "Name is always searchable; no extended searchable attribute or schema change needed"],
                 ["Status calculated on refresh, not only on aggregation", "People change state on the right day even when the HR file has not changed"],
                 ["LDAP group membership handled by provisioning rules (JNDI)", "The LDAP connector sent 'groups' as an attribute; ApacheDS rejected it"],
                 ["Disable by ApacheDS admin lock pwdAccountLockedTime = 000001010000Z", "ApacheDS has no enabled flag; the password policy lock is the standard mechanism"],
                 ["Two-level roles (business -> IT)", "Business roles cannot hold entitlements; IT roles carry the LDAP group"],
                 ["Setup rules instead of importing ObjectConfig / UIConfig", "Importing those objects would overwrite the whole configuration"],
                 ["Inactive calculated by a global rule instead of mapped from HR", "Keeps the LCM disabled status in step with Emergency Disable on every refresh"],
                 ["Emergency workflow re-validates admin rights and current state", "The quick link scope only hides the link; the workflow is the security boundary"],
                 ["Emergency LDAP disable reuses LDAP ApacheDS - Set Account Status", "One proven disable / enable path for leavers and emergencies"]],
                [70, 100]),

          p("10. Non-functional considerations", H1),
          *bullets(["<b>Security:</b> bind password stored encrypted in IIQ (re-enter it in the UI after import). Lab "
                    "uses plain LDAP on 10389 and an initial password pattern Welcome@&lt;employeeNumber&gt; - both must change for production.",
                    "<b>Logging:</b> log4j2 file appender (C:/SailPoint/logs); rules log with the prefix 'LDAP ApacheDS:' / 'HR CSV'.",
                    "<b>Performance:</b> sized for a lab (16 users). Tomcat heap 1-4 GB; LDAP rules reuse one connection per aggregation.",
                    "<b>Resilience:</b> catch-up rules (Disable Terminated Users, Aggregate Single Account) recover from missed events."]),

          p("11. Assumptions, risks and open items", H1),
          table([["Item", "Type", "Notes"],
                 ["ApacheDS password policy must be enabled", "Assumption", "Needed for pwdAccountLockedTime to be accepted and to block logins"],
                 ["LDAP disable / status read-back not yet confirmed in the lab", "Open item", "Last test: attribute not visible; Studio hides operational attributes by default"],
                 ["Group membership via After Provisioning rule", "Risk", "Verify uniqueMember changes after first provisioning run"],
                 ["Mail delivery depends on Gmail app password", "Assumption", "Use the Send Test Email rule to verify"],
                 ["Lifecycle Events page requires Lifecycle Manager", "Assumption", "Event works without it; view via Debug > IdentityTrigger"],
                 ["Emergency form fields read the selected identity with form.getField()", "Open item", "Confirm on the first test that the read-only fields fill in after selection"],
                 ["Applications without the ENABLE feature", "Risk", "Reported as MANUAL by the emergency workflow; disable them on the target system"]],
                [65, 25, 80])]

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title="HLD - SailPoint IIQ HR CSV and LDAP",
                            author=AUTHOR)
    doc.build(glue_headings(s), onFirstPage=footer("HLD"), onLaterPages=footer("HLD"))


# ---------------------------------------------------------------- LLD
def build_lld(path):
    s = cover("Low-Level Design (LLD)", "Configuration, rules, workflows and runbook")

    s += [p("1. Environment", H1),
          table([["Item", "Value"],
                 ["IIQ URL", "http://localhost:8080/identityiq (Tomcat on Windows)"],
                 ["Source package", "SailPointIIQ-HR-CSV/ (config/, data/, ldif/)"],
                 ["Master import file", "config/init-HR-CSV.xml (run from the IIQ console: import .../config/init-HR-CSV.xml)"],
                 ["HR file", "C:/SailPoint/hrfeed/HR_Employees.csv"],
                 ["ApacheDS", "ldap://localhost:10389, bind uid=admin,ou=system / secret (lab default)"],
                 ["Logs", "WEB-INF/classes/log4j2.properties -> C:/SailPoint/logs/sailpoint.log"]],
                [40, 130]),

          p("2. HR Authoritative CSV application", H1),
          table([["Setting", "Value"],
                 ["Connector", "sailpoint.connector.DelimitedFileConnector (type DelimitedFile), authoritative"],
                 ["file / delimiter / hasHeader", "C:/SailPoint/hrfeed/HR_Employees.csv / | / true"],
                 ["Account ID / display", "employeeNumber"],
                 ["Rules", "Correlation, Creation (IdentityCreation), Customization, Manager Correlation"],
                 ["Provisioning policy", "Create Account Policy (fields from identity; date validation DD-MM-YYYY)"]],
                [45, 125]),
          p("<b>File layout</b>"),
          code("employeeNumber|firstName|lastName|startDate|endDate|managerId|jobDescription|country|employeeType|isManager\n"
               "1000|Ashokkumar|Chidambaram|01-01-2014|||Managing Director|India|Employee|Y\n"
               "1001|Rajesh|Kumar|01-04-2015||1000|Chief Executive Officer|India|Employee|N"),
          table([["Schema attribute", "Notes"],
                 ["employeeNumber, firstName, lastName, startDate, endDate, managerId, jobDescription, country, employeeType, isManager", "From the file"],
                 ["status, inactive, IIQDisabled", "Calculated by HR CSV - Customization (Terminated -> IIQDisabled = true)"]],
                [110, 60]),

          p("3. Identity attributes (ObjectConfig Identity)", H1),
          p("Created by the setup rule <b>HR CSV - Setup Identity Mappings</b> (run once; safe to re-run). "
            "They are shown on View Identity by <b>HR CSV - Show Attributes On Identity Page</b> (UIConfig identityViewAttributes)."),
          table([["Identity attribute", "Source", "Target"],
                 ["employeeNumber, startDate, endDate, jobDescription, country, employeeType, isManager", "HR CSV attribute of the same name", "-"],
                 ["firstname / lastname / manager", "HR firstName / lastName / managerId", "-"],
                 ["inactive", "Global rule Emergency Identity - Inactive Attribute (true if emergencyDisable, else HR inactive)", "-"],
                 ["emergencyDisable", "No source; editable (Permanent); set by the emergency workflow", "-"],
                 ["displayName", "Global rule HR CSV - Display Name", "LDAP ApacheDS: displayName"],
                 ["status", "Global rule HR Lifecycle - Status Attribute", "-"],
                 ["email", "LDAP ApacheDS: mail (generated by the Create Account policy)", "-"]],
                [70, 60, 40]),
          p("<b>Status calculation</b> (whole days; still Active on the end date):"),
          code("if emergencyDisable -> Disabled   (overrides the dates)\n"
               "if endDate  < today  -> Terminated\n"
               "if startDate > today -> PreHire\n"
               "otherwise            -> Active"),

          p("4. Rules", H1),
          table([["Rule", "Type", "Purpose"],
                 ["HR CSV - Customization", "ResourceObjectCustomization", "Trim values, validate dates, normalise isManager Y/N, set status / inactive / IIQDisabled"],
                 ["HR CSV - Correlation", "Correlation", "identityName = employeeNumber"],
                 ["HR CSV - Manager Correlation", "ManagerCorrelation", "Manager identity name = managerId"],
                 ["HR CSV - Identity Creation", "IdentityCreation", "Name = employeeNumber, first/last/display name, type"],
                 ["HR Lifecycle - Status Attribute", "IdentityAttribute (global)", "Disabled if emergencyDisable, else PreHire / Active / Terminated from HR dates"],
                 ["HR CSV - Display Name", "IdentityAttribute (global)", "firstName + ' ' + lastName"],
                 ["LDAP ApacheDS - Correlation", "Correlation", "identityName = LDAP employeeNumber"],
                 ["LDAP ApacheDS - Library", "Library", "JNDI connect, group add/remove, disable/enable, read attributes, time format"],
                 ["LDAP ApacheDS - Before Provisioning", "BeforeProvisioning", "Remove 'groups' from the request; keep changes as hrGroupsAdd / hrGroupsRemove"],
                 ["LDAP ApacheDS - After Provisioning", "AfterProvisioning", "Apply group changes as uniqueMember add/remove"],
                 ["LDAP ApacheDS - Customization", "ResourceObjectCustomization", "Read groups and account status (pwdAccountLockedTime etc.)"],
                 ["LDAP ApacheDS - Set Account Status", "Called rule", "Disable / enable LDAP account and update the IIQ link"],
                 ["LDAP ApacheDS - Disable Terminated Users", "Utility", "Catch-up: disable LDAP for identities already Terminated"],
                 ["HR CSV - Setup Identity Mappings", "Setup", "Create identity attributes, sources, global rules and LDAP target"],
                 ["HR CSV - Show Attributes On Identity Page", "Setup", "Add attributes to UIConfig identityViewAttributes"],
                 ["HR CSV - Diagnose", "Utility (read-only)", "Mappings (DB / cache), HR link, identity values, status rule result"],
                 ["Aggregate Single Account", "Utility", "Targeted aggregation of one account for any application"],
                 ["HR Lifecycle - Send Test Email", "Utility", "Show mail settings and send one test email"],
                 ["Emergency Identity - Inactive Attribute", "IdentityAttribute (global)", "inactive = emergencyDisable OR HR inactive"],
                 ["Emergency Identity - Provision Accounts", "Called rule", "Disable / enable every non-authoritative account; returns status + per-account details"],
                 ["Emergency Identity - Audit", "Called rule", "Write the AuditEvent and the log line"],
                 ["Emergency Identity - Setup", "Setup", "Create emergencyDisable, switch inactive to the global rule, add audit actions"]],
                [55, 38, 77]),

          p("5. LDAP ApacheDS application", H1),
          table([["Setting", "Value"],
                 ["Connector", "sailpoint.connector.LDAPConnector (type LDAP)"],
                 ["host / port / SSL", "localhost / 10389 / false; authorizationType simple"],
                 ["Account search DN / filter", "ou=people,dc=example,dc=com / (objectClass=inetOrgPerson), SUBTREE"],
                 ["Group search DN / filter", "ou=groups,dc=example,dc=com / (objectClass=groupOfUniqueNames); member attribute uniqueMember"],
                 ["beforeProvisioningRule / afterProvisioningRule", "LDAP ApacheDS - Before Provisioning / After Provisioning (application attributes)"],
                 ["CustomizationRule / CorrelationRule", "LDAP ApacheDS - Customization / Correlation"]],
                [60, 110]),
          p("<b>Account schema</b> (identityAttribute dn, display uid): uid, cn, sn, givenName, displayName, mail, "
            "employeeNumber, employeeType, title, objectClass (multi), groups (entitlement, managed, multi), "
            "accountStatus, pwdAccountLockedTime, lockedTime, lastFailedLogin, passwordLastChanged, createdOn, modifiedOn."),
          p("<b>Create Account Policy</b>"),
          table([["Field", "Value"],
                 ["uid", "firstname.lastname (lower case), made unique with 2, 3, ... against existing LDAP links"],
                 ["dn", "uid=&lt;uid&gt;,ou=people,dc=example,dc=com"],
                 ["objectClass", "top, person, organizationalPerson, inetOrgPerson"],
                 ["cn / displayName / sn / givenName", "identity display name / display name / last name / first name"],
                 ["mail / employeeNumber / title / employeeType", "&lt;uid&gt;@example.com / identity name / jobDescription / employeeType"],
                 ["password", "Welcome@&lt;employeeNumber&gt; (lab only)"]],
                [55, 115]),
          p("<b>Account status mapping</b>"),
          table([["pwdAccountLockedTime", "accountStatus", "IIQ flags"],
                 ["not present", "Active", "-"],
                 ["000001010000Z (admin lock)", "Disabled", "IIQDisabled = true"],
                 ["any other timestamp (failed logins)", "Locked", "IIQLocked = true; lockedTime set"]],
                [65, 45, 60]),

          p("6. ApacheDS directory layout (LDIF)", H1),
          code("dc=example,dc=com\n"
               "  ou=people   users created by IIQ: uid=<first.last>\n"
               "  ou=groups   groupOfUniqueNames (placeholder member uid=admin,ou=system)\n"
               "              cn=AllEmployees, cn=Contractors, cn=Managers, cn=Office365Access"),
          p("Files: ldif/ApacheDS-ou-people-and-groups.ldif, ldif/ApacheDS-group-Office365Access.ldif. "
            "The dc=example,dc=com partition must exist (Studio: server configuration > Partitions)."),

          p("7. Roles and entitlements", H1),
          table([["Role", "Type", "Assignment / requirement", "Entitlement"],
                 ["Birthright - All Active Users", "business", "MatchTerm status = Active", "requires LDAP - All Employees"],
                 ["Birthright - Contractors", "business", "status = Active AND employeeType = Contractor", "requires LDAP - Contractors"],
                 ["Birthright - Managers", "business", "status = Active AND isManager = Y", "requires LDAP - Managers"],
                 ["Office365 Access", "business", "No selector - requestable only", "requires LDAP - Office365Access"],
                 ["LDAP - All Employees / Contractors / Managers / Office365Access", "it",
                  "Profile on LDAP ApacheDS", "groups CONTAINS_ALL cn=...,ou=groups,dc=example,dc=com"]],
                [45, 18, 52, 55]),
          p("ManagedAttribute: groups = cn=Office365Access,ou=groups,dc=example,dc=com (requestable, with description)."),

          p("8. Lifecycle event, workflow and email", H1),
          table([["Object", "Configuration"],
                 ["IdentityTrigger 'HR Lifecycle - Status Change'", "type AttributeChange, attributeName status, handler WorkflowTriggerHandler, "
                  "HandlerParameters/Attributes: workflow = HR Lifecycle - Status Change Notification"],
                 ["Workflow 'HR Lifecycle - Status Change Notification'", "Collect Details -> [Disable LDAP | Enable LDAP] -> Check Notify -> Send Email -> Stop"],
                 ["EmailTemplate 'HR Lifecycle - Status Change'", "Name, employee number, old / new status, dates, job, manager, LDAP result"],
                 ["Recipient", "notifyEmail = ashokhearts@gmail.com"]],
                [60, 110]),
          code("Collect Details : oldStatus / newStatus from the IdentityChangeEvent\n"
               "Disable LDAP    : newStatus = Terminated and oldStatus != Terminated\n"
               "                  -> rule LDAP ApacheDS - Set Account Status (action Disable)\n"
               "Enable LDAP     : oldStatus = Terminated and newStatus = Active\n"
               "                  and emergencyDisable is not true\n"
               "                  -> rule LDAP ApacheDS - Set Account Status (action Enable)\n"
               "Check Notify    : email only when oldStatus and newStatus are set and differ"),

          p("9. Emergency Identity Disable / Enable", H1),
          table([["Object", "Configuration"],
                 ["SPRight / Capability", "EmergencyIdentityDisableEnable / EmergencyIdentityAdministrator"],
                 ["DynamicScope 'Emergency Identity Administrators'", "capabilities.name = SystemAdministrator OR EmergencyIdentityAdministrator"],
                 ["QuickLink 'Emergency Identity Disable / Enable'", "action workflow, category Manage, workflowName = Emergency Identity Status Management Workflow"],
                 ["Workflow 'Emergency Identity Status Management Workflow'", "transient; no approvals; form owner = launcher"],
                 ["File", "config/QuickLink/QuickLink-Emergency_Identity-DisableEnable.xml, "
                          "config/Workflow/Workflow-Emergency_Identity-StatusManagement.xml"]],
                [65, 105]),
          code("Request Form      : targetIdentity (Identity, postBack), read-only Identity Name, Current Status,\n"
               "                    Emergency Disable, HR Status; requestedAction (only the valid value);\n"
               "                    justification (required). Cancel -> Stop\n"
               "Validate Request  : launcher has SystemAdministrator / EmergencyIdentityAdministrator; target exists,\n"
               "                    is not the launcher; action matches emergencyDisable -> else DENIED -> Audit\n"
               "Update Identity   : ObjectUtil.lockIdentity; emergencyDisable = (action == Disable);\n"
               "                    status = rule HR Lifecycle - Status Attribute (Disabled / HR value);\n"
               "                    inactive = rule Emergency Identity - Inactive Attribute; unlock (commits)\n"
               "Provision Accounts: rule Emergency Identity - Provision Accounts -> provisioningResult\n"
               "Collect Result    : workflowResult = SUCCESS | PARTIAL | FAILED | NOTHING_TO_DO\n"
               "Audit             : rule Emergency Identity - Audit\n"
               "Show Result       : read-only form for the requestor -> Stop"),
          p("<b>Account handling</b> (Emergency Identity - Provision Accounts)"),
          table([["Account", "Disable", "Enable"],
                 ["Authoritative (HR Authoritative CSV)", "skipped", "skipped"],
                 ["Already in the requested state", "skipped", "skipped"],
                 ["Any account, HR status Terminated", "processed", "skipped (stays disabled)"],
                 ["LDAP ApacheDS", "rule LDAP ApacheDS - Set Account Status (Disable)", "same rule (Enable)"],
                 ["Connector supports ENABLE", "AccountRequest Disable via Provisioner", "AccountRequest Enable via Provisioner"],
                 ["Other", "MANUAL (counted as failed)", "MANUAL (counted as failed)"]],
                [60, 55, 55]),
          p("<b>Audit event</b>"),
          table([["Field", "Value"],
                 ["action", "EmergencyIdentityDisable / EmergencyIdentityEnable / EmergencyIdentityDenied"],
                 ["source / target / created", "requestor / target identity / date and time"],
                 ["string1", "workflow result: SUCCESS, PARTIAL, FAILED, NOTHING_TO_DO, DENIED"],
                 ["string2 / string3 / string4", "justification / emergencyDisable before -> after / account summary"],
                 ["attributes", "requestedAction, accounts (full list), workflowCaseId"]],
                [50, 120]),

          p("10. Tasks", H1),
          table([["Task", "Type", "Key options"],
                 ["HR Authoritative CSV - Account Aggregation", "AccountAggregation", "applications = HR Authoritative CSV, checkDeleted, noOptimizeReaggregation"],
                 ["HR Lifecycle - Daily Identity Refresh", "Identity refresh", "promoteAttributes, processTriggers, correlateEntitlements, provision, synchronizeAttributes, refreshManagerStatus"],
                 ["LDAP ApacheDS - Account Aggregation", "AccountAggregation", "applications = LDAP ApacheDS, checkDeleted"]],
                [60, 32, 78]),
          p("<b>Recommended schedule:</b> HR aggregation -> Daily Identity Refresh (00:05) -> LDAP aggregation."),

          p("11. Deployment runbook", H1),
          table([["Step", "Action"],
                 ["1", "ApacheDS: create the dc=example,dc=com partition; import both LDIF files; enable Password Policy"],
                 ["2", "Copy data/HR_Employees.csv to C:/SailPoint/hrfeed/"],
                 ["3", "IIQ console: import .../config/init-HR-CSV.xml"],
                 ["4", "Applications > LDAP ApacheDS: re-enter bind password, Test Connection; check the Rules tab"],
                 ["5", "rule \"HR CSV - Setup Identity Mappings\" then rule \"HR CSV - Show Attributes On Identity Page\"; log out / in"],
                 ["6", "Global Settings > Mail Settings: smtp.gmail.com, 587, TLS, app password; rule \"HR Lifecycle - Send Test Email\""],
                 ["7", "Run HR aggregation, Daily Identity Refresh, LDAP aggregation"],
                 ["8", "rule \"LDAP ApacheDS - Disable Terminated Users\" once for existing leavers"],
                 ["9", "Schedule the three tasks"],
                 ["10", "rule \"Emergency Identity - Setup\" (after step 5); give non-admin operators the Emergency Identity Administrator capability"],
                 ["11", "Run the Daily Identity Refresh once so inactive is recalculated by the new global rule"]],
                [12, 158]),

          p("12. Test cases", H1),
          table([["#", "Scenario", "Steps", "Expected result"],
                 ["T1", "Initial load", "HR aggregation + refresh", "16 identities named 1000-1015; Ashok is everyone's manager"],
                 ["T2", "Status", "Diagnose rule for 1000", "status = Active; 1009/1011/1015 Terminated; 1014 PreHire"],
                 ["T3", "Joiner", "Set 1014 startDate to today; aggregate + refresh", "Status Active; LDAP uid=james.taylor created in cn=AllEmployees; email"],
                 ["T4", "Leaver", "Set endDate to yesterday; aggregate + refresh", "Status Terminated; HR account disabled; LDAP pwdAccountLockedTime = 000001010000Z; groups removed; email"],
                 ["T5", "Rehire", "Clear endDate; aggregate + refresh", "Status Active; LDAP lock removed; email"],
                 ["T6", "Name change", "Change lastName; aggregate + refresh", "Identity last / display name updated; LDAP displayName updated"],
                 ["T7", "Request", "Request Office365 Access; approve", "User in cn=Office365Access"],
                 ["T8", "Status read-back", "Lock an entry in Studio; LDAP aggregation", "accountStatus Disabled / Locked in IIQ"],
                 ["T9", "Emergency access", "Log in as a user without the capabilities", "Quick link not shown"],
                 ["T10", "Emergency disable", "spadmin: quick link, active user, Disable", "Only Disable offered; emergencyDisable = true; inactive; LDAP locked; SUCCESS; audit EmergencyIdentityDisable"],
                 ["T11", "Emergency enable", "Same user again, Enable", "Only Enable offered; emergencyDisable = false; LDAP unlocked; audit EmergencyIdentityEnable"],
                 ["T12", "Refresh keeps state", "Emergency-disable a user; run Daily Identity Refresh", "Status stays Disabled whatever the HR dates; identity inactive; LDAP stays locked; birthright groups removed"]],
                [9, 22, 54, 85]),

          p("13. Troubleshooting", H1),
          table([["Symptom", "Cause / fix"],
                 ["Import: 'must match DOCTYPE root null'", "File has no DOCTYPE - every file in the package now has one"],
                 ["Unable to open filestream", "File path wrong or under OneDrive; use C:/SailPoint/hrfeed and check with Test-Path"],
                 ["could not resolve property: employeeNumber", "Non-searchable attribute; correlation now uses identity name"],
                 ["Attributes missing on identity", "Run the setup rule, then the Daily Identity Refresh; check with HR CSV - Diagnose"],
                 ["LDAP NO_SUCH_ATTRIBUTE groups", "Handled by Before / After Provisioning rules"],
                 ["Account not updated after HR change", "IIQ reads a different file; check File Path, schema Preview, Aggregate Single Account output"],
                 ["pwdAccountLockedTime not visible in Studio", "Enable 'Fetch operational attributes' in the connection's Browser Options"],
                 ["No email", "Mail settings / Gmail app password; run HR Lifecycle - Send Test Email"],
                 ["Emergency quick link not shown", "User lacks SystemAdministrator / EmergencyIdentityAdministrator; log out and in after granting"],
                 ["Emergency result PARTIAL / MANUAL", "An application has no ENABLE feature or provisioning failed; see the result lines and the audit event"],
                 ["Refresh re-activates an emergency-disabled identity", "inactive still mapped from HR; run rule \"Emergency Identity - Setup\""],
                 ["Java heap space", "setenv.bat CATALINA_OPTS -Xms1024m -Xmx4096m, or tomcat9w.exe Java tab for the service"]],
                [60, 110])]

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title="LLD - SailPoint IIQ HR CSV and LDAP",
                            author=AUTHOR)
    doc.build(glue_headings(s), onFirstPage=footer("LLD"), onLaterPages=footer("LLD"))


if __name__ == "__main__":
    OUT_DIR = sys.argv[1]
    build_hld(f"{OUT_DIR}/SailPointIIQ_HR_LDAP_HLD.pdf")
    build_lld(f"{OUT_DIR}/SailPointIIQ_HR_LDAP_LLD.pdf")
    print("done")
