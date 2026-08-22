import { describe, expect, it, vi } from "vitest";
import { measureViewportSpace } from "./useViewportMeasurement";

describe("measureViewportSpace", () => {
  it("reports container dimensions and remaining viewport height", () => {
    vi.stubGlobal("innerHeight", 800);
    const element = document.createElement("div");
    element.getBoundingClientRect = () => ({
      bottom: 500,
      height: 400,
      left: 0,
      right: 640,
      top: 100,
      width: 640,
      x: 0,
      y: 100,
      toJSON: () => ({})
    });

    expect(measureViewportSpace(element, 20)).toEqual({
      availableHeight: 680,
      height: 400,
      width: 640
    });
    vi.unstubAllGlobals();
  });
});
