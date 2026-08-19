import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "./utils";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-panel",
  {
    variants: {
      variant: {
        default: "bg-panel-2 text-fg border border-border hover:border-accent",
        primary: "bg-accent/15 text-accent border border-accent/40 hover:bg-accent/25",
        ghost: "text-muted hover:text-fg hover:bg-panel-2",
        danger: "bg-deny/10 text-deny border border-deny/40 hover:bg-deny/20",
      },
      size: {
        sm: "h-7 px-2",
        md: "h-9 px-3",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(button({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = "Button";
