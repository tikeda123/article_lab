"""
Experiment 2: レジーム別の条件付き相関

記事:「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク
レジームスイッチする5資産の人工データを生成し、全期間 / 通常日 / 市場上位10%日 /
市場下位10%日 の平均ペア相関とヒートマップを比較する。
実データで試す場合は df を自分のリターン DataFrame に差し替えるだけでよい。

出力: figs/fig2_regime_corr.png
実行: python exp2_regime_correlation.py
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

n_days = 2500
n_assets = 5
names = ["A", "B", "C", "D", "E"]

# レジームスイッチング: 通常(95%) は共通因子の負荷が小さい、
# ストレス(5%) は共通因子の負荷が大きく、共通因子自身のボラも高い
stress = rng.random(n_days) < 0.05

beta_normal = np.array([0.35, 0.30, 0.40, 0.25, 0.35])
beta_stress = np.array([0.95, 0.90, 1.00, 0.85, 0.95])

f = np.where(stress, rng.standard_normal(n_days) * 3.0 - 1.2,
             rng.standard_normal(n_days) * 1.0)
idio = rng.standard_normal((n_days, n_assets)) * 1.0

B = np.where(stress[:, None], beta_stress[None, :], beta_normal[None, :])
R = B * f[:, None] + idio
R = R / 100.0  # 日次リターン（%→小数）

df2 = pd.DataFrame(R, columns=names)

# ---------------------------------------------------------------------
# 実データで試す場合は、上のブロックを丸ごと次に置き換える:
#
#   df2 = your_returns_df          # index=日付, columns=資産名, 値=日次リターン
#   df2 = df2.sort_index().dropna(how="any")
#
# 注意:
#   - 日付を揃えること。市場ごとに休場日が違うと、片方だけ欠けた日が
#     「動かなかった日」として相関を薄める。dropna(how="any") で共通営業日に揃える。
#   - リターンの頻度を揃えること（日次なら全資産日次）。混在すると相関は無意味になる。
#   - 価格ではなくリターンを渡すこと。
# ---------------------------------------------------------------------

# 以降のコードは資産数・列名をDataFrameから取得するので、任意の資産数で動く
names = df2.columns.tolist()
n_assets = df2.shape[1]

# 市場リターンの代理として等ウェイト平均を使う。
# ベンチマーク（TOPIX、S&P500など）がある場合はそれに置き換えたほうが解釈しやすい。
mkt = df2.mean(axis=1)

def corr_summary(d, label):
    c = d.corr().values
    off = c[np.triu_indices_from(c, k=1)]
    print(f"{label:<28} n={len(d):>5}  平均相関={off.mean():.3f}  "
          f"最小={off.min():.3f} 最大={off.max():.3f}")
    return c

c_all = corr_summary(df2, "全期間")
q10 = mkt.quantile(0.10)
q90 = mkt.quantile(0.90)
c_norm = corr_summary(df2[(mkt > q10) & (mkt < q90)], "通常日(中央80%)")
c_dn = corr_summary(df2[mkt <= q10], "市場下位10%日")
c_up = corr_summary(df2[mkt >= q90], "市場上位10%日")
print()

fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
for ax, c, t in zip(axes, [c_all, c_norm, c_dn],
                    ["全期間", "通常日（中央80%）", "市場下位10%日"]):
    im = ax.imshow(c, vmin=-0.2, vmax=1, cmap="RdYlBu_r")
    ax.set_xticks(range(n_assets)); ax.set_xticklabels(names)
    ax.set_yticks(range(n_assets)); ax.set_yticklabels(names)
    ax.set_title(t)
    ax.grid(False)
    for i in range(n_assets):
        for j in range(n_assets):
            ax.text(j, i, f"{c[i,j]:.2f}", ha="center", va="center",
                    fontsize=8, color="black")
fig.colorbar(im, ax=axes, shrink=0.85, label="相関")
fig.suptitle("同じ資産・同じ期間でも、条件を切り替えると相関構造は変わる", y=1.02)
fig.savefig(f"{OUT}/fig2_regime_corr.png", bbox_inches="tight")
plt.close(fig)

print(f"\n図を出力しました: {OUT}")
