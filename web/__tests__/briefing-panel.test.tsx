import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BriefingPanel } from "@/components/briefing-panel";
import type { Artifacts, ChallengeDetail } from "@/lib/types";

const EMPTY_ARTIFACTS: Artifacts = {
  skills: [],
  agents: [],
  tools: [],
  resources: [],
  workflows: [],
  prompts: [],
};

const detail = (over: Partial<ChallengeDetail> = {}): ChallengeDetail => ({
  id: "DVAH-008",
  title: "Skill Permissions",
  difficulty: "medium",
  invariants: [{ id: "INV-07", statement: "granted = requested ∩ approved" }],
  objective_exploit: "A skill escalates its permissions.",
  objective_fix: "Grant only the intersection.",
  readme_markdown: "",
  environment: { users: {}, agents: {}, resources_summary: {} },
  editable_files: [{ path: "vulnerable/loader.py", contents: "x", writable: true, group: "patch" }],
  references: [],
  artifacts: EMPTY_ARTIFACTS,
  tasks: [],
  overridden_slots: ["skill_loader"],
  components: [],
  order: 8,
  estimated_minutes: 20,
  teaches: "skill permissions",
  prerequisites: [],
  ...over,
});

describe("BriefingPanel — artifacts section", () => {
  it("renders skills, agents, and tools when a skill is declared", () => {
    render(
      <BriefingPanel
        mode="learn"
        detail={detail({
          artifacts: {
            skills: [
              {
                role: "investigator",
                name: "github-investigator",
                version: "1.2.0",
                description: "looks at issues",
                requested_permissions: ["github.issue.read"],
                tools: ["github"],
              },
            ],
            agents: [
              { agent_id: "skill-runner", description: "d", model: "m", tools: ["github"], skills: ["investigator"] },
            ],
            tools: [
              {
                id: "github.issue.read",
                name: "read issue",
                description: "read an issue",
                side_effect: "read",
                requires_approval: false,
              },
            ],
            resources: [],
            workflows: [],
            prompts: [],
          },
        })}
      />,
    );
    const section = screen.getByTestId("artifacts-section");
    expect(section).toHaveTextContent("github-investigator@1.2.0");
    expect(section).toHaveTextContent("github.issue.read");
    expect(section).toHaveTextContent("skill-runner");
  });

  it("hides the section when no structured artifacts are declared (tools-only lab)", () => {
    render(
      <BriefingPanel
        mode="learn"
        detail={detail({
          artifacts: {
            skills: [],
            agents: [],
            tools: [
              {
                id: "files.delete",
                name: "delete",
                description: "delete a file",
                side_effect: "destructive",
                requires_approval: true,
              },
            ],
            resources: [],
            workflows: [],
            prompts: [],
          },
        })}
      />,
    );
    expect(screen.queryByTestId("artifacts-section")).toBeNull();
  });

  it("renders resources, workflows, prompt layers, and tool side-effects/approval", () => {
    render(
      <BriefingPanel
        mode="learn"
        detail={detail({
          artifacts: {
            skills: [],
            agents: [
              { agent_id: "triage", description: "d", model: "m", tools: ["github"], skills: [] },
            ],
            tools: [
              {
                id: "github.repository.delete",
                name: "delete repo",
                description: "delete a repository",
                side_effect: "destructive",
                requires_approval: true,
              },
            ],
            resources: [{ id: "issue-42", name: "Issue 42", trust: "untrusted", mime_type: "text/markdown" }],
            workflows: [{ id: "triage-flow", driver: "code", steps: 3 }],
            prompts: [{ agent_id: "triage", layers: ["system", "agent", "task"] }],
          },
        })}
      />,
    );
    const section = screen.getByTestId("artifacts-section");
    // Resources: id + trust badge.
    expect(screen.getByTestId("artifacts-resources")).toHaveTextContent("issue-42");
    expect(screen.getByTestId("artifacts-resources")).toHaveTextContent("trust: untrusted");
    // Workflows: id + driver + step count.
    expect(screen.getByTestId("artifacts-workflows")).toHaveTextContent("triage-flow");
    expect(screen.getByTestId("artifacts-workflows")).toHaveTextContent("code-driven");
    expect(screen.getByTestId("artifacts-workflows")).toHaveTextContent("3 steps");
    // Prompt layers: agent_id + ordered layer chips.
    const prompts = screen.getByTestId("artifacts-prompts");
    expect(prompts).toHaveTextContent("triage");
    expect(prompts).toHaveTextContent("system");
    expect(prompts).toHaveTextContent("agent");
    expect(prompts).toHaveTextContent("task");
    // Tools: side_effect + approval marker.
    expect(section).toHaveTextContent("github.repository.delete");
    expect(section).toHaveTextContent("destructive");
    expect(section).toHaveTextContent("approval");
  });
});
