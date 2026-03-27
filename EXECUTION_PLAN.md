# SP Index Lab Execution Plan (No Broker Priority)

## Objective

Ship a robust, testable Phase 2 trading core first. Defer broker connectivity and live trading integrations until the strategy, risk, and validation stack is production-grade.

## Scope Decision

- In scope now: S1-S6 (foundation, signal stack, strategies, execution abstraction, risk, backtest validation)
- Deprioritized for now: S11-S12 live trading adapters and broker connectivity
- Reason: Current dependency graph and codebase maturity indicate core research/trading engine must come first

## Priority Order

### P0: Build the Core Engine (Critical Path)

1. Sprint 1 (Issues `#32`-`#35`)
   - Extract metrics module
   - Build walk-forward engine
   - Implement classical optimizers
   - Extend config constants for fund mode

2. Sprint 2 (Issues `#36`-`#40`)
   - Technical features
   - Regime model (HMM)
   - Factor model (LightGBM)
   - Ensemble optimizer
   - Rebalancer logic

3. Sprint 3 (Issues `#41`-`#44`)
   - Pod abstractions
   - Passive core strategy
   - Portfolio aggregator
   - Index class hierarchy

### P1: Execution + Risk + Validation

4. Sprint 4 (Issues `#45`-`#49`)
   - Execution domain models
   - Broker interface abstraction
   - Internal paper broker only
   - Order router and broker factory

5. Sprint 5 (Issues `#50`-`#53`)
   - VaR/CVaR calculators
   - Circuit breaker rules
   - Risk snapshot monitoring
   - Portfolio state + ledger

6. Sprint 6 (Issues `#54`-`#57`)
   - Backtest simulator
   - Promotion-gate report
   - Full backtest runner script
   - Validation against target thresholds

### Deferred Until Core Is Stable

- Sprint 11-12 live trading and broker adapters (`#73`, `#75`, `#80`, related)
- Any production broker API connectivity work

## Parallel Development Model (Cursor Multi-Agent)

Use one issue per branch per agent, merged through PR only.

### Parallelization Rules

- Parallelize only independent issues
- Keep agents in non-overlapping file areas
- Merge by dependency order (S1 -> S2 -> S3 -> ...)
- Run full CI on every PR

### Suggested Branch Naming

- `feat/s1-1-backtest-metrics`
- `feat/s1-2-walk-forward-engine`
- `feat/s1-3-classical-optimizers`
- `test/t1-4-data-pipeline-tests`
- `test/t2-5-proof-layer-tests`

### Recommended Workstream Split

- Agent A: `src/backtest/*` + related tests
- Agent B: `src/optimizer/*` + related tests
- Agent C: `src/strategies/*` and `src/indices/*`
- Agent D: CI, test harness, lint/type/build gates

## CI/CD Best-Practice Baseline

## Required checks on every PR

- Python lint + format check
- Python tests + coverage threshold
- Frontend lint + typecheck + build
- No direct push to `main`

## Governance

- Branch protection on `main`
- PR approvals required
- Squash merge policy
- Conventional commit messages preferred

## Data automation hardening

- Replace direct auto-commit-to-main patterns with PR-based bot updates where practical
- Ensure data refresh workflows are observable and reproducible

## Engineering Standards

- Python 3.11+ with type hints
- Public function docstrings
- No look-ahead bias in any analytics or backtests
- Centralize constants in `src/config.py`
- Prefer vectorized operations; avoid row-by-row loops

## Where K-Dense Fits

Use [K-Dense Web](https://www.k-dense.ai) as a research and experimentation copilot, not as the source of truth for production portfolio logic.

### Use K-Dense For

- Strategy ideation and hypothesis generation
- Parallel research on factor definitions and regime features
- Experiment design and comparison frameworks
- Draft analysis narratives and decision memos

### Keep In This Repo

- All production code in `src/` and `scripts/`
- Backtest/risk logic and promotion gates
- CI/CD policy, tests, and release governance
- Any execution path that can impact portfolio decisions

### Import Gate For Any K-Dense Output

Before adopting any output:

1. Convert to deterministic, typed code in this repo
2. Add tests (unit + integration where relevant)
3. Prove no look-ahead bias and document assumptions
4. Re-run walk-forward/backtest gates
5. Merge via PR with required CI checks

## Immediate Next Actions

1. Implement issue `#32` (metrics extraction)
2. Implement issue `#33` (walk-forward engine)
3. Implement issue `#34` (classical optimizers)
4. In parallel: implement test issues `#1` and `#2`
5. Add/upgrade CI checks before increasing parallel agent count

## Definition of Done for This Phase

Before starting broker connectivity:

- S1-S6 issues merged
- Core modules have passing unit/integration tests
- Backtest promotion gates implemented and enforced
- CI/CD checks stable and required on `main`
- Documented reproducible pipeline from data -> signals -> portfolio -> risk -> report
