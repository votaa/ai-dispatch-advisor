import { Maximize2, Minimize2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ElementType, ReactNode } from "react";

type ExpandableWorkspaceProps = {
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  expanded: boolean;
  icon: ElementType;
  id: string;
  onExpand: () => void;
  onRestore: () => void;
  title: string;
};

export function ExpandableWorkspace({
  action,
  children,
  className,
  expanded,
  icon: Icon,
  id,
  onExpand,
  onRestore,
  title
}: ExpandableWorkspaceProps) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const wasExpandedRef = useRef(false);
  const [hasToggled, setHasToggled] = useState(false);
  const onRestoreRef = useRef(onRestore);

  useEffect(() => {
    onRestoreRef.current = onRestore;
  }, [onRestore]);

  useEffect(() => {
    if (!expanded) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (event.key !== "Escape" || event.defaultPrevented || target?.closest(".side-sheet")) return;
      event.preventDefault();
      onRestoreRef.current();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [expanded]);

  useEffect(() => {
    if (wasExpandedRef.current && !expanded) {
      window.setTimeout(() => triggerRef.current?.focus(), 0);
    }
    wasExpandedRef.current = expanded;
  }, [expanded]);

  const toggleWorkspace = () => {
    setHasToggled(true);
    if (expanded) {
      onRestore();
    } else {
      onExpand();
    }
  };

  const panelClassName = ["panel", className].filter(Boolean).join(" ");
  const wrapperClassName = ["expandable-workspace", className, expanded ? "is-expanded" : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      aria-label={`${title} workspace`}
      className={wrapperClassName}
      data-testid={`expandable-workspace-${id}`}
      id={id}
      role="region"
    >
      <section className={panelClassName}>
        <div className="panel-title">
          <Icon aria-hidden="true" size={18} />
          <h2>{title}</h2>
          <div className="workspace-header-actions">
            {action}
            <button
              aria-controls={id}
              aria-expanded={expanded}
              aria-label={`${expanded ? "Restore" : "Expand"} ${title} workspace`}
              className="workspace-toggle"
              onClick={toggleWorkspace}
              ref={triggerRef}
              type="button"
            >
              {expanded ? <Minimize2 aria-hidden="true" size={17} /> : <Maximize2 aria-hidden="true" size={17} />}
              <span>{expanded ? "Restore" : "Expand"}</span>
            </button>
          </div>
        </div>
        {children}
      </section>
      <span aria-live="polite" className="sr-only">
        {hasToggled ? `${title} workspace ${expanded ? "expanded" : "restored"}.` : ""}
      </span>
    </div>
  );
}
