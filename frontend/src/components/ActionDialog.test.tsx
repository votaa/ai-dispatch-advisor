import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { useState } from "react";
import { ActionDialog } from "./ActionDialog";

afterEach(cleanup);

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)} type="button">Open action</button>
      {open ? (
        <ActionDialog id="test-action-title" onCancel={() => setOpen(false)} title="Confirm action">
          <button onClick={() => setOpen(false)} type="button">Cancel</button>
          <button type="button">Continue</button>
        </ActionDialog>
      ) : null}
    </>
  );
}

it("opens inside the app, traps keyboard focus, and restores the trigger on Escape", async () => {
  render(<DialogHarness />);
  const opener = screen.getByRole("button", { name: "Open action" });
  opener.focus();
  fireEvent.click(opener);

  const dialog = screen.getByRole("dialog", { name: "Confirm action" });
  expect(dialog.getAttribute("aria-modal")).toBe("true");
  expect(screen.getByRole("heading", { name: "Confirm action" })).toBe(document.activeElement);
  expect(document.body.style.overflow).toBe("hidden");

  const continueButton = screen.getByRole("button", { name: "Continue" });
  continueButton.focus();
  fireEvent.keyDown(document, { key: "Tab" });
  expect(screen.getByRole("button", { name: "Cancel" })).toBe(document.activeElement);

  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog", { name: "Confirm action" })).toBeNull();
  await waitFor(() => expect(opener).toBe(document.activeElement));
  expect(document.body.style.overflow).toBe("");
});
