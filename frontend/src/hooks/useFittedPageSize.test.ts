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

  it("uses the complete expanded workspace for dense rows and crew cards", () => {
    expect(calculateFittedPageSize({
      availableHeight: 719,
      fallbackPageSize: 50,
      itemCount: 500,
      itemHeight: 99,
      itemTop: 183.5
    })).toBe(5);
    expect(calculateFittedPageSize({
      availableHeight: 719,
      columns: 4,
      fallbackPageSize: 24,
      gap: 10,
      itemCount: 500,
      itemHeight: 174,
      itemTop: 174
    })).toBe(12);
  });
});
