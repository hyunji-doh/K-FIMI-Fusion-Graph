"""
데이터베이스 로더 모듈

샘플 CSV 데이터를 PostgreSQL 및 Neo4j에 적재합니다.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Union
from urllib.parse import urlparse

import pandas as pd
from loguru import logger

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 직접 csv_ingest 모듈 import (다른 ingest 모듈의 의존성 회피)
from src.ingest.csv_ingest import CSVIngester, PostData


# ============================================
# PostgreSQL 로더
# ============================================

class PostgresLoader:
    """
    PostgreSQL 데이터 로더
    
    샘플 데이터를 PostgreSQL에 적재합니다.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "k_fimi",
        user: str = "postgres",
        password: str = ""
    ):
        """
        PostgresLoader 초기화
        
        Args:
            host: 호스트
            port: 포트
            database: 데이터베이스 이름
            user: 사용자
            password: 비밀번호
        """
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password or os.getenv("POSTGRES_PASSWORD", "")
        }
        self._conn = None
        
        logger.info(f"PostgresLoader initialized: {host}:{port}/{database}")
    
    @property
    def conn(self):
        """데이터베이스 연결"""
        if self._conn is None:
            try:
                import psycopg2
                self._conn = psycopg2.connect(**self.connection_params)
                logger.info("PostgreSQL connected")
            except ImportError:
                raise ImportError("psycopg2 is required: pip install psycopg2-binary")
        return self._conn
    
    def execute_schema(self, schema_path: str = "db/postgres/schema.sql"):
        """
        스키마 SQL 실행
        
        Args:
            schema_path: 스키마 파일 경로
        """
        schema_file = PROJECT_ROOT / schema_path
        
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        with self.conn.cursor() as cur:
            cur.execute(schema_sql)
        
        self.conn.commit()
        logger.info("Schema executed successfully")
    
    def load_accounts(self, posts: list[PostData]) -> dict[str, str]:
        """
        계정 데이터 적재
        
        Args:
            posts: PostData 리스트
        
        Returns:
            {account_key: account_id} 매핑
        """
        account_map = {}
        accounts_seen = {}
        
        for post in posts:
            key = f"{post.platform}:{post.account_hash}"
            
            if key in accounts_seen:
                continue
            
            accounts_seen[key] = {
                "account_hash": post.account_hash,
                "platform": post.platform,
                "account_created_days": post.account_created_days,
                "followers": post.followers,
                "following": post.following,
                "is_verified": post.is_verified,
                "country_inferred": post.country_inferred,
                "primary_language": post.language
            }
        
        insert_sql = """
            INSERT INTO accounts (
                account_hash, platform, account_created_days,
                followers, following, is_verified,
                country_inferred, primary_language
            ) VALUES (
                %(account_hash)s, %(platform)s, %(account_created_days)s,
                %(followers)s, %(following)s, %(is_verified)s,
                %(country_inferred)s, %(primary_language)s
            )
            ON CONFLICT (account_hash, platform) DO UPDATE SET
                followers = EXCLUDED.followers,
                following = EXCLUDED.following,
                last_seen_at = NOW()
            RETURNING id;
        """
        
        with self.conn.cursor() as cur:
            for key, account in accounts_seen.items():
                cur.execute(insert_sql, account)
                result = cur.fetchone()
                account_map[key] = str(result[0])
        
        self.conn.commit()
        logger.info(f"Loaded {len(account_map)} accounts")
        
        return account_map
    
    def load_posts(
        self,
        posts: list[PostData],
        account_map: dict[str, str]
    ) -> dict[str, str]:
        """
        게시물 데이터 적재
        
        Args:
            posts: PostData 리스트
            account_map: 계정 ID 매핑
        
        Returns:
            {post_id: db_id} 매핑
        """
        post_map = {}
        
        insert_sql = """
            INSERT INTO posts (
                post_id, platform, account_id, account_hash,
                text, text_template_id, language,
                created_at_utc, time_bucket,
                embedding, topic_tags, privacy_flag
            ) VALUES (
                %(post_id)s, %(platform)s, %(account_id)s, %(account_hash)s,
                %(text)s, %(text_template_id)s, %(language)s,
                %(created_at_utc)s, %(time_bucket)s,
                %(embedding)s, %(topic_tags)s, %(privacy_flag)s
            )
            ON CONFLICT (post_id, platform) DO UPDATE SET
                text = EXCLUDED.text
            RETURNING id;
        """
        
        with self.conn.cursor() as cur:
            for post in posts:
                account_key = f"{post.platform}:{post.account_hash}"
                account_id = account_map.get(account_key)
                
                data = {
                    "post_id": post.post_id,
                    "platform": post.platform,
                    "account_id": account_id,
                    "account_hash": post.account_hash,
                    "text": post.text,
                    "text_template_id": post.text_template_id,
                    "language": post.language,
                    "created_at_utc": post.created_at,
                    "time_bucket": post.time_bucket,
                    "embedding": json.dumps(post.embedding) if post.embedding else None,
                    "topic_tags": post.topic_tags if post.topic_tags else None,
                    "privacy_flag": post.privacy_flag
                }
                
                cur.execute(insert_sql, data)
                result = cur.fetchone()
                post_map[post.post_id] = str(result[0])
        
        self.conn.commit()
        logger.info(f"Loaded {len(post_map)} posts")
        
        return post_map
    
    def load_urls(self, posts: list[PostData]) -> dict[str, str]:
        """
        URL 데이터 적재
        
        Args:
            posts: PostData 리스트
        
        Returns:
            {url: url_id} 매핑
        """
        url_map = {}
        urls_seen = set()
        
        for post in posts:
            for url in post.urls:
                if url and url not in urls_seen:
                    urls_seen.add(url)
        
        insert_sql = """
            INSERT INTO urls (url, domain)
            VALUES (%(url)s, %(domain)s)
            ON CONFLICT (url) DO UPDATE SET
                share_count = urls.share_count + 1,
                last_seen_at = NOW()
            RETURNING id;
        """
        
        with self.conn.cursor() as cur:
            for url in urls_seen:
                try:
                    parsed = urlparse(url if url.startswith("http") else f"http://{url}")
                    domain = parsed.netloc or url.split("/")[0]
                except Exception:
                    domain = url.split("/")[0]
                
                cur.execute(insert_sql, {"url": url, "domain": domain})
                result = cur.fetchone()
                url_map[url] = str(result[0])
        
        self.conn.commit()
        logger.info(f"Loaded {len(url_map)} URLs")
        
        return url_map
    
    def load_post_urls(
        self,
        posts: list[PostData],
        post_map: dict[str, str],
        url_map: dict[str, str]
    ):
        """게시물-URL 관계 적재"""
        insert_sql = """
            INSERT INTO post_urls (post_id, url_id)
            VALUES (%(post_id)s, %(url_id)s)
            ON CONFLICT DO NOTHING;
        """
        
        count = 0
        with self.conn.cursor() as cur:
            for post in posts:
                post_db_id = post_map.get(post.post_id)
                if not post_db_id:
                    continue
                
                for url in post.urls:
                    url_db_id = url_map.get(url)
                    if url_db_id:
                        cur.execute(insert_sql, {
                            "post_id": post_db_id,
                            "url_id": url_db_id
                        })
                        count += 1
        
        self.conn.commit()
        logger.info(f"Loaded {count} post-URL relationships")
    
    def load_hashtags(self, posts: list[PostData]) -> dict[str, str]:
        """해시태그(토픽 태그) 데이터 적재"""
        tag_map = {}
        tags_seen = set()
        
        for post in posts:
            for tag in post.topic_tags:
                if tag:
                    tags_seen.add(tag)
        
        insert_sql = """
            INSERT INTO hashtags (tag, usage_count)
            VALUES (%(tag)s, 1)
            ON CONFLICT (tag) DO UPDATE SET
                usage_count = hashtags.usage_count + 1,
                last_seen_at = NOW()
            RETURNING id;
        """
        
        with self.conn.cursor() as cur:
            for tag in tags_seen:
                cur.execute(insert_sql, {"tag": tag})
                result = cur.fetchone()
                tag_map[tag] = str(result[0])
        
        self.conn.commit()
        logger.info(f"Loaded {len(tag_map)} hashtags/topics")
        
        return tag_map
    
    def load_all(self, posts: list[PostData]):
        """
        모든 데이터 적재
        
        Args:
            posts: PostData 리스트
        """
        logger.info(f"Loading {len(posts)} posts to PostgreSQL...")
        
        account_map = self.load_accounts(posts)
        post_map = self.load_posts(posts, account_map)
        url_map = self.load_urls(posts)
        self.load_post_urls(posts, post_map, url_map)
        self.load_hashtags(posts)
        
        logger.info("PostgreSQL loading completed")
    
    def close(self):
        """연결 종료"""
        if self._conn:
            self._conn.close()
            self._conn = None


