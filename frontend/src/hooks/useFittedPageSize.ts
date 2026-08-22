import { useLayoutEffect, useRef, useState } from "react";
import { useViewportMeasurement } from "./useViewportMeasurement";

type FittedPageSizeInput = {
  availableHeight: number;
  columns?: number;
  fallbackPageSize: number;
  gap?: number;
  itemCount: number;
  itemHeight: number;
  itemTop: number;
};

type FittedPageSizeOptions = {
  fallbackPageSize: number;
  itemCount: number;
  itemSelector: string;
  layout: "grid" | "rows";
  measurementKey: string;
};

export function calculateFittedPageSize({
  availableHeight,
  columns = 1,
  fallbackPageSize,
  gap = 0,
  itemCount,
  itemHeight,
  itemTop
}: FittedPageSizeInput) {
  if (availableHeight <= 0 || itemHeight <= 0 || itemCount <= 0) return fallbackPageSize;
  const usableHeight = Math.max(0, availableHeight - itemTop);
  const rows = Math.max(1, Math.floor((usableHeight + gap) / (itemHeight + gap)));
  return Math.max(1, Math.min(itemCount, rows * Math.max(1, columns)));
}

export function useFittedPageSize({
  fallbackPageSize,
  itemCount,
  itemSelector,
  layout,
  measurementKey
}: FittedPageSizeOptions) {
  const { availableHeight, containerRef, height, width } = useViewportMeasurement<HTMLDivElement>();
  const [pageSize, setPageSize] = useState(fallbackPageSize);
  const maximumItemHeightRef = useRef(0);
  const measuredWidthRef = useRef(0);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container || availableHeight <= 0 || itemCount <= 0) return;

    if (Math.abs(measuredWidthRef.current - width) > 1) {
      measuredWidthRef.current = width;
      maximumItemHeightRef.current = 0;
    }

    const items = Array.from(container.querySelectorAll<HTMLElement>(itemSelector));
    if (!items.length) return;

    const containerBounds = container.getBoundingClientRect();
    const itemBounds = items.map((item) => item.getBoundingClientRect());
    maximumItemHeightRef.current = Math.max(
      maximumItemHeightRef.current,
      ...itemBounds.map((bounds) => bounds.height)
    );

    let columns = 1;
    let gap = 0;
    if (layout === "grid") {
      const grid = items[0].parentElement;
      if (grid) {
        const styles = window.getComputedStyle(grid);
        const tracks = styles.gridTemplateColumns.split(/\s+/).filter(Boolean);
        columns = Math.max(1, tracks.length);
        gap = Number.parseFloat(styles.rowGap) || 0;
      }
    }

    const nextPageSize = calculateFittedPageSize({
      availableHeight,
      columns,
      fallbackPageSize,
      gap,
      itemCount,
      itemHeight: maximumItemHeightRef.current,
      itemTop: Math.max(0, itemBounds[0].top - containerBounds.top)
    });
    setPageSize((current) => current === nextPageSize ? current : nextPageSize);
  }, [availableHeight, containerRef, fallbackPageSize, height, itemCount, itemSelector, layout, measurementKey, pageSize, width]);

  return { containerRef, pageSize };
}
