package com.plugin.taskstatus.rest;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Renders task status rows as an HTML email.
 *
 * IdentityIQ strips table tags from outgoing mail, so the layout uses only
 * div/span/b with inline styles (mail clients also ignore stylesheets).
 */
public class TaskStatusReport {

    // status -> {label, color, light background}; order is the order rows appear in the report
    private static final Map<String, String[]> STATUS = new LinkedHashMap<>();
    static {
        STATUS.put(TaskStatusResource.STATUS_FAILED, new String[] {"Failed", "#c62828", "#fdecea"});
        STATUS.put(TaskStatusResource.STATUS_WARNING, new String[] {"Warning", "#ef8f00", "#fff4e0"});
        STATUS.put(TaskStatusResource.STATUS_RUNNING, new String[] {"Running", "#1565c0", "#e8f0fb"});
        STATUS.put(TaskStatusResource.STATUS_SUCCESS, new String[] {"Success", "#2e7d32", "#f1f8f1"});
        STATUS.put(TaskStatusResource.STATUS_NEVER_RUN, new String[] {"Never Run", "#9e9e9e", "#f5f5f5"});
    }

    private static final String DETAIL = "font-size:12px;color:#555;margin-top:4px;";
    private static final String SEP = "<span style=\"color:#bbb;\">&nbsp;&nbsp;|&nbsp;&nbsp;</span>";

    private TaskStatusReport() {
    }

    public static String toHtml(List<Map<String, Object>> rows) {
        SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        SimpleDateFormat full = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss z");
        StringBuilder sb = new StringBuilder();

        sb.append("<div style=\"font-family:Arial,Helvetica,sans-serif;color:#333;max-width:900px;\">");
        sb.append("<div style=\"font-size:20px;font-weight:bold;margin-bottom:4px;\">IdentityIQ Scheduled Task Status</div>");
        sb.append("<div style=\"font-size:12px;color:#777;margin-bottom:14px;\">Generated ")
          .append(esc(full.format(new Date()))).append(". All times in server time zone.</div>");

        // Summary counts as colored tiles
        sb.append("<div style=\"margin-bottom:18px;\">");
        for (Map.Entry<String, String[]> e : STATUS.entrySet()) {
            String[] st = e.getValue();
            sb.append("<span style=\"display:inline-block;min-width:90px;margin:0 8px 8px 0;padding:8px 12px;")
              .append("border-radius:6px;background:").append(st[2]).append(";border-top:3px solid ").append(st[1])
              .append(";\"><span style=\"display:block;font-size:12px;color:#555;\">").append(esc(st[0]))
              .append("</span><span style=\"display:block;font-size:22px;font-weight:bold;color:").append(st[1])
              .append(";\">").append(rowsWithStatus(rows, e.getKey()).size()).append("</span></span>");
        }
        sb.append("</div>");

        // One block per task: failures first, then the rest in STATUS order
        for (Map.Entry<String, String[]> e : STATUS.entrySet()) {
            String[] st = e.getValue();
            for (Map<String, Object> row : rowsWithStatus(rows, e.getKey())) {
                sb.append("<div style=\"padding:10px 14px;margin-bottom:8px;border-radius:4px;background:")
                  .append(st[2]).append(";border-left:5px solid ").append(st[1]).append(";\">");

                sb.append("<div><span style=\"background:").append(st[1])
                  .append(";color:#fff;padding:2px 8px;border-radius:10px;font-weight:bold;font-size:11px;\">")
                  .append(esc(st[0])).append("</span>&nbsp;&nbsp;<b style=\"font-size:14px;\">")
                  .append(esc(str(row.get("scheduleName")))).append("</b></div>");

                sb.append("<div style=\"").append(DETAIL).append("\">")
                  .append("<b>Task:</b> ").append(esc(str(row.get("taskDefinition"))))
                  .append(SEP).append("<b>Started:</b> ").append(date(fmt, row.get("launched")))
                  .append(SEP).append("<b>Completed:</b> ").append(date(fmt, row.get("completed")))
                  .append(SEP).append("<b>Duration:</b> ").append(duration(row.get("launched"), row.get("completed")))
                  .append(SEP).append("<b>Next run:</b> ").append(date(fmt, row.get("nextExecution")))
                  .append("</div>");

                Object message = row.get("message");
                if (message != null) {
                    sb.append("<div style=\"").append(DETAIL).append("color:#c62828;\"><b>Error:</b> ")
                      .append(esc(message.toString())).append("</div>");
                }
                sb.append("</div>");
            }
        }

        if (rows.isEmpty()) {
            sb.append("<div style=\"color:#777;\">No scheduled tasks found.</div>");
        }
        sb.append("</div>");
        return sb.toString();
    }

    private static List<Map<String, Object>> rowsWithStatus(List<Map<String, Object>> rows, String status) {
        List<Map<String, Object>> matching = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            if (status.equals(row.get("status"))) {
                matching.add(row);
            }
        }
        return matching;
    }

    private static String str(Object value) {
        return value != null ? value.toString() : "-";
    }

    private static String date(SimpleDateFormat fmt, Object millis) {
        return millis instanceof Long ? fmt.format(new Date((Long) millis)) : "-";
    }

    private static String duration(Object start, Object end) {
        if (!(start instanceof Long) || !(end instanceof Long)) {
            return "-";
        }
        long secs = Math.max(0, ((Long) end - (Long) start) / 1000);
        long h = secs / 3600, m = (secs % 3600) / 60, s = secs % 60;
        return (h > 0 ? h + "h " : "") + (h > 0 || m > 0 ? m + "m " : "") + s + "s";
    }

    private static String esc(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
    }
}