# ============================================
# Neo4j 로더
# ============================================

class Neo4jLoader:
    """
    Neo4j 데이터 로더
    
    샘플 데이터를 Neo4j에 적재합니다.
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = ""
    ):
        """
        Neo4jLoader 초기화
        
        Args:
            uri: Neo4j URI
            user: 사용자
            password: 비밀번호
        """
        self.uri = uri
        self.user = user
        self.password = password or os.getenv("NEO4J_PASSWORD", "")
        self._driver = None
        
        logger.info(f"Neo4jLoader initialized: {uri}")
    
    @property
    def driver(self):
        """Neo4j 드라이버"""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
                logger.info("Neo4j connected")
            except ImportError:
                raise ImportError("neo4j is required: pip install neo4j")
        return self._driver
    
    def execute_schema(self, schema_path: str = "db/neo4j/schema.cypher"):
        """
        스키마 Cypher 실행 (제약조건/인덱스만)
        
        Args:
            schema_path: 스키마 파일 경로
        """
        schema_file = PROJECT_ROOT / schema_path
        
        with open(schema_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # CREATE CONSTRAINT/INDEX 문만 추출
        lines = content.split(";")
        schema_statements = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("CREATE CONSTRAINT") or line.startswith("CREATE INDEX"):
                schema_statements.append(line)
        
        with self.driver.session() as session:
            for stmt in schema_statements:
                try:
                    session.run(stmt)
                except Exception as e:
                    # 이미 존재하는 제약조건은 무시
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Schema error: {e}")
        
        logger.info(f"Executed {len(schema_statements)} schema statements")
    
    def load_accounts(self, posts: list[PostData]):
        """계정 노드 생성"""
        accounts_seen = {}
        
        for post in posts:
            key = f"{post.platform}:{post.account_hash}"
            if key not in accounts_seen:
                accounts_seen[key] = {
                    "accountHash": post.account_hash,
                    "platform": post.platform,
                    "accountCreatedDays": post.account_created_days,
                    "followers": post.followers,
                    "following": post.following,
                    "isVerified": post.is_verified,
                    "countryInferred": post.country_inferred,
                    "primaryLanguage": post.language,
                    "firstSeenAt": post.created_at.isoformat()
                }
        
        query = """
            UNWIND $accounts AS acc
            MERGE (a:Account {accountHash: acc.accountHash, platform: acc.platform})
            SET a.accountCreatedDays = acc.accountCreatedDays,
                a.followers = acc.followers,
                a.following = acc.following,
                a.isVerified = acc.isVerified,
                a.countryInferred = acc.countryInferred,
                a.primaryLanguage = acc.primaryLanguage,
                a.firstSeenAt = datetime(acc.firstSeenAt),
                a.lastSeenAt = datetime()
        """
        
        with self.driver.session() as session:
            session.run(query, accounts=list(accounts_seen.values()))
        
        logger.info(f"Created {len(accounts_seen)} Account nodes")
    
    def load_posts(self, posts: list[PostData]):
        """게시물 노드 생성"""
        post_data = []
        
        for post in posts:
            post_data.append({
                "postId": post.post_id,
                "platform": post.platform,
                "accountHash": post.account_hash,
                "text": post.text,
                "textTemplateId": post.text_template_id,
                "language": post.language,
                "createdAtUtc": post.created_at.isoformat(),
                "timeBucket": post.time_bucket,
                "embedding": post.embedding,
                "privacyFlag": post.privacy_flag,
                "replyToPost": post.reply_to_post,
                "retweetOf": post.retweet_of
            })
        
        query = """
            UNWIND $posts AS p
            MERGE (post:Post {postId: p.postId, platform: p.platform})
            SET post.text = p.text,
                post.textTemplateId = p.textTemplateId,
                post.language = p.language,
                post.createdAtUtc = datetime(p.createdAtUtc),
                post.timeBucket = p.timeBucket,
                post.embedding = p.embedding,
                post.privacyFlag = p.privacyFlag
        """
        
        with self.driver.session() as session:
            session.run(query, posts=post_data)
        
        logger.info(f"Created {len(posts)} Post nodes")
    
    def load_urls(self, posts: list[PostData]):
        """URL 노드 생성"""
        urls_seen = set()
        
        for post in posts:
            for url in post.urls:
                if url:
                    urls_seen.add(url)
        
        url_data = []
        for url in urls_seen:
            try:
                parsed = urlparse(url if url.startswith("http") else f"http://{url}")
                domain = parsed.netloc or url.split("/")[0]
            except Exception:
                domain = url.split("/")[0]
            
            url_data.append({
                "url": url,
                "domain": domain
            })
        
        query = """
            UNWIND $urls AS u
            MERGE (url:URL {url: u.url})
            SET url.domain = u.domain,
                url.firstSeenAt = datetime()
        """
        
        with self.driver.session() as session:
            session.run(query, urls=url_data)
        
        logger.info(f"Created {len(url_data)} URL nodes")
    
    def load_topics(self, posts: list[PostData]):
        """토픽 노드 생성"""
        topics_seen = set()
        
        for post in posts:
            for tag in post.topic_tags:
                if tag:
                    topics_seen.add(tag)
        
        topic_data = [{"tag": t} for t in topics_seen]
        
        query = """
            UNWIND $topics AS t
            MERGE (topic:Topic {tag: t.tag})
        """
        
        with self.driver.session() as session:
            session.run(query, topics=topic_data)
        
        logger.info(f"Created {len(topics_seen)} Topic nodes")
    
    def load_domains(self, posts: list[PostData]):
        """도메인 노드 생성"""
        domains_seen = set()
        
        for post in posts:
            for url in post.urls:
                if url:
                    try:
                        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
                        domain = parsed.netloc or url.split("/")[0]
                        domains_seen.add(domain)
                    except Exception:
                        pass
        
        domain_data = [{"domain": d} for d in domains_seen]
        
        query = """
            UNWIND $domains AS d
            MERGE (domain:Domain {domain: d.domain})
        """
        
        with self.driver.session() as session:
            session.run(query, domains=domain_data)
        
        logger.info(f"Created {len(domains_seen)} Domain nodes")
    
    def create_authored_relationships(self, posts: list[PostData]):
        """AUTHORED 관계 생성"""
        rel_data = [
            {
                "accountHash": post.account_hash,
                "platform": post.platform,
                "postId": post.post_id,
                "createdAt": post.created_at.isoformat()
            }
            for post in posts
        ]
        
        query = """
            UNWIND $rels AS r
            MATCH (a:Account {accountHash: r.accountHash, platform: r.platform})
            MATCH (p:Post {postId: r.postId, platform: r.platform})
            MERGE (a)-[rel:AUTHORED]->(p)
            SET rel.at = datetime(r.createdAt)
        """
        
        with self.driver.session() as session:
            session.run(query, rels=rel_data)
        
        logger.info(f"Created {len(rel_data)} AUTHORED relationships")
    
    def create_contains_url_relationships(self, posts: list[PostData]):
        """CONTAINS_URL 관계 생성"""
        rel_data = []
        
        for post in posts:
            for url in post.urls:
                if url:
                    rel_data.append({
                        "postId": post.post_id,
                        "platform": post.platform,
                        "url": url
                    })
        
        query = """
            UNWIND $rels AS r
            MATCH (p:Post {postId: r.postId, platform: r.platform})
            MATCH (u:URL {url: r.url})
            MERGE (p)-[:CONTAINS_URL]->(u)
        """
        
        with self.driver.session() as session:
            session.run(query, rels=rel_data)
        
        logger.info(f"Created {len(rel_data)} CONTAINS_URL relationships")
    
    def create_about_topic_relationships(self, posts: list[PostData]):
        """ABOUT_TOPIC 관계 생성"""
        rel_data = []
        
        for post in posts:
            for tag in post.topic_tags:
                if tag:
                    rel_data.append({
                        "postId": post.post_id,
                        "platform": post.platform,
                        "tag": tag
                    })
        
        query = """
            UNWIND $rels AS r
            MATCH (p:Post {postId: r.postId, platform: r.platform})
            MATCH (t:Topic {tag: r.tag})
            MERGE (p)-[:ABOUT_TOPIC]->(t)
        """
        
        with self.driver.session() as session:
            session.run(query, rels=rel_data)
        
        logger.info(f"Created {len(rel_data)} ABOUT_TOPIC relationships")
    
    def create_url_domain_relationships(self, posts: list[PostData]):
        """URL -> Domain 관계 생성"""
        query = """
            MATCH (u:URL)
            WHERE u.domain IS NOT NULL
            MATCH (d:Domain {domain: u.domain})
            MERGE (u)-[:BELONGS_TO]->(d)
        """
        
        with self.driver.session() as session:
            result = session.run(query)
        
        logger.info("Created URL-Domain relationships")
    
    def create_reply_relationships(self, posts: list[PostData]):
        """REPLY_TO 관계 생성"""
        rel_data = [
            {
                "postId": post.post_id,
                "platform": post.platform,
                "replyTo": post.reply_to_post
            }
            for post in posts
            if post.reply_to_post
        ]
        
        if not rel_data:
            return
        
        query = """
            UNWIND $rels AS r
            MATCH (reply:Post {postId: r.postId, platform: r.platform})
            MATCH (original:Post {postId: r.replyTo})
            MERGE (reply)-[:REPLY_TO]->(original)
        """
        
        with self.driver.session() as session:
            session.run(query, rels=rel_data)
        
        logger.info(f"Created {len(rel_data)} REPLY_TO relationships")
    
    def create_retweet_relationships(self, posts: list[PostData]):
        """RETWEET_OF 관계 생성"""
        rel_data = [
            {
                "postId": post.post_id,
                "platform": post.platform,
                "retweetOf": post.retweet_of
            }
            for post in posts
            if post.retweet_of
        ]
        
        if not rel_data:
            return
        
        query = """
            UNWIND $rels AS r
            MATCH (retweet:Post {postId: r.postId, platform: r.platform})
            MATCH (original:Post {postId: r.retweetOf})
            MERGE (retweet)-[:RETWEET_OF]->(original)
        """
        
        with self.driver.session() as session:
            session.run(query, rels=rel_data)
        
        logger.info(f"Created {len(rel_data)} RETWEET_OF relationships")
    
    def create_similar_text_relationships(self, posts: list[PostData]):
        """동일 템플릿 텍스트 SIMILAR_TO 관계 생성"""
        # 동일 text_template_id를 가진 게시물 그룹화
        template_groups = {}
        for post in posts:
            if post.text_template_id:
                if post.text_template_id not in template_groups:
                    template_groups[post.text_template_id] = []
                template_groups[post.text_template_id].append(post)
        
        rel_data = []
        for template_id, group_posts in template_groups.items():
            if len(group_posts) < 2:
                continue
            
            for i, p1 in enumerate(group_posts):
                for p2 in group_posts[i+1:]:
                    rel_data.append({
                        "postId1": p1.post_id,
                        "platform1": p1.platform,
                        "postId2": p2.post_id,
                        "platform2": p2.platform,
                        "templateId": template_id
                    })
        
        if not rel_data:
            return
        
        query = """
            UNWIND $rels AS r
            MATCH (p1:Post {postId: r.postId1, platform: r.platform1})
            MATCH (p2:Post {postId: r.postId2, platform: r.platform2})
            MERGE (p1)-[rel:SIMILAR_TO]->(p2)
            SET rel.score = 1.0,
                rel.type = 'same_template',
                rel.templateId = r.templateId
        """
        
        with self.driver.session() as session:
            session.run(query, rels=rel_data)
        
        logger.info(f"Created {len(rel_data)} SIMILAR_TO relationships")
    
    def load_all(self, posts: list[PostData]):
        """
        모든 데이터 적재
        
        Args:
            posts: PostData 리스트
        """
        logger.info(f"Loading {len(posts)} posts to Neo4j...")
        
        # 노드 생성
        self.load_accounts(posts)
        self.load_posts(posts)
        self.load_urls(posts)
        self.load_topics(posts)
        self.load_domains(posts)
        
        # 관계 생성
        self.create_authored_relationships(posts)
        self.create_contains_url_relationships(posts)
        self.create_about_topic_relationships(posts)
        self.create_url_domain_relationships(posts)
        self.create_reply_relationships(posts)
        self.create_retweet_relationships(posts)
        self.create_similar_text_relationships(posts)
        
        logger.info("Neo4j loading completed")
    
    def close(self):
        """연결 종료"""
        if self._driver:
            self._driver.close()
            self._driver = None


# ============================================
# SQL 생성기 (연결 없이 SQL만 생성)
# ============================================

class SQLGenerator:
    """
    SQL/Cypher 쿼리 생성기
    
    데이터베이스 연결 없이 INSERT/CREATE 문을 생성합니다.
    """
    
    @staticmethod
    def generate_postgres_inserts(posts: list[PostData]) -> str:
        """
        PostgreSQL INSERT 문 생성
        
        Args:
            posts: PostData 리스트
        
        Returns:
            SQL INSERT 문자열
        """
        sql_lines = []
        sql_lines.append("-- K-FIMI Sample Data INSERT Statements")
        sql_lines.append("-- Generated at: " + datetime.now().isoformat())
        sql_lines.append("")
        
        # 계정 INSERT
        sql_lines.append("-- Accounts")
        accounts_seen = {}
        for post in posts:
            key = f"{post.platform}:{post.account_hash}"
            if key not in accounts_seen:
                accounts_seen[key] = post
                
                sql_lines.append(f"""INSERT INTO accounts (account_hash, platform, account_created_days, followers, following, is_verified, country_inferred, primary_language)
