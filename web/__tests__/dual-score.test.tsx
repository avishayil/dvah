import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { DualScorePanel } from "@/components/dual-score";
import type { DualScore } from "@/lib/types";

const base: DualScore = {
  runtime_security: { secure: true, unauthorized: [], basis: "complete-mediation (INV-01)" },
  live_agent_exercise: {
    attempted: false,
    blocked: false,
    recovered: false,
    avoided: true,
    proposed_ops: [],
    summary: "model did not exercise the dangerous path",
  },
};

describe("DualScorePanel", () => {
  it("renders a secure runtime verdict", () => {
    render(<DualScorePanel score={base} />);
    expect(screen.getByTestId("runtime-security").getAttribute("data-secure")).toBe("true");
    expect(screen.getByText(/Harness held/i)).toBeTruthy();
    // secure + avoided → no contradiction warning.
    expect(screen.queryByTestId("avoided-warning")).toBeNull();
  });

  it("teaches that avoiding the bait is NOT the same as a secure architecture", () => {
    const score: DualScore = {
      runtime_security: { secure: false, unauthorized: ["sha256:bad"], basis: "b" },
      live_agent_exercise: { ...base.live_agent_exercise }, // avoided
    };
    render(<DualScorePanel score={score} />);
    expect(screen.getByTestId("runtime-security").getAttribute("data-secure")).toBe("false");
    expect(screen.getByTestId("avoided-warning").textContent).toMatch(
      /does not mean the architecture\s+is secure/i,
    );
  });

  it("shows attempted + blocked badges when the model took the bait", () => {
    const score: DualScore = {
      runtime_security: { secure: true, unauthorized: [], basis: "b" },
      live_agent_exercise: {
        attempted: true,
        blocked: true,
        recovered: false,
        avoided: false,
        proposed_ops: ["files.delete"],
        summary: "model attempted a dangerous action; harness blocked it",
      },
    };
    render(<DualScorePanel score={score} />);
    expect(screen.getByText("attempted")).toBeTruthy();
    expect(screen.getByText("blocked")).toBeTruthy();
    expect(screen.queryByTestId("avoided-warning")).toBeNull();
  });
});
