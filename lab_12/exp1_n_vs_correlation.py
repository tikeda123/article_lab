"""
Experiment 1: 銘柄数 N × 共通相関 ρ

記事:「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク
同一ボラ・等ウェイト・等相関の N 資産で σp/σ = sqrt(ρ + (1-ρ)/N) を計算し、
銘柄数を増やしても共通相関が正ならリスクに下限が残ることを図示する。
2資産50:50の相関別ボラ表も併せて出力する。

出力: figs/fig1_n_vs_rho.png
実行: python exp1_n_vs_correlation.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 日本語フォント（環境に応じて Meiryo / Hiragino Sans / IPAexGothic などに変更）
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130
plt.rcParams["savefig.dpi"] = 130
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

RED = "#EE0000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)

def port_vol_ratio(n, rho):
    """同一ボラ・等ウェイト・等相関のN資産の σp/σ"""
    return np.sqrt(rho + (1.0 - rho) / n)

Ns = np.arange(1, 101)
rhos = [0.0, 0.2, 0.5, 0.8]

fig, ax = plt.subplots(figsize=(8, 5))
colors = ["#1f77b4", "#2ca02c", "#ff7f0e", RED]
for rho, c in zip(rhos, colors):
    ax.plot(Ns, [port_vol_ratio(n, rho) * 20 for n in Ns],
            label=f"ρ = {rho}", color=c, lw=2)
    ax.axhline(np.sqrt(rho) * 20, color=c, ls=":", lw=1, alpha=0.7)

ax.set_xlabel("銘柄数 N")
ax.set_ylabel("ポートフォリオ年率ボラ (%)  ※各資産20%")
ax.set_title("銘柄数を増やしても、共通相関が正なら下限が残る")
ax.set_ylim(0, 21)
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT}/fig1_n_vs_rho.png")
plt.close(fig)

rows = []
for n in [1, 2, 5, 10, 20, 50, 100, 1000]:
    rows.append({"N": n, **{f"rho={r}": f"{port_vol_ratio(n, r)*20:.2f}%" for r in rhos}})
df1 = pd.DataFrame(rows)
print(df1.to_string(index=False))
print()
print("下限 (N→∞):", {f"rho={r}": f"{np.sqrt(r)*20:.2f}%" for r in rhos})
print()

# 2資産の相関別ボラ表
print("--- 2資産50:50 各ボラ20% ---")
for rho in [1.0, 0.5, 0.0, -0.5, -1.0]:
    v = np.sqrt(max(0.0, 0.25*0.04 + 0.25*0.04 + 2*0.5*0.5*0.2*0.2*rho))
    print(f"rho = {rho:+.1f} -> {v*100:.1f}%")
print()

print(f"\n図を出力しました: {OUT}")
