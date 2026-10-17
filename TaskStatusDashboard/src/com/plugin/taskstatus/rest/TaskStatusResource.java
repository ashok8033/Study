package com.plugin.taskstatus.rest;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import sailpoint.api.SailPointContext;
import sailpoint.object.EmailOptions;
import sailpoint.object.EmailTemplate;
import sailpoint.object.Filter;
import sailpoint.object.QueryOptions;
import sailpoint.object.TaskDefinition;
import sailpoint.object.TaskResult;
import sailpoint.object.TaskResult.CompletionStatus;
import sailpoint.object.TaskSchedule;
import sailpoint.rest.plugin.BasePluginResource;
import sailpoint.rest.plugin.RequiredRight;
import sailpoint.tools.GeneralException;
import sailpoint.tools.Message;
import sailpoint.tools.Util;

/**
 * REST endpoints returning the latest execution status of every TaskSchedule
 * and emailing it as a report.
 *
 * GET  /identityiq/plugin/rest/taskstatus/schedules
 * POST /identityiq/plugin/rest/taskstatus/email
 */
@Path("taskstatus")
@Produces(MediaType.APPLICATION_JSON)
public class TaskStatusResource extends BasePluginResource {

    private static final Log log = LogFactory.getLog(TaskStatusResource.class);

    // Status values the UI maps to colors
    public static final String STATUS_SUCCESS = "Success";
    public static final String STATUS_FAILED = "Failed";
    public static final String STATUS_WARNING = "Warning";
    public static final String STATUS_RUNNING = "Running";
    public static final String STATUS_NEVER_RUN = "NeverRun";

    // Plugin setting (manifest.xml) holding comma separated report recipients
    public static final String SETTING_RECIPIENTS = "reportRecipients";

    @Override
    public String getPluginName() {
        return "TaskStatusDashboard";
    }

    @GET
    @Path("schedules")
    @RequiredRight("ViewTaskStatusDashboard")
    public List<Map<String, Object>> getSchedules() throws GeneralException {
        SailPointContext context = getContext();
        List<Map<String, Object>> rows = new ArrayList<>();

        // TaskSchedules live in Quartz, not Hibernate, so fetch all and sort in memory
        List<TaskSchedule> schedules = context.getObjects(TaskSchedule.class, new QueryOptions());
        if (schedules == null) {
            return rows;
        }
        schedules.sort(Comparator.comparing(s -> Util.otos(s.getName())));
        for (TaskSchedule schedule : schedules) {
            try {
                rows.add(buildRow(context, schedule));
            } catch (Exception e) {
                log.error("Unable to read status for schedule " + schedule.getName(), e);
            }
        }
        return rows;
    }

    /**
     * Emails the current status report to the recipients in the plugin's
     * "reportRecipients" setting.
     *
     * POST /identityiq/plugin/rest/taskstatus/email
     */
    @POST
    @Path("email")
    @RequiredRight("ViewTaskStatusDashboard")
    public Response emailReport() {
        Map<String, Object> body = new HashMap<>();
        String recipients = getSettingString(SETTING_RECIPIENTS);
        if (Util.isNullOrEmpty(recipients)) {
            body.put("message", "No recipients configured in the plugin setting 'Report recipients'.");
            return Response.status(Response.Status.BAD_REQUEST).entity(body).build();
        }

        try {
            List<Map<String, Object>> rows = getSchedules();

            EmailTemplate template = new EmailTemplate();
            template.setSubject("IdentityIQ Scheduled Task Status - " + countFailed(rows) + " failed");
            // The report goes in as a variable so Velocity does not parse task names or messages
            template.setBody("<html><body>$reportHtml</body></html>");

            EmailOptions options = new EmailOptions(recipients, null);
            options.setVariable("reportHtml", TaskStatusReport.toHtml(rows));
            options.setSendImmediate(true);

            getContext().sendEmailNotification(template, options);
        } catch (Exception e) {
            log.error("Unable to send task status report to " + recipients, e);
            body.put("message", "Failed to send email: " + e.getMessage());
            return Response.status(Response.Status.INTERNAL_SERVER_ERROR).entity(body).build();
        }

        body.put("recipients", recipients);
        return Response.ok(body).build();
    }

    private int countFailed(List<Map<String, Object>> rows) {
        int failed = 0;
        for (Map<String, Object> row : rows) {
            if (STATUS_FAILED.equals(row.get("status"))) {
                failed++;
            }
        }
        return failed;
    }

    private Map<String, Object> buildRow(SailPointContext context, TaskSchedule schedule)
            throws GeneralException {
        Map<String, Object> row = new HashMap<>();
        row.put("scheduleName", schedule.getName());
        row.put("description", schedule.getDescription());
        row.put("nextExecution", toMillis(schedule.getNextExecution()));
        row.put("cron", schedule.getCronExpressions());

        TaskDefinition definition = getDefinition(context, schedule);
        row.put("taskDefinition", definition != null ? definition.getName() : null);

        TaskResult result = getLatestResult(context, schedule, definition);
        if (result == null) {
            row.put("status", STATUS_NEVER_RUN);
            return row;
        }

        row.put("resultId", result.getId());
        row.put("resultName", result.getName());
        row.put("launched", toMillis(result.getLaunched()));
        row.put("completed", toMillis(result.getCompleted()));
        row.put("host", result.getHost());
        row.put("status", toStatus(result));
        row.put("completionStatus",
                result.getCompletionStatus() != null ? result.getCompletionStatus().name() : null);
        row.put("message", firstError(result));
        return row;
    }

    private TaskDefinition getDefinition(SailPointContext context, TaskSchedule schedule)
            throws GeneralException {
        Object executor = schedule.getArgument(TaskSchedule.ARG_EXECUTOR);
        if (executor == null) {
            return null;
        }
        return context.getObject(TaskDefinition.class, executor.toString());
    }

    /**
     * Find the newest TaskResult launched by this schedule. Falls back to the newest
     * result of the schedule's TaskDefinition when results do not record the schedule.
     */
    private TaskResult getLatestResult(SailPointContext context, TaskSchedule schedule,
                                       TaskDefinition definition) throws GeneralException {
        TaskResult result = findNewest(context, Filter.eq("schedule", schedule.getName()));
        if (result == null && definition != null) {
            result = findNewest(context, Filter.eq("definition.id", definition.getId()));
        }
        return result;
    }

    private TaskResult findNewest(SailPointContext context, Filter filter) throws GeneralException {
        QueryOptions qo = new QueryOptions();
        qo.addFilter(filter);
        qo.addOrdering("launched", false);
        qo.setResultLimit(1);
        List<TaskResult> results = context.getObjects(TaskResult.class, qo);
        return Util.isEmpty(results) ? null : results.get(0);
    }

    private String toStatus(TaskResult result) {
        if (result.getCompleted() == null) {
            return STATUS_RUNNING;
        }
        CompletionStatus cs = result.getCompletionStatus();
        if (cs == null || cs == CompletionStatus.Success) {
            return STATUS_SUCCESS;
        }
        if (cs == CompletionStatus.Warning) {
            return STATUS_WARNING;
        }
        // Error, Terminated, TempError
        return STATUS_FAILED;
    }

    private String firstError(TaskResult result) {
        List<Message> errors = result.getErrors();
        if (Util.isEmpty(errors)) {
            return null;
        }
        return errors.get(0).getLocalizedMessage();
    }

    private Long toMillis(Date date) {
        return date != null ? date.getTime() : null;
    }
}
