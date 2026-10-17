package com.plugin.taskstatus.rest;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Renders task status rows as an HTML email with inline styles
 * (mail clients ignore stylesheets).
 */
public class TaskStatusReport {

    // status -> {label, color}; order is the order rows appear in the report
    private static final Map<String, String[]> STATUS = new LinkedHashMap<>();
    static {
        STATUS.put(TaskStatusResource.STATUS_FAILED, new String[] {"Failed", "#c62828"});
        STATUS.put(TaskStatusResource.STATUS_WARNING, new String[] {"Warning", "#ef8f00"});
        STATUS.put(TaskStatusResource.STATUS_RUNNING, new String[] {"Running", "#1565c0"});
        STATUS.put(TaskStatusResource.STATUS_SUCCESS, new String[] {"Success", "#2e7d32"});
        STATUS.put(TaskStatusResource.STATUS_NEVER_RUN, new String[] {"Never Run", "#9e9e9e"});
    }

    private static final String CELL = "padding:6px 10px;border-bottom:1px solid #e5e5e5;font-size:13px;";

    private TaskStatusReport() {
    }

    public static String toHtml(List<Map<String, Object>> rows) {
        SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss z");
        StringBuilder sb = new StringBuilder();

        sb.append("<div style=\"font-family:Arial,sans-serif;color:#333;\">");
        sb.append("<h2 style=\"margin:0 0 4px;\">IdentityIQ Scheduled Task Status</h2>");
        sb.append("<div style=\"font-size:12px;color:#777;margin-bottom:12px;\">Generated ")
          .append(esc(fmt.format(new Date()))).append("</div>");

        // Summary counts
        sb.append("<div style=\"margin-bottom:14px;\">");
        for (Map.Entry<String, String[]> e : STATUS.entrySet()) {
            int count = 0;
            for (Map<String, Object> row : rows) {
                if (e.getKey().equals(row.get("status"))) {
                    count++;
                }
            }
            sb.append("<span style=\"display:inline-block;margin-right:16px;font-size:14px;\">")
              .append(esc(e.getValue()[0])).append(": <b style=\"color:").append(e.getValue()[1])
              .append(";\">").append(count).append("</b></span>");
        }
        sb.append("</div>");

        sb.append("<table cellspacing=\"0\" style=\"border-collapse:collapse;width:100%;\">");
        sb.append("<tr style=\"background:#f7f7f7;text-align:left;\">");
        for (String h : new String[] {"Status", "Schedule", "Task Definition", "Last Run Started",
                                      "Last Run Completed", "Next Run", "Message"}) {
            sb.append("<th style=\"").append(CELL).append("\">").append(h).append("</th>");
        }
        sb.append("</tr>");

        // Failures first, then the rest in STATUS order
        for (String status : STATUS.keySet()) {
            for (Map<String, Object> row : rowsWithStatus(rows, status)) {
                String[] st = STATUS.get(status);
                sb.append("<tr>");
                sb.append("<td style=\"").append(CELL).append("\"><span style=\"background:").append(st[1])
                  .append(";color:#fff;padding:2px 8px;border-radius:10px;font-weight:bold;font-size:12px;\">")
                  .append(esc(st[0])).append("</span></td>");
                cell(sb, row.get("scheduleName"));
                cell(sb, row.get("taskDefinition"));
                cell(sb, date(fmt, row.get("launched")));
                cell(sb, date(fmt, row.get("completed")));
                cell(sb, date(fmt, row.get("nextExecution")));
                cell(sb, row.get("message"));
                sb.append("</tr>");
            }
        }
        sb.append("</table></div>");
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

    private static void cell(StringBuilder sb, Object value) {
        sb.append("<td style=\"").append(CELL).append("\">")
          .append(value != null ? esc(value.toString()) : "-").append("</td>");
    }

    private static String date(SimpleDateFormat fmt, Object millis) {
        return millis instanceof Long ? fmt.format(new Date((Long) millis)) : null;
    }

    private static String esc(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
    }
}
