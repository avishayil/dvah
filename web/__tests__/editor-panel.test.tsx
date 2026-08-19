import { render, screen, within, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EditorPanel } from "@/components/editor-panel";
import type { EditableFile } from "@/lib/types";

const FILES: EditableFile[] = [
  { path: "vulnerable/executor.py", contents: "class VulnerableExecutor: ...", writable: true, group: "patch" },
  { path: "environment/users.yaml", contents: "principal: {}", writable: false, group: "world" },
  { path: "dvah/harness/resolver.py", contents: "def build_envelope(): ...", writable: false, group: "reference", label: "dvah.harness.resolver" },
];

describe("editor panel — grouped read-only tabs", () => {
  it("shows patch + world tabs but hides the reference group until expanded", () => {
    render(<EditorPanel files={FILES} onChange={() => {}} onReset={() => {}} />);
    // Reference tab is collapsed by default → only the editable + world tabs show.
    expect(screen.getAllByRole("tab")).toHaveLength(2);
    expect(screen.getByRole("tab", { name: /executor\.py/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /users\.yaml/i })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /dvah\.harness\.resolver/i })).toBeNull();
  });

  it("expands the harness-reference group on toggle", () => {
    render(<EditorPanel files={FILES} onChange={() => {}} onReset={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /reference files/i }));
    expect(screen.getByRole("tab", { name: /dvah\.harness\.resolver.*read-only/i })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
  });

  it("labels the groups and marks the editable tab selected first", () => {
    render(<EditorPanel files={FILES} onChange={() => {}} onReset={() => {}} />);
    expect(screen.getByText(/patch this/i)).toBeInTheDocument();
    expect(screen.getByText(/the world · read-only/i)).toBeInTheDocument();
    const tabs = screen.getAllByRole("tab");
    expect(tabs[0]).toHaveAttribute("aria-selected", "true"); // the editable file
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
  });

  it("keeps Reset outside the tablist (a11y: tablist owns only tabs)", () => {
    render(<EditorPanel files={FILES} onChange={() => {}} onReset={() => {}} />);
    const tablist = screen.getByRole("tablist");
    expect(within(tablist).queryByRole("button", { name: /reset/i })).toBeNull();
    expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
  });
});
