// ============================================
// K-FIMI Fusion Graph - Neo4j Schema
// 외국발 영향·허위정보 캠페인 탐지 시스템
// ============================================

// ============================================
// 1. 제약조건 및 인덱스 생성
// ============================================

// --- Account 노드 제약조건 ---
CREATE CONSTRAINT account_unique IF NOT EXISTS
FOR (a:Account) REQUIRE (a.accountHash, a.platform) IS UNIQUE;

CREATE INDEX account_platform_idx IF NOT EXISTS
FOR (a:Account) ON (a.platform);

CREATE INDEX account_country_idx IF NOT EXISTS
FOR (a:Account) ON (a.countryInferred);

CREATE INDEX account_suspicion_idx IF NOT EXISTS
FOR (a:Account) ON (a.suspicionScore);

// --- Post 노드 제약조건 ---
CREATE CONSTRAINT post_unique IF NOT EXISTS
FOR (p:Post) REQUIRE (p.postId, p.platform) IS UNIQUE;

CREATE INDEX post_platform_idx IF NOT EXISTS
FOR (p:Post) ON (p.platform);

CREATE INDEX post_created_idx IF NOT EXISTS
FOR (p:Post) ON (p.createdAtUtc);

CREATE INDEX post_template_idx IF NOT EXISTS
FOR (p:Post) ON (p.textTemplateId);

CREATE INDEX post_language_idx IF NOT EXISTS
FOR (p:Post) ON (p.language);

// --- URL 노드 제약조건 ---
CREATE CONSTRAINT url_unique IF NOT EXISTS
FOR (u:URL) REQUIRE u.url IS UNIQUE;

CREATE INDEX url_domain_idx IF NOT EXISTS
FOR (u:URL) ON (u.domain);

// --- Hashtag 노드 제약조건 ---
CREATE CONSTRAINT hashtag_unique IF NOT EXISTS
FOR (h:Hashtag) REQUIRE h.tag IS UNIQUE;

// --- Domain 노드 제약조건 ---
CREATE CONSTRAINT domain_unique IF NOT EXISTS
FOR (d:Domain) REQUIRE d.domain IS UNIQUE;

CREATE INDEX domain_credibility_idx IF NOT EXISTS
FOR (d:Domain) ON (d.credibilityScore);

// --- Campaign 노드 제약조건 ---
CREATE CONSTRAINT campaign_unique IF NOT EXISTS
FOR (c:Campaign) REQUIRE c.campaignId IS UNIQUE;

// --- Topic 노드 제약조건 ---
CREATE CONSTRAINT topic_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.tag IS UNIQUE;

// ============================================
// 2. 노드 레이블 설명
// ============================================
/*
노드 타입:
- :Account     - 소셜 미디어 계정
- :Post        - 게시물/트윗/메시지
- :URL         - 공유된 URL
- :Domain      - URL 도메인
- :Hashtag     - 해시태그
- :Topic       - 토픽 태그
- :Campaign    - 탐지된 캠페인
- :Media       - 미디어 파일 (이미지/비디오)

관계 타입:
- (:Account)-[:AUTHORED]->(:Post)
- (:Account)-[:FOLLOWS]->(:Account)
- (:Post)-[:MENTIONS]->(:Account)
- (:Post)-[:CONTAINS_URL]->(:URL)
- (:Post)-[:TAGGED_WITH]->(:Hashtag)
- (:Post)-[:ABOUT_TOPIC]->(:Topic)
- (:Post)-[:REPLY_TO]->(:Post)
- (:Post)-[:RETWEET_OF]->(:Post)
- (:Post)-[:SIMILAR_TO]->(:Post)
- (:URL)-[:BELONGS_TO]->(:Domain)
- (:Account)-[:PART_OF_CAMPAIGN]->(:Campaign)
- (:Post)-[:PART_OF_CAMPAIGN]->(:Campaign)
- (:Account)-[:COORDINATED_WITH]->(:Account)
*/

// ============================================
// 3. 샘플 노드 생성 (스키마 예시)
// ============================================

// --- Account 노드 예시 ---
// CREATE (a:Account {
//     accountHash: 'aff3e8c9d2b1',
//     platform: 'twitter',
//     accountCreatedDays: 450,
//     followers: 1200,
//     following: 300,
//     isVerified: false,
//     countryInferred: 'KR',
//     primaryLanguage: 'ko',
//     suspicionScore: 0.0,
//     firstSeenAt: datetime('2025-12-01T08:12:34Z'),
//     lastSeenAt: datetime('2025-12-01T09:05:00Z')
// });

// --- Post 노드 예시 ---
// CREATE (p:Post {
//     postId: 'x_10001',
//     platform: 'twitter',
//     text: '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.',
//     textTemplateId: 'tmpl_001',
//     language: 'ko',
//     createdAtUtc: datetime('2025-12-01T08:12:34Z'),
//     timeBucket: '2025-12-01T08:00:00Z_bucket_1h',
//     embedding: [0.12, -0.03, 0.45, 0.22, -0.18],
//     privacyFlag: 'pseudonymized'
// });

// --- URL 노드 예시 ---
// CREATE (u:URL {
//     url: 'news.example.com/article/123',
//     domain: 'news.example.com',
//     credibilityScore: 0.5,
//     shareCount: 1,
//     firstSeenAt: datetime('2025-12-01T08:12:34Z')
// });

// --- Hashtag 노드 예시 ---
// CREATE (h:Hashtag {
//     tag: 'security',
//     usageCount: 8,
//     firstSeenAt: datetime('2025-12-01T08:12:34Z')
// });

