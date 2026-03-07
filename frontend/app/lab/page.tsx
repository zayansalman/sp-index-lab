"use client";

import { useMachineState } from "@/hooks/useMachineState";
import MachineCanvas from "@/components/machine/MachineCanvas";
import ResultsPanel from "@/components/results/ResultsPanel";

export default function LabPage() {
  const { isOn, stage, activeComponents, activeWires, showResults, toggle } =
    useMachineState();

  return (
    <main className="relative min-h-screen bg-bg-primary">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4">
        <a
          href="/"
          className="font-heading text-xs uppercase tracking-widest text-text-muted transition-colors hover:text-text-secondary"
        >
          &larr; Back
        </a>
        <h1 className="font-heading text-sm uppercase tracking-widest text-text-secondary">
          S&P Index Lab
        </h1>
        <div className="w-16" /> {/* Spacer for alignment */}
      </div>

      {/* Machine */}
      <div className="flex flex-col items-center px-4 pt-4 pb-16">
        <MachineCanvas
          isOn={isOn}
          stage={stage}
          activeComponents={new Set(activeComponents)}
          activeWires={new Set(activeWires)}
          onToggle={toggle}
        />

        {/* Instruction text */}
        {!isOn && (
          <p className="mt-8 animate-pulse text-center text-sm text-text-muted">
            Toggle the switch to start the analysis engine
          </p>
        )}

        {/* Stage indicator during animation */}
        {isOn && !showResults && (
          <p className="mt-6 text-center text-sm text-text-muted">
            {stage === "powering_up" && "Initialising circuits and loading configuration..."}
            {stage === "data_pipeline" && "Ingesting 12+ years of daily price data..."}
            {stage === "concentration" && "Running OLS regressions to find the concentration elbow..."}
            {stage === "building" && "Constructing cap-weighted and equal-weighted SP-20 indices..."}
            {stage === "optimizing" && "Preparing optimizer, factor model, and regime detector..."}
            {stage === "monitoring" && "Computing Sharpe, Sortino, drawdowns, and 15+ metrics..."}
          </p>
        )}
      </div>

      {/* Results Panel -- appears below machine when animation completes */}
      <ResultsPanel visible={showResults} />
    </main>
  );
}
