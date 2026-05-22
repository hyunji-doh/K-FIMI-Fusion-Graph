-- ============================================
-- K-FIMI Fusion Graph - PostgreSQL Schema
-- 외국발 영향·허위정보 캠페인 탐지 시스템
-- ============================================

-- 확장 모듈 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 텍스트 유사도 검색용

-- ============================================
-- 1. 계정 테이블 (Accounts)
-- ============================================
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_hash VARCHAR(64) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    
    -- 계정 메타데이터
    account_created_days INTEGER DEFAULT 0,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    
    -- 추론된 정보
    country_inferred VARCHAR(10),
    primary_language VARCHAR(10),
    
    -- 분석 결과
    suspicion_score FLOAT DEFAULT 0.0,
    cluster_id INTEGER,
    campaign_id UUID,
    
    -- 타임스탬프
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 유니크 제약
    CONSTRAINT uq_account_platform UNIQUE (account_hash, platform)
);

-- 인덱스
CREATE INDEX idx_accounts_platform ON accounts(platform);
CREATE INDEX idx_accounts_country ON accounts(country_inferred);
CREATE INDEX idx_accounts_suspicion ON accounts(suspicion_score DESC);
CREATE INDEX idx_accounts_cluster ON accounts(cluster_id);
CREATE INDEX idx_accounts_campaign ON accounts(campaign_id);

-- ============================================
-- 2. 게시물 테이블 (Posts)
-- ============================================
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id VARCHAR(100) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    
    -- 작성자 참조
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    account_hash VARCHAR(64),
    
    -- 콘텐츠
    text TEXT NOT NULL,
    text_template_id VARCHAR(50),
    language VARCHAR(10),
    
    -- 시간 정보
    created_at_utc TIMESTAMPTZ NOT NULL,
    time_bucket VARCHAR(50),
    
    -- 참여 지표
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    
    -- 연결 정보
    reply_to_post_id UUID REFERENCES posts(id) ON DELETE SET NULL,
    retweet_of_post_id UUID REFERENCES posts(id) ON DELETE SET NULL,
    
    -- 미디어
    media_hash VARCHAR(64),
    
    -- 임베딩 (vector 타입 또는 JSONB)
    embedding JSONB,
    
    -- 분석 결과
    topic_tags TEXT[],
    sentiment_score FLOAT,
    is_coordinated BOOLEAN DEFAULT FALSE,
    campaign_id UUID,
    
    -- 개인정보 보호
    privacy_flag VARCHAR(20) DEFAULT 'pseudonymized',
    
    -- 타임스탬프
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 유니크 제약
    CONSTRAINT uq_post_platform UNIQUE (post_id, platform)
);

-- 인덱스
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_account ON posts(account_id);
CREATE INDEX idx_posts_created ON posts(created_at_utc DESC);
CREATE INDEX idx_posts_time_bucket ON posts(time_bucket);
CREATE INDEX idx_posts_template ON posts(text_template_id);
CREATE INDEX idx_posts_language ON posts(language);
CREATE INDEX idx_posts_campaign ON posts(campaign_id);
CREATE INDEX idx_posts_tags ON posts USING GIN(topic_tags);
CREATE INDEX idx_posts_text_search ON posts USING GIN(to_tsvector('simple', text));

-- ============================================
-- 3. URL 테이블 (URLs)
-- ============================================
CREATE TABLE IF NOT EXISTS urls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL,
    
    -- 메타데이터
    title TEXT,
    description TEXT,
    
    -- 신뢰도 점수
    credibility_score FLOAT DEFAULT 0.5,
    category VARCHAR(50),
    
    -- 통계
    share_count INTEGER DEFAULT 0,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 분석 결과
    is_shortened BOOLEAN DEFAULT FALSE,
    is_known_disinfo BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_urls_domain ON urls(domain);
CREATE INDEX idx_urls_credibility ON urls(credibility_score);
CREATE INDEX idx_urls_disinfo ON urls(is_known_disinfo) WHERE is_known_disinfo = TRUE;

-- ============================================
-- 4. 해시태그 테이블 (Hashtags)
-- ============================================
CREATE TABLE IF NOT EXISTS hashtags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag VARCHAR(255) NOT NULL UNIQUE,
    
    -- 통계
    usage_count INTEGER DEFAULT 0,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 분석 결과
    is_trending BOOLEAN DEFAULT FALSE,
    campaign_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_hashtags_usage ON hashtags(usage_count DESC);
CREATE INDEX idx_hashtags_trending ON hashtags(is_trending) WHERE is_trending = TRUE;

-- ============================================
-- 5. 도메인 테이블 (Domains)
-- ============================================
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255) NOT NULL UNIQUE,
    
    -- 메타데이터
    category VARCHAR(50),
    country VARCHAR(10),
    
    -- 신뢰도
    credibility_score FLOAT DEFAULT 0.5,
    is_news_outlet BOOLEAN DEFAULT FALSE,
    is_government BOOLEAN DEFAULT FALSE,
    is_social_media BOOLEAN DEFAULT FALSE,
    is_known_disinfo BOOLEAN DEFAULT FALSE,
    
    -- 통계
    total_shares INTEGER DEFAULT 0,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_domains_credibility ON domains(credibility_score);
CREATE INDEX idx_domains_category ON domains(category);

