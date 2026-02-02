import numpy as np
from collections import defaultdict
from itertools import permutations

def simulate_plackett_luce(
    horse_ids,
    win_probs,
    n_sim=30000
):
    """
    horse_ids : list[int]
    win_probs : np.array (shape = [n_horses])
    """

    win_probs = np.array(win_probs, dtype=float)
    win_probs = win_probs / win_probs.sum()

    win_count = defaultdict(int)
    top3_count = defaultdict(int)
    trifecta_count = defaultdict(int)

    for _ in range(n_sim):
        remaining_ids = horse_ids.copy()
        remaining_probs = win_probs.copy()
        order = []

        for _ in range(3):
            p = remaining_probs / remaining_probs.sum()
            idx = np.random.choice(len(remaining_ids), p=p)
            chosen = remaining_ids[idx]

            order.append(chosen)

            remaining_ids.pop(idx)
            remaining_probs = np.delete(remaining_probs, idx)

        win_count[order[0]] += 1
        for h in order:
            top3_count[h] += 1
        trifecta_count[tuple(order)] += 1

    # 確率化
    place_prob = {h: top3_count[h] / n_sim for h in horse_ids}
    win_prob_sim = {h: win_count[h] / n_sim for h in horse_ids}
    trifecta_prob = {
        k: v / n_sim for k, v in trifecta_count.items()
    }

    return win_prob_sim, place_prob, trifecta_prob
