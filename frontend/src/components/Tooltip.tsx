import React, { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";

interface TooltipProps {
  children: React.ReactNode;
  title?: string;
  text: string;
  position?: "top" | "right" | "bottom" | "left";
  className?: string;
}

interface TooltipCoords {
  top: number;
  left: number;
  transform: string;
}

const getTooltipCoords = (
  rect: DOMRect,
  position: "top" | "right" | "bottom" | "left"
): TooltipCoords => {
  const gap = 14;

  switch (position) {
    case "top":
      return {
        top: rect.top - gap,
        left: rect.left + rect.width / 2,
        transform: "translate(-50%, -100%)",
      };

    case "bottom":
      return {
        top: rect.bottom + gap,
        left: rect.left + rect.width / 2,
        transform: "translate(-50%,0)",
      };

    case "left":
      return {
        top: rect.top + rect.height / 2,
        left: rect.left - gap,
        transform: "translate(-100%,-50%)",
      };

    case "right":
    default:
      return {
        top: rect.top + rect.height / 2,
        left: rect.right + gap,
        transform: "translate(0,-50%)",
      };
  }
};

const Tooltip = ({
  children,
  title,
  text,
  position = "right",
  className = "",
}: TooltipProps) => {
  const wrapperRef = useRef<HTMLDivElement>(null);

  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState<TooltipCoords | null>(null);

  const showTooltip = () => {
    if (!wrapperRef.current) return;

    const rect = wrapperRef.current.getBoundingClientRect();

    setCoords(getTooltipCoords(rect, position));
    setVisible(true);
  };

  const hideTooltip = () => {
    setVisible(false);
  };

  const arrowClasses: Record<
    "top" | "bottom" | "left" | "right",
    string
  > = {
    top: "top-full left-1/2 -translate-x-1/2 border-[8px] border-transparent border-t-[var(--corporate-panel)]",
    bottom:
      "bottom-full left-1/2 -translate-x-1/2 border-[8px] border-transparent border-b-[var(--corporate-panel)]",
    left: "left-full top-1/2 -translate-y-1/2 border-[8px] border-transparent border-l-[var(--corporate-panel)]",
    right:
      "right-full top-1/2 -translate-y-1/2 border-[8px] border-transparent border-r-[var(--corporate-panel)]",
  };

  return (
    <div
      ref={wrapperRef}
      className={`relative flex items-center ${className}`}
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}

      {createPortal(
        <AnimatePresence>
          {visible && coords && (
            <motion.div
              initial={{
                opacity: 0,
                x: position === "right" ? -8 : 0,
                scale: 0.96,
              }}
              animate={{
                opacity: 1,
                x: 0,
                scale: 1,
              }}
              exit={{
                opacity: 0,
                x: position === "right" ? -8 : 0,
                scale: 0.96,
              }}
              transition={{
                duration: 0.18,
              }}
              style={{
                position: "fixed",
                top: coords.top,
                left: coords.left,
                transform: coords.transform,
              }}
              className="
                z-[9999]
                w-80
                overflow-hidden
                rounded-2xl
                border border-[var(--corporate-border-strong)]
                bg-[var(--corporate-panel)]
                backdrop-blur-xl
                shadow-2xl
                pointer-events-none
              "
            >
              {/* Left Accent */}
              <div className="absolute left-0 top-0 h-full w-1 bg-[var(--corporate-accent)]" />

              <div className="px-5 py-4 pl-6">
                {title && (
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-2 w-2 rounded-full bg-[var(--corporate-accent)]" />

                    <h3 className="text-[15px] font-semibold text-[var(--corporate-text)]">
                      {title}
                    </h3>
                  </div>
                )}

                <p className="text-[14px] leading-6 text-[var(--corporate-muted)]">
                  {text}
                </p>
              </div>

              <div className={`absolute ${arrowClasses[position]}`} />
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </div>
  );
};

export default Tooltip;