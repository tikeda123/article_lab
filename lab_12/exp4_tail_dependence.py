"""
Experiment 4: 低相関 × テール依存

記事:「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク

(a) 通常時はほぼ独立に動き、まれに共通のリスクオフ要因で同時に落ちる2資産を生成する。
    比較対象として、同じ平均・分散・Pearson相関を母数に設定した二変量正規からもデータを作り、
    条件付きテール確率 / 下方相関 / Joint ES / 等ウェイトPFの最悪日 を比較する。
(b) その「共同暴落」を、実データで手元にある程度のサンプル数（250〜5000日）から
    推定できるかを検証する。テール依存の推定がどれだけ不安定かを見る。

出力: figs/fig4_tail_dependence.png, figs/fig4b_estimation_instability.png
実行: python exp4_tail_dependence.py
"""
import os
import numpy as np
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

# =====================================================================
# (a) 神の視点：40,000日（約160年）分のデータを生成して真の姿を見る
# =====================================================================
n = 40_000
p_joint = 0.005          # 各営業日に0.5% → 平均すると約200営業日に1日
                         #                  （1000営業日なら約5日）
sigma_day = 0.02         # 通常日の日次ボラ 2%

joint = rng.random(n) < p_joint

# 通常日：それぞれ独自の理由で動く（独立）
a_normal = rng.standard_normal(n) * sigma_day
b_normal = rng.standard_normal(n) * sigma_day

# リスクオフ日：共通のグローバル要因 g に、資産ごとの感応度と固有ノイズが乗る
#   g は指数分布 → 「軽いリスクオフ」から「歴史的暴落」まで連続的に分布する
g = -rng.exponential(scale=0.07, size=n) - 0.02
beta_a = 0.8 + rng.random(n) * 0.5
beta_b = 0.8 + rng.random(n) * 0.5
a_shock = beta_a * g + rng.standard_normal(n) * sigma_day * 0.6
b_shock = beta_b * g + rng.standard_normal(n) * sigma_day * 0.6

A = np.where(joint, a_shock, a_normal)
B = np.where(joint, b_shock, b_normal)

# 比較用：人工データの標本平均・標本共分散を「母数として設定した」二変量正規。
#   新しい有限標本なので、実現相関・実現ボラは完全一致ではなくほぼ一致になる。
rho_emp = np.corrcoef(A, B)[0, 1]
cov = np.array([[A.var(), rho_emp * A.std() * B.std()],
                [rho_emp * A.std() * B.std(), B.var()]])
G = rng.multivariate_normal([A.mean(), B.mean()], cov, size=n)
GA, GB = G[:, 0], G[:, 1]


def tail_dep(x, y, q):
    """下側テール依存の経験推定 P(B <= q分位 | A <= q分位)"""
    tx, ty = np.percentile(x, q), np.percentile(y, q)
    mask = x <= tx
    if mask.sum() == 0:
        return np.nan
    return (y[mask] <= ty).mean()


def summary(x, y, label):
    pf = (x + y) / 2
    tx, ty = np.percentile(x, 1), np.percentile(y, 1)
    both = (x <= tx) & (y <= ty)
    dn = (x < np.median(x)) & (y < np.median(y))
    print(label)
    print(f"  Pearson相関                        : {np.corrcoef(x, y)[0,1]:+.3f}")
    for q in [10, 5, 1, 0.5]:
        print(f"  P(B<={q:>4}%タイル | A<={q:>4}%タイル)  : {tail_dep(x, y, q):.3f}"
              f"   (独立なら {q/100:.3f})")
    print(f"  下方相関（両者が中央値未満の日）   : {np.corrcoef(x[dn], y[dn])[0,1]:+.3f}")
    print(f"  Joint ES（両者1%テール日のPF平均） : {pf[both].mean()*100:>6.2f}%  該当 {both.sum()} 日")
    print(f"  等ウェイトPF 年率ボラ              : {pf.std()*np.sqrt(252)*100:>6.2f}%")
    print(f"  等ウェイトPF ES(1%) 日次           : {pf[pf <= np.percentile(pf,1)].mean()*100:>6.2f}%")
    print(f"  等ウェイトPF 最悪日                : {pf.min()*100:>6.2f}%")


