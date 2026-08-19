import * as React from "react";
import { cn } from "./utils";

export function Badge({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border border-border px-1.5 py-0.5 text-xs mono",
        className,
      )}
      {...props}
    />
  );
}
