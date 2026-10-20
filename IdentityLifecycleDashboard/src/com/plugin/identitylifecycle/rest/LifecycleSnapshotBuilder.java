package com.plugin.identitylifecycle.rest;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import sailpoint.api.IncrementalObjectIterator;
import sailpoint.api.SailPointContext;
import sailpoint.object.Application;
import sailpoint.object.Filter;
import sailpoint.object.Identity;
import sailpoint.object.Link;
import sailpoint.object.QueryOptions;
import sailpoint.tools.GeneralException;
import sailpoint.tools.Util;

/**
 * Walks every identity and its accounts once and builds the dashboard snapshot:
 * KPI totals, a breakdown per lifecycle status, a breakdown per application and
 * the list of accounts whose enabled/disabled state does not match the identity.
 */
public class LifecycleSnapshotBuilder {

    public static final String ISSUE_INACTIVE_ENABLED = "InactiveIdentityEnabledAccount";
    public static final String ISSUE_ACTIVE_DISABLED = "ActiveIdentityDisabledAccount";

    static final String STATUS_ACTIVE = "Active";
    static final String STATUS_INACTIVE = "Inactive";
    static final String STATUS_NOT_SET = "(not set)";

    // Objects are released from the Hibernate session after this many identities
    private static final int DECACHE_EVERY = 100;

    private final SailPointContext context;
    private final String statusAttribute;
    private final Set<String> inactiveValues;
    private final Set<String> excludedApps;
    private final boolean includeAuthoritative;
    private final int maxMismatchRows;

    // Totals
    private int identities;
    private int identitiesExpectEnabled;
    private int identitiesExpectDisabled;
    private int identitiesWithMismatch;
    private int identitiesWithoutAccounts;
    private int accounts;
    private int enabledAccounts;
    private int disabledAccounts;
    private int lockedAccounts;
    private int inactiveEnabled;
    private int activeDisabled;

    private final Map<String, Bucket> lifecycle = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
    private final Map<String, Bucket> applications = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
    private final List<Map<String, Object>> mismatches = new ArrayList<>();

    public LifecycleSnapshotBuilder(SailPointContext context, String statusAttribute, Set<String> inactiveValues,
                                    Set<String> excludedApps, boolean includeAuthoritative, int maxMismatchRows) {
        this.context = context;
        this.statusAttribute = Util.isNullOrEmpty(statusAttribute) ? null : statusAttribute.trim();
        this.inactiveValues = lowerCase(inactiveValues);
        this.excludedApps = lowerCase(excludedApps);
        this.includeAuthoritative = includeAuthoritative;
        this.maxMismatchRows = maxMismatchRows;
    }

    public Map<String, Object> build() throws GeneralException {
        long start = System.currentTimeMillis();
        Set<String> authoritativeApps = includeAuthoritative ? new HashSet<>() : loadAuthoritativeApps();

        QueryOptions qo = new QueryOptions();
        qo.addFilter(Filter.eq("workgroup", false));
        IncrementalObjectIterator<Identity> it = new IncrementalObjectIterator<>(context, Identity.class, qo);
        int count = 0;
        while (it.hasNext()) {
            processIdentity(it.next(), authoritativeApps);
            if (++count % DECACHE_EVERY == 0) {
                context.decache();
            }
        }
        context.decache();

        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("generatedAt", System.currentTimeMillis());
        snapshot.put("durationMs", System.currentTimeMillis() - start);
        snapshot.put("kpis", kpis());
        snapshot.put("lifecycle", toList(lifecycle, "status"));
        snapshot.put("applications", toList(applications, "application"));
        snapshot.put("mismatches", mismatches);
        snapshot.put("mismatchTotal", inactiveEnabled + activeDisabled);
        snapshot.put("mismatchTruncated", inactiveEnabled + activeDisabled > mismatches.size());
        return snapshot;
    }

    private void processIdentity(Identity identity, Set<String> authoritativeApps) {
        String status = lifecycleStatus(identity);
        boolean expectEnabled = expectEnabled(identity, status);

        identities++;
        if (expectEnabled) {
            identitiesExpectEnabled++;
        } else {
            identitiesExpectDisabled++;
        }

        Bucket lc = lifecycle.computeIfAbsent(status, k -> new Bucket());
        lc.identities++;
        lc.expectEnabled = expectEnabled;

        boolean hasMismatch = false;
        int counted = 0;
        List<Link> links = identity.getLinks();
        if (links != null) {
            for (Link link : links) {
                String app = link.getApplicationName();
                if (app == null || excludedApps.contains(app.toLowerCase())
                        || authoritativeApps.contains(app.toLowerCase())) {
                    continue;
                }
                counted++;
                boolean disabled = link.isDisabled();
                boolean locked = link.isLocked();

                accounts++;
                if (disabled) {
                    disabledAccounts++;
                } else {
                    enabledAccounts++;
                }
                if (locked) {
                    lockedAccounts++;
                }

                Bucket ab = applications.computeIfAbsent(app, k -> new Bucket());
                ab.accounts++;
                lc.accounts++;
                if (disabled) {
                    ab.disabled++;
                    lc.disabled++;
                } else {
                    ab.enabled++;
                    lc.enabled++;
                }
                if (locked) {
                    ab.locked++;
                }

                String issue = null;
                if (!expectEnabled && !disabled) {
                    issue = ISSUE_INACTIVE_ENABLED;
                    inactiveEnabled++;
                    ab.inactiveEnabled++;
                    lc.inactiveEnabled++;
                } else if (expectEnabled && disabled) {
                    issue = ISSUE_ACTIVE_DISABLED;
                    activeDisabled++;
                    ab.activeDisabled++;
                    lc.activeDisabled++;
                }
                if (issue != null) {
                    hasMismatch = true;
                    ab.mismatches++;
                    lc.mismatches++;
                    if (mismatches.size() < maxMismatchRows) {
                        mismatches.add(mismatchRow(identity, status, link, app, disabled, locked, issue));
                    }
                }
            }
        }
        if (counted == 0) {
            identitiesWithoutAccounts++;
        }
        if (hasMismatch) {
            identitiesWithMismatch++;
            lc.identitiesWithMismatch++;
        }
    }

