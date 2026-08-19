import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { InvariantBoard } from "@/components/invariant-board";

describe("InvariantBoard", () => {
  it("renders hold/broken/pending with data-state and accessible state text", () => {
    const { container } = render(
      <InvariantBoard
        cells={[
          { id: "INV-01", holds: true },
          { id: "INV-02", holds: false },
          { id: "INV-03", holds: null },
        ]}
      />,
    );
    const chips = Array.from(container.querySelectorAll("[data-state]"));
    expect(chips).toHaveLength(3);
    const byState = (s: string) => chips.find((c) => c.getAttribute("data-state") === s)!;

    expect(byState("hold").textContent).toContain("INV-01");
    expect(byState("hold").textContent).toContain("holds"); // sr-only state text
    expect(byState("broken").textContent).toContain("broken");
    expect(byState("pending").textContent).toContain("not yet evaluated");
  });

  it("is an accessible, live status list", () => {
    render(<InvariantBoard cells={[{ id: "INV-01", holds: true }]} />);
    const list = screen.getByRole("list", { name: /invariants/i });
    expect(list).toHaveAttribute("aria-live", "polite");
  });
});
