import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AlertTriangle } from "lucide-react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ExpandableWorkspace } from "./ExpandableWorkspace";

function WorkspaceHarness() {
  const [expanded, setExpanded] = useState(false);
  const [value, setValue] = useState("");

  return (
    <ExpandableWorkspace
      expanded={expanded}
      icon={AlertTriangle}
      id="test-workspace"
      onExpand={() => setExpanded(true)}
      onRestore={() => setExpanded(false)}
      title="Priority Incidents"
    >
      <label>
        Search
        <input aria-label="Workspace search" onChange={(event) => setValue(event.target.value)} value={value} />
      </label>
    </ExpandableWorkspace>
  );
}

describe("ExpandableWorkspace", () => {
  afterEach(() => {
    cleanup();
    document.body.style.overflow = "";
  });

  it("expands, preserves child state, restores with Escape, and returns focus", async () => {
    render(<WorkspaceHarness />);

    const expand = screen.getByRole("button", { name: "Expand Priority Incidents workspace" });
    const search = screen.getByLabelText("Workspace search") as HTMLInputElement;
    fireEvent.change(search, { target: { value: "INC-2002" } });
    fireEvent.click(expand);

    expect(screen.getByTestId("expandable-workspace-test-workspace").classList.contains("is-expanded")).toBe(true);
    expect(screen.getByRole("button", { name: "Restore Priority Incidents workspace" }).getAttribute("aria-expanded")).toBe("true");
    expect(search.value).toBe("INC-2002");
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.getByTestId("expandable-workspace-test-workspace").classList.contains("is-expanded")).toBe(false);
    expect(search.value).toBe("INC-2002");
    expect(document.body.style.overflow).toBe("");
    await waitFor(() => expect(expand).toBe(document.activeElement));
  });

  it("restores from the visible control and announces the state", async () => {
    render(<WorkspaceHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Expand Priority Incidents workspace" }));
    fireEvent.click(screen.getByRole("button", { name: "Restore Priority Incidents workspace" }));

    expect(await screen.findByText("Priority Incidents workspace restored.")).toBeTruthy();
  });
});
