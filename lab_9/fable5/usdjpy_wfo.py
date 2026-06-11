"""
USDJPY systematic strategy research pipeline
- Data validation / timeframe inference
- Candidate strategy comparison (trend / breakout / mean-reversion / vol-filter / regime)
- Walk-Forward Optimization (rolling, train-only parameter selection, pure OOS test)
- Robustness checks (cost sensitivity, parameter neighborhood, regime split, bootstrap)

Execution model: signal computed on bar t close -> position effective from bar t+1
PnL of bar t+1 = pos(t) * (close[t+1]/close[t] - 1) - cost * |pos change at t+1 open|
Round-trip cost default 1.0 pip (= 0.01 JPY), charged per unit of position change (0.5 pip/side).
"""

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from itertools import product
import json, sys

RNG = np.random.default_rng(42)
PIP = 0.01  # USDJPY 1 pip

# ----------------------------------------------------------------------
# 1. Data loading / validation
# ----------------------------------------------------------------------
def load_data(path):
    df = pd.read_csv(path, sep="\t", header=None,
                     names=["datetime", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df

def validate_data(df, name=""):
    rep = {"name": name}
    rep["rows"] = len(df)
    rep["start"] = str(df["datetime"].iloc[0])
    rep["end"] = str(df["datetime"].iloc[-1])
    # timeframe inference
    diffs = df["datetime"].diff().dropna()
    mode_td = diffs.mode().iloc[0]
    rep["inferred_timeframe_min"] = mode_td.total_seconds() / 60
    rep["pct_bars_at_mode"] = float((diffs == mode_td).mean())
    rep["duplicates"] = int(df["datetime"].duplicated().sum())
    rep["nans"] = int(df[["open","high","low","close"]].isna().sum().sum())
    bad_ohlc = ((df["high"] < df[["open","close","low"]].max(axis=1)) |
                (df["low"]  > df[["open","close","high"]].min(axis=1))).sum()
    rep["ohlc_violations"] = int(bad_ohlc)
    ret = np.log(df["close"]).diff().dropna()
    rep["ret_mean_bp"] = float(ret.mean()*1e4)
    rep["ret_std_bp"] = float(ret.std()*1e4)
    rep["ret_skew"] = float(ret.skew())
    rep["ret_kurt"] = float(ret.kurt())
    rep["abs_ret_>1pct_bars"] = int((ret.abs() > 0.01).sum())
    rep["max_gap_hours"] = float(diffs.max().total_seconds()/3600)
    return rep

# ----------------------------------------------------------------------
# 2. Features
# ----------------------------------------------------------------------
def create_features(df):
    out = df.copy().set_index("datetime")
    c = out["close"]
    out["ret"] = c.pct_change()
    out["logret"] = np.log(c).diff()
    tr = np.maximum(out["high"] - out["low"],
         np.maximum((out["high"] - c.shift()).abs(), (out["low"] - c.shift()).abs()))
    out["atr20"] = tr.rolling(20).mean()
    out["atr_pctile"] = out["atr20"].rolling(500, min_periods=200).rank(pct=True)
    return out

# ----------------------------------------------------------------------
# 3. Signal generators  (positions in {-1,0,+1}, computed with info up to bar t)
# ----------------------------------------------------------------------
def sig_donchian(df, n_entry, n_exit):
    """Donchian breakout: enter on n_entry-bar high/low break, exit on n_exit-bar opposite channel."""
    hi = df["high"].rolling(n_entry).max().shift(1)
    lo = df["low"].rolling(n_entry).min().shift(1)
    xhi = df["high"].rolling(n_exit).max().shift(1)
    xlo = df["low"].rolling(n_exit).min().shift(1)
    c = df["close"].values
    pos = np.zeros(len(df))
    p = 0
    hi_v, lo_v, xhi_v, xlo_v = hi.values, lo.values, xhi.values, xlo.values
    for i in range(len(df)):
        if np.isnan(hi_v[i]) or np.isnan(xlo_v[i]):
            pos[i] = 0; continue
        if p == 0:
            if c[i] > hi_v[i]: p = 1
            elif c[i] < lo_v[i]: p = -1
        elif p == 1:
            if c[i] < xlo_v[i]:
                p = -1 if c[i] < lo_v[i] else 0
        elif p == -1:
            if c[i] > xhi_v[i]:
                p = 1 if c[i] > hi_v[i] else 0
        pos[i] = p
    return pd.Series(pos, index=df.index)

def sig_ma_cross(df, fast, slow):
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    pos = np.where(f > s, 1.0, np.where(f < s, -1.0, 0.0))
    pos[:slow] = 0
    return pd.Series(pos, index=df.index)

def sig_meanrev(df, n, z_in, z_out=0.0):
    m = df["close"].rolling(n).mean()
    sd = df["close"].rolling(n).std()
    z = (df["close"] - m) / sd
    pos = np.zeros(len(df)); p = 0
    zv = z.values
    for i in range(len(df)):
        if np.isnan(zv[i]): pos[i]=0; continue
        if p == 0:
            if zv[i] > z_in: p = -1
            elif zv[i] < -z_in: p = 1
        elif p == 1 and zv[i] >= -z_out: p = 0
        elif p == -1 and zv[i] <= z_out: p = 0
        pos[i] = p
    return pd.Series(pos, index=df.index)

def sig_donchian_volfilter(df, n_entry, n_exit, vol_max):
    """Donchian, but new entries only when ATR percentile < vol_max (filter applied at entry)."""
    base = sig_donchian(df, n_entry, n_exit)
    ok = (df["atr_pctile"] < vol_max).values
    pos = base.values.copy()
    p = 0
    for i in range(len(pos)):
        tgt = pos[i]
        if tgt != p:  # position change requested
            if tgt != 0 and not ok[i] and p == 0:
                tgt = 0  # block new entry in high vol
        p = tgt
        pos[i] = p
    return pd.Series(pos, index=df.index)

def sig_ma_regime_donchian(df, n_entry, n_exit, regime_n):
    """Donchian entries only in direction of long-term MA regime."""
    base = sig_donchian(df, n_entry, n_exit)
    reg = np.sign(df["close"] - df["close"].rolling(regime_n).mean()).values
    pos = base.values.copy()
    p = 0
    for i in range(len(pos)):
        tgt = pos[i]
        if tgt != p and tgt != 0 and tgt != reg[i]:
            tgt = 0 if p != 0 else p  # block counter-regime entries
        p = tgt
        pos[i] = p
    return pd.Series(pos, index=df.index)

# ----------------------------------------------------------------------
# 4. Backtest
# ----------------------------------------------------------------------
def backtest(df, pos, cost_pips=1.0):
    """pos: position decided at bar t close, held over bar t+1. Returns per-bar strategy returns."""
    pos_eff = pos.shift(1).fillna(0)          # effective during bar t (decided at t-1)
    ret = df["close"].pct_change().fillna(0)
    gross = pos_eff * ret
    dpos = pos_eff.diff().abs().fillna(pos_eff.abs())
    cost = dpos * (cost_pips / 2 * PIP) / df["close"]   # per-side cost on each unit traded
    net = gross - cost
    return net, pos_eff

def evaluate_performance(net, pos_eff, bars_per_year):
    eq = (1 + net).cumprod()
    n = len(net)
    yrs = n / bars_per_year
    total = eq.iloc[-1] - 1
    ann = (1 + total) ** (1 / max(yrs, 1e-9)) - 1
    mu, sd = net.mean(), net.std()
    sharpe = mu / sd * np.sqrt(bars_per_year) if sd > 0 else 0.0
    downside = net[net < 0].std()
    sortino = mu / downside * np.sqrt(bars_per_year) if downside and downside > 0 else 0.0
    peak = eq.cummax(); dd = eq / peak - 1
    maxdd = dd.min()
    calmar = ann / abs(maxdd) if maxdd < 0 else np.nan
    # trades
    chg = pos_eff.diff().fillna(pos_eff)
    entries = (chg != 0) & (pos_eff != 0)
    trade_ids = (chg != 0).cumsum()
    tr = pd.DataFrame({"id": trade_ids, "pos": pos_eff, "net": net})
    tr = tr[tr["pos"] != 0]
    trades = tr.groupby("id").agg(pnl=("net", lambda x: (1+x).prod()-1),
                                  nbars=("net", "size"),
                                  side=("pos", "first"))
    ntr = len(trades)
    wins = trades[trades["pnl"] > 0]; losses = trades[trades["pnl"] <= 0]
    winrate = len(wins)/ntr if ntr else np.nan
    pf = wins["pnl"].sum() / abs(losses["pnl"].sum()) if len(losses) and losses["pnl"].sum() != 0 else np.nan
    return {
        "total_return": total, "annual_return": ann, "sharpe": sharpe,
        "sortino": sortino, "calmar": calmar, "max_dd": maxdd,
        "win_rate": winrate, "profit_factor": pf,
        "avg_win": wins["pnl"].mean() if len(wins) else np.nan,
        "avg_loss": losses["pnl"].mean() if len(losses) else np.nan,
        "n_trades": ntr,
        "avg_hold_bars": trades["nbars"].mean() if ntr else np.nan,
        "exposure": float((pos_eff != 0).mean()),
        "long_pnl": trades[trades["side"]>0]["pnl"].sum() if ntr else np.nan,
        "short_pnl": trades[trades["side"]<0]["pnl"].sum() if ntr else np.nan,
        "n_long": int((trades["side"]>0).sum()) if ntr else 0,
        "n_short": int((trades["side"]<0).sum()) if ntr else 0,
    }

# ----------------------------------------------------------------------
# 5. Strategy registry & grids (deliberately coarse)
# ----------------------------------------------------------------------
STRATEGIES = {
    "donchian": {
        "fn": lambda df, p: sig_donchian(df, p["n_entry"], p["n_exit"]),
        "grid": [{"n_entry": ne, "n_exit": max(ne//2, 5)} for ne in [20, 40, 60, 90, 120]],
    },
    "ma_cross": {
        "fn": lambda df, p: sig_ma_cross(df, p["fast"], p["slow"]),
        "grid": [{"fast": f, "slow": s} for f, s in product([10, 20, 40], [60, 120, 200]) if s >= 3*f],
    },
    "meanrev": {
        "fn": lambda df, p: sig_meanrev(df, p["n"], p["z_in"]),
        "grid": [{"n": n, "z_in": z} for n, z in product([20, 50], [1.5, 2.0, 2.5])],
    },
    "donchian_volf": {
        "fn": lambda df, p: sig_donchian_volfilter(df, p["n_entry"], max(p["n_entry"]//2,5), p["vol_max"]),
        "grid": [{"n_entry": ne, "vol_max": vm} for ne, vm in product([40, 60, 90, 120], [0.7, 0.9])],
    },
    "donchian_regime": {
        "fn": lambda df, p: sig_ma_regime_donchian(df, p["n_entry"], max(p["n_entry"]//2,5), p["regime_n"]),
        "grid": [{"n_entry": ne, "regime_n": rn} for ne, rn in product([40, 60, 90], [200, 400])],
    },
}

# ----------------------------------------------------------------------
# 6. Walk Forward Optimization
# ----------------------------------------------------------------------
def walk_forward_optimization(df, strat_name, bars_per_year, cost_pips=1.0,
                              train_months=36, test_months=6, min_trades_train=20):
    spec = STRATEGIES[strat_name]
    idx = df.index
    start, end = idx[0], idx[-1]
    folds = []
    t0 = start
    while True:
        tr_end = t0 + pd.DateOffset(months=train_months)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if tr_end >= end: break
        folds.append((t0, tr_end, min(te_end, end)))
        if te_end >= end: break
        t0 = t0 + pd.DateOffset(months=test_months)  # rolling

    results, oos_net_all, oos_pos_all = [], [], []
    for (a, b, cthru) in folds:
        train = df.loc[a:b]
        # extend test slice backwards by max lookback so indicators warm up, then cut
        warm = df.loc[:b].tail(600)
        test_full = pd.concat([warm, df.loc[b:cthru].iloc[1:]])
        best, best_score, best_stats = None, -np.inf, None
        for p in spec["grid"]:
            pos = spec["fn"](train, p)
            net, pe = backtest(train, pos, cost_pips)
            st = evaluate_performance(net, pe, bars_per_year)
            score = st["sharpe"] if st["n_trades"] >= min_trades_train else -np.inf
            if score > best_score:
                best, best_score, best_stats = p, score, st
        if best is None:
            continue
        pos = spec["fn"](test_full, best)
        net, pe = backtest(test_full, pos, cost_pips)
        net = net.loc[b:cthru].iloc[1:]; pe = pe.loc[b:cthru].iloc[1:]
        st = evaluate_performance(net, pe, bars_per_year)
        results.append({"train_start": a, "train_end": b, "test_end": cthru,
                        "params": json.dumps(best), "train_sharpe": best_score, **st})
        oos_net_all.append(net); oos_pos_all.append(pe)
    fold_df = pd.DataFrame(results)
    oos_net = pd.concat(oos_net_all) if oos_net_all else pd.Series(dtype=float)
    oos_pos = pd.concat(oos_pos_all) if oos_pos_all else pd.Series(dtype=float)
    return fold_df, oos_net, oos_pos

# ----------------------------------------------------------------------
# 7. Robustness
# ----------------------------------------------------------------------
def robustness_check(df, strat_name, bars_per_year):
    spec = STRATEGIES[strat_name]
    out = {}
    # cost sensitivity on WFO OOS
    for cp in [0.5, 1.0, 2.0]:
        _, net, pe = walk_forward_optimization(df, strat_name, bars_per_year, cost_pips=cp)
        st = evaluate_performance(net, pe, bars_per_year)
        out[f"cost_{cp}pips"] = {k: st[k] for k in ["annual_return","sharpe","max_dd","n_trades"]}
    return out

def block_bootstrap(net, bars_per_year, block=100, n_sim=2000):
    arr = net.values
    n = len(arr)
    nb = int(np.ceil(n / block))
    maxdds, finals = [], []
    for _ in range(n_sim):
        starts = RNG.integers(0, n - block, nb)
        sim = np.concatenate([arr[s:s+block] for s in starts])[:n]
        eq = np.cumprod(1 + sim)
        peak = np.maximum.accumulate(eq)
        maxdds.append((eq/peak - 1).min())
        finals.append(eq[-1] - 1)
    maxdds = np.array(maxdds); finals = np.array(finals)
    return {"maxdd_p50": np.median(maxdds), "maxdd_p95": np.percentile(maxdds, 5),
            "final_p50": np.median(finals), "prob_loss": (finals < 0).mean(),
            "prob_dd_gt_20": (maxdds < -0.20).mean(),
            "cvar5_bar": finals[finals <= np.percentile(finals,5)].mean()}

# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    pd.set_option("display.width", 200)
    files = {"M30": "/mnt/user-data/uploads/USDJPY30.csv",
             "H1": "/mnt/user-data/uploads/USDJPY60.csv",
             "H4": "/mnt/user-data/uploads/USDJPY240.csv"}
    print("="*80); print("1. DATA DIAGNOSTICS"); print("="*80)
    data = {}
    for k, f in files.items():
        df = load_data(f)
        rep = validate_data(df, k)
        data[k] = df
        print(json.dumps(rep, indent=1, default=str))

    # primary timeframe: H4 (longest history, best cost/vol ratio)
    df = create_features(data["H4"])
    BPY = 6 * 252  # H4 bars/year approx (FX ~6 bars/day, 252 trading days -> verify)
    bars_per_day = len(df) / ((df.index[-1] - df.index[0]).days * 5/7)
    BPY = round(bars_per_day * 252)
    print(f"\nH4 bars/year (empirical): {BPY}")

    # vol regimes / trend share quick diag
    yearly_vol = df["logret"].groupby(df.index.year).std() * np.sqrt(BPY)
    print("\nAnnualized vol by year:\n", (yearly_vol*100).round(1).to_string())

    # --------------------------------------------------------------
    print("\n" + "="*80); print("2. WFO PER STRATEGY  (cost = 1.0 pip RT, H4)"); print("="*80)
    summary = []
    wfo_store = {}
    for s in STRATEGIES:
        fold_df, net, pe = walk_forward_optimization(df, s, BPY)
        st = evaluate_performance(net, pe, BPY)
        pos_share = fold_df["total_return"] > 0
        summary.append({"strategy": s, "oos_sharpe": st["sharpe"], "oos_ann": st["annual_return"],
                        "oos_maxdd": st["max_dd"], "n_trades": st["n_trades"],
                        "folds": len(fold_df), "pos_folds_pct": pos_share.mean(),
                        "fold_sharpe_mean": fold_df["sharpe"].mean(),
                        "fold_sharpe_std": fold_df["sharpe"].std()})
        wfo_store[s] = (fold_df, net, pe)
    sm = pd.DataFrame(summary).sort_values("oos_sharpe", ascending=False)
    print(sm.round(3).to_string(index=False))

    best_name = sm.iloc[0]["strategy"]
    print(f"\nBest OOS strategy: {best_name}")
    fold_df, net, pe = wfo_store[best_name]

    print("\n" + "="*80); print(f"3. FOLD-BY-FOLD OOS  ({best_name})"); print("="*80)
    cols = ["train_end","test_end","params","train_sharpe","sharpe","total_return","max_dd","n_trades","win_rate"]
    print(fold_df[cols].round(3).to_string(index=False))

    print("\n" + "="*80); print("4. FULL OOS PERFORMANCE"); print("="*80)
    st = evaluate_performance(net, pe, BPY)
    for k, v in st.items(): print(f"  {k:18s}: {v:.4f}" if isinstance(v,(int,float)) and not np.isnan(v) else f"  {k:18s}: {v}")

    # benchmarks
    bh_net = df["close"].pct_change().loc[net.index].fillna(0)
    bh = evaluate_performance(bh_net, pd.Series(1.0, index=net.index), BPY)
    sma200pos = pd.Series(np.where(df["close"] > df["close"].rolling(200).mean(), 1.0, -1.0), index=df.index)
    sma_net, sma_pe = backtest(df, sma200pos, 1.0)
    sma_st = evaluate_performance(sma_net.loc[net.index], sma_pe.loc[net.index], BPY)
    print(f"\nBenchmarks over same OOS period:")
    print(f"  Buy&Hold  : ann={bh['annual_return']:.3f} sharpe={bh['sharpe']:.2f} maxdd={bh['max_dd']:.3f}")
    print(f"  SMA200 L/S: ann={sma_st['annual_return']:.3f} sharpe={sma_st['sharpe']:.2f} maxdd={sma_st['max_dd']:.3f}")
    print(f"  Flat      : ann=0.000 sharpe=0.00 maxdd=0.000")

    # monthly returns
    eq = (1+net).cumprod()
    monthly = eq.resample("ME").last().pct_change().dropna()
    print("\nMonthly OOS return stats: mean=%.3f%% std=%.3f%% pos_months=%.1f%%" %
          (monthly.mean()*100, monthly.std()*100, (monthly>0).mean()*100))
    yearly = eq.groupby(eq.index.year).apply(lambda x: x.iloc[-1]/x.iloc[0]-1)
    print("Yearly OOS returns:\n", (yearly*100).round(2).to_string())

    print("\n" + "="*80); print("5. ROBUSTNESS"); print("="*80)
    rb = robustness_check(df, best_name, BPY)
    for k, v in rb.items():
        print(f"  {k}: ann={v['annual_return']:.3f} sharpe={v['sharpe']:.2f} maxdd={v['max_dd']:.3f} trades={v['n_trades']}")

    # parameter sensitivity (full-sample, fixed params around the modal WFO choice)
    print("\nParameter sensitivity (full-sample, cost=1pip):")
    modal = json.loads(fold_df["params"].mode().iloc[0])
    print(f"  modal WFO params: {modal}")
    sens = []
    if best_name in ("donchian", "donchian_volf", "donchian_regime"):
        base_ne = modal.get("n_entry", 60)
        for ne in sorted({max(10, base_ne+d) for d in [-30,-20,-10,0,10,20,30]}):
            p = dict(modal); p["n_entry"] = ne
            if best_name == "donchian": p["n_exit"] = max(ne//2,5)
            pos = STRATEGIES[best_name]["fn"](df, p)
            nn, pp = backtest(df, pos, 1.0)
            s2 = evaluate_performance(nn, pp, BPY)
            sens.append({"n_entry": ne, "sharpe": s2["sharpe"], "ann": s2["annual_return"], "maxdd": s2["max_dd"], "trades": s2["n_trades"]})
    elif best_name == "ma_cross":
        for f_, s_ in product([modal["fast"]-10, modal["fast"], modal["fast"]+10],
                              [modal["slow"]-40, modal["slow"], modal["slow"]+40]):
            if f_ <= 0 or s_ <= 3*f_: continue
            pos = sig_ma_cross(df, f_, s_)
            nn, pp = backtest(df, pos, 1.0)
            s2 = evaluate_performance(nn, pp, BPY)
            sens.append({"fast": f_, "slow": s_, "sharpe": s2["sharpe"], "ann": s2["annual_return"]})
    print(pd.DataFrame(sens).round(3).to_string(index=False))

    # vol & trend regime split of OOS returns
    print("\nOOS performance by volatility regime (ATR percentile median split):")
    vp = df["atr_pctile"].reindex(net.index)
    for lab, mask in [("low_vol", vp < 0.5), ("high_vol", vp >= 0.5)]:
        sub = net[mask.fillna(False)]
        if len(sub) > 100:
            sh = sub.mean()/sub.std()*np.sqrt(BPY) if sub.std()>0 else 0
            print(f"  {lab}: bars={len(sub)} ann_ret={(sub.mean()*BPY)*100:.2f}% sharpe={sh:.2f}")

    # long/short split
    print(f"\nLong/Short split: long_pnl={st['long_pnl']:.4f} ({st['n_long']} tr) | short_pnl={st['short_pnl']:.4f} ({st['n_short']} tr)")

    # block bootstrap
    print("\nBlock bootstrap of OOS returns (2000 sims, block=100 bars):")
    bb = block_bootstrap(net, BPY)
    for k, v in bb.items(): print(f"  {k}: {v:.4f}")

    # plots
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=False)
    eq.plot(ax=axes[0], label=f"{best_name} WFO OOS")
    (1+bh_net).cumprod().plot(ax=axes[0], label="Buy&Hold", alpha=.6)
    (1+sma_net.loc[net.index]).cumprod().plot(ax=axes[0], label="SMA200 L/S", alpha=.6)
    axes[0].legend(); axes[0].set_title("WFO OOS Equity Curves (cost=1.0pip)"); axes[0].grid(alpha=.3)
    dd = eq/eq.cummax()-1
    dd.plot(ax=axes[1], color="crimson"); axes[1].set_title("OOS Drawdown"); axes[1].grid(alpha=.3)
    fold_df.set_index("test_end")["sharpe"].plot(kind="bar", ax=axes[2], color=np.where(fold_df["sharpe"]>0,"seagreen","indianred"))
    axes[2].set_title("Fold-by-fold OOS Sharpe"); axes[2].grid(alpha=.3)
    axes[2].set_xticklabels([pd.Timestamp(t).strftime("%Y-%m") for t in fold_df["test_end"]], rotation=60, fontsize=7)
    plt.tight_layout()
    plt.savefig("/home/claude/wfo_results.png", dpi=110)
    print("\nSaved plot: wfo_results.png")

    # cross-timeframe sanity check: run best strategy spec on H1
    print("\n" + "="*80); print("6. CROSS-TIMEFRAME CHECK (H1, same strategy family)"); print("="*80)
    dfh1 = create_features(data["H1"])
    bpd1 = len(dfh1) / ((dfh1.index[-1]-dfh1.index[0]).days * 5/7)
    BPY1 = round(bpd1*252)
    fold1, net1, pe1 = walk_forward_optimization(dfh1, best_name, BPY1)
    st1 = evaluate_performance(net1, pe1, BPY1)
    print(f"H1 WFO OOS: ann={st1['annual_return']:.3f} sharpe={st1['sharpe']:.2f} maxdd={st1['max_dd']:.3f} trades={st1['n_trades']} pos_folds={(fold1['total_return']>0).mean():.0%}")

    fold_df.to_csv("/home/claude/fold_results.csv", index=False)
    print("\nDone.")

if __name__ == "__main__":
    main()