VALUES ('{post.account_hash}', '{post.platform}', {post.account_created_days}, {post.followers}, {post.following}, {str(post.is_verified).upper()}, '{post.country_inferred or ""}', '{post.language or ""}')
ON CONFLICT (account_hash, platform) DO NOTHING;""")
        
        sql_lines.append("")
        sql_lines.append("-- Posts")
        for post in posts:
            text_escaped = post.text.replace("'", "''")
            embedding_json = json.dumps(post.embedding) if post.embedding else "NULL"
            tags_array = "ARRAY[" + ",".join(f"'{t}'" for t in post.topic_tags) + "]" if post.topic_tags else "NULL"
            
            sql_lines.append(f"""INSERT INTO posts (post_id, platform, account_hash, text, text_template_id, language, created_at_utc, time_bucket, embedding, topic_tags, privacy_flag)
VALUES ('{post.post_id}', '{post.platform}', '{post.account_hash}', '{text_escaped}', '{post.text_template_id or ""}', '{post.language or ""}', '{post.created_at.isoformat()}', '{post.time_bucket or ""}', '{embedding_json}', {tags_array}, '{post.privacy_flag}')
ON CONFLICT (post_id, platform) DO NOTHING;""")
        
        sql_lines.append("")
        sql_lines.append("-- URLs")
        urls_seen = set()
        for post in posts:
            for url in post.urls:
                if url and url not in urls_seen:
                    urls_seen.add(url)
                    try:
                        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
                        domain = parsed.netloc or url.split("/")[0]
                    except Exception:
                        domain = url.split("/")[0]
                    
                    sql_lines.append(f"""INSERT INTO urls (url, domain) VALUES ('{url}', '{domain}') ON CONFLICT (url) DO NOTHING;""")
        
        sql_lines.append("")
        sql_lines.append("-- Hashtags/Topics")
        tags_seen = set()
        for post in posts:
            for tag in post.topic_tags:
                if tag and tag not in tags_seen:
                    tags_seen.add(tag)
                    sql_lines.append(f"""INSERT INTO hashtags (tag) VALUES ('{tag}') ON CONFLICT (tag) DO NOTHING;""")
        
        return "\n".join(sql_lines)
    
    @staticmethod
    def generate_neo4j_creates(posts: list[PostData]) -> str:
        """
        Neo4j CREATE/MERGE 문 생성
        
        Args:
            posts: PostData 리스트
        
        Returns:
            Cypher 문자열
        """
        cypher_lines = []
        cypher_lines.append("// K-FIMI Sample Data Cypher Statements")
        cypher_lines.append("// Generated at: " + datetime.now().isoformat())
        cypher_lines.append("")
        
        # 계정 노드
        cypher_lines.append("// Account Nodes")
        accounts_seen = {}
        for post in posts:
            key = f"{post.platform}:{post.account_hash}"
            if key not in accounts_seen:
                accounts_seen[key] = post
                
                cypher_lines.append(f"""MERGE (a:Account {{accountHash: '{post.account_hash}', platform: '{post.platform}'}})
