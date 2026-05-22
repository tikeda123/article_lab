# lab_3: FX Kelly Criterion Order Risk Management Tool

Japanese: [README.ja.md](README.ja.md)

This lab supports the Qiita article "[Practical Math for Reducing FX Ruin Risk: Turning Kelly into Stop Width and Order Size](https://qiita.com/tikeda123/items/d5e16444da576c545c43)".

The article's purpose is to treat the Kelly criterion not as a formula for finding a winning order size, but as a way to estimate the maximum acceptable loss per trade and translate that amount into order size, stop width, pip value, and margin usage.

This lab is not investment advice and does not define a trading strategy. It is an educational pre-order risk-check tool for confirming whether a proposed order is too large under the user's assumptions.

## Learning Log and Feedback

This lab is also part of a public learning log for translating trading-risk theory into practical checks. The tool and article notes are shared so that the calculation assumptions can be inspected, corrected, and improved.

Corrections, edge-case reports, usability comments, and alternative risk-management perspectives are welcome when they are based on the tool behavior, formulas, or linked article.

## Experiment Role

The lab converts the Kelly criterion into an FX order checklist in this order:

1. Compute the Full Kelly fraction from win rate, average profit, and average loss.
2. Subtract spread and normal slippage as trading costs.
3. Apply a Kelly multiplier and a per-trade risk cap.
4. Compute maximum acceptable loss from account equity.
5. Convert order quantity into acceptable stop width.
6. Convert stop width into a Kelly-based maximum order quantity.
7. Apply margin-usage cap, hard margin limit, minimum order size, and order-size step.
8. Use a fixed random seed for losing streak, Monte Carlo, and Kelly-multiplier comparisons.

The canonical tool is `kelly_fx_position_size_tool.html`. The article outline is `fx_kelly_article_outline_with_tools.md`.

## Main Files

| File | Content |
|---|---|
| `kelly_fx_position_size_tool.html` | Standalone HTML tool with order-risk and ruin-resilience tabs |
| `fx_kelly_article_outline_with_tools.md` | Article outline aligned with the tool |
| `README.md` | English lab documentation |
| `README.ja.md` | Japanese lab documentation |

This lab has no input CSV and no Python aggregation script. The tool runs with HTML, CSS, and JavaScript only.

## Tool Structure

`kelly_fx_position_size_tool.html` has two tabs.

| Tab | Role |
|---|---|
| Order Risk Calculator | Convert Kelly-based risk into maximum acceptable loss, order size, stop width, and margin usage |
| Ruin Resilience Simulator | Check losing streaks, Monte Carlo ruin-line probability, Kelly multiplier comparison, maximum drawdown, and final equity distribution |

The order-risk tab has two calculation modes.

| Mode | Purpose |
|---|---|
| Order quantity -> acceptable stop pips | Check how much adverse movement is allowed for a planned order size |
| Stop pips -> maximum order quantity | Choose a stop width first and solve for the maximum order size |

## Input Fields

Important inputs:

| Input | Purpose |
|---|---|
| Account equity | Maximum acceptable loss, margin capacity, and simulator initial equity |
| Win rate | Kelly fraction and Monte Carlo win probability |
| Average profit pips | Kelly calculation and simulator profit size |
| Average loss pips | Kelly calculation and simulator loss size |
| Spread | Trading-cost adjustment |
| Normal slippage | Trading-cost adjustment |
| Stop overshoot estimate | Added to stop-width and order-size calculations |
| Kelly multiplier | Fraction of Full Kelly to use |
| Per-trade risk cap | Upper bound when Kelly suggests too much risk |
| Minimum order quantity | Lower bound for tradability |
| Order quantity step | Rounding unit for order size |
| Planned order quantity | Used in quantity-to-stop mode |
| Planned stop width | Used in stop-to-quantity mode |
| Settlement currency, current rate, settlement-to-JPY rate | Pip value, notional value, and margin calculations |
| Account type and leverage | Domestic retail 25x cap and margin limit |
| Margin usage cap | Maximum share of equity to allocate to required margin |
| Random seed | Reproducible Monte Carlo results |

The displayed "order quantity" is actual currency units, not broker-specific lot notation.

## Formulas

Trading costs and stop overshoot are separated.

