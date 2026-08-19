import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: any) => (
    <a href={typeof href === "string" ? href : "#"} {...p}>
      {children}
    </a>
  ),
}));

import { CatalogBoard } from "@/components/catalog-board";
import type { ChallengeSummary } from "@/lib/types";

const challenges: ChallengeSummary[] = [
  {
    id: "DVAH-001",
    title: "Check Once, Execute Forever",
    difficulty: "easy",
    invariants: ["INV-01"],
    objective: "Cause an unauthorized execution.",
    blurb: "",
  },
];

describe("CatalogBoard", () => {
  it("renders a lab row with its invariant and status", () => {
    render(
      <CatalogBoard challenges={challenges} statuses={{ "DVAH-001": "proven" }} mode="learn" />,
    );
    expect(screen.getByText("DVAH-001")).toBeInTheDocument();
    expect(screen.getByText("Check Once, Execute Forever")).toBeInTheDocument();
    expect(screen.getByText("INV-01")).toBeInTheDocument();
    expect(screen.getByText("proven")).toBeInTheDocument();
  });

  it("defaults unseen labs to not-started", () => {
    render(<CatalogBoard challenges={challenges} statuses={{}} mode="ctf" />);
    expect(screen.getByText("not-started")).toBeInTheDocument();
  });
});
