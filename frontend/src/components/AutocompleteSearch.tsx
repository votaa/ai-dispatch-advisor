import { useId, useMemo, useState } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";

export type AutocompleteSuggestion = {
  count: number;
  group: string;
  value: string;
};

export type AutocompleteField<T> = {
  group: string;
  values: (item: T) => string | string[];
};

const DEFAULT_MAX_PER_GROUP = 8;

export function buildAutocompleteSuggestions<T>(
  items: T[],
  fields: AutocompleteField<T>[],
  query: string,
  maxPerGroup = DEFAULT_MAX_PER_GROUP
): AutocompleteSuggestion[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return [];

  return fields.flatMap((field) => {
    const counts = new Map<string, { count: number; value: string }>();

    items.forEach((item) => {
      const rawValues = field.values(item);
      const uniqueValues = new Map<string, string>();
      (Array.isArray(rawValues) ? rawValues : [rawValues]).forEach((rawValue) => {
        const value = rawValue.trim();
        if (value) uniqueValues.set(value.toLowerCase(), value);
      });
      uniqueValues.forEach((value, normalizedValue) => {
        const existing = counts.get(normalizedValue);
        counts.set(normalizedValue, { count: (existing?.count ?? 0) + 1, value: existing?.value ?? value });
      });
    });

    return Array.from(counts.values())
      .filter(({ value }) => value.toLowerCase().includes(normalizedQuery))
      .sort((left, right) => (
        right.count - left.count ||
        left.value.localeCompare(right.value, "en", { numeric: true, sensitivity: "base" })
      ))
      .slice(0, maxPerGroup)
      .map(({ count, value }) => ({ count, group: field.group, value }));
  });
}

type AutocompleteSearchProps = {
  accessibleLabel?: string;
  label: string;
  onChange: (value: string) => void;
  placeholder: string;
  suggestions: AutocompleteSuggestion[];
  value: string;
};

export function AutocompleteSearch({
  accessibleLabel,
  label,
  onChange,
  placeholder,
  suggestions,
  value
}: AutocompleteSearchProps) {
  const generatedId = useId().replace(/:/g, "");
  const inputId = `autocomplete-${generatedId}`;
  const listboxId = `${inputId}-listbox`;
  const hintId = `${inputId}-hint`;
  const [openRequested, setOpenRequested] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const isOpen = openRequested && value.trim().length > 0 && suggestions.length > 0;
  const selectedIndex = activeIndex >= 0 && suggestions.length > 0
    ? Math.min(activeIndex, suggestions.length - 1)
    : -1;
  const groupedSuggestions = useMemo(() => {
    const groups = new Map<string, Array<AutocompleteSuggestion & { index: number }>>();
    suggestions.forEach((suggestion, index) => {
      const group = groups.get(suggestion.group) ?? [];
      group.push({ ...suggestion, index });
      groups.set(suggestion.group, group);
    });
    return Array.from(groups.entries());
  }, [suggestions]);

  const chooseSuggestion = (suggestion: AutocompleteSuggestion) => {
    onChange(suggestion.value);
    setOpenRequested(false);
    setActiveIndex(-1);
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
    setOpenRequested(Boolean(event.target.value.trim()));
    setActiveIndex(0);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      if (isOpen) event.preventDefault();
      setOpenRequested(false);
      setActiveIndex(-1);
      return;
    }
    if (event.key === "Tab") {
      setOpenRequested(false);
      return;
    }
    if (suggestions.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpenRequested(true);
      setActiveIndex((current) => current < 0 ? 0 : (current + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setOpenRequested(true);
      setActiveIndex((current) => current <= 0 ? suggestions.length - 1 : current - 1);
    } else if (event.key === "Enter" && isOpen && selectedIndex >= 0) {
      event.preventDefault();
      chooseSuggestion(suggestions[selectedIndex]);
    }
  };

  return (
    <div
      className="autocomplete-field"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setOpenRequested(false);
          setActiveIndex(-1);
        }
      }}
    >
      <label htmlFor={inputId}>{label}</label>
      <div className="autocomplete-control">
        <input
          aria-label={accessibleLabel}
          aria-activedescendant={isOpen && selectedIndex >= 0 ? `${listboxId}-option-${selectedIndex}` : undefined}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-describedby={hintId}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          autoComplete="off"
          id={inputId}
          onChange={handleChange}
          onFocus={() => setOpenRequested(Boolean(value.trim()))}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          role="combobox"
          type="search"
          value={value}
        />
        <span className="sr-only" id={hintId}>Type to see grouped matches. Use the arrow keys to navigate suggestions, Enter to select, and Escape to dismiss.</span>
        <span aria-live="polite" className="sr-only">{isOpen ? `${suggestions.length} suggestions available.` : ""}</span>
        {isOpen ? (
          <div className="autocomplete-listbox" id={listboxId} role="listbox">
            {groupedSuggestions.map(([group, groupSuggestions], groupIndex) => {
              const groupId = `${listboxId}-group-${groupIndex}`;
              return (
                <div aria-labelledby={groupId} className="autocomplete-group" key={group} role="group">
                  <div className="autocomplete-group-label" id={groupId}>{group}</div>
                  {groupSuggestions.map((suggestion) => (
                    <div
                      aria-label={`${suggestion.value}, ${suggestion.group}, ${suggestion.count} ${suggestion.count === 1 ? "match" : "matches"}`}
                      aria-selected={selectedIndex === suggestion.index}
                      className={selectedIndex === suggestion.index ? "autocomplete-option is-active" : "autocomplete-option"}
                      id={`${listboxId}-option-${suggestion.index}`}
                      key={`${suggestion.group}-${suggestion.value}`}
                      onPointerDown={(event) => event.preventDefault()}
                      onClick={() => chooseSuggestion(suggestion)}
                      role="option"
                    >
                      <span>{suggestion.value}</span>
                      <span className="autocomplete-count">({suggestion.count})</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}