SET a.accountCreatedDays = {post.account_created_days},
    a.followers = {post.followers},
    a.following = {post.following},
    a.isVerified = {str(post.is_verified).lower()},
    a.countryInferred = '{post.country_inferred or ""}',
    a.primaryLanguage = '{post.language or ""}';""")
        
        cypher_lines.append("")
        cypher_lines.append("// Post Nodes")
        for post in posts:
            text_escaped = post.text.replace("'", "\\'").replace('"', '\\"')
            embedding_str = str(post.embedding) if post.embedding else "[]"
            
            cypher_lines.append(f"""MERGE (p:Post {{postId: '{post.post_id}', platform: '{post.platform}'}})
SET p.text = '{text_escaped}',
    p.textTemplateId = '{post.text_template_id or ""}',
    p.language = '{post.language or ""}',
    p.createdAtUtc = datetime('{post.created_at.isoformat()}'),
    p.timeBucket = '{post.time_bucket or ""}',
    p.embedding = {embedding_str};""")
        
        cypher_lines.append("")
        cypher_lines.append("// URL Nodes")
        urls_seen = set()
        for post in posts:
            for url in post.urls:
                if url and url not in urls_seen:
                    urls_seen.add(url)
                    try:
                        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
                        domain = parsed.netloc or url.split("/")[0]
                    except Exception:
                        domain = url.split("/")[0]
                    
                    cypher_lines.append(f"""MERGE (u:URL {{url: '{url}'}}) SET u.domain = '{domain}';""")
        
        cypher_lines.append("")
        cypher_lines.append("// Topic Nodes")
        tags_seen = set()
        for post in posts:
            for tag in post.topic_tags:
                if tag and tag not in tags_seen:
                    tags_seen.add(tag)
                    cypher_lines.append(f"""MERGE (t:Topic {{tag: '{tag}'}});""")
        
        cypher_lines.append("")
        cypher_lines.append("// AUTHORED Relationships")
        for post in posts:
            cypher_lines.append(f"""MATCH (a:Account {{accountHash: '{post.account_hash}', platform: '{post.platform}'}})