    String lifecycleStatus(Identity identity) {
        if (statusAttribute == null) {
            return identity.isInactive() ? STATUS_INACTIVE : STATUS_ACTIVE;
        }
        Object value = identity.getAttribute(statusAttribute);
        String status = value != null ? value.toString().trim() : "";
        return status.isEmpty() ? STATUS_NOT_SET : status;
    }

    /** Accounts should be enabled unless the status is an inactive value (or the Inactive flag when unset). */
    boolean expectEnabled(Identity identity, String status) {
        if (STATUS_NOT_SET.equals(status)) {
            return !identity.isInactive();
        }
        return !inactiveValues.contains(status.toLowerCase());
    }

    private Map<String, Object> mismatchRow(Identity identity, String status, Link link, String app,
                                            boolean disabled, boolean locked, String issue) {
        Map<String, Object> row = new HashMap<>();
        row.put("identityId", identity.getId());
        row.put("identity", identity.getName());
        row.put("identityDisplayName", identity.getDisplayableName());
        row.put("identityStatus", status);
        row.put("application", app);
        row.put("account", link.getDisplayableName());
        row.put("nativeIdentity", link.getNativeIdentity());
        row.put("accountStatus", disabled ? "Disabled" : "Enabled");
        row.put("locked", locked);
        row.put("issue", issue);
        return row;
    }

    private Map<String, Object> kpis() {
        Map<String, Object> k = new LinkedHashMap<>();
        int mismatched = inactiveEnabled + activeDisabled;
        k.put("identities", identities);
        k.put("identitiesExpectEnabled", identitiesExpectEnabled);
        k.put("identitiesExpectDisabled", identitiesExpectDisabled);
        k.put("identitiesWithMismatch", identitiesWithMismatch);
        k.put("identitiesWithoutAccounts", identitiesWithoutAccounts);
        k.put("accounts", accounts);
        k.put("enabledAccounts", enabledAccounts);
        k.put("disabledAccounts", disabledAccounts);
        k.put("lockedAccounts", lockedAccounts);
        k.put("mismatchedAccounts", mismatched);
        k.put("inactiveIdentityEnabledAccounts", inactiveEnabled);
        k.put("activeIdentityDisabledAccounts", activeDisabled);
        // One decimal place; 100% when there are no accounts to compare
        k.put("compliancePct", accounts == 0 ? 100.0 : Math.floor((accounts - mismatched) * 1000.0 / accounts) / 10.0);
        return k;
    }

    private Set<String> loadAuthoritativeApps() throws GeneralException {
        Set<String> names = new HashSet<>();
        QueryOptions qo = new QueryOptions();
        qo.addFilter(Filter.eq("authoritative", true));
        Iterator<Object[]> it = context.search(Application.class, qo, "name");
        while (it.hasNext()) {
            Object name = it.next()[0];
            if (name != null) {
                names.add(name.toString().toLowerCase());
            }
        }
        return names;
    }

    private static Set<String> lowerCase(Set<String> values) {
        Set<String> out = new HashSet<>();
        if (values != null) {
            for (String v : values) {
                out.add(v.trim().toLowerCase());
            }
        }
        return out;
    }

    private static List<Map<String, Object>> toList(Map<String, Bucket> buckets, String keyName) {
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map.Entry<String, Bucket> e : buckets.entrySet()) {
            Map<String, Object> m = e.getValue().toMap();
            m.put(keyName, e.getKey());
            list.add(m);
        }
        return list;
    }

    /** Running counts for one lifecycle status or one application. */
    private static class Bucket {
        int identities;
        int identitiesWithMismatch;
        Boolean expectEnabled;
        int accounts;
        int enabled;
        int disabled;
        int locked;
        int mismatches;
        int inactiveEnabled;
        int activeDisabled;

        Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("identities", identities);
            m.put("identitiesWithMismatch", identitiesWithMismatch);
            m.put("expectEnabled", expectEnabled);
            m.put("accounts", accounts);
            m.put("enabled", enabled);
            m.put("disabled", disabled);
            m.put("locked", locked);
            m.put("mismatches", mismatches);
            m.put("inactiveEnabled", inactiveEnabled);
            m.put("activeDisabled", activeDisabled);
            return m;
        }
    }
}
