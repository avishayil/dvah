import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BriefingPanel } from "@/components/briefing-panel";
import type { Artifacts, ChallengeDetail } from "@/lib/types";

const EMPTY_ARTIFACTS: Artifacts = { skills: [], agents: [], tools: [] };

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
            tools: [{ id: "github.issue.read", name: "read issue", description: "read an issue" }],
          },
        })}
      />,
    );
    const section = screen.getByTestId("artifacts-section");
    expect(section).toHaveTextContent("github-investigator@1.2.0");
    expect(section).toHaveTextContent("github.issue.read");
    expect(section).toHaveTextContent("skill-runner");
  });

  it("hides the section when no skills or agents are declared (tools-only lab)", () => {
    render(
      <BriefingPanel
        mode="learn"
        detail={detail({
          artifacts: {
            skills: [],
            agents: [],
            tools: [{ id: "files.delete", name: "delete", description: "delete a file" }],
          },
        })}
      />,
    );
    expect(screen.queryByTestId("artifacts-section")).toBeNull();
  });
});