print("=" * 72)
print("(a) 40,000日（約160年）分のデータで見た「真の姿」")
print("=" * 72)
summary(A, B, "[人工データ] 通常時は独立 + まれに共通のリスクオフ要因")
print()
summary(GA, GB, "[比較] 同じ平均・分散・Pearson相関を持つ二変量正規")
print()

# --- 散布図 ---
fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharex=True, sharey=True)
for ax, (x, y), t in zip(axes, [(A, B), (GA, GB)],
                         ["人工データ（まれな共通リスクオフ要因）",
                          "同じ相関の二変量正規"]):
    ax.scatter(x * 100, y * 100, s=4, alpha=0.2, color="#1f77b4")
    ax.axvline(np.percentile(x, 1) * 100, color=RED, ls="--", lw=1)
    ax.axhline(np.percentile(y, 1) * 100, color=RED, ls="--", lw=1)
    ax.set_xlabel("資産A 日次リターン (%)")
    ax.set_title(t)
axes[0].set_ylabel("資産B 日次リターン (%)")
axes[0].text(0.03, 0.03, "赤破線 = 各資産の1%タイル", transform=axes[0].transAxes,
             fontsize=8, color=RED)
fig.suptitle(f"Pearson相関はどちらも約 {rho_emp:.2f} — だが左下の伸び方が違う")
fig.tight_layout()
fig.savefig(f"{OUT}/fig4_tail_dependence.png", bbox_inches="tight")
plt.close(fig)

# =====================================================================
# (b) 実データの現実：手元のサンプル数でテール依存を推定できるか
# =====================================================================
print("=" * 72)
print("(b) サンプル数を絞ったときの、テール依存の推定精度")
print("=" * 72)

true_lambda = tail_dep(A, B, 1.0)
print(f"真値の目安（40,000日から推定した λ(1%)）: {true_lambda:.3f}")
print()

n_trials = 500
windows = [250, 500, 1000, 2000, 5000]
results = {}

print(f"{'サンプル数':>10} {'年数':>7} {'中央値':>8} {'5-95%レンジ':>20} {'ゼロと推定':>12}")
for T in windows:
    est = []
    for _ in range(n_trials):
        s = rng.integers(0, n - T)
        est.append(tail_dep(A[s:s + T], B[s:s + T], 1.0))
    est = np.array(est)
    results[T] = est
    lo, hi = np.percentile(est, [5, 95])
    print(f"{T:>10} {T/252:>6.1f}年 {np.median(est):>8.3f} "
          f"   [{lo:.3f}, {hi:.3f}]   {(est == 0).mean()*100:>10.1f}%")
print()

# --- 推定不安定性の図 ---
fig, ax = plt.subplots(figsize=(9, 5))
positions = np.arange(len(windows))
ax.boxplot([results[T] for T in windows], positions=positions, widths=0.55,
           showfliers=False,
           medianprops=dict(color=RED, lw=2),
           boxprops=dict(color="#333333"),
           whiskerprops=dict(color="#333333"),
           capprops=dict(color="#333333"))
for i, T in enumerate(windows):
    jitter = (rng.random(len(results[T])) - 0.5) * 0.35
    ax.scatter(positions[i] + jitter, results[T], s=6, alpha=0.15, color="#1f77b4")
ax.axhline(true_lambda, color="black", ls="--", lw=1.2,
           label=f"40,000日から推定した値 = {true_lambda:.2f}")
ax.set_xticks(positions)
ax.set_xticklabels([f"{T}日\n({T/252:.0f}年)" for T in windows])
ax.set_xlabel("推定に使ったサンプル数")
ax.set_ylabel("推定されたテール依存 λ(1%)")
ax.set_title("同じデータ生成過程でも、手元のサンプル数で推定値は大きくばらつく")
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT}/fig4b_estimation_instability.png", bbox_inches="tight")
plt.close(fig)

print(f"\n図を出力しました: {OUT}")
