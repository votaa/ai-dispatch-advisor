import type { KeyboardEvent, PointerEvent, ReactNode } from "react";
import { useRef } from "react";

export const SIDEBAR_DEFAULT_WIDTH = 220;
export const SIDEBAR_MIN_WIDTH = 200;
export const SIDEBAR_MAX_WIDTH = 360;

type ResizableSidebarProps = {
  children: ReactNode;
  onWidthChange: (width: number) => void;
  width: number;
};

function clampWidth(width: number) {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, Math.round(width)));
}

export function ResizableSidebar({ children, onWidthChange, width }: ResizableSidebarProps) {
  const dragState = useRef<{ pointerId: number; startWidth: number; startX: number } | null>(null);

  const finishResize = (event: PointerEvent<HTMLDivElement>) => {
    if (dragState.current?.pointerId !== event.pointerId) return;
    dragState.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const increment = event.shiftKey ? 25 : 10;
    let nextWidth: number | undefined;

    if (event.key === "ArrowLeft") nextWidth = width - increment;
    if (event.key === "ArrowRight") nextWidth = width + increment;
    if (event.key === "Home") nextWidth = SIDEBAR_MIN_WIDTH;
    if (event.key === "End") nextWidth = SIDEBAR_MAX_WIDTH;
    if (nextWidth === undefined) return;

    event.preventDefault();
    onWidthChange(clampWidth(nextWidth));
  };

  return (
    <aside className="sidebar">
      {children}
      <div
        aria-label="Resize primary navigation"
        aria-orientation="vertical"
        aria-valuemax={SIDEBAR_MAX_WIDTH}
        aria-valuemin={SIDEBAR_MIN_WIDTH}
        aria-valuenow={width}
        className="sidebar-resize-handle"
        onKeyDown={handleKeyDown}
        onPointerCancel={finishResize}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          dragState.current = { pointerId: event.pointerId, startWidth: width, startX: event.clientX };
          event.currentTarget.setPointerCapture?.(event.pointerId);
          event.preventDefault();
        }}
        onPointerMove={(event) => {
          const drag = dragState.current;
          if (!drag || drag.pointerId !== event.pointerId) return;
          onWidthChange(clampWidth(drag.startWidth + event.clientX - drag.startX));
        }}
        onPointerUp={finishResize}
        role="separator"
        tabIndex={0}
      />
    </aside>
  );
}
