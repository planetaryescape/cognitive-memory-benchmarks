import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

np.random.seed(42)

DAYS = 365
COLD_THRESHOLD_DAYS = 7
FLOOR_REGULAR = 0.02
FLOOR_CORE = 0.60
CONSOLIDATION_THRESHOLD = 0.20
CONSOLIDATION_GROUP_SIZE = 5
CORE_STABILITY_THRESHOLD = 0.85
CORE_ACCESS_THRESHOLD = 10
CORE_SESSION_THRESHOLD = 3

TYPE_DIST = {'episodic': 0.6, 'semantic': 0.35, 'procedural': 0.05}
BASE_DECAY = {'episodic': 30, 'semantic': 90, 'procedural': 9999}

class Memory:
    __slots__ = ['id', 'mtype', 'importance', 'stability', 'last_accessed',
                 'created', 'access_count', 'sessions', 'is_core', 'is_cold',
                 'is_superseded', 'days_at_floor', 'floor']
    def __init__(self, mid, day, mtype, importance):
        self.id = mid; self.mtype = mtype; self.importance = importance
        self.stability = 0.1; self.last_accessed = day; self.created = day
        self.access_count = 0; self.sessions = set()
        self.is_core = False; self.is_cold = False; self.is_superseded = False
        self.days_at_floor = 0; self.floor = FLOOR_REGULAR
    def retention(self, day):
        dt = day - self.last_accessed
        if dt <= 0: return 1.0
        B = 1 + (self.importance * 2)
        beta = BASE_DECAY[self.mtype]
        return max(self.floor, np.exp(-dt / (max(self.stability, 0.001) * B * beta)))
    def boost(self, day, direct=True):
        dt = day - self.last_accessed
        gap = min(2.0, max(dt, 1) / 7)
        self.stability = min(1.0, self.stability + (0.1 if direct else 0.03) * gap)
        self.last_accessed = day; self.access_count += 1; self.sessions.add(day)
        self.days_at_floor = 0
        if (not self.is_core and self.stability >= CORE_STABILITY_THRESHOLD
                and self.access_count >= CORE_ACCESS_THRESHOLD
                and len(self.sessions) >= CORE_SESSION_THRESHOLD):
            self.is_core = True; self.floor = FLOOR_CORE

def run_scenario(memories_per_day, queries_per_day, results_per_query, label):
    all_memories = []; mid_counter = 0; daily_hot = []; daily_total = []
    for day in range(1, DAYS + 1):
        for _ in range(np.random.poisson(memories_per_day)):
            mtype = np.random.choice(list(TYPE_DIST.keys()), p=list(TYPE_DIST.values()))
            importance = np.clip(np.random.beta(2, 5), 0.1, 1.0)
            all_memories.append(Memory(mid_counter, day, mtype, importance)); mid_counter += 1
        hot_active = [m for m in all_memories if not m.is_cold and not m.is_superseded]
        if hot_active and queries_per_day > 0:
            for _ in range(queries_per_day):
                if len(hot_active) <= results_per_query:
                    retrieved = hot_active
                else:
                    scores = np.array([m.retention(day) * np.random.random() for m in hot_active])
                    retrieved = [hot_active[i] for i in np.argsort(scores)[-results_per_query:]]
                for i, m in enumerate(retrieved): m.boost(day, direct=(i == 0))
        for m in all_memories:
            if m.is_cold or m.is_superseded: continue
            r = m.retention(day)
            if abs(r - m.floor) < 0.001: m.days_at_floor += 1
            else: m.days_at_floor = 0
            if (m.days_at_floor >= COLD_THRESHOLD_DAYS and not m.is_core and (day - m.created) > 14):
                m.is_cold = True
        if day % 7 == 0:
            fading = [m for m in all_memories if not m.is_cold and not m.is_superseded
                      and not m.is_core and m.retention(day) < CONSOLIDATION_THRESHOLD]
            by_type = {}
            for m in fading: by_type.setdefault(m.mtype, []).append(m)
            for mtype, group in by_type.items():
                while len(group) >= CONSOLIDATION_GROUP_SIZE:
                    batch = group[:CONSOLIDATION_GROUP_SIZE]; group = group[CONSOLIDATION_GROUP_SIZE:]
                    s = Memory(mid_counter, day, mtype, np.mean([m.importance for m in batch]))
                    s.stability = np.mean([m.stability for m in batch])
                    s.access_count = max(m.access_count for m in batch)
                    all_memories.append(s); mid_counter += 1
                    for m in batch: m.is_superseded = True; m.is_cold = True; m.floor = FLOOR_REGULAR
        daily_hot.append(sum(1 for m in all_memories if not m.is_cold))
        daily_total.append(len(all_memories))
    pct = 100 * daily_hot[-1] / daily_total[-1] if daily_total[-1] else 100
    print(f"{label}: total={daily_total[-1]}, hot={daily_hot[-1]} ({pct:.1f}%), peak={max(daily_hot)}")
    return daily_hot, daily_total

scenarios = [
    (4, 1, 3, "Light use (4 mem/day, 1 query/day)"),
    (4, 3, 3, "Moderate (4 mem/day, 3 queries/day)"),
    (4, 6, 4, "Active (4 mem/day, 6 queries/day)"),
    (4, 12, 4, "Heavy (4 mem/day, 12 queries/day)"),
    (10, 2, 3, "Bursty ingest (10 mem/day, 2 queries/day)"),
    (2, 6, 4, "Low ingest (2 mem/day, 6 queries/day)"),
]

results = {}
for mem, q, r, label in scenarios:
    hot, total = run_scenario(mem, q, r, label)
    results[label] = (hot, total)

x = np.arange(1, DAYS + 1)
fig, axes = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={'wspace': 0.3})

colors = ['#dc2626', '#f97316', '#2563eb', '#16a34a', '#7c3aed', '#06b6d4']
ax = axes[0]
for (label, (hot, total)), color in zip(results.items(), colors):
    short = label.split('(')[0].strip()
    ax.plot(x, hot, color=color, linewidth=1.5, label=short)
ax.set_xlabel('Days', fontsize=11); ax.set_ylabel('Hot index size', fontsize=11)
ax.set_title('Hot index size across access patterns', fontsize=11)
ax.legend(fontsize=8, loc='upper left')

ax = axes[1]
labels_short = [l.split('(')[0].strip() for l in results.keys()]
hot_pcts = [100 * h[-1] / t[-1] for (h, t) in results.values()]
bars = ax.barh(range(len(hot_pcts)), hot_pcts, color=colors, height=0.6)
ax.set_yticks(range(len(labels_short))); ax.set_yticklabels(labels_short, fontsize=9)
ax.set_xlabel('Hot index (% of total at day 365)', fontsize=11)
ax.set_title('Index efficiency by access pattern', fontsize=11); ax.set_xlim(0, 60)
for bar, val in zip(bars, hot_pcts):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, f'{val:.1f}%', va='center', fontsize=10)

fig.suptitle('Tiered Storage Scaling: Sensitivity to Access Patterns', fontsize=13, fontweight='bold', y=1.02)
plt.savefig('/home/claude/paper/cold_storage.pdf', bbox_inches='tight', dpi=300)
plt.savefig('/home/claude/paper/cold_storage.png', bbox_inches='tight', dpi=300)
print("\nFigures saved.")
