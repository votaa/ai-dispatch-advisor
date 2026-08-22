import { describe, expect, it } from "vitest";
import { calculateFittedPageSize } from "./useFittedPageSize";

describe("calculateFittedPageSize", () => {
  it("fits complete grid rows within the available height", () => {
    expect(calculateFittedPageSize({
      availableHeight: 600,
      columns: 3,
      fallbackPageSize: 24,
      gap: 12,
      itemCount: 30,
      itemHeight: 140,
      itemTop: 120
    })).toBe(9);
  });

  it("fits table rows and retains a safe fallback before measurement", () => {
    expect(calculateFittedPageSize({
      availableHeight: 520,
      fallbackPageSize: 50,
      itemCount: 80,
      itemHeight: 52,
      itemTop: 156
    })).toBe(7);
    expect(calculateFittedPageSize({
      availableHeight: 0,
      fallbackPageSize: 50,
      itemCount: 80,
      itemHeight: 0,
      itemTop: 0
    })).toBe(50);
  });
});
