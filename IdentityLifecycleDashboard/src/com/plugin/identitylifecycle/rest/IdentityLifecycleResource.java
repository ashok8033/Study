package com.plugin.identitylifecycle.rest;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.QueryParam;
import javax.ws.rs.core.MediaType;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import sailpoint.rest.plugin.BasePluginResource;
import sailpoint.rest.plugin.RequiredRight;
import sailpoint.tools.GeneralException;
import sailpoint.tools.Util;

/**
 * REST endpoint for the Identity Lifecycle Dashboard.
 *
 * GET /identityiq/plugin/rest/identitylifecycle/snapshot[?refresh=true]
 */
@Path("identitylifecycle")
@Produces(MediaType.APPLICATION_JSON)
public class IdentityLifecycleResource extends BasePluginResource {

    private static final Log log = LogFactory.getLog(IdentityLifecycleResource.class);

    // Plugin settings (manifest.xml)
    public static final String SETTING_STATUS_ATTRIBUTE = "identityStatusAttribute";
    public static final String SETTING_INACTIVE_VALUES = "inactiveStatusValues";
    public static final String SETTING_EXCLUDED_APPS = "excludedApplications";
    public static final String SETTING_INCLUDE_AUTHORITATIVE = "includeAuthoritativeApps";
    public static final String SETTING_CACHE_SECONDS = "cacheSeconds";
    public static final String SETTING_MAX_MISMATCH_ROWS = "maxMismatchRows";

    // Defaults match SailPointIIQ-HR-CSV: identity "status" = PreHire / Active / Terminated
    private static final String DEFAULT_STATUS_ATTRIBUTE = "status";
    private static final String DEFAULT_INACTIVE_VALUES = "Terminated,PreHire";
    private static final int DEFAULT_CACHE_SECONDS = 30;
    private static final int DEFAULT_MAX_MISMATCH_ROWS = 2000;

    // Shared across requests so concurrent viewers reuse one computation
    private static final Object LOCK = new Object();
    private static Map<String, Object> cachedSnapshot;
    private static String cachedConfigKey;
    private static long cachedAt;

    @Override
    public String getPluginName() {
        return "IdentityLifecycleDashboard";
    }

    @GET
    @Path("snapshot")
    @RequiredRight("ViewIdentityLifecycleDashboard")
    public Map<String, Object> getSnapshot(@QueryParam("refresh") boolean refresh) throws GeneralException {
        String statusSetting = getSettingString(SETTING_STATUS_ATTRIBUTE);
        String statusAttribute = (statusSetting == null ? DEFAULT_STATUS_ATTRIBUTE : statusSetting).trim();
        String inactiveSetting = getSettingString(SETTING_INACTIVE_VALUES);
        Set<String> inactiveValues = csv(inactiveSetting == null ? DEFAULT_INACTIVE_VALUES : inactiveSetting);
        Set<String> excludedApps = csv(getSettingString(SETTING_EXCLUDED_APPS));
        boolean includeAuthoritative = getSettingBool(SETTING_INCLUDE_AUTHORITATIVE);
        int cacheSeconds = setting(SETTING_CACHE_SECONDS, DEFAULT_CACHE_SECONDS);
        int maxRows = setting(SETTING_MAX_MISMATCH_ROWS, DEFAULT_MAX_MISMATCH_ROWS);

        // A settings change invalidates the cache
        String configKey = statusAttribute + "|" + inactiveValues + "|" + excludedApps + "|"
                + includeAuthoritative + "|" + maxRows;

        synchronized (LOCK) {
            long ageMs = System.currentTimeMillis() - cachedAt;
            boolean fresh = cachedSnapshot != null && configKey.equals(cachedConfigKey)
                    && ageMs < cacheSeconds * 1000L;
            if (!refresh && fresh) {
                return withMeta(cachedSnapshot, true, statusAttribute, inactiveValues, excludedApps,
                        includeAuthoritative, cacheSeconds);
            }

            LifecycleSnapshotBuilder builder = new LifecycleSnapshotBuilder(getContext(), statusAttribute,
                    inactiveValues, excludedApps, includeAuthoritative, maxRows);
            Map<String, Object> snapshot = builder.build();
            if (log.isDebugEnabled()) {
                log.debug("Identity lifecycle snapshot built in " + snapshot.get("durationMs") + " ms");
            }

            cachedSnapshot = snapshot;
            cachedConfigKey = configKey;
            cachedAt = System.currentTimeMillis();
            return withMeta(snapshot, false, statusAttribute, inactiveValues, excludedApps,
                    includeAuthoritative, cacheSeconds);
        }
    }

    private Map<String, Object> withMeta(Map<String, Object> snapshot, boolean cached, String statusAttribute,
                                         Set<String> inactiveValues, Set<String> excludedApps,
                                         boolean includeAuthoritative, int cacheSeconds) {
        Map<String, Object> config = new LinkedHashMap<>();
        config.put("statusAttribute", statusAttribute.isEmpty() ? null : statusAttribute);
        config.put("inactiveStatusValues", inactiveValues);
        config.put("excludedApplications", excludedApps);
        config.put("includeAuthoritativeApps", includeAuthoritative);
        config.put("cacheSeconds", cacheSeconds);

        Map<String, Object> result = new LinkedHashMap<>(snapshot);
        result.put("cached", cached);
        result.put("config", config);
        return result;
    }

    private int setting(String name, int defaultValue) {
        String value = getSettingString(name);
        if (Util.isNullOrEmpty(value)) {
            return defaultValue;
        }
        try {
            return Math.max(0, Integer.parseInt(value.trim()));
        } catch (NumberFormatException e) {
            log.warn("Invalid number for plugin setting " + name + ": " + value);
            return defaultValue;
        }
    }

    private static Set<String> csv(String value) {
        Set<String> out = new LinkedHashSet<>();
        if (value != null) {
            for (String part : value.split(",")) {
                if (!part.trim().isEmpty()) {
                    out.add(part.trim());
                }
            }
        }
        return out;
    }
}