// --- Topic 노드 예시 ---
// CREATE (t:Topic {
//     tag: 'alliance',
//     description: '동맹 관련 토픽'
// });

// --- Domain 노드 예시 ---
// CREATE (d:Domain {
//     domain: 'news.example.com',
//     category: 'news',
//     credibilityScore: 0.7,
//     isNewsOutlet: true,
//     isKnownDisinfo: false
// });

// --- Campaign 노드 예시 ---
// CREATE (c:Campaign {
//     campaignId: 'campaign_001',
//     name: '한미동맹 흔들기 캠페인',
//     detectedAt: datetime('2025-12-01T10:00:00Z'),
//     confidenceScore: 0.85,
//     accountCount: 5,
//     postCount: 10,
//     primaryNarratives: ['alliance_crisis', 'government_failure'],
//     status: 'detected'
// });

// ============================================
// 4. 관계 생성 예시
// ============================================

// --- 계정이 게시물 작성 ---
// MATCH (a:Account {accountHash: 'aff3e8c9d2b1', platform: 'twitter'})
// MATCH (p:Post {postId: 'x_10001', platform: 'twitter'})
// CREATE (a)-[:AUTHORED {at: datetime('2025-12-01T08:12:34Z')}]->(p);

// --- 게시물에 URL 포함 ---
// MATCH (p:Post {postId: 'x_10001'})
// MATCH (u:URL {url: 'news.example.com/article/123'})
// CREATE (p)-[:CONTAINS_URL]->(u);

// --- 게시물에 토픽 태그 ---
// MATCH (p:Post {postId: 'x_10001'})
// MATCH (t:Topic {tag: 'security'})
// CREATE (p)-[:ABOUT_TOPIC {relevance: 0.9}]->(t);

// --- 답글 관계 ---
// MATCH (reply:Post {postId: 'x_10006'})
// MATCH (original:Post {postId: 'x_10001'})
// CREATE (reply)-[:REPLY_TO]->(original);

// --- 리트윗 관계 ---
// MATCH (retweet:Post {postId: 'x_10008'})
// MATCH (original:Post {postId: 'x_10001'})
// CREATE (retweet)-[:RETWEET_OF]->(original);

// --- 텍스트 유사도 관계 ---
// MATCH (p1:Post {postId: 'x_10001'})
// MATCH (p2:Post {postId: 'x_10004'})
// CREATE (p1)-[:SIMILAR_TO {score: 1.0, type: 'exact_match'}]->(p2);

// --- 협응 행위 관계 ---
// MATCH (a1:Account {accountHash: 'aff3e8c9d2b1'})
// MATCH (a2:Account {accountHash: 'c9d8e7f6a5b4'})
// CREATE (a1)-[:COORDINATED_WITH {
//     sharedUrls: 1,
//     avgTimeDiff: 120.5,
//     confidence: 0.75,
//     detectedAt: datetime()
// }]->(a2);

// --- 캠페인 소속 관계 ---
// MATCH (a:Account {accountHash: 'aff3e8c9d2b1'})
// MATCH (c:Campaign {campaignId: 'campaign_001'})
// CREATE (a)-[:PART_OF_CAMPAIGN {role: 'spreader', confidence: 0.8}]->(c);

// ============================================
// 5. 유용한 쿼리 예시
// ============================================

// --- 특정 계정의 모든 게시물 조회 ---
// MATCH (a:Account {accountHash: 'aff3e8c9d2b1'})-[:AUTHORED]->(p:Post)
// RETURN a, p ORDER BY p.createdAtUtc DESC;

// --- 동일 텍스트 게시물 찾기 ---
// MATCH (p1:Post)-[:SIMILAR_TO {type: 'exact_match'}]-(p2:Post)
// WHERE p1.postId < p2.postId
// RETURN p1.postId, p2.postId, p1.text;

// --- 협응 행위 네트워크 조회 ---
// MATCH (a1:Account)-[r:COORDINATED_WITH]->(a2:Account)
// WHERE r.confidence > 0.7
// RETURN a1, r, a2;

// --- 특정 URL을 공유한 모든 계정 ---
// MATCH (a:Account)-[:AUTHORED]->(p:Post)-[:CONTAINS_URL]->(u:URL {url: 'news.example.com/article/123'})
// RETURN DISTINCT a.accountHash, a.platform, count(p) as shareCount;

// --- 캠페인 참여 계정 및 게시물 ---
// MATCH (c:Campaign {campaignId: 'campaign_001'})
// OPTIONAL MATCH (a:Account)-[:PART_OF_CAMPAIGN]->(c)
// OPTIONAL MATCH (p:Post)-[:PART_OF_CAMPAIGN]->(c)
// RETURN c, collect(DISTINCT a) as accounts, collect(DISTINCT p) as posts;

// --- 2-hop 네트워크 탐색 (의심 계정 주변) ---
// MATCH (a:Account {suspicionScore: 0.8})-[:AUTHORED]->(p:Post)-[:CONTAINS_URL]->(u:URL)
// MATCH (u)<-[:CONTAINS_URL]-(p2:Post)<-[:AUTHORED]-(a2:Account)
// WHERE a <> a2
// RETURN a, p, u, p2, a2;

// --- 시간대별 게시물 집계 ---
// MATCH (p:Post)
// RETURN p.timeBucket, count(p) as postCount
// ORDER BY p.timeBucket;

// --- 토픽별 게시물 및 계정 수 ---
// MATCH (t:Topic)<-[:ABOUT_TOPIC]-(p:Post)<-[:AUTHORED]-(a:Account)
// RETURN t.tag, count(DISTINCT p) as posts, count(DISTINCT a) as accounts
// ORDER BY posts DESC;

