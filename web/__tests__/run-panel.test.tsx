import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RunPanel } from "@/components/run-panel";
import type { RunResult } from "@/lib/types";

const result: RunResult = {
  tests: [
    { name: "test_can_read", marker: "functional", outcome: "passed" },
    { name: "test_toctou_blocked", marker: "exploit", outcome: "failed" },
  ],
  invariants: { holding: 0, total: 1, per: [{ id: "INV-01", holds: false }] },
  stdout: "",
  exit_code: 1,
};

describe("RunPanel", () => {
  it("renders per-test outcomes", () => {
    render(<RunPanel onRun={() => {}} running={false} result={result} logLines={[]} />);
    expect(screen.getByText("test_can_read")).toBeInTheDocument();
    expect(screen.getByText("test_toctou_blocked")).toBeInTheDocument();
  });

  it("invokes onRun with the chosen marker", () => {
    const onRun = vi.fn();
    render(<RunPanel onRun={onRun} running={false} result={null} logLines={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /exploit/i }));
    expect(onRun).toHaveBeenCalledWith(["exploit"]);
  });

  it("disables run buttons while running", () => {
    render(<RunPanel onRun={() => {}} running={true} result={null} logLines={[]} />);
    expect(screen.getByRole("button", { name: /functional/i })).toBeDisabled();
  });
});
