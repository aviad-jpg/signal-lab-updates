# Signal Lab Model Editor v6.1

Shadow-only retrospective test. It does not change production.

## Run on Windows

Run the desktop shortcut `Signal Lab Backtest v6`. A timestamped ZIP is created
automatically and opened in File Explorer when the run finishes.

The runner processes all frozen days. If one day fails, it records an
`error_DATE.json` file and continues, so a single API error cannot erase the rest
of the test.

## v6.1 changes and hard guards

- same-day and historical duplicate removal before model judgment;
- only model selections that meet numeric relevance and transferability gates
  can enter the portfolio;
- no more than one borderline item, enforced in code;
- no portfolio IDs outside the eligible slate;
- no quota filling and a maximum of eight items;
- examples prioritize the latest manually defined Signal Lab preferences.
- model judgment and portfolio selection receive only source title and factual
  summary, never upstream `body` framing or `depth_analysis`;
- every explicit positive and negative gold example is available to the judge;
- source titles are preserved in walk-forward history for cross-source repeats.
- every strong candidate that passes all numeric gates is retained, up to eight;
- unmistakable event recaps are removed before judgment.
- malformed or truncated model JSON is retried automatically up to three times.
- legacy upstream `post_potential` labels cannot veto an independently strong
  model judgment;
- no source can occupy more than two final portfolio slots and no topic can
  occupy more than four;
- missing frozen inputs are reported as skipped instead of crashing the day;
- selection diagnostics expose eligible candidates omitted from the portfolio.

## Acceptance gate

- no unmarked repeats or same-day duplicates;
- no more than one borderline item per day;
- no core miss in AI search/discovery, media-model change, B2B social/content,
  work transformation or measurable marketing change;
- selected items score 8+, except at most one explicit borderline;
- quality over volume.
