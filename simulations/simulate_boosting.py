import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

days = 90
stability_direct = 0.1
stability_assoc = 0.1
beta_c = 30
importance = 0.5
B = 1 + (importance * 2)
floor_regular = 0.02
floor_core = 0.60
core_stability_threshold = 0.85
core_access_threshold = 10
core_session_threshold = 3

retrieval_days = sorted(range(7, days + 1, 7))
session_boundaries = set(range(1, days + 1, 14))

last_access_d = 0; last_access_a = 0
access_count_d = 0; access_count_a = 0
sessions_d = set(); sessions_a = set()
current_session = 0
promoted_d = False; promoted_a = False
promotion_day_d = None

hist_stab_d, hist_stab_a = [], []
hist_ret_d, hist_ret_a = [], []
hist_floor_d, hist_floor_a = [], []

for day in range(1, days + 1):
    if day in session_boundaries:
        current_session += 1

    floor_d = floor_core if promoted_d else floor_regular
    floor_a = floor_core if promoted_a else floor_regular

    dt_d = day - last_access_d
    dt_a = day - last_access_a
    R_d = max(floor_d, np.exp(-dt_d / (max(stability_direct, 0.001) * B * beta_c)))
    R_a = max(floor_a, np.exp(-dt_a / (max(stability_assoc, 0.001) * B * beta_c)))

    if day in retrieval_days:
        gap_d = min(2.0, dt_d / 7)
        stability_direct = min(1.0, stability_direct + 0.1 * gap_d)
        last_access_d = day; access_count_d += 1; sessions_d.add(current_session)
        R_d = 1.0

        gap_a = min(2.0, dt_a / 7)
        stability_assoc = min(1.0, stability_assoc + 0.03 * gap_a)
        last_access_a = day; access_count_a += 1; sessions_a.add(current_session)
        R_a = 1.0

        if (not promoted_d and stability_direct >= core_stability_threshold
                and access_count_d >= core_access_threshold
                and len(sessions_d) >= core_session_threshold):
            promoted_d = True; promotion_day_d = day; floor_d = floor_core

        if (not promoted_a and stability_assoc >= core_stability_threshold
                and access_count_a >= core_access_threshold
                and len(sessions_a) >= core_session_threshold):
            promoted_a = True; floor_a = floor_core

    hist_stab_d.append(stability_direct)
    hist_stab_a.append(stability_assoc)
    hist_ret_d.append(R_d); hist_ret_a.append(R_a)
    hist_floor_d.append(floor_d); hist_floor_a.append(floor_a)

x = np.arange(1, days + 1)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True,
                                gridspec_kw={'hspace': 0.28})
fig.suptitle('Two-Tier Retrieval Boosting: Direct vs. Associative', fontsize=13, fontweight='bold', y=0.98)

# --- Top: Stability ---
ax1.plot(x, hist_stab_d, color='#2563eb', linewidth=2, label='Direct retrieval')
ax1.plot(x, hist_stab_a, color='#dc2626', linewidth=2, label='Associative retrieval')
ax1.axhline(core_stability_threshold, color='#16a34a', linewidth=1.5, linestyle='--',
            label=f'Core threshold ($S \\geq {core_stability_threshold}$)')
for rd in retrieval_days:
    ax1.axvline(rd, color='#f3f4f6', linewidth=0.5, zorder=0)

# Shade post-promotion region
if promotion_day_d:
    ax1.axvspan(promotion_day_d, days, color='#16a34a', alpha=0.06, zorder=0)
    ax1.annotate(f'Core promoted (day {promotion_day_d})',
                 xy=(promotion_day_d, core_stability_threshold),
                 xytext=(12, 0.42),
                 fontsize=9, color='#16a34a', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#16a34a', lw=1.5))

ax1.set_ylabel('Stability  $S(m)$', fontsize=11)
ax1.set_ylim(0, 1.08)
ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax1.set_title('Stability growth over time', fontsize=11)

# --- Bottom: Retention ---
ax2.plot(x, hist_ret_d, color='#2563eb', linewidth=2, label='Direct retrieval')
ax2.plot(x, hist_ret_a, color='#dc2626', linewidth=2, label='Associative retrieval')

# Floor lines - thicker and clearer
ax2.step(x, hist_floor_d, color='#2563eb', linewidth=1.5, linestyle='--', alpha=0.5,
         where='post', label=f'Floor (direct)')
ax2.step(x, hist_floor_a, color='#dc2626', linewidth=1.5, linestyle='--', alpha=0.5,
         where='post', label=f'Floor (associative)')

for rd in retrieval_days:
    ax2.axvline(rd, color='#f3f4f6', linewidth=0.5, zorder=0)

# Shade post-promotion region
if promotion_day_d:
    ax2.axvspan(promotion_day_d, days, color='#16a34a', alpha=0.06, zorder=0)
    ax2.annotate(f'Floor jumps 0.02 → 0.60',
                 xy=(promotion_day_d, floor_core),
                 xytext=(15, 0.35),
                 fontsize=9, color='#16a34a', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#16a34a', lw=1.5))

ax2.set_ylabel('Retention  $R(m)$', fontsize=11)
ax2.set_xlabel('Days', fontsize=11)
ax2.set_ylim(0, 1.08)
ax2.legend(loc='upper left', fontsize=9, framealpha=0.9, ncol=2)
ax2.set_title('Retention between retrieval events (with decay floors)', fontsize=11)

plt.savefig('/home/claude/paper/boosting_divergence.pdf', bbox_inches='tight', dpi=300)
plt.savefig('/home/claude/paper/boosting_divergence.png', bbox_inches='tight', dpi=300)

print(f"Direct:  stability={hist_stab_d[-1]:.3f}, promoted day {promotion_day_d}, accesses={access_count_d}, sessions={len(sessions_d)}")
print(f"Assoc:   stability={hist_stab_a[-1]:.3f}, promoted=no, accesses={access_count_a}, sessions={len(sessions_a)}")
