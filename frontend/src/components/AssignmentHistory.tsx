import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AssignmentMutation, AssignmentReasonCategory } from "../types";

const PAGE_SIZE = 25;
const reasonLabels: Record<AssignmentReasonCategory, string> = {
  field_condition_changed: "Field condition changed",
  crew_unavailable: "Crew unavailable",
  assignment_entered_in_error: "Assignment entered in error",
  incident_priority_changed: "Incident priority changed",
  supervisor_direction: "Supervisor direction",
  other: "Other"
};

function formatEventTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short"
  }).format(date);
}

function EventField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function AssignmentHistory({ scenarioId, scenarioName }: { scenarioId: string; scenarioName: string }) {
  const [events, setEvents] = useState<AssignmentMutation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [failedRequest, setFailedRequest] = useState<{ offset: number; replace: boolean } | null>(null);
  const requestVersion = useRef(0);

  const loadPage = useCallback(async (offset: number, replace: boolean) => {
    const version = ++requestVersion.current;
    setLoading(true);
    setError("");
    setFailedRequest(null);
    try {
      const page = await api.assignmentHistory(PAGE_SIZE, offset);
      if (version !== requestVersion.current) return;
      setEvents((current) => replace ? page : [...current, ...page]);
      setHasMore(page.length === PAGE_SIZE);
    } catch (failure) {
      if (version !== requestVersion.current) return;
      setError(failure instanceof Error ? failure.message : "Assignment history could not be loaded.");
      setFailedRequest({ offset, replace });
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setEvents([]);
    setHasMore(false);
    void loadPage(0, true);
    return () => { requestVersion.current += 1; };
  }, [loadPage, scenarioId]);

  return (
    <section aria-busy={loading} aria-labelledby="assignment-history-title" className="panel assignment-history">
      <div className="assignment-history-heading">
        <div>
          <h2 id="assignment-history-title">Audit / Assignment History</h2>
          <p>Unassign and reassign actions recorded for {scenarioName} ({scenarioId}). Recommendation decisions have separate history.</p>
        </div>
        <button className="secondary-action" disabled={loading} onClick={() => void loadPage(0, true)} type="button">Refresh history</button>
      </div>

      {error ? (
        <div className="assignment-history-error" role="alert">
          <p>Assignment history could not be loaded: {error}</p>
          <button onClick={() => void loadPage(failedRequest?.offset ?? 0, failedRequest?.replace ?? true)} type="button">Retry history</button>
        </div>
      ) : null}

      {loading && events.length === 0 ? <p role="status">Loading assignment history...</p> : null}
      {!loading && !error && events.length === 0 ? <p>No assignment changes recorded for this scenario.</p> : null}

      {events.length > 0 ? (
        <>
          <p className="assignment-history-count">Showing {events.length} most recent assignment change{events.length === 1 ? "" : "s"}.</p>
          <ol className="assignment-history-list">
            {events.map((event) => (
              <li key={event.mutation_id}>
                <article aria-label={`${event.action === "reassigned" ? "Reassigned" : "Unassigned"} ${event.incident_id}`} className="assignment-history-event">
                  <header>
                    <strong>{event.action === "reassigned" ? "Reassigned" : "Unassigned"}</strong>
                    <time dateTime={event.created_at}>{formatEventTime(event.created_at)}</time>
                  </header>
                  <dl>
                    <EventField label="Incident" value={event.incident_id} />
                    <EventField label="Prior crew" value={event.crew_id} />
                    <EventField
                      label="New crew"
                      value={event.action === "unassigned" ? "None" : event.new_crew_id ?? "Unavailable (legacy event)"}
                    />
                    <EventField label="Reason category" value={reasonLabels[event.reason_category]} />
                    <EventField label="Note" value={event.note || "None provided"} />
                    <EventField label="Actor" value={event.actor} />
                    <EventField label="Scenario" value={event.scenario_id} />
                    <EventField
                      label="Incident status after action"
                      value={event.resulting_incident_status ?? "Unavailable (legacy event)"}
                    />
                    <EventField label="Prior assignment" value={event.assignment_id} />
                    {event.action === "reassigned" ? (
                      <EventField label="New assignment" value={event.new_assignment_id ?? "Unavailable (legacy event)"} />
                    ) : null}
                  </dl>
                </article>
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {hasMore && !error ? (
        <button className="secondary-action" disabled={loading} onClick={() => void loadPage(events.length, false)} type="button">
          {loading ? "Loading more..." : "Load more history"}
        </button>
      ) : null}
    </section>
  );
}
