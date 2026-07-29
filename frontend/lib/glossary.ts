/* ================================================================
   Glossary -- plain-language definitions.

   The site's audience runs from quant PMs to people who have never
   seen a Sharpe ratio. Every term that carries a number on the page
   gets an entry here, written for the second group without being
   wrong for the first.

   Rules for entries:
   - Lead with what the number answers, not with its formula.
   - Say what a good/bad value looks like where that is meaningful.
   - Where a term is routinely misread, say what it does NOT mean.
   ================================================================ */

export interface GlossaryEntry {
  /** Display term. */
  term: string;
  /** One sentence: what question this number answers. */
  short: string;
  /** Plain-language explanation, 2-4 sentences. */
  long: string;
  /** The misreading worth heading off, if there is one. */
  notThis?: string;
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  rSquared: {
    term: "R-squared",
    short:
      "How much of the index's daily movement can be accounted for by a handful of its biggest stocks.",
    long:
      "Take every day the market was open and note how much the S&P 500 moved. Now try to reproduce those daily moves using only the 20 largest companies in the index. R-squared is the share of the index's day-to-day movement that attempt accounts for — 0% would mean the 20 tell you nothing about where the index went, 100% would mean they tell you everything.",
    notThis:
      "It is not the share of the index those 20 companies represent by size, and it does not mean a 20-stock portfolio earns the same return as the index. It is about moving together, not about being the same thing.",
  },

  totalReturn: {
    term: "Total Return",
    short: "What the whole period added up to, including dividends.",
    long:
      "The cumulative gain from start to finish. A total return of 400% means $1 became $5. Because it compounds, a strategy measured over a longer period will usually show a bigger number regardless of how good it is — which is why this row is never ranked here.",
  },

  cagr: {
    term: "CAGR",
    short: "The steady annual rate that would produce the same end result.",
    long:
      "Compound annual growth rate. Real returns are lumpy — up 30% one year, down 15% the next. CAGR is the single smooth yearly rate that would have got you to the same place. It makes periods of different lengths comparable in a way total return does not.",
  },

  annualizedVolatility: {
    term: "Annualised Volatility",
    short: "How violently the value swings around, per year.",
    long:
      "A measure of how much the day-to-day returns scatter, scaled to a yearly figure. Higher means a bumpier ride: bigger gains, bigger losses, less predictability. Two strategies can end at the same place with very different volatility, and the calmer one is generally preferred.",
  },

  sharpe: {
    term: "Sharpe Ratio",
    short: "Return earned per unit of risk taken.",
    long:
      "Growth above what cash would have paid you, divided by how much the value swung around getting there. It answers whether a high return was skill or just a bigger gamble. Roughly: below 0.5 is unremarkable, around 1 is good, above 2 is rare and usually worth double-checking.",
  },

  sortino: {
    term: "Sortino Ratio",
    short: "Like Sharpe, but only counting the downside.",
    long:
      "Sharpe penalises all volatility, including the upside — but nobody complains about an unexpectedly good day. Sortino divides return only by the size of the losing moves, so it rewards a strategy whose bumpiness is mostly in the right direction.",
  },

  maxDrawdown: {
    term: "Max Drawdown",
    short: "The worst peak-to-trough fall over the whole period.",
    long:
      "If you had bought at the most unlucky moment, this is how far your money fell before it started recovering. It is the number that matters for whether someone can actually hold a strategy: a 50% drawdown is what makes people sell at the bottom.",
  },

  calmar: {
    term: "Calmar Ratio",
    short: "Annual return divided by the worst fall.",
    long:
      "Pairs the reward with the single worst experience rather than with average bumpiness. A high Calmar means the strategy grew well without ever putting you through a terrifying decline.",
  },

  beta: {
    term: "Beta",
    short: "How much it moves when the market moves.",
    long:
      "A beta of 1.00 means it tends to move point-for-point with the S&P 500. Above 1 means it exaggerates the market's moves in both directions; below 1 means it damps them. The benchmark's own beta is 1.00 by definition, which is why it is not ranked.",
  },

  alpha: {
    term: "Alpha",
    short: "Return beyond what its market exposure alone would explain.",
    long:
      "A strategy that takes more market risk should earn more; alpha is what is left after crediting that. Positive alpha is the claim that something other than simply riding the market was at work. Small alphas over short periods are very often luck.",
    notThis:
      "Here alpha is measured against the S&P 500 only. It does not control for tilts toward large companies or recent winners, so some of it may be exposure rather than skill.",
  },

  trackingError: {
    term: "Tracking Error",
    short: "How far it typically strays from the benchmark.",
    long:
      "The size of the typical gap between this strategy's return and the index's, per year. Low tracking error means it hugs the index closely; high means it goes its own way. Neither is good or bad on its own — it depends on whether you wanted a substitute for the index or an alternative to it.",
  },

  informationRatio: {
    term: "Information Ratio",
    short: "Reward per unit of straying from the benchmark.",
    long:
      "How much a strategy beat the index by, relative to how far it wandered from it to do so. It answers whether the deviation was worth taking. It is also the number that determines how many years of data you would need before a lead could be called real rather than lucky.",
  },

  tStat: {
    term: "t-statistic",
    short: "How confidently a gap can be called real rather than luck.",
    long:
      "Any two strategies will differ over any period, purely by chance. The t-statistic measures how large a gap is relative to how noisy the data is. The bigger it is, the less plausible that the gap is an accident of the particular decade measured.",
    notThis:
      "This project uses a hurdle of 3.0 rather than the conventional 2.0, because many strategy variants were tried and the best of many tries flatters itself. No comparison on this site clears it.",
  },

  deflatedSharpe: {
    term: "Deflated Sharpe",
    short: "A Sharpe ratio discounted for how many attempts it took.",
    long:
      "If you try twenty strategies, the best one looks good even if all twenty are worthless. Deflated Sharpe adjusts the winner's score downward based on how many were tried and how much they varied, so the number reflects the search, not just the result.",
  },

  turnover: {
    term: "Turnover",
    short: "How much of the portfolio is bought and sold each year.",
    long:
      "A turnover of 1.0x means the equivalent of the entire portfolio changes hands once a year. Every trade costs money, so higher turnover has to earn its keep before it helps.",
  },

  holdout: {
    term: "Holdout",
    short: "Data deliberately set aside and looked at only once.",
    long:
      "A strategy tuned on the same data used to judge it will always look good. Here everything was developed using data up to the end of 2023; 2024 onward was sealed off and evaluated a single time, against criteria written down in advance.",
  },
};

/** Definitions shown beneath the strategy comparison table, in row order. */
export const COMPARISON_GLOSSARY_KEYS = [
  "totalReturn",
  "cagr",
  "annualizedVolatility",
  "sharpe",
  "sortino",
  "maxDrawdown",
  "calmar",
  "beta",
  "alpha",
  "trackingError",
  "informationRatio",
] as const;
