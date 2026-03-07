/* ================================================================
   S&P Index Lab -- useMachineState Hook
   Finite state machine for the boot-up animation sequence.
   Progresses through stages on a timer and exposes which
   components / wires are currently active.
   ================================================================ */

"use client";

import { useReducer, useCallback, useEffect, useRef } from "react";
import type { MachineStage } from "@/lib/types";
import {
  STAGE_DURATIONS,
  STAGE_COMPONENTS,
  STAGE_WIRES,
  machineStages,
} from "@/lib/constants";

/* ──────────────────────────────────────────────────────────────
   State Shape
   ────────────────────────────────────────────────────────────── */

export interface MachineState {
  /** Current stage identifier */
  stage: MachineStage;
  /** Whether the machine power switch is ON */
  isOn: boolean;
  /** IDs of components currently active (lit up) */
  activeComponents: string[];
  /** IDs of wires currently active (animated) */
  activeWires: string[];
  /** True once the "complete" stage is reached */
  showResults: boolean;
}

/* ──────────────────────────────────────────────────────────────
   Actions
   ────────────────────────────────────────────────────────────── */

type MachineAction =
  | { type: "TOGGLE_ON" }
  | { type: "ADVANCE"; nextStage: MachineStage }
  | { type: "RESET" };

/* ──────────────────────────────────────────────────────────────
   Initial State
   ────────────────────────────────────────────────────────────── */

const initialState: MachineState = {
  stage: "idle",
  isOn: false,
  activeComponents: [],
  activeWires: [],
  showResults: false,
};

/* ──────────────────────────────────────────────────────────────
   Reducer
   ────────────────────────────────────────────────────────────── */

function machineReducer(state: MachineState, action: MachineAction): MachineState {
  switch (action.type) {
    case "TOGGLE_ON":
      return {
        ...state,
        isOn: true,
        stage: "powering_up",
        activeComponents: STAGE_COMPONENTS.powering_up,
        activeWires: STAGE_WIRES.powering_up,
        showResults: false,
      };

    case "ADVANCE":
      return {
        ...state,
        stage: action.nextStage,
        activeComponents: STAGE_COMPONENTS[action.nextStage],
        activeWires: STAGE_WIRES[action.nextStage],
        showResults: action.nextStage === "complete",
      };

    case "RESET":
      return { ...initialState };

    default:
      return state;
  }
}

/* ──────────────────────────────────────────────────────────────
   Ordered stage progression (excluding "idle")
   ────────────────────────────────────────────────────────────── */

const STAGE_ORDER: MachineStage[] = machineStages
  .filter((s) => s.id !== "idle")
  .sort((a, b) => a.order - b.order)
  .map((s) => s.id);

/* ──────────────────────────────────────────────────────────────
   Hook Return Type
   ────────────────────────────────────────────────────────────── */

export interface UseMachineStateReturn {
  /** Current stage identifier */
  stage: MachineStage;
  /** Whether the machine is powered on */
  isOn: boolean;
  /** Array of currently-active component IDs */
  activeComponents: string[];
  /** Array of currently-active wire IDs */
  activeWires: string[];
  /** True when the animation sequence has completed */
  showResults: boolean;
  /** Toggle the machine on or off */
  toggle: () => void;
  /** Reset to idle state */
  reset: () => void;
}

/* ──────────────────────────────────────────────────────────────
   useMachineState Hook
   ────────────────────────────────────────────────────────────── */

export function useMachineState(): UseMachineStateReturn {
  const [state, dispatch] = useReducer(machineReducer, initialState);

  // Track timeout IDs for cleanup
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  /**
   * Clear all pending stage-advancement timeouts.
   */
  const clearAllTimeouts = useCallback(() => {
    timeoutsRef.current.forEach((id) => clearTimeout(id));
    timeoutsRef.current = [];
  }, []);

  /**
   * Schedule the entire stage progression using cumulative delays.
   * Each stage waits for its own duration before advancing.
   */
  const startSequence = useCallback(() => {
    clearAllTimeouts();

    let cumulativeDelay = 0;

    for (let i = 0; i < STAGE_ORDER.length; i++) {
      const stage = STAGE_ORDER[i];
      const duration = STAGE_DURATIONS[stage];

      // The first stage ("powering_up") is dispatched immediately
      // via TOGGLE_ON, so we start scheduling from index 1.
      if (i === 0) {
        cumulativeDelay += duration;
        continue;
      }

      const timeoutId = setTimeout(() => {
        dispatch({ type: "ADVANCE", nextStage: stage });
      }, cumulativeDelay);

      timeoutsRef.current.push(timeoutId);
      cumulativeDelay += duration;
    }
  }, [clearAllTimeouts]);

  /**
   * Toggle the machine on (starts sequence) or off (resets).
   */
  const toggle = useCallback(() => {
    if (state.isOn) {
      clearAllTimeouts();
      dispatch({ type: "RESET" });
    } else {
      dispatch({ type: "TOGGLE_ON" });
      startSequence();
    }
  }, [state.isOn, clearAllTimeouts, startSequence]);

  /**
   * Force reset to idle regardless of current state.
   */
  const reset = useCallback(() => {
    clearAllTimeouts();
    dispatch({ type: "RESET" });
  }, [clearAllTimeouts]);

  // Cleanup all timeouts on unmount
  useEffect(() => {
    return () => {
      clearAllTimeouts();
    };
  }, [clearAllTimeouts]);

  return {
    stage: state.stage,
    isOn: state.isOn,
    activeComponents: state.activeComponents,
    activeWires: state.activeWires,
    showResults: state.showResults,
    toggle,
    reset,
  };
}

export default useMachineState;
