import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Term } from "@/components/term";

describe("Term", () => {
  it("renders a definition trigger with an accessible plain-language label", () => {
    render(<Term id="invariant">invariant</Term>);
    const btn = screen.getByRole("button", { name: /invariant/i });
    expect(btn.getAttribute("aria-label")).toMatch(/safety rule/i);
  });

  it("falls back to plain text for an unknown term", () => {
    render(<Term id="does-not-exist">widget</Term>);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("widget")).toBeInTheDocument();
  });
});
