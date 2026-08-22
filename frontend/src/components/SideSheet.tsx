import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { ReactNode, RefObject } from "react";

type SideSheetProps = {
  ariaLabel?: string;
  children: ReactNode;
  onClose: () => void;
  open: boolean;
  returnFocusRef?: RefObject<HTMLElement | null>;
  title: string;
};

export function SideSheet({ ariaLabel, children, onClose, open, returnFocusRef, title }: SideSheetProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    headingRef.current?.focus();

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onCloseRef.current();
      window.setTimeout(() => returnFocusRef?.current?.focus(), 0);
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, returnFocusRef]);

  if (!open) return null;

  const closeAndRestoreFocus = () => {
    onCloseRef.current();
    window.setTimeout(() => returnFocusRef?.current?.focus(), 0);
  };

  return (
    <aside aria-label={ariaLabel ?? title} className="side-sheet">
      <div className="side-sheet-heading">
        <h2 ref={headingRef} tabIndex={-1}>{title}</h2>
        <button aria-label={`Close ${title}`} className="side-sheet-close" onClick={closeAndRestoreFocus} type="button">
          <X aria-hidden="true" size={20} />
        </button>
      </div>
      <div className="side-sheet-content">{children}</div>
    </aside>
  );
}
