import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RunPanel } from "@/components/run-panel";
import { EditorPanel } from "@/components/editor-panel";

describe("accessibility", () => {
  it("run panel: 'run all' has a stable accessible name and shows onboarding when idle", () => {
    render(<RunPanel onRun={() => {}} running={false} result={null} logLines={[]} />);
    expect(screen.getByRole("button", { name: /run all four test markers/i })).toBeInTheDocument();
    // onboarding coach note explains the loop when there is no result yet
    expect(screen.getByText(/How this works/i)).toBeInTheDocument();
    // marker button still resolves uniquely (aria-label no longer collides)
    expect(screen.getByRole("button", { name: "exploit" })).toBeInTheDocument();
  });

  it("editor tabs expose the tab role and selected state", () => {
    render(
      <EditorPanel
        files={[
          { path: "vulnerable/a.py", contents: "" },
          { path: "vulnerable/b.py", contents: "" },
        ]}
        onChange={() => {}}
        onReset={() => {}}
      />,
    );
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(2);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
  });
});