```text
Trading cost = spread + normal slippage
Effective average profit = average profit - trading cost
Effective average loss = average loss + trading cost
Payoff ratio b = effective average profit / effective average loss
Full Kelly f* = (b * p - q) / b
Adopted risk fraction = min(Full Kelly * Kelly multiplier, risk cap)
Maximum acceptable loss = account equity * adopted risk fraction
```

For order quantity -> acceptable stop pips:

```text
One-currency-unit pip value = pip value per 10,000 units / 10,000
Loss per pip = order quantity * one-currency-unit pip value
Effective loss-width limit = maximum acceptable loss / loss per pip
Chart stop-width guide = max(0, effective loss-width limit - stop overshoot estimate)
```

For stop pips -> maximum order quantity:

```text
Kelly theoretical max quantity
= maximum acceptable loss / ((planned stop width + stop overshoot estimate) * one-currency-unit pip value)

Margin-buffer max quantity
= account equity * margin usage cap * leverage / notional price in JPY

Hard margin max quantity
= account equity * leverage / notional price in JPY

Adopted maximum quantity
= min(Kelly theoretical max quantity, margin-buffer max quantity), rounded by order-size step
```

The hard margin limit is not a recommended size. It is only the theoretical margin boundary.

## Launch

The tool can be opened directly in a browser. To serve it from the repository root:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8765/lab_3/kelly_fx_position_size_tool.html
```

Use another port if needed.

```bash
python3 -m http.server 8770 --bind 127.0.0.1
```

```text
http://127.0.0.1:8770/lab_3/kelly_fx_position_size_tool.html
```

## Syntax Check

To check the embedded JavaScript syntax:

```bash
node - <<'NODE'
const fs = require('fs');
const html = fs.readFileSync('lab_3/kelly_fx_position_size_tool.html', 'utf8');
for (const [, script] of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)) {
  new Function(script);
}
console.log('syntax OK');
NODE
```

Expected output:

```text
syntax OK
```

## Default Assumptions

| Item | Default |
|---|---:|
| Account equity | JPY 1,000,000 |
| Win rate | 55% |
| Average profit / loss | 30 pips / 30 pips |
| Spread | 0.2 pips |
| Normal slippage | 0.1 pips |
| Stop overshoot estimate | 0.3 pips |
| Kelly multiplier | Half Kelly |
| Per-trade risk cap | 2% |
| Planned order quantity | 10,000 units |
| Minimum order quantity | 100 units |
| Order quantity step | 100 units |
| Account type | Japanese domestic retail account |
| Leverage | 5x |
| Margin usage cap | 50% |

Under these defaults, the adopted risk fraction is capped at 2%, so maximum acceptable loss is JPY 20,000.

## Simulator Caveats

The ruin-resilience simulator inherits inputs from the order-risk tab. For losing-trade width, it can use either:

| Option | Meaning |
|---|---|
| Kelly effective average loss pips | Uses historical strategy-level average loss |
| Current stop width + stop overshoot estimate | Uses the stop width entered in the current order calculation |

If you solve "how many units can I trade with a 30-pip stop?", the simulator does not automatically use 30 pips unless that option is selected.

Monte Carlo uses a random seed. The same seed produces the same win/loss sequence and large-loss events, which makes article screenshots and reader reproduction easier.

## Caveats

The tool does not guarantee safety.

- Kelly depends on the estimated win rate, average profit, and average loss being realistic.
- Average profit and loss should come from the same pair, strategy condition, and order-size context.
- Spread, slippage, stop overshoot, execution rejection, gaps, and liquidity stress can be worse than assumed.
- Domestic Japanese retail FX should respect the 25x leverage limit.
- The hard margin limit is not a recommended quantity.
- Monte Carlo is a simplified seeded simulation, not a full model of stress execution.

## Article Mapping

The article's core message is:

```text
The Kelly criterion does not directly produce stop pips or order size.
It produces a theoretical risk fraction of account equity.

For FX practice, that fraction must be converted into:
maximum acceptable loss
=> order quantity
=> loss per pip
=> stop width
=> margin usage.
```

The article should present Kelly as a risk-visibility tool for avoiding oversized positions, not as a profit-maximization shortcut.
