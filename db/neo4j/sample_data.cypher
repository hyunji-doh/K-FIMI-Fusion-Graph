// K-FIMI Sample Data Cypher Statements
// Generated at: 2025-12-02T16:15:30.263842

// Account Nodes
MERGE (a:Account {accountHash: 'aff3e8c9d2b1', platform: 'twitter'})
SET a.accountCreatedDays = 450,
    a.followers = 1200,
    a.following = 300,
    a.isVerified = false,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'b2c4e5f6a7d8', platform: 'twitter'})
SET a.accountCreatedDays = 120,
    a.followers = 850,
    a.following = 420,
    a.isVerified = false,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'c9d8e7f6a5b4', platform: 'twitter'})
SET a.accountCreatedDays = 30,
    a.followers = 150,
    a.following = 2000,
    a.isVerified = false,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'd1e2f3a4b5c6', platform: 'twitter'})
SET a.accountCreatedDays = 15,
    a.followers = 50,
    a.following = 5000,
    a.isVerified = false,
    a.countryInferred = 'US',
    a.primaryLanguage = 'en';
MERGE (a:Account {accountHash: 'bb9a2f77e3c4', platform: 'youtube'})
SET a.accountCreatedDays = 30,
    a.followers = 5000,
    a.following = 45,
    a.isVerified = true,
    a.countryInferred = 'US',
    a.primaryLanguage = 'en';
MERGE (a:Account {accountHash: 'cc8b3f88d4e5', platform: 'youtube'})
SET a.accountCreatedDays = 180,
    a.followers = 12000,
    a.following = 120,
    a.isVerified = true,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'dd9c4g99e5f6', platform: 'youtube'})
SET a.accountCreatedDays = 60,
    a.followers = 800,
    a.following = 30,
    a.isVerified = false,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'c3d1f4aab2e5', platform: 'telegram'})
SET a.accountCreatedDays = 200,
    a.followers = 250,
    a.following = 10,
    a.isVerified = false,
    a.countryInferred = 'RU',
    a.primaryLanguage = 'ru';
MERGE (a:Account {accountHash: 'e4f2g5hhi6j7', platform: 'telegram'})
SET a.accountCreatedDays = 90,
    a.followers = 180,
    a.following = 25,
    a.isVerified = false,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'f5g3h6ii7k8l', platform: 'telegram'})
SET a.accountCreatedDays = 45,
    a.followers = 1200,
    a.following = 80,
    a.isVerified = false,
    a.countryInferred = 'CN',
    a.primaryLanguage = 'zh';
MERGE (a:Account {accountHash: 'g6h4i7jj8k9m', platform: 'twitter'})
SET a.accountCreatedDays = 500,
    a.followers = 8500,
    a.following = 150,
    a.isVerified = true,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';
MERGE (a:Account {accountHash: 'h7i5j8kk9l0n', platform: 'twitter'})
SET a.accountCreatedDays = 10,
    a.followers = 25,
    a.following = 8000,
    a.isVerified = false,
    a.countryInferred = 'KR',
    a.primaryLanguage = 'ko';

// Post Nodes
MERGE (p:Post {postId: 'x_10001', platform: 'twitter'})
SET p.text = '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.',
    p.textTemplateId = 'tmpl_001',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:12:34+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.12, -0.03, 0.45, 0.22, -0.18];
MERGE (p:Post {postId: 'x_10002', platform: 'twitter'})
SET p.text = '미군 철수설이 돌고 있다. 확인되지 않은 정보에 주의하세요.',
    p.textTemplateId = 'tmpl_003',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:14:22+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.08, -0.12, 0.33, 0.19, -0.25];
MERGE (p:Post {postId: 'x_10003', platform: 'twitter'})
SET p.text = '정부 대응이 너무 늦다. 안보 위기 상황이다.',
    p.textTemplateId = 'tmpl_001',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:22:11+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.15, -0.05, 0.42, 0.25, -0.2];
