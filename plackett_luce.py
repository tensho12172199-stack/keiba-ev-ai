"""
Plackett-Luce モデルによる着順シミュレーション

改善点:
- 三連複（トリオ）確率の計算を追加
- パフォーマンス最適化
- Streamlit用の簡易関数を追加
"""

import numpy as np
from collections import defaultdict


def simulate_race_probabilities(scores, n_simulations=50000):
    """
    予測スコアから各馬の確率を計算（Streamlit用簡易版）
    
    Args:
        scores: 予測スコア（配列またはリスト）
        n_simulations: シミュレーション回数
    
    Returns:
        {
            'win': [馬1の勝率, 馬2の勝率, ...],
            'place': [馬1の複勝率, 馬2の複勝率, ...],
            'show': [馬1の3着内率, 馬2の3着内率, ...]
        }
    """
    scores = np.array(scores, dtype=float)
    n_horses = len(scores)
    
    # スコアが低い方が上位なので、逆転させる
    # または、スコアをそのまま使って確率化
    # ここでは exp(-score) で確率に変換（スコアが低い方が確率が高い）
    probs = np.exp(-scores / scores.std())  # 標準化して指数化
    probs = probs / probs.sum()  # 正規化
    
    # カウンター
    win_counts = np.zeros(n_horses)
    place_counts = np.zeros(n_horses)
    show_counts = np.zeros(n_horses)
    
    # シミュレーション
    for _ in range(n_simulations):
        remaining_probs = probs.copy()
        finish_order = []
        
        for _ in range(min(3, n_horses)):  # TOP3だけ計算
            probs_normalized = remaining_probs / remaining_probs.sum()
            selected_idx = np.random.choice(n_horses, p=probs_normalized)
            
            finish_order.append(selected_idx)
            remaining_probs[selected_idx] = 0
        
        # カウント
        if len(finish_order) >= 1:
            win_counts[finish_order[0]] += 1
        
        if len(finish_order) >= 2:
            place_counts[finish_order[0]] += 1
            place_counts[finish_order[1]] += 1
        
        if len(finish_order) >= 3:
            show_counts[finish_order[0]] += 1
            show_counts[finish_order[1]] += 1
            show_counts[finish_order[2]] += 1
    
    # 確率に変換
    return {
        'win': win_counts / n_simulations,
        'place': place_counts / n_simulations,
        'show': show_counts / n_simulations
    }


def simulate_plackett_luce(horse_ids, win_probs, n_sim=30000):
    """
    Plackett-Luceモデルでレース結果をシミュレーション
    
    Args:
        horse_ids: 馬番のリスト
        win_probs: 各馬の勝率（正規化済み）
        n_sim: シミュレーション回数
    
    Returns:
        win_counts: {horse_id: 1着回数}
        place_probs: {horse_id: 3着以内確率}
        trifecta_probs: {(1着, 2着, 3着): 確率}
        trio_probs: {(馬番1, 馬番2, 馬番3): 確率} (順不同)
    """
    n_horses = len(horse_ids)
    horse_ids = np.array(horse_ids)
    win_probs = np.array(win_probs, dtype=float)
    
    # カウンター初期化
    win_counts = defaultdict(int)
    place_counts = defaultdict(int)
    trifecta_counts = defaultdict(int)
    trio_counts = defaultdict(int)
    
    # シミュレーション実行
    for _ in range(n_sim):
        # Plackett-Luceサンプリング
        remaining_probs = win_probs.copy()
        finish_order = []
        
        for _ in range(n_horses):
            # 確率で次の馬を選択
            probs_normalized = remaining_probs / remaining_probs.sum()
            selected_idx = np.random.choice(n_horses, p=probs_normalized)
            
            finish_order.append(horse_ids[selected_idx])
            remaining_probs[selected_idx] = 0  # 選ばれた馬を除外
        
        # 1着
        win_counts[finish_order[0]] += 1
        
        # 3着以内
        for h in finish_order[:3]:
            place_counts[h] += 1
        
        # 三連単（1-2-3着の順序付き）
        trifecta = tuple(finish_order[:3])
        trifecta_counts[trifecta] += 1
        
        # 三連複（1-2-3着の順序なし）
        trio = tuple(sorted(finish_order[:3]))
        trio_counts[trio] += 1
    
    # 確率に変換
    win_probs_result = {h: count / n_sim for h, count in win_counts.items()}
    place_probs = {h: count / n_sim for h, count in place_counts.items()}
    trifecta_probs = {k: v / n_sim for k, v in trifecta_counts.items()}
    trio_probs = {k: v / n_sim for k, v in trio_counts.items()}
    
    return win_probs_result, place_probs, trifecta_probs, trio_probs


if __name__ == "__main__":
    # テスト
    print("Plackett-Luce シミュレーションのテスト")
    print("="*60)
    
    # テスト1: 簡易版
    print("\n【テスト1: 簡易版】")
    scores = np.array([3.5, 4.2, 5.1, 6.3, 7.8])
    result = simulate_race_probabilities(scores, n_simulations=10000)
    
    print("予測スコア:", scores)
    print("\n単勝確率:")
    for i, prob in enumerate(result['win'], 1):
        print(f"  馬{i}: {prob:.2%}")
    
    print("\n複勝確率:")
    for i, prob in enumerate(result['place'], 1):
        print(f"  馬{i}: {prob:.2%}")
    
    # テスト2: 完全版
    print("\n" + "="*60)
    print("【テスト2: 完全版】")
    horse_ids = [1, 2, 3, 4, 5]
    win_probs = np.array([0.3, 0.25, 0.2, 0.15, 0.1])
    
    print(f"馬番: {horse_ids}")
    print(f"勝率: {win_probs}")
    print(f"\nシミュレーション実行中...")
    
    win_sim, place_prob, trifecta_prob, trio_prob = simulate_plackett_luce(
        horse_ids, win_probs, n_sim=10000
    )
    
    print("\n【単勝確率】")
    for h in sorted(win_sim.keys()):
        print(f"  馬番{h}: {win_sim[h]:.2%}")
    
    print("\n【複勝確率（3着以内）】")
    for h in sorted(place_prob.keys()):
        print(f"  馬番{h}: {place_prob[h]:.2%}")
    
    print("\n【三連単 TOP5】")
    sorted_trifecta = sorted(trifecta_prob.items(), key=lambda x: x[1], reverse=True)
    for i, (combo, prob) in enumerate(sorted_trifecta[:5], 1):
        print(f"  {i}. {combo[0]}-{combo[1]}-{combo[2]}: {prob:.2%}")
    
    print("\n【三連複 TOP5】")
    sorted_trio = sorted(trio_prob.items(), key=lambda x: x[1], reverse=True)
    for i, (combo, prob) in enumerate(sorted_trio[:5], 1):
        print(f"  {i}. {combo[0]}-{combo[1]}-{combo[2]}: {prob:.2%}")
