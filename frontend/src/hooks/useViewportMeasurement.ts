import { useCallback, useLayoutEffect, useRef, useState } from "react";

export type ViewportMeasurement = {
  availableHeight: number;
  height: number;
  width: number;
};

type ViewportMeasurementOptions = {
  bottomPadding?: number;
};

const EMPTY_MEASUREMENT: ViewportMeasurement = { availableHeight: 0, height: 0, width: 0 };

export function measureViewportSpace(element: HTMLElement, bottomPadding = 24): ViewportMeasurement {
  const bounds = element.getBoundingClientRect();
  return {
    availableHeight: Math.max(0, Math.floor(window.innerHeight - bounds.top - bottomPadding)),
    height: Math.max(0, Math.floor(bounds.height)),
    width: Math.max(0, Math.floor(bounds.width))
  };
}

export function useViewportMeasurement<T extends HTMLElement>({ bottomPadding = 24 }: ViewportMeasurementOptions = {}) {
  const containerRef = useRef<T>(null);
  const [measurement, setMeasurement] = useState<ViewportMeasurement>(EMPTY_MEASUREMENT);

  const updateMeasurement = useCallback(() => {
    if (!containerRef.current) return;
    const next = measureViewportSpace(containerRef.current, bottomPadding);
    setMeasurement((current) => (
      current.availableHeight === next.availableHeight && current.height === next.height && current.width === next.width
        ? current
        : next
    ));
  }, [bottomPadding]);

  useLayoutEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    updateMeasurement();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(updateMeasurement);
    observer?.observe(element);
    window.addEventListener("resize", updateMeasurement, { passive: true });

    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", updateMeasurement);
    };
  }, [updateMeasurement]);

  return { containerRef, ...measurement };
}
