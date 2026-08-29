import { useEffect, useRef } from "react";
import {
  animate,
  useMotionValue,
  useMotionValueEvent,
  useReducedMotion,
} from "framer-motion";

export interface AnimatedNumberProps {
  value: number;
  className?: string;
}

/** Counts up from its previous value to the new one. Writes textContent
 * directly on each animation frame instead of a React re-render per frame —
 * the standard framer-motion pattern for a value that changes ~60x/second. */
export function AnimatedNumber({ value, className }: AnimatedNumberProps) {
  const motionValue = useMotionValue(0);
  const reduceMotion = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (reduceMotion) {
      motionValue.jump(value);
      return;
    }
    const controls = animate(motionValue, value, {
      duration: 1,
      ease: "easeOut",
    });
    return () => controls.stop();
  }, [value, reduceMotion, motionValue]);

  useMotionValueEvent(motionValue, "change", (latest) => {
    if (ref.current)
      ref.current.textContent = Math.round(latest).toLocaleString();
  });

  return (
    <span ref={ref} className={className}>
      0
    </span>
  );
}
