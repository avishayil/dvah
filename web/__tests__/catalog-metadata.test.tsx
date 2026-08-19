import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CatalogBoard } from "@/components/catalog-board";
import type { ChallengeSummary } from "@/lib/types";

const chal = (over: Partial<ChallengeSummary> = {}): ChallengeSummary => ({
  id: "DVAH-001",
  title: "Check Once",
  difficulty: "easy",
  invariants: ["INV-01"],
  objective: "obj",
  blurb: "b",
  order: 1,
  estimated_minutes: 10,
  teaches: "authorize every action the moment it runs",
  prerequisites: [],
  ...over,
});

describe("CatalogBoard metadata", () => {
  it("shows 'what you'll learn' + difficulty and orders beginner→advanced", () => {
    render(
      <CatalogBoard
        mode="learn"
        statuses={{}}
        challenges={[
          chal({ id: "DVAH-002", order: 2, teaches: "attenuate child capabilities" }),
          chal(),
        ]}
      />,
    );
    expect(screen.getByText(/authorize every action/)).toBeInTheDocument();
    expect(screen.getAllByText("easy").length).toBeGreaterThan(0);
    const ids = screen.getAllByText(/^DVAH-00\d$/).map((e) => e.textContent);
    expect(ids[0]).toBe("DVAH-001"); // order 1 before order 2
  });
});