MERGE (p:Post {postId: 'x_10004', platform: 'twitter'})
SET p.text = '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.',
    p.textTemplateId = 'tmpl_001',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:25:45+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.12, -0.03, 0.45, 0.22, -0.18];
MERGE (p:Post {postId: 'x_10005', platform: 'twitter'})
SET p.text = 'Breaking: US-Korea alliance in jeopardy according to sources',
    p.textTemplateId = 'tmpl_004',
    p.language = 'en',
    p.createdAtUtc = datetime('2025-12-01T08:30:00+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.22, 0.15, 0.38, -0.12, 0.08];
MERGE (p:Post {postId: 'yt_20012', platform: 'youtube'})
SET p.text = 'Exclusive: New evidence suggests policy shift on deployed troops',
    p.textTemplateId = 'tmpl_002',
    p.language = 'en',
    p.createdAtUtc = datetime('2025-12-01T08:15:10+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.05, 0.33, 0.28, -0.15, 0.42];
MERGE (p:Post {postId: 'yt_20013', platform: 'youtube'})
SET p.text = '[팩트체크] 미군 철수설의 진실은?',
    p.textTemplateId = 'tmpl_005',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:18:30+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.18, -0.08, 0.52, 0.11, -0.33];
MERGE (p:Post {postId: 'yt_20014', platform: 'youtube'})
SET p.text = '미국이 한국을 버릴 것이라는 증거 공개',
    p.textTemplateId = 'tmpl_006',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:45:00+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.25, 0.18, 0.35, -0.22, 0.15];
MERGE (p:Post {postId: 'tg_3307', platform: 'telegram'})
SET p.text = '동맹 포기설을 퍼뜨리는 기사 링크',
    p.textTemplateId = 'tmpl_001',
    p.language = 'ru',
    p.createdAtUtc = datetime('2025-12-01T08:09:02+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [-0.02, 0.11, 0.48, 0.2, -0.15];
MERGE (p:Post {postId: 'tg_3308', platform: 'telegram'})
SET p.text = '러시아 매체에서 나온 정보인데 확인 필요',
    p.textTemplateId = 'tmpl_007',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T08:11:45+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.08, 0.22, 0.4, 0.18, -0.28];
