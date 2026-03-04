import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

np.random.seed(42)

# Fixed parameters
days = 90
beta_c = 30
importance = 0.5
B = 1 + (importance * 2)
floor_regular = 0.02
floor_core = 0.60
core_stability_threshold = 0.85
core_access_threshold = 10
core_session_threshold = 3
session_length = 14  # new session every 14 days

n_runs = 500
# Mean 12 retrievals over 90 days (like the deterministic case), but randomised
mean_retrievals = 12

final_stab_d = []
final_stab_a = []
promoted_d_count = 0
promoted_a_count = 0
promotion_days_d = []
all_stab_d = np.zeros((n_runs, days))
all_stab_a = np.zeros((n_runs, days))
all_ret_d = np.zeros((n_runs, days))
all_ret_a = np.zeros((n_runs, days))

for run in range(n_runs):
    # Generate random retrieval days: Poisson-like, ~12 events in 90 days
    n_retrievals = np.random.poisson(mean_retrievals)
    n_retrievals = max(3, min(n_retrievals, 25))  # clamp to reasonable range
    retrieval_days = sorted(np.random.choice(range(1, days + 1), size=n_retrievals, replace=False))

    stab_d = 0.1
    stab_a = 0.1
    last_d = 0
    last_a = 0
    acc_d = 0
    acc_a = 0
    sess_d = set()
    sess_a = set()
    prom_d = False
    prom_a = False
    prom_day_d = None

    for day in range(1, days + 1):
        current_session = (day - 1) // session_length + 1

        fl_d = floor_core if prom_d else floor_regular
        fl_a = floor_core if prom_a else floor_regular

        dt_d = day - last_d
        dt_a = day - last_a
        R_d = max(fl_d, np.exp(-dt_d / (max(stab_d, 0.001) * B * beta_c)))
        R_a = max(fl_a, np.exp(-dt_a / (max(stab_a, 0.001) * B * beta_c)))

        if day in retrieval_days:
            gap_d = min(2.0, dt_d / 7)
            stab_d = min(1.0, stab_d + 0.1 * gap_d)
            last_d = day
            acc_d += 1
            sess_d.add(current_session)
            R_d = 1.0

            gap_a = min(2.0, dt_a / 7)
            stab_a = min(1.0, stab_a + 0.03 * gap_a)
            last_a = day
            acc_a += 1
            sess_a.add(current_session)
            R_a = 1.0

            if (not prom_d and stab_d >= core_stability_threshold
                    and acc_d >= core_access_threshold
                    and len(sess_d) >= core_session_threshold):
                prom_d = True
                prom_day_d = day

            if (not prom_a and stab_a >= core_stability_threshold
                    and acc_a >= core_access_threshold
                    and len(sess_a) >= core_session_threshold):
                prom_a = True

        all_stab_d[run, day - 1] = stab_d
        all_stab_a[run, day - 1] = stab_a
        all_ret_d[run, day - 1] = R_d
        all_ret_a[run, day - 1] = R_a

    final_stab_d.append(stab_d)
    final_stab_a.append(stab_a)
    if prom_d:
        promoted_d_count += 1
        promotion_days_d.append(prom_day_d)
    if prom_a:
        promoted_a_count += 1

pct_d = 100 * promoted_d_count / n_runs
pct_a = 100 * promoted_a_count / n_runs

print(f"=== Monte Carlo Results ({n_runs} runs) ===")
print(f"Direct:  core promotion rate = {pct_d:.1f}% ({promoted_d_count}/{n_runs})")
print(f"Assoc:   core promotion rate = {pct_a:.1f}% ({promoted_a_count}/{n_runs})")
print(f"Direct:  final stability = {np.mean(final_stab_d):.3f} ± {np.std(final_stab_d):.3f}")
print(f"Assoc:   final stability = {np.mean(final_stab_a):.3f} ± {np.std(final_stab_a):.3f}")
if promotion_days_d:
    print(f"Direct:  median promotion day = {np.median(promotion_days_d):.0f} (IQR: {np.percentile(promotion_days_d, 25):.0f}-{np.percentile(promotion_days_d, 75):.0f})")