-- ============================================
-- 6. 캠페인 테이블 (Campaigns)
-- ============================================
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255),
    description TEXT,
    
    -- 탐지 정보
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    confidence_score FLOAT,
    detection_method VARCHAR(50),
    
    -- 통계
    account_count INTEGER DEFAULT 0,
    post_count INTEGER DEFAULT 0,
    
    -- 시간 범위
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    
    -- 특성
    primary_narratives TEXT[],
    primary_platforms TEXT[],
    target_countries TEXT[],
    
    -- 상태
    status VARCHAR(20) DEFAULT 'detected',
    verified_by VARCHAR(100),
    verified_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 7. 관계 테이블들 (Junction Tables)
-- ============================================

-- 게시물-URL 관계
CREATE TABLE IF NOT EXISTS post_urls (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    url_id UUID REFERENCES urls(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (post_id, url_id)
);

-- 게시물-해시태그 관계
CREATE TABLE IF NOT EXISTS post_hashtags (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    hashtag_id UUID REFERENCES hashtags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (post_id, hashtag_id)
);

-- 계정 팔로우 관계
CREATE TABLE IF NOT EXISTS account_follows (
    follower_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    followee_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, followee_id)
);

-- 텍스트 유사도 관계
CREATE TABLE IF NOT EXISTS text_similarities (
    post_id_1 UUID REFERENCES posts(id) ON DELETE CASCADE,
    post_id_2 UUID REFERENCES posts(id) ON DELETE CASCADE,
    similarity_score FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (post_id_1, post_id_2),
    CHECK (post_id_1 < post_id_2)  -- 중복 방지
);

CREATE INDEX idx_text_sim_score ON text_similarities(similarity_score DESC);

-- 협응 행위 관계
CREATE TABLE IF NOT EXISTS coordinated_pairs (
    account_id_1 UUID REFERENCES accounts(id) ON DELETE CASCADE,
    account_id_2 UUID REFERENCES accounts(id) ON DELETE CASCADE,
    shared_url_count INTEGER DEFAULT 0,
    avg_time_diff_seconds FLOAT,
    confidence_score FLOAT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (account_id_1, account_id_2),
    CHECK (account_id_1 < account_id_2)
);

-- ============================================
-- 8. 뷰 (Views)
-- ============================================

-- 플랫폼별 게시물 통계
CREATE OR REPLACE VIEW v_platform_stats AS
SELECT 
    platform,
    COUNT(*) as post_count,
    COUNT(DISTINCT account_id) as account_count,
    MIN(created_at_utc) as first_post,
    MAX(created_at_utc) as last_post
FROM posts
GROUP BY platform;

-- 의심 계정 뷰
CREATE OR REPLACE VIEW v_suspicious_accounts AS
SELECT 
    a.*,
    COUNT(p.id) as post_count,
    COUNT(DISTINCT p.text_template_id) as template_count
FROM accounts a
LEFT JOIN posts p ON a.id = p.account_id
WHERE a.suspicion_score > 0.7
   OR a.account_created_days < 30
   OR (a.following > 1000 AND a.followers < 100)
GROUP BY a.id;

-- 중복 텍스트 뷰
CREATE OR REPLACE VIEW v_duplicate_texts AS
SELECT 
    text_template_id,
    text,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT account_id) as unique_accounts,
    array_agg(DISTINCT platform) as platforms
FROM posts
WHERE text_template_id IS NOT NULL
GROUP BY text_template_id, text
HAVING COUNT(*) > 1;

-- ============================================
-- 9. 함수 (Functions)
-- ============================================

-- 계정 통계 업데이트 함수
CREATE OR REPLACE FUNCTION update_account_stats(p_account_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE accounts 
    SET 
        last_seen_at = NOW(),
        updated_at = NOW()
    WHERE id = p_account_id;
END;
$$ LANGUAGE plpgsql;

-- URL 공유 수 증가 함수
CREATE OR REPLACE FUNCTION increment_url_share(p_url TEXT)
RETURNS UUID AS $$
DECLARE
    v_url_id UUID;
BEGIN
    INSERT INTO urls (url, domain)
    VALUES (p_url, split_part(p_url, '/', 3))
    ON CONFLICT (url) DO UPDATE SET
        share_count = urls.share_count + 1,
        last_seen_at = NOW()
    RETURNING id INTO v_url_id;
    
    RETURN v_url_id;
END;
$$ LANGUAGE plpgsql;

-- 트리거: 게시물 삽입 시 계정 통계 업데이트
CREATE OR REPLACE FUNCTION trigger_update_account_on_post()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.account_id IS NOT NULL THEN
        PERFORM update_account_stats(NEW.account_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_post_insert
    AFTER INSERT ON posts
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_account_on_post();

-- ============================================
-- 10. 초기 데이터 (시드 데이터)
-- ============================================

-- 알려진 허위정보 도메인 시드
INSERT INTO domains (domain, category, credibility_score, is_known_disinfo) VALUES
('fakenews.xyz', 'suspicious', 0.1, TRUE),
('anonnews.ru', 'suspicious', 0.2, TRUE),
('leakedfiles.onion', 'suspicious', 0.1, TRUE)
ON CONFLICT (domain) DO NOTHING;

-- 신뢰할 수 있는 도메인 시드
INSERT INTO domains (domain, category, credibility_score, is_news_outlet, is_government) VALUES
('yna.co.kr', 'news_agency', 0.85, TRUE, FALSE),
('mofa.go.kr', 'government', 0.95, FALSE, TRUE),
('youtube.com', 'social_media', 0.5, FALSE, FALSE)
ON CONFLICT (domain) DO NOTHING;

