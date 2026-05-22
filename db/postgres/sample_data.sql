-- K-FIMI Sample Data INSERT Statements
-- Generated at: 2025-12-02T16:15:30.263460

-- Accounts
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('aff3e8c9d2b1', 'twitter', 450, 1200, 300, FALSE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('b2c4e5f6a7d8', 'twitter', 120, 850, 420, FALSE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('c9d8e7f6a5b4', 'twitter', 30, 150, 2000, FALSE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('d1e2f3a4b5c6', 'twitter', 15, 50, 5000, FALSE, 'US', 'en')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('bb9a2f77e3c4', 'youtube', 30, 5000, 45, TRUE, 'US', 'en')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('cc8b3f88d4e5', 'youtube', 180, 12000, 120, TRUE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('dd9c4g99e5f6', 'youtube', 60, 800, 30, FALSE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('c3d1f4aab2e5', 'telegram', 200, 250, 10, FALSE, 'RU', 'ru')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('e4f2g5hhi6j7', 'telegram', 90, 180, 25, FALSE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('f5g3h6ii7k8l', 'telegram', 45, 1200, 80, FALSE, 'CN', 'zh')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('g6h4i7jj8k9m', 'twitter', 500, 8500, 150, TRUE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;
INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('h7i5j8kk9l0n', 'twitter', 10, 25, 8000, FALSE, 'KR', 'ko')
ON CONFLICT (account_hash, platform) DO NOTHING;

-- Posts
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10001', 'twitter', 'aff3e8c9d2b1', '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.', 'tmpl_001', 'ko', '2025-12-01T08:12:34+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.12, -0.03, 0.45, 0.22, -0.18]', ARRAY['security','alliance'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10002', 'twitter', 'b2c4e5f6a7d8', '미군 철수설이 돌고 있다. 확인되지 않은 정보에 주의하세요.', 'tmpl_003', 'ko', '2025-12-01T08:14:22+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.08, -0.12, 0.33, 0.19, -0.25]', ARRAY['security','military'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10003', 'twitter', 'aff3e8c9d2b1', '정부 대응이 너무 늦다. 안보 위기 상황이다.', 'tmpl_001', 'ko', '2025-12-01T08:22:11+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.15, -0.05, 0.42, 0.25, -0.2]', ARRAY['security','crisis'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10004', 'twitter', 'c9d8e7f6a5b4', '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.', 'tmpl_001', 'ko', '2025-12-01T08:25:45+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.12, -0.03, 0.45, 0.22, -0.18]', ARRAY['security','alliance'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10005', 'twitter', 'd1e2f3a4b5c6', 'Breaking: US-Korea alliance in jeopardy according to sources', 'tmpl_004', 'en', '2025-12-01T08:30:00+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.22, 0.15, 0.38, -0.12, 0.08]', ARRAY['alliance','disinfo'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('yt_20012', 'youtube', 'bb9a2f77e3c4', 'Exclusive: New evidence suggests policy shift on deployed troops', 'tmpl_002', 'en', '2025-12-01T08:15:10+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.05, 0.33, 0.28, -0.15, 0.42]', ARRAY['security','military'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('yt_20013', 'youtube', 'cc8b3f88d4e5', '[팩트체크] 미군 철수설의 진실은?', 'tmpl_005', 'ko', '2025-12-01T08:18:30+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.18, -0.08, 0.52, 0.11, -0.33]', ARRAY['factcheck','military'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('yt_20014', 'youtube', 'dd9c4g99e5f6', '미국이 한국을 버릴 것이라는 증거 공개', 'tmpl_006', 'ko', '2025-12-01T08:45:00+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.25, 0.18, 0.35, -0.22, 0.15]', ARRAY['disinfo','alliance'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('tg_3307', 'telegram', 'c3d1f4aab2e5', '동맹 포기설을 퍼뜨리는 기사 링크', 'tmpl_001', 'ru', '2025-12-01T08:09:02+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[-0.02, 0.11, 0.48, 0.2, -0.15]', ARRAY['alliance','disinfo'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('tg_3308', 'telegram', 'e4f2g5hhi6j7', '러시아 매체에서 나온 정보인데 확인 필요', 'tmpl_007', 'ko', '2025-12-01T08:11:45+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.08, 0.22, 0.4, 0.18, -0.28]', ARRAY['russia','disinfo'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('tg_3309', 'telegram', 'c3d1f4aab2e5', '한국 정부 내부 문서 유출 - 동맹 재검토', 'tmpl_008', 'ru', '2025-12-01T08:35:20+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[-0.05, 0.15, 0.52, 0.25, -0.1]', ARRAY['leak','disinfo'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('tg_3310', 'telegram', 'f5g3h6ii7k8l', '美韩同盟动摇 - 最新消息', 'tmpl_009', 'zh', '2025-12-01T08:40:15+00:00', '2025-12-01T08:00:00Z_bucket_1h', '[0.3, 0.12, 0.28, -0.18, 0.22]', ARRAY['china','alliance'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10006', 'twitter', 'aff3e8c9d2b1', '후속 보도: 정부 관계자 발언 정리', 'tmpl_010', 'ko', '2025-12-01T09:05:00+00:00', '2025-12-01T09:00:00Z_bucket_1h', '[0.1, -0.02, 0.48, 0.3, -0.12]', ARRAY['security','update'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10007', 'twitter', 'g6h4i7jj8k9m', '[공식] 외교부 입장문 발표 예정', 'tmpl_011', 'ko', '2025-12-01T09:10:30+00:00', '2025-12-01T09:00:00Z_bucket_1h', '[0.02, 0.08, 0.55, 0.35, -0.05]', ARRAY['official','security'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;
INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('x_10008', 'twitter', 'h7i5j8kk9l0n', '한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.', 'tmpl_001', 'ko', '2025-12-01T09:15:45+00:00', '2025-12-01T09:00:00Z_bucket_1h', '[0.12, -0.03, 0.45, 0.22, -0.18]', ARRAY['security','alliance'], 'pseudonymized')
ON CONFLICT (post_id, platform) DO NOTHING;

-- URLs
INSERT INTO urls (url, domain) VALUES ('news.example.com/article/123', 'news.example.com') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('blog.example.kr/post/456', 'blog.example.kr') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('fakenews.xyz/story/789', 'fakenews.xyz') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('youtube.com/watch?v=abc123', 'youtube.com') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('youtube.com/watch?v=def456', 'youtube.com') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('youtube.com/watch?v=ghi789', 'youtube.com') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('anonnews.ru/post/45', 'anonnews.ru') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('rt.com/news/123', 'rt.com') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('leakedfiles.onion/doc/99', 'leakedfiles.onion') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('chinanews.example.cn/article/567', 'chinanews.example.cn') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('news.example.com/article/124', 'news.example.com') ON CONFLICT (url) DO NOTHING;
INSERT INTO urls (url, domain) VALUES ('mofa.go.kr/press/789', 'mofa.go.kr') ON CONFLICT (url) DO NOTHING;

-- Hashtags/Topics
INSERT INTO hashtags (tag) VALUES ('security') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('alliance') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('military') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('crisis') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('disinfo') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('factcheck') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('russia') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('leak') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('china') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('update') ON CONFLICT (tag) DO NOTHING;
INSERT INTO hashtags (tag) VALUES ('official') ON CONFLICT (tag) DO NOTHING;