# --- Figure ---
x = np.arange(1, days + 1)
mean_d = np.mean(all_stab_d, axis=0)
mean_a = np.mean(all_stab_a, axis=0)
p10_d = np.percentile(all_stab_d, 10, axis=0)
p90_d = np.percentile(all_stab_d, 90, axis=0)
p10_a = np.percentile(all_stab_a, 10, axis=0)
p90_a = np.percentile(all_stab_a, 90, axis=0)

fig, axes = plt.subplots(2, 2, figsize=(10, 7), gridspec_kw={'width_ratios': [3, 1], 'hspace': 0.35, 'wspace': 0.25})

# --- Top left: Stability trajectories with confidence bands ---
ax = axes[0, 0]
ax.fill_between(x, p10_d, p90_d, color='#2563eb', alpha=0.15, label='Direct (10th–90th pctl)')
ax.fill_between(x, p10_a, p90_a, color='#dc2626', alpha=0.15, label='Assoc. (10th–90th pctl)')
ax.plot(x, mean_d, color='#2563eb', linewidth=2, label='Direct (mean)')
ax.plot(x, mean_a, color='#dc2626', linewidth=2, label='Assoc. (mean)')
ax.axhline(core_stability_threshold, color='#16a34a', linewidth=1.5, linestyle='--',
           label=f'Core threshold ({core_stability_threshold})')
ax.set_ylabel('Stability  $S(m)$', fontsize=11)
ax.set_xlabel('Days', fontsize=11)
ax.set_ylim(0, 1.08)
ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
ax.set_title(f'Stability over time ({n_runs} randomised schedules)', fontsize=11)

# --- Top right: Final stability distributions ---
ax = axes[0, 1]
ax.hist(final_stab_d, bins=25, color='#2563eb', alpha=0.6, orientation='horizontal', label='Direct')
ax.hist(final_stab_a, bins=25, color='#dc2626', alpha=0.6, orientation='horizontal', label='Associative')
ax.axhline(core_stability_threshold, color='#16a34a', linewidth=1.5, linestyle='--')
ax.set_xlabel('Count', fontsize=10)
ax.set_ylim(0, 1.08)
ax.set_title('Final $S(m)$ at day 90', fontsize=10)
ax.legend(fontsize=8)

# --- Bottom left: Promotion day distribution ---
ax = axes[1, 0]
if promotion_days_d:
    ax.hist(promotion_days_d, bins=range(1, days + 2, 3), color='#16a34a', alpha=0.7, edgecolor='white')
    ax.axvline(np.median(promotion_days_d), color='#166534', linewidth=2, linestyle='--',
               label=f'Median: day {np.median(promotion_days_d):.0f}')
ax.set_xlabel('Day of core promotion', fontsize=11)
ax.set_ylabel('Count', fontsize=11)
ax.set_xlim(1, days)
ax.set_title(f'Core promotion timing (direct only, {promoted_d_count}/{n_runs} runs)', fontsize=11)
ax.legend(fontsize=9)

# --- Bottom right: Promotion rates ---
ax = axes[1, 1]
bars = ax.bar(['Direct', 'Assoc.'], [pct_d, pct_a], color=['#2563eb', '#dc2626'], width=0.5, edgecolor='white')
ax.set_ylabel('Core promotion rate (%)', fontsize=10)
ax.set_ylim(0, 105)
ax.set_title('Promotion rate', fontsize=10)
for bar, val in zip(bars, [pct_d, pct_a]):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
            f'{val:.1f}%', ha='center', fontsize=11, fontweight='bold')

fig.suptitle('Monte Carlo Analysis: Two-Tier Boosting Under Randomised Retrieval', fontsize=13, fontweight='bold', y=1.01)
plt.savefig('/home/claude/paper/monte_carlo.pdf', bbox_inches='tight', dpi=300)
plt.savefig('/home/claude/paper/monte_carlo.png', bbox_inches='tight', dpi=300)
print("\nFigures saved.")
