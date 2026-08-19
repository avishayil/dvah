"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CatalogBoard } from "@/components/catalog-board";
import { InvariantSidebar } from "@/components/invariant-sidebar";
import { Button } from "@/components/ui/button";
import { Tour, type TourStep } from "@/components/tour";
import { loadStatuses, type LabStatus } from "@/lib/status";

const CATALOG_TOUR: TourStep[] = [
  { el: '[data-tour="lab-table"]', title: "Pick a lab", text: "Labs run beginner → advanced. Start at the top (DVAH-001) — each row shows what you'll learn." },
  { el: '[data-tour="mode-toggle"]', title: "Learn vs CTF", text: "Learn mode gives hints + the solution. CTF locks them for a self-test." },
];

export default function LabsPage() {
  const [mode, setMode] = useState<"learn" | "ctf">("learn");
  const [statuses, setStatuses] = useState<Record<string, LabStatus>>({});
  useEffect(() => setStatuses(loadStatuses()), []);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["challenges"],
    queryFn: api.listChallenges,
  });

  return (
    <div className="flex">
      <section className="min-w-0 flex-1 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold">Labs</h1>
            <p className="text-xs text-muted">
              Exploit → trace → patch the harness → prove the invariant holds.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Tour tourKey="catalog" steps={CATALOG_TOUR} />
            <div data-tour="mode-toggle" className="flex items-center gap-1">
              <Button size="sm" variant={mode === "learn" ? "primary" : "ghost"} onClick={() => setMode("learn")}>
                learn
              </Button>
              <Button size="sm" variant={mode === "ctf" ? "primary" : "ghost"} onClick={() => setMode("ctf")}>
                ctf
              </Button>
            </div>
          </div>
        </div>

        {isLoading && <p className="text-sm text-muted">loading challenges…</p>}
        {error && (
          <div className="text-sm text-deny">
            <p>Could not reach the DVAH API. Is it running?</p>
            <div className="mt-2 flex gap-2">
              <Button size="sm" onClick={() => refetch()}>
                Retry
              </Button>
              <Link href="/settings">
                <Button size="sm" variant="ghost">
                  Configure API
                </Button>
              </Link>
            </div>
          </div>
        )}
        {data && <CatalogBoard challenges={data.challenges} statuses={statuses} mode={mode} />}
      </section>
      <InvariantSidebar />
    </div>
  );
}
