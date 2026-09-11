import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AutocompleteSearch, buildAutocompleteSuggestions } from "./AutocompleteSearch";

describe("AutocompleteSearch", () => {
  afterEach(cleanup);

  it("counts unique records and sorts matches by count then label within each group", () => {
    const records = [
      { feeder: "FDR-ES-13", municipality: "East Meadow" },
      { feeder: "FDR-ES-13", municipality: "East Hampton" },
      { feeder: "FDR-ES-03", municipality: "East Meadow" }
    ];

    expect(buildAutocompleteSuggestions(records, [
      { group: "Feeder", values: (record) => record.feeder },
      { group: "Municipality", values: (record) => record.municipality }
    ], "e")).toEqual([
      { count: 2, group: "Feeder", value: "FDR-ES-13" },
      { count: 1, group: "Feeder", value: "FDR-ES-03" },
      { count: 2, group: "Municipality", value: "East Meadow" },
      { count: 1, group: "Municipality", value: "East Hampton" }
    ]);
  });

  it("supports grouped screen-reader semantics, keyboard selection, and dismissal", () => {
    const onChange = vi.fn();
    const suggestions = [
      { count: 2, group: "Feeder", value: "FDR-ES-13" },
      { count: 1, group: "Feeder", value: "FDR-ES-03" },
      { count: 1, group: "Municipality", value: "East Meadow" }
    ];
    const { rerender } = render(
      <AutocompleteSearch
        accessibleLabel="Active incidents search"
        label="Search"
        onChange={onChange}
        placeholder="ID, municipality, feeder, or hazard"
        suggestions={suggestions}
        value="FDR"
      />
    );

    const input = screen.getByRole("combobox", { name: "Active incidents search" });
    fireEvent.focus(input);
    expect(input.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("group", { name: "Feeder" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "FDR-ES-13, Feeder, 2 matches" })).toBeTruthy();

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenLastCalledWith("FDR-ES-03");
    expect(input.getAttribute("aria-expanded")).toBe("false");

    rerender(
      <AutocompleteSearch
        accessibleLabel="Active incidents search"
        label="Search"
        onChange={onChange}
        placeholder="ID, municipality, feeder, or hazard"
        suggestions={suggestions}
        value="FDR"
      />
    );
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: "Escape" });
    expect(input.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("listbox")).toBeNull();
  });
});