MERGE (p:Post {postId: 'tg_3309', platform: 'telegram'})
SET p.text = '한국 정부 내부 문서 유출 - 동맹 재검토',
    p.textTemplateId = 'tmpl_008',
    p.language = 'ru',
    p.createdAtUtc = datetime('2025-12-01T08:35:20+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [-0.05, 0.15, 0.52, 0.25, -0.1];
MERGE (p:Post {postId: 'tg_3310', platform: 'telegram'})
SET p.text = '美韩同盟动摇 - 最新消息',
    p.textTemplateId = 'tmpl_009',
    p.language = 'zh',
    p.createdAtUtc = datetime('2025-12-01T08:40:15+00:00'),
    p.timeBucket = '2025-12-01T08:00:00Z_bucket_1h',
    p.embedding = [0.3, 0.12, 0.28, -0.18, 0.22];
MERGE (p:Post {postId: 'x_10006', platform: 'twitter'})
SET p.text = '후속 보도: 정부 관계자 발언 정리',
    p.textTemplateId = 'tmpl_010',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T09:05:00+00:00'),
    p.timeBucket = '2025-12-01T09:00:00Z_bucket_1h',
    p.embedding = [0.1, -0.02, 0.48, 0.3, -0.12];
MERGE (p:Post {postId: 'x_10007', platform: 'twitter'})
SET p.text = '[공식] 외교부 입장문 발표 예정',
    p.textTemplateId = 'tmpl_011',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T09:10:30+00:00'),
    p.timeBucket = '2025-12-01T09:00:00Z_bucket_1h',
    p.embedding = [0.02, 0.08, 0.55, 0.35, -0.05];
MERGE (p:Post {postId: 'x_10008', platform: 'twitter'})
SET p.text = '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.',
    p.textTemplateId = 'tmpl_001',
    p.language = 'ko',
    p.createdAtUtc = datetime('2025-12-01T09:15:45+00:00'),
    p.timeBucket = '2025-12-01T09:00:00Z_bucket_1h',
    p.embedding = [0.12, -0.03, 0.45, 0.22, -0.18];

// URL Nodes
MERGE (u:URL {url: 'news.example.com/article/123'}) SET u.domain = 'news.example.com';
MERGE (u:URL {url: 'blog.example.kr/post/456'}) SET u.domain = 'blog.example.kr';
MERGE (u:URL {url: 'fakenews.xyz/story/789'}) SET u.domain = 'fakenews.xyz';
MERGE (u:URL {url: 'youtube.com/watch?v=abc123'}) SET u.domain = 'youtube.com';
MERGE (u:URL {url: 'youtube.com/watch?v=def456'}) SET u.domain = 'youtube.com';
MERGE (u:URL {url: 'youtube.com/watch?v=ghi789'}) SET u.domain = 'youtube.com';
MERGE (u:URL {url: 'anonnews.ru/post/45'}) SET u.domain = 'anonnews.ru';
MERGE (u:URL {url: 'rt.com/news/123'}) SET u.domain = 'rt.com';
MERGE (u:URL {url: 'leakedfiles.onion/doc/99'}) SET u.domain = 'leakedfiles.onion';
MERGE (u:URL {url: 'chinanews.example.cn/article/567'}) SET u.domain = 'chinanews.example.cn';
MERGE (u:URL {url: 'news.example.com/article/124'}) SET u.domain = 'news.example.com';
MERGE (u:URL {url: 'mofa.go.kr/press/789'}) SET u.domain = 'mofa.go.kr';

// Topic Nodes
MERGE (t:Topic {tag: 'security'});
MERGE (t:Topic {tag: 'alliance'});
MERGE (t:Topic {tag: 'military'});
MERGE (t:Topic {tag: 'crisis'});
MERGE (t:Topic {tag: 'disinfo'});
MERGE (t:Topic {tag: 'factcheck'});
MERGE (t:Topic {tag: 'russia'});
MERGE (t:Topic {tag: 'leak'});
MERGE (t:Topic {tag: 'china'});
MERGE (t:Topic {tag: 'update'});
MERGE (t:Topic {tag: 'official'});

// AUTHORED Relationships
MATCH (a:Account {accountHash: 'aff3e8c9d2b1', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10001', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'b2c4e5f6a7d8', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10002', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'aff3e8c9d2b1', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10003', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'c9d8e7f6a5b4', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10004', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'd1e2f3a4b5c6', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10005', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'bb9a2f77e3c4', platform: 'youtube'})
MATCH (p:Post {postId: 'yt_20012', platform: 'youtube'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'cc8b3f88d4e5', platform: 'youtube'})
MATCH (p:Post {postId: 'yt_20013', platform: 'youtube'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'dd9c4g99e5f6', platform: 'youtube'})
MATCH (p:Post {postId: 'yt_20014', platform: 'youtube'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'c3d1f4aab2e5', platform: 'telegram'})
MATCH (p:Post {postId: 'tg_3307', platform: 'telegram'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'e4f2g5hhi6j7', platform: 'telegram'})
MATCH (p:Post {postId: 'tg_3308', platform: 'telegram'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'c3d1f4aab2e5', platform: 'telegram'})
MATCH (p:Post {postId: 'tg_3309', platform: 'telegram'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'f5g3h6ii7k8l', platform: 'telegram'})
MATCH (p:Post {postId: 'tg_3310', platform: 'telegram'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'aff3e8c9d2b1', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10006', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'g6h4i7jj8k9m', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10007', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);
MATCH (a:Account {accountHash: 'h7i5j8kk9l0n', platform: 'twitter'})
MATCH (p:Post {postId: 'x_10008', platform: 'twitter'})
MERGE (a)-[:AUTHORED]->(p);

// CONTAINS_URL Relationships
MATCH (p:Post {postId: 'x_10001', platform: 'twitter'})
MATCH (u:URL {url: 'news.example.com/article/123'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'x_10002', platform: 'twitter'})
MATCH (u:URL {url: 'blog.example.kr/post/456'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'x_10004', platform: 'twitter'})
MATCH (u:URL {url: 'news.example.com/article/123'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'x_10005', platform: 'twitter'})
MATCH (u:URL {url: 'fakenews.xyz/story/789'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'yt_20012', platform: 'youtube'})
MATCH (u:URL {url: 'youtube.com/watch?v=abc123'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'yt_20013', platform: 'youtube'})
MATCH (u:URL {url: 'youtube.com/watch?v=def456'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'yt_20014', platform: 'youtube'})
MATCH (u:URL {url: 'youtube.com/watch?v=ghi789'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'tg_3307', platform: 'telegram'})
MATCH (u:URL {url: 'anonnews.ru/post/45'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'tg_3308', platform: 'telegram'})
MATCH (u:URL {url: 'rt.com/news/123'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'tg_3309', platform: 'telegram'})
MATCH (u:URL {url: 'leakedfiles.onion/doc/99'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'tg_3310', platform: 'telegram'})
MATCH (u:URL {url: 'chinanews.example.cn/article/567'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'x_10006', platform: 'twitter'})
MATCH (u:URL {url: 'news.example.com/article/124'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'x_10007', platform: 'twitter'})
MATCH (u:URL {url: 'mofa.go.kr/press/789'})
MERGE (p)-[:CONTAINS_URL]->(u);
MATCH (p:Post {postId: 'x_10008', platform: 'twitter'})
MATCH (u:URL {url: 'news.example.com/article/123'})
MERGE (p)-[:CONTAINS_URL]->(u);

// ABOUT_TOPIC Relationships
MATCH (p:Post {postId: 'x_10001', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10001', platform: 'twitter'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10002', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10002', platform: 'twitter'})
MATCH (t:Topic {tag: 'military'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10003', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10003', platform: 'twitter'})
MATCH (t:Topic {tag: 'crisis'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10004', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10004', platform: 'twitter'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10005', platform: 'twitter'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10005', platform: 'twitter'})
MATCH (t:Topic {tag: 'disinfo'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'yt_20012', platform: 'youtube'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'yt_20012', platform: 'youtube'})
MATCH (t:Topic {tag: 'military'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'yt_20013', platform: 'youtube'})
MATCH (t:Topic {tag: 'factcheck'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'yt_20013', platform: 'youtube'})
MATCH (t:Topic {tag: 'military'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'yt_20014', platform: 'youtube'})
MATCH (t:Topic {tag: 'disinfo'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'yt_20014', platform: 'youtube'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3307', platform: 'telegram'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3307', platform: 'telegram'})
MATCH (t:Topic {tag: 'disinfo'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3308', platform: 'telegram'})
MATCH (t:Topic {tag: 'russia'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3308', platform: 'telegram'})
MATCH (t:Topic {tag: 'disinfo'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3309', platform: 'telegram'})
MATCH (t:Topic {tag: 'leak'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3309', platform: 'telegram'})
MATCH (t:Topic {tag: 'disinfo'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3310', platform: 'telegram'})
MATCH (t:Topic {tag: 'china'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'tg_3310', platform: 'telegram'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10006', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10006', platform: 'twitter'})
MATCH (t:Topic {tag: 'update'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10007', platform: 'twitter'})
MATCH (t:Topic {tag: 'official'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10007', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10008', platform: 'twitter'})
MATCH (t:Topic {tag: 'security'})
MERGE (p)-[:ABOUT_TOPIC]->(t);
MATCH (p:Post {postId: 'x_10008', platform: 'twitter'})
MATCH (t:Topic {tag: 'alliance'})
MERGE (p)-[:ABOUT_TOPIC]->(t);