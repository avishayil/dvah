import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TraceGraph } from "@/components/trace-graph";
import type { TraceResult } from "@/lib/types";

const withViolation: TraceResult = {
  events: [
    { kind: "policy.decision", task_id: "t", action_hash: "sha256:aaa", detail: { verdict: "allow" } },
    { kind: "executed", task_id: "t", action_hash: "sha256:aaa", detail: { namespace: "files", action: "read" } },
    { kind: "executed", task_id: "t", action_hash: "sha256:bbb", detail: { namespace: "files", action: "delete", resource: "/prod/customer.db" } },
  ],
  summary: {
    total_events: 3,
    executed: 2,
    denials: [],
    unauthorized_executions: ["sha256:bbb"],
    delegations: [],
    untrusted_instruction: false,
  },
};

const clean: TraceResult = {
  events: [{ kind: "executed", task_id: "t", action_hash: "sha256:aaa", detail: {} }],
  summary: {
    total_events: 1,
    executed: 1,
    denials: [],
    unauthorized_executions: [],
    delegations: [],
    untrusted_instruction: false,
  },
};

describe("TraceGraph", () => {
  it("highlights an unauthorized execution as an INV-01 violation", () => {
    const { container } = render(<TraceGraph trace={withViolation} />);
    expect(screen.getAllByText(/INV-01/).length).toBeGreaterThan(0);
    expect(container.querySelector('[data-violation="true"]')).not.toBeNull();
  });

  it("reports a clean trace with no violations", () => {
    render(<TraceGraph trace={clean} />);
    expect(screen.getByText(/no invariant violations observed/)).toBeInTheDocument();
  });
});
