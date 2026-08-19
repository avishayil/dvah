import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AgentTimeline, laneFor } from "@/components/agent-timeline";
import type { TraceResult } from "@/lib/types";

describe("laneFor", () => {
  it("maps each event kind to its agent-loop lane", () => {
    expect(laneFor("user.task")).toBe("Model");
    expect(laneFor("model.response")).toBe("Model");
    expect(laneFor("tool.proposed")).toBe("Model");
    expect(laneFor("skill.loaded")).toBe("Skill");
    expect(laneFor("boundary.trust_downgraded")).toBe("MCP");
    expect(laneFor("policy.decision")).toBe("Policy");
    expect(laneFor("denied")).toBe("Policy");
    expect(laneFor("approval.used")).toBe("Approval");
    expect(laneFor("executed")).toBe("Tool");
    expect(laneFor("observation.received")).toBe("Tool");
  });

  it("defaults unknown kinds to the Model lane", () => {
    expect(laneFor("something.new")).toBe("Model");
  });
});

const trace: TraceResult = {
  events: [
    { kind: "user.task", task_id: "t", action_hash: null, detail: { task: "do it" } },
    { kind: "tool.proposed", task_id: "t", action_hash: null, detail: { namespace: "files", action: "delete" } },
    { kind: "policy.decision", task_id: "t", action_hash: "sha256:a", detail: { verdict: "allow" } },
    { kind: "executed", task_id: "t", action_hash: "sha256:a", detail: { namespace: "files", action: "delete" } },
  ],
  summary: {
    total_events: 4,
    executed: 1,
    denials: [],
    unauthorized_executions: [],
    delegations: [],
    untrusted_instruction: false,
  },
};

describe("AgentTimeline", () => {
  it("renders each event tagged with its lane", () => {
    render(<AgentTimeline trace={trace} />);
    const rows = screen.getByTestId("agent-timeline").querySelectorAll("li[data-lane]");
    expect(rows.length).toBe(4);
    const lanes = Array.from(rows).map((r) => r.getAttribute("data-lane"));
    expect(lanes).toEqual(["Model", "Model", "Policy", "Tool"]);
  });
});
