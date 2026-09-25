import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

type ActionDialogProps = {
  children: ReactNode;
  closeDisabled?: boolean;
  id: string;
  onCancel: () => void;
  title: string;
};

export function ActionDialog({ children, closeDisabled = false, id, onCancel, title }: ActionDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const onCancelRef = useRef(onCancel);
  const closeDisabledRef = useRef(closeDisabled);
  onCancelRef.current = onCancel;
  closeDisabledRef.current = closeDisabled;

  useEffect(() => {
    const priorFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const priorOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    titleRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (closeDisabledRef.current) return;
        event.preventDefault();
        onCancelRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
        "button:not([disabled]), select:not([disabled]), textarea:not([disabled]), input:not([disabled])"
      ) ?? []);
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === titleRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = priorOverflow;
      if (priorFocus?.isConnected) priorFocus.focus();
    };
  }, []);

  return (
    <div className="assignment-action-overlay" role="presentation">
      <section aria-labelledby={id} aria-modal="true" className="assignment-action-dialog" ref={dialogRef} role="dialog">
        <h2 id={id} ref={titleRef} tabIndex={-1}>{title}</h2>
        {children}
      </section>
    </div>
  );
}
