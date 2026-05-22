#!/usr/bin/env python3
"""
GNN 기반 캠페인 탐지 실행 스크립트
- 데이터 로드 → 그래프 구축 → GNN 학습 → 클러스터링 → 결과 출력
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from collections import Counter

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import SAGEConv, to_hetero
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from src.ingest.csv_ingest import CSVIngester
from src.graph.fusion_graph_builder import FusionGraphBuilder


class HeteroGraphSAGE(nn.Module):
    """이종 그래프용 GraphSAGE 모델"""
    
    def __init__(self, hidden_dim: int = 64, out_dim: int = 32, num_layers: int = 2):
        super().__init__()
        self.convs = nn.ModuleList()
        for _ in range(num_layers):
            conv = SAGEConv((-1, -1), hidden_dim)
            self.convs.append(conv)
        self.lin = nn.Linear(hidden_dim, out_dim)
    
    def forward(self, x, edge_index):
        for conv in self.convs:
            x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=0.2, training=self.training)
        return self.lin(x)


def create_hetero_data(builder: FusionGraphBuilder) -> HeteroData:
    """FusionGraphBuilder에서 PyG HeteroData 생성"""
    data = HeteroData()
    
    # 노드 타입별 인덱스 매핑
    node_type_map = {}
    node_idx_map = {}
    
    for node_id, node in builder.nodes.items():
        node_type = node.node_type.value
        if node_type not in node_type_map:
            node_type_map[node_type] = []
        node_idx_map[node_id] = (node_type, len(node_type_map[node_type]))
        node_type_map[node_type].append(node_id)
    
    # 노드 특성 생성 (랜덤 초기화 + 메타데이터)
    for node_type, node_ids in node_type_map.items():
        num_nodes = len(node_ids)
        # 기본 특성: 랜덤 임베딩 (실제로는 텍스트 임베딩 사용)
        features = torch.randn(num_nodes, 64)
        
        # 메타데이터 추가
        for i, node_id in enumerate(node_ids):
            node = builder.nodes[node_id]
            if node.attrs:
                if 'followers_count' in node.attrs:
                    features[i, 0] = np.log1p(node.attrs.get('followers_count', 0)) / 10
                if 'following_count' in node.attrs:
                    features[i, 1] = np.log1p(node.attrs.get('following_count', 0)) / 10
                if 'verified' in node.attrs:
                    features[i, 2] = 1.0 if node.attrs.get('verified') else 0.0
        
        data[node_type].x = features
        data[node_type].num_nodes = num_nodes
        data[node_type].node_ids = node_ids
    
    # 엣지 생성
    edge_dict = {}
    for edge in builder.edges:
        if edge.source_id not in node_idx_map or edge.target_id not in node_idx_map:
            continue
        
        src_type, src_idx = node_idx_map[edge.source_id]
        tgt_type, tgt_idx = node_idx_map[edge.target_id]
        edge_type = (src_type, edge.edge_type.value, tgt_type)
        
        if edge_type not in edge_dict:
            edge_dict[edge_type] = [[], []]
        edge_dict[edge_type][0].append(src_idx)
        edge_dict[edge_type][1].append(tgt_idx)
    
    for edge_type, (src_list, tgt_list) in edge_dict.items():
        data[edge_type].edge_index = torch.tensor([src_list, tgt_list], dtype=torch.long)
    
    return data, node_idx_map


def train_gnn(data: HeteroData, epochs: int = 100) -> dict:
    """GNN 모델 학습 (자기지도 학습)"""
    
    # 간단한 동종 그래프로 변환하여 학습
    # 모든 노드를 하나로 합침
    all_features = []
    all_node_ids = []
    node_offset = {}
    current_offset = 0
    
    for node_type in data.node_types:
        if hasattr(data[node_type], 'x'):
            all_features.append(data[node_type].x)
            all_node_ids.extend(data[node_type].node_ids)
            node_offset[node_type] = current_offset
            current_offset += data[node_type].num_nodes
    
    x = torch.cat(all_features, dim=0)
    
    # 모든 엣지 합치기
    edge_list = [[], []]
    for edge_type in data.edge_types:
        if hasattr(data[edge_type], 'edge_index'):
            src_type, _, tgt_type = edge_type
            src_offset = node_offset.get(src_type, 0)
            tgt_offset = node_offset.get(tgt_type, 0)
            
            ei = data[edge_type].edge_index
            edge_list[0].extend((ei[0] + src_offset).tolist())
            edge_list[1].extend((ei[1] + tgt_offset).tolist())
    
    edge_index = torch.tensor(edge_list, dtype=torch.long)
    
    # 모델 생성
    model = HeteroGraphSAGE(hidden_dim=64, out_dim=32, num_layers=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    print(f"\n GNN 모델 학습 시작...")
    print(f"   노드 수: {x.shape[0]}, 특성 차원: {x.shape[1]}")
    print(f"   엣지 수: {edge_index.shape[1]}")
    
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        
        # Forward
        out = model(x, edge_index)
        
        # 자기지도 손실: 연결된 노드는 유사하게
        if edge_index.shape[1] > 0:
            src_emb = out[edge_index[0]]
            tgt_emb = out[edge_index[1]]
            pos_loss = F.mse_loss(src_emb, tgt_emb)
            
            # 랜덤 네거티브 샘플
            neg_idx = torch.randint(0, x.shape[0], (edge_index.shape[1],))
            neg_emb = out[neg_idx]
            neg_loss = F.relu(1 - F.mse_loss(src_emb, neg_emb))
            
            loss = pos_loss + 0.5 * neg_loss
        else:
            loss = torch.tensor(0.0)
        
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 20 == 0:
            print(f"   Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")
    
    # 최종 임베딩 추출
    model.eval()
    with torch.no_grad():
        embeddings = model(x, edge_index).numpy()
    
    return {
        'embeddings': embeddings,
        'node_ids': all_node_ids,
        'model': model
    }


def detect_campaigns(embeddings: np.ndarray, node_ids: list, builder: FusionGraphBuilder, n_clusters: int = 5) -> dict:
    """임베딩 기반 캠페인 클러스터링"""
    
    print(f"\n 캠페인 클러스터링...")
    
    # K-Means 클러스터링
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(embeddings)
    
    # 클러스터별 분석
    cluster_results = []
    
    for cluster_id in range(n_clusters):
        cluster_mask = clusters == cluster_id
        cluster_node_ids = [node_ids[i] for i in range(len(node_ids)) if cluster_mask[i]]
        cluster_embeddings = embeddings[cluster_mask]
        
        # 클러스터 내 유사도
        if len(cluster_embeddings) > 1:
            sim_matrix = cosine_similarity(cluster_embeddings)
            avg_similarity = (sim_matrix.sum() - len(cluster_embeddings)) / (len(cluster_embeddings) * (len(cluster_embeddings) - 1))
        else:
            avg_similarity = 1.0
        
        # 노드 타입별 분류
        node_types = Counter()
        platforms = Counter()
        accounts = set()
        contents = []
        
        for node_id in cluster_node_ids:
            node = builder.nodes.get(node_id)
            if node:
                node_types[node.node_type.value] += 1
                if node.node_type.value == 'user':
                    platform = node.attrs.get('platform', 'unknown')
                    platforms[platform] += 1
                    accounts.add(node_id)
                elif node.node_type.value == 'content':
                    text = node.attrs.get('text', '')[:50]
                    contents.append(text)
        
        # 캠페인 위험도 평가
        risk_score = 0
        reasons = []
        
        if avg_similarity > 0.8:
            risk_score += 30
            reasons.append("높은 내부 유사도")
        if node_types.get('user', 0) > 3 and avg_similarity > 0.7:
            risk_score += 25
            reasons.append("다수 계정 협응 의심")
        if len(platforms) > 1:
            risk_score += 20
            reasons.append("크로스 플랫폼 활동")
        if node_types.get('url', 0) > 2:
            risk_score += 15
            reasons.append("다수 URL 공유")
        
        cluster_results.append({
            'cluster_id': cluster_id,
            'size': len(cluster_node_ids),
            'avg_similarity': float(avg_similarity),
            'node_types': dict(node_types),
            'platforms': dict(platforms),
            'num_accounts': len(accounts),
            'sample_contents': contents[:3],
            'risk_score': risk_score,
            'risk_reasons': reasons,
            'is_campaign': risk_score >= 40
        })
    
    # 위험도 순 정렬
    cluster_results.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return {
        'clusters': cluster_results,
        'total_clusters': n_clusters,
        'detected_campaigns': len([c for c in cluster_results if c['is_campaign']])
    }


def main():
    print("=" * 60)
    print("  K-FIMI GNN 기반 캠페인 탐지 시스템")
    print("=" * 60)
    
    # 1. 데이터 로드
    print("\n 데이터 로드 중...")
    csv_file = PROJECT_ROOT / "data" / "raw" / "economic_disinfo.csv"
    
    ingester = CSVIngester()
    df = ingester.load_csv(str(csv_file))
    posts = ingester.parse_posts(df)
    print(f"   로드된 게시물: {len(posts)}개")
    
    # 2. Fusion Graph 구축
    print("\n  Fusion Graph 구축 중...")
    builder = FusionGraphBuilder()
    
    for post in posts:
        user_id = builder.add_user(
            platform=post.platform,
            user_id=post.account_hash,
            followers_count=post.followers,
            following_count=post.following,
            verified=post.is_verified
        )
        
        content_id = builder.add_content(
            platform=post.platform,
            content_id=post.post_id,
            text=post.text,
            author_id=user_id,
            created_at=post.created_at
        )
        
        for url in post.urls:
            url_id = builder.add_url(url)
            builder.link_content_to_url(content_id, url_id)
        
        for tag in post.topic_tags:
            tag_id = builder.add_hashtag(tag)
            builder.link_content_to_hashtag(content_id, tag_id)
    
    stats = builder.get_statistics()
    print(f"   노드: {stats['total_nodes']}개, 엣지: {stats['total_edges']}개")
    print(f"   노드 타입: {stats['node_counts']}")
    
    # 3. PyG HeteroData 생성
    print("\n PyG HeteroData 변환 중...")
    hetero_data, node_idx_map = create_hetero_data(builder)
    print(f"   노드 타입: {hetero_data.node_types}")
    print(f"   엣지 타입: {len(hetero_data.edge_types)}개")
    
    # 4. GNN 학습
    result = train_gnn(hetero_data, epochs=100)
    print(f"\n GNN 학습 완료!")
    print(f"   임베딩 차원: {result['embeddings'].shape}")
    
    # 5. 캠페인 탐지
    detection = detect_campaigns(
        result['embeddings'], 
        result['node_ids'], 
        builder,
        n_clusters=5
    )
    
    # 6. 결과 출력
    print("\n" + "=" * 60)
    print(" GNN 캠페인 탐지 결과")
    print("=" * 60)
    
    print(f"\n총 클러스터: {detection['total_clusters']}개")
    print(f"탐지된 캠페인: {detection['detected_campaigns']}개")
    
    for cluster in detection['clusters']:
        is_campaign = " 캠페인" if cluster['is_campaign'] else " 정상"
        print(f"\n[클러스터 {cluster['cluster_id']}] {is_campaign}")
        print(f"   크기: {cluster['size']}개 노드")
        print(f"   내부 유사도: {cluster['avg_similarity']:.2%}")
        print(f"   위험 점수: {cluster['risk_score']}/100")
        print(f"   노드 타입: {cluster['node_types']}")
        if cluster['platforms']:
            print(f"   플랫폼: {cluster['platforms']}")
        if cluster['risk_reasons']:
            print(f"   위험 요인: {', '.join(cluster['risk_reasons'])}")
        if cluster['sample_contents']:
            print(f"   샘플 콘텐츠:")
            for content in cluster['sample_contents'][:2]:
                print(f"      - {content}...")
    
    # 7. 결과 저장
    output_path = PROJECT_ROOT / "data" / "processed" / "gnn_detection_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_posts': len(posts),
            'graph_stats': stats,
            'detection': detection
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n 결과 저장: {output_path}")
    print("\n GNN 기반 캠페인 탐지 완료!")


if __name__ == "__main__":
    main()

