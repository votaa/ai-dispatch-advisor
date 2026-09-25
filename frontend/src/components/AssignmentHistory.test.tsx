import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ assignmentHistory: vi.fn() }));
vi.mock("../api", () => ({ api: apiMocks }));

import { AssignmentHistory } from "./AssignmentHistory";

const legacyEvent = {
  mutation_id: "MUT-OLD",
  scenario_id: "base",
  assignment_id: "ASG-OLD",
  incident_id: "INC-1001",
  crew_id: "CR-01",
  action: "reassigned" as const,
  reason: "Crew unavailable",
  reason_category: "crew_unavailable" as const,
  note: null,
  actor: "demo-dispatcher",
  created_at: "2026-09-22T12:00:00Z",
  new_assignment_id: null,
  new_crew_id: null,
  resulting_incident_status: null
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("labels unknown legacy values and retries a failed history request", async () => {
  apiMocks.assignmentHistory.mockRejectedValueOnce(new Error("History service unavailable"))
    .mockResolvedValueOnce([legacyEvent]);
  render(<AssignmentHistory scenarioId="base" scenarioName="Base Operations" />);

  expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("History service unavailable"));
  fireEvent.click(screen.getByRole("button", { name: "Retry history" }));

  const event = await screen.findByRole("article", { name: "Reassigned INC-1001" });
  expect(within(event).getAllByText("Unavailable (legacy event)")).toHaveLength(3);
  expect(within(event).getByText("None provided")).toBeTruthy();
  expect(within(event).getByText(/Sep 22, 2026/)).toBeTruthy();
});

it("pages through history and refreshes from the first page", async () => {
  const firstPage = Array.from({ length: 25 }, (_, index) => ({
    ...legacyEvent,
    mutation_id: `MUT-${index}`,
    incident_id: `INC-${index}`,
    action: "unassigned" as const,
    resulting_incident_status: "unassigned" as const
  }));
  apiMocks.assignmentHistory.mockResolvedValueOnce(firstPage)
    .mockResolvedValueOnce([{ ...legacyEvent, mutation_id: "MUT-25", incident_id: "INC-25" }])
    .mockResolvedValueOnce([legacyEvent]);
  render(<AssignmentHistory scenarioId="base" scenarioName="Base Operations" />);

  expect(await screen.findByText("Showing 25 most recent assignment changes.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Load more history" }));
  expect(await screen.findByText("Showing 26 most recent assignment changes.")).toBeTruthy();
  expect(apiMocks.assignmentHistory).toHaveBeenNthCalledWith(2, 25, 25);

  fireEvent.click(screen.getByRole("button", { name: "Refresh history" }));
  await waitFor(() => expect(screen.getByText("Showing 1 most recent assignment change.")).toBeTruthy());
  expect(apiMocks.assignmentHistory).toHaveBeenNthCalledWith(3, 25, 0);
});
