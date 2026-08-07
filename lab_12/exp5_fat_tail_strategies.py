"""
Experiment 5: 同じ平均・同じ標準偏差、違う壊れ方

記事:「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク

対称戦略 A とショートボラ型戦略 B を生成する。
戦略Aは、標準正規乱数を「標本平均0・標本SD1」に再標準化したうえで戦略Bの実現平均・
実現SDへ合わせる。これにより実現日次平均と実現日次SDが厳密に一致し、
リスクフリー0のSharpeも定義上一致する。つまり両者の差はすべて「分布の形」に由来する。

比較する指標:
  Sharpe / 勝率 / 歪度 / 尖度 / ES(5%) / ES(1%) / 最悪の1日 /
  1日・5日・20日の最大損失 / 最大DD / 最大DD所要日数 /
  最大DD区間内の最悪1日が占める割合（対数損失ベース）

出力: figs/fig5_fat_tail_strategies.png
実行: python exp5_fat_tail_strategies.py
"""
import os
import numpy as np
from scipy import stats
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

n = 2000

# --- 戦略B: 普段は小さく勝つ／まれに大損（ショートボラ・キャリー型） ---
p_blow = 0.0025
blow = rng.random(n) < p_blow
retB = np.where(blow,
                -0.20 + rng.standard_normal(n) * 0.03,
                0.0012 + rng.standard_normal(n) * 0.0015)

# --- 戦略A: 対称。実現平均・実現SDを厳密に戦略Bへ合わせる ---
z = rng.standard_normal(n)
z = (z - z.mean()) / z.std(ddof=1)          # 標本平均0・標本SD1に再標準化
retA = z * retB.std(ddof=1) + retB.mean()

assert abs(retA.mean() - retB.mean()) < 1e-12
assert abs(retA.std(ddof=1) - retB.std(ddof=1)) < 1e-12


def max_loss_over(r, w):
    """w日間の累積リターンの最小値（複利）"""
    if w == 1:
        return r.min()
    logc = np.concatenate([[0.0], np.cumsum(np.log1p(r))])
    return np.exp(np.min(logc[w:] - logc[:-w])) - 1.0


def strat_stats(r, label):
    eq = np.cumprod(1 + r)
    dd = eq / np.maximum.accumulate(eq) - 1

    # 最大DDのピーク〜ボトム区間を特定する
    dd_end = int(np.argmin(dd))
    dd_start = int(np.argmax(eq[:dd_end + 1]))
    seg = r[dd_start + 1:dd_end + 1]          # 区間内の日次リターン

    # 区間内の最悪1日が、区間全体の対数損失に占める割合
    #   （対数なら加法的に分解できるので、寄与率として定義できる）
    seg_log_loss = -np.log1p(seg).sum()
    worst_in_seg = seg.min()
    share = (-np.log1p(worst_in_seg)) / seg_log_loss * 100 if seg_log_loss > 0 else np.nan

    print(label)
    print(f"  年率リターン        : {(eq[-1] ** (252/len(r)) - 1)*100:>8.2f}%")
    print(f"  年率ボラ            : {r.std(ddof=1)*np.sqrt(252)*100:>8.2f}%")
    print(f"  Sharpe (rf=0)       : {r.mean()/r.std(ddof=1)*np.sqrt(252):>8.2f}")
    print(f"  勝率                : {(r>0).mean()*100:>8.2f}%")
    print(f"  歪度                : {stats.skew(r):>8.2f}")
    print(f"  尖度(超過)          : {stats.kurtosis(r):>8.2f}")
    print(f"  ES(5%) 日次         : {r[r <= np.percentile(r, 5)].mean()*100:>8.2f}%")
    print(f"  ES(1%) 日次         : {r[r <= np.percentile(r, 1)].mean()*100:>8.2f}%")
    print(f"  最大損失  1日       : {max_loss_over(r, 1)*100:>8.2f}%")
    print(f"  最大損失  5日       : {max_loss_over(r, 5)*100:>8.2f}%")
    print(f"  最大損失 20日       : {max_loss_over(r, 20)*100:>8.2f}%")
    print(f"  最大DD              : {dd.min()*100:>8.2f}%")
    print(f"  最大DD区間          : {dd_start} 〜 {dd_end} 日目 ({dd_end-dd_start} 日)")
    print(f"  最大DD区間内の最悪1日: {worst_in_seg*100:>8.2f}%")
    print(f"  └ 区間の対数損失に占める割合: {share:>6.1f}%")
    print(f"  （参考）全期間の最悪日 : {r.min()*100:>6.2f}%  ({int(np.argmin(r))} 日目)")
    return eq


eqA = strat_stats(retA, "戦略A（対称）")
print()
eqB = strat_stats(retB, "戦略B（ショートボラ型）")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].plot(eqA, label="戦略A（対称）", color="#1f77b4", lw=1.6)
axes[0].plot(eqB, label="戦略B（ショートボラ型）", color=RED, lw=1.6)
axes[0].set_yscale("log")
axes[0].set_xlabel("日"); axes[0].set_ylabel("累積（対数軸）")
axes[0].set_title("エクイティカーブ")
axes[0].legend()

bins = np.linspace(-0.30, 0.06, 140)
axes[1].hist(retA, bins=bins, alpha=0.55, label="戦略A", color="#1f77b4")
axes[1].hist(retB, bins=bins, alpha=0.55, label="戦略B", color=RED)
axes[1].set_yscale("log")
axes[1].set_xlabel("日次リターン"); axes[1].set_ylabel("頻度（対数軸）")
axes[1].set_title("リターン分布 — 平均も標準偏差も一致している")
axes[1].legend()
axes[1].annotate("戦略Bのテール", xy=(-0.22, 1.5), xytext=(-0.26, 40),
                 fontsize=9, color=RED,
                 arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
fig.suptitle("同じ平均・同じ年率ボラ・同じSharpeでも、損失の形は同じではない")
fig.tight_layout()
fig.savefig(f"{OUT}/fig5_fat_tail_strategies.png", bbox_inches="tight")
plt.close(fig)

print(f"\n図を出力しました: {OUT}")