MATCH (p:Post {{postId: '{post.post_id}', platform: '{post.platform}'}})
MERGE (a)-[:AUTHORED]->(p);""")
        
        cypher_lines.append("")
        cypher_lines.append("// CONTAINS_URL Relationships")
        for post in posts:
            for url in post.urls:
                if url:
                    cypher_lines.append(f"""MATCH (p:Post {{postId: '{post.post_id}', platform: '{post.platform}'}})
MATCH (u:URL {{url: '{url}'}})
MERGE (p)-[:CONTAINS_URL]->(u);""")
        
        cypher_lines.append("")
        cypher_lines.append("// ABOUT_TOPIC Relationships")
        for post in posts:
            for tag in post.topic_tags:
                if tag:
                    cypher_lines.append(f"""MATCH (p:Post {{postId: '{post.post_id}', platform: '{post.platform}'}})
MATCH (t:Topic {{tag: '{tag}'}})
MERGE (p)-[:ABOUT_TOPIC]->(t);""")
        
        return "\n".join(cypher_lines)


# ============================================
# 메인 실행
# ============================================

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="K-FIMI Database Loader")
    parser.add_argument("--csv", default="data/raw/sample_posts.csv", help="CSV 파일 경로")
    parser.add_argument("--target", choices=["postgres", "neo4j", "sql", "cypher", "all"], 
                        default="sql", help="적재 대상")
    parser.add_argument("--output", help="SQL/Cypher 출력 파일")
    
    # PostgreSQL 옵션
    parser.add_argument("--pg-host", default="localhost")
    parser.add_argument("--pg-port", type=int, default=5432)
    parser.add_argument("--pg-db", default="k_fimi")
    parser.add_argument("--pg-user", default="postgres")
    
    # Neo4j 옵션
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    
    args = parser.parse_args()
    
    # CSV 로드
    csv_path = PROJECT_ROOT / args.csv
    ingester = CSVIngester()
    df = ingester.load_csv(csv_path)
    posts = ingester.parse_posts(df)
    
    print(f"\n📊 Loaded {len(posts)} posts from CSV")
    print(f"   Platforms: {set(p.platform for p in posts)}")
    print()
    
    if args.target == "postgres":
        loader = PostgresLoader(
            host=args.pg_host,
            port=args.pg_port,
            database=args.pg_db,
            user=args.pg_user
        )
        loader.execute_schema()
        loader.load_all(posts)
        loader.close()
        
    elif args.target == "neo4j":
        loader = Neo4jLoader(
            uri=args.neo4j_uri,
            user=args.neo4j_user
        )
        loader.execute_schema()
        loader.load_all(posts)
        loader.close()
        
    elif args.target == "sql":
        sql = SQLGenerator.generate_postgres_inserts(posts)
        output_file = args.output or PROJECT_ROOT / "db/postgres/sample_data.sql"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(sql)
        print(f" PostgreSQL INSERT 문 생성: {output_file}")
        
    elif args.target == "cypher":
        cypher = SQLGenerator.generate_neo4j_creates(posts)
        output_file = args.output or PROJECT_ROOT / "db/neo4j/sample_data.cypher"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cypher)
        print(f" Neo4j Cypher 문 생성: {output_file}")
        
    elif args.target == "all":
        # SQL 생성
        sql = SQLGenerator.generate_postgres_inserts(posts)
        sql_file = PROJECT_ROOT / "db/postgres/sample_data.sql"
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write(sql)
        print(f" PostgreSQL INSERT 문 생성: {sql_file}")
        
        # Cypher 생성
        cypher = SQLGenerator.generate_neo4j_creates(posts)
        cypher_file = PROJECT_ROOT / "db/neo4j/sample_data.cypher"
        with open(cypher_file, "w", encoding="utf-8") as f:
            f.write(cypher)
        print(f" Neo4j Cypher 문 생성: {cypher_file}")


if __name__ == "__main__":
    main()

