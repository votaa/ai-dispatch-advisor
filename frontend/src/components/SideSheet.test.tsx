import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useRef, useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { SideSheet } from "./SideSheet";

afterEach(cleanup);

function SideSheetHarness() {
  const [open, setOpen] = useState(false);
  const openerRef = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button onClick={() => setOpen(true)} ref={openerRef} type="button">Open details</button>
      <SideSheet onClose={() => setOpen(false)} open={open} returnFocusRef={openerRef} title="Details">
        Sheet content
      </SideSheet>
    </>
  );
}

describe("SideSheet", () => {
  it("opens as a non-modal complementary region and restores focus after Escape", async () => {
    render(<SideSheetHarness />);
    const opener = screen.getByRole("button", { name: "Open details" });
    fireEvent.click(opener);

    expect(screen.getByRole("complementary", { name: "Details" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: "Details" })).toBe(document.activeElement);
    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("complementary", { name: "Details" })).toBeNull();
    await waitFor(() => expect(opener).toBe(document.activeElement));
  });
});
