import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ResizableSidebar,
  SIDEBAR_MAX_WIDTH,
  SIDEBAR_MIN_WIDTH
} from "./ResizableSidebar";

class MockPointerEvent extends MouseEvent {
  pointerId: number;

  constructor(type: string, properties: PointerEventInit = {}) {
    super(type, properties);
    this.pointerId = properties.pointerId ?? 0;
  }
}

beforeEach(() => vi.stubGlobal("PointerEvent", MockPointerEvent));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ResizableSidebar", () => {
  it("exposes bounded keyboard resizing", () => {
    const onWidthChange = vi.fn();
    render(<ResizableSidebar onWidthChange={onWidthChange} width={220}>Navigation</ResizableSidebar>);

    const separator = screen.getByRole("separator", { name: "Resize primary navigation" });
    expect(separator.getAttribute("aria-valuenow")).toBe("220");
    fireEvent.keyDown(separator, { key: "ArrowRight" });
    expect(onWidthChange).toHaveBeenLastCalledWith(230);
    fireEvent.keyDown(separator, { key: "Home" });
    expect(onWidthChange).toHaveBeenLastCalledWith(SIDEBAR_MIN_WIDTH);
    fireEvent.keyDown(separator, { key: "End" });
    expect(onWidthChange).toHaveBeenLastCalledWith(SIDEBAR_MAX_WIDTH);
  });

  it("supports pointer movement and clamps the result", () => {
    const onWidthChange = vi.fn();
    render(<ResizableSidebar onWidthChange={onWidthChange} width={220}>Navigation</ResizableSidebar>);

    const separator = screen.getByRole("separator", { name: "Resize primary navigation" });
    fireEvent.pointerDown(separator, { button: 0, clientX: 220, pointerId: 1 });
    fireEvent.pointerMove(separator, { clientX: 500, pointerId: 1 });
    expect(onWidthChange).toHaveBeenLastCalledWith(SIDEBAR_MAX_WIDTH);
    fireEvent.pointerUp(separator, { pointerId: 1 });
  });
});
