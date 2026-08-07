"""
Experiment 3: 標本分散の推定安定性

記事:「分散したつもり」の罠 — 共分散とファットテールから考えるポートフォリオリスク

(a) 日次0.3%の低ボラ系列999日に、1000日目として -15% を1回だけ追加し、標本ボラの変化を測る。
(b) 正規分布と Student-t(ν=3) から標本標準偏差の収束を比較する。
    ν=3 は母分散が有限なので標本SDは一致推定量であり、標本数を増やせば母SDへ収束する。
    ただし4次モーメントが無限なので、標本分散の標本分布の分散が有限にならず、
    通常の √n 正規近似や分散ベースの誤差評価が使えない。
    ここでは複数シードで中央値と5-95%レンジの幅の推移を出力し、
    「収束はするが、正規分布より遅く不規則で、有限標本の不確実性が大きい」ことを示す。
(c) 参考として ν=1.5（母分散が存在しない）を並べ、(b) の「遅い収束」と
    「そもそも収束しない」を区別する。

出力: figs/fig3_sample_var.png
実行: python exp3_sample_variance_stability.py
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
# (a) 単発ショックが標本ボラに与える影響
# =====================================================================
print("=" * 72)
print("(a) 1日だけ -15% を加えると標本ボラはどうなるか")
print("=" * 72)
n = 1000
base = rng.standard_normal(n - 1) * 0.003  # 日次0.3%
vol_before = base.std(ddof=1) * np.sqrt(252)
shocked = np.append(base, -0.15)
vol_after = shocked.std(ddof=1) * np.sqrt(252)
print(f"999日までの年率ボラ : {vol_before*100:.2f}%")
print(f"1000日目に -15% 追加: {vol_after*100:.2f}%")
print(f"倍率               : {vol_after/vol_before:.2f}x")
print()

# =====================================================================
# (b)(c) 標本標準偏差の収束：Normal vs Student-t
# =====================================================================
N_PATHS = 4000
N_MAX = 8000
CHECKPOINTS = [100, 250, 500, 1000, 2000, 4000, 8000]
SEEDS = [42, 43, 44]


def running_std(paths):
    cs = np.cumsum(paths, axis=1)
    cs2 = np.cumsum(paths ** 2, axis=1)
    k = np.arange(1, paths.shape[1] + 1)
    var = (cs2 - cs ** 2 / k) / np.maximum(k - 1, 1)
    return np.sqrt(np.maximum(var, 0))


def gen(kind, r, n_paths, n_max):
    """母標準偏差が1になるよう正規化した系列を生成"""
    if kind == "normal":
        return r.standard_normal((n_paths, n_max))
    nu = kind
    if nu > 2:                                  # 母分散が有限 → 分散1に正規化
        return r.standard_t(nu, size=(n_paths, n_max)) / np.sqrt(nu / (nu - 2))
    return r.standard_t(nu, size=(n_paths, n_max))   # 母分散なし（正規化不能）


# 複数シードで中央値・5-95%幅を集計する
agg = {k: {c: {"med": [], "width": [], "lo": [], "hi": []} for c in CHECKPOINTS}
       for k in ["normal", 3.0, 1.5]}
paths_for_plot = {}

for si, seed in enumerate(SEEDS):
    for kind in ["normal", 3.0, 1.5]:
        r = np.random.default_rng(seed * 100 + (0 if kind == "normal" else int(kind * 10)))
        rs = running_std(gen(kind, r, N_PATHS, N_MAX))
        if si == 0:
            paths_for_plot[kind] = rs[:80]
        for c in CHECKPOINTS:
            col = rs[:, c - 1]
            lo, hi = np.percentile(col, [5, 95])
            agg[kind][c]["med"].append(np.median(col))
            agg[kind][c]["lo"].append(lo)
            agg[kind][c]["hi"].append(hi)
            agg[kind][c]["width"].append(hi - lo)
        del rs

label = {"normal": "正規分布", 3.0: "Student-t (ν=3)", 1.5: "Student-t (ν=1.5)"}

print("=" * 72)
print(f"(b) 標本標準偏差の 5-95% レンジ（{len(SEEDS)}シードの平均、各{N_PATHS}パス）")
print("=" * 72)
print(f"{'サンプル数':>10} | {'正規分布':^24} | {'Student-t (ν=3)':^24}")
print(f"{'':>10} | {'レンジ':^15}{'幅':>9} | {'レンジ':^15}{'幅':>9}")
for c in CHECKPOINTS:
    out = f"{c:>10} |"
    for kind in ["normal", 3.0]:
        a = agg[kind][c]
        out += (f" [{np.mean(a['lo']):.3f}, {np.mean(a['hi']):.3f}]"
                f" {np.mean(a['width']):>8.3f} |")
    print(out)
print()
print("→ ν=3 でもレンジは縮み続ける（標本SDは一致推定量）。")
print("  ただし縮み方は正規分布よりはるかに遅く、シード間のばらつきも大きい。")
print()

print("=" * 72)
print("(c) 参考: ν=1.5 は母分散が存在しない → 標本SDは収束しない")
print("=" * 72)
print(f"{'サンプル数':>10} {'中央値':>10} {'5-95%レンジ':>22}")
for c in CHECKPOINTS:
    a = agg[1.5][c]
    print(f"{c:>10} {np.mean(a['med']):>10.3f}   "
          f"[{np.mean(a['lo']):.3f}, {np.mean(a['hi']):.3f}]")
print()
print("→ 中央値がサンプル数とともに増え続ける。収束先が存在しない。")
print("  ν=3 の『遅い収束』と ν=1.5 の『非収束』は別の現象である。")
print()

# --- 図 ---
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
x = np.arange(1, N_MAX + 1)
for ax, kind in zip(axes, ["normal", 3.0, 1.5]):
    rs = paths_for_plot[kind]
    for i in range(len(rs)):
        ax.plot(x, rs[i], color="gray", alpha=0.15, lw=0.6)
    ax.plot(x, np.median(rs, axis=0), color=RED, lw=2, label="中央値")
    if kind != 1.5:
        ax.axhline(1.0, color="black", ls="--", lw=1, label="母標準偏差 = 1")
    ax.set_xscale("log")
    ax.set_xlabel("サンプル数（対数軸）")
    sub = "母分散あり" if kind != 1.5 else "母分散なし → 収束先が存在しない"
    ax.set_title(f"{label[kind]}\n（{sub}）", fontsize=10)
    if kind == 1.5:
        ax.set_yscale("log")
        ax.set_ylim(0.05, 300)
        ax.set_ylabel("標本標準偏差（対数軸）")
    else:
        ax.set_ylim(0, 2.2)
axes[0].set_ylabel("標本標準偏差")
axes[0].legend(fontsize=8)
axes[2].legend(fontsize=8)
fig.suptitle("分散が有限でも、標本標準偏差の収束は速いとは限らない")
fig.tight_layout()
fig.savefig(f"{OUT}/fig3_sample_var.png", bbox_inches="tight")
plt.close(fig)

print(f"図を出力しました: {OUT}")
