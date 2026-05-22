"""
IP 주소 익명화 모듈

IP 주소를 국가/대륙 수준으로만 사용하도록 익명화합니다.
"""

import ipaddress
from typing import Optional, Tuple
from dataclasses import dataclass

from loguru import logger

try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.warning("geoip2 not available. Using basic IP anonymization.")


@dataclass
class IPInfo:
    """IP 정보 (익명화된)"""
    country_code: Optional[str] = None
    continent_code: Optional[str] = None
    is_private: bool = False
    is_valid: bool = True
    
    def to_dict(self) -> dict:
        return {
            "country_code": self.country_code,
            "continent_code": self.continent_code,
            "is_private": self.is_private,
            "is_valid": self.is_valid
        }


class IPAnonymizer:
    """
    IP 주소 익명화기
    
    IP 주소를 국가/대륙 수준으로만 추출합니다.
    """
    
    # 대륙 코드 매핑
    CONTINENT_MAP = {
        "AS": "Asia",
        "EU": "Europe",
        "NA": "North America",
        "SA": "South America",
        "AF": "Africa",
        "OC": "Oceania",
        "AN": "Antarctica"
    }
    
    def __init__(self, geoip_db_path: Optional[str] = None):
        """
        IPAnonymizer 초기화
        
        Args:
            geoip_db_path: GeoIP2 데이터베이스 파일 경로 (선택사항)
        """
        self.geoip_reader = None
        
        if geoip_db_path and GEOIP2_AVAILABLE:
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
                logger.info(f"GeoIP2 database loaded: {geoip_db_path}")
            except Exception as e:
                logger.warning(f"Failed to load GeoIP2 database: {e}")
    
    def anonymize(self, ip_address: str) -> IPInfo:
        """
        IP 주소 익명화
        
        Args:
            ip_address: IP 주소 문자열
        
        Returns:
            익명화된 IP 정보
        """
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return IPInfo(is_valid=False)
        
        # 사설 IP 확인
        if ip.is_private:
            return IPInfo(is_private=True)
        
        # GeoIP2를 사용한 국가/대륙 추출
        if self.geoip_reader:
            try:
                response = self.geoip_reader.country(ip_address)
                country_code = response.country.iso_code
                continent_code = response.continent.code
                
                return IPInfo(
                    country_code=country_code,
                    continent_code=continent_code,
                    is_private=False,
                    is_valid=True
                )
            except geoip2.errors.AddressNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"GeoIP2 lookup error: {e}")
        
        # 기본 익명화: IP 주소의 마지막 옥텟을 0으로 설정
        # 실제로는 국가 코드만 반환하는 것이 더 안전
        return IPInfo(
            country_code=None,  # 알 수 없음
            continent_code=None,
            is_private=False,
            is_valid=True
        )
    
    def anonymize_to_country(self, ip_address: str) -> Optional[str]:
        """
        IP 주소를 국가 코드로만 변환
        
        Args:
            ip_address: IP 주소
        
        Returns:
            국가 코드 (예: "KR", "US") 또는 None
        """
        info = self.anonymize(ip_address)
        return info.country_code
    
    def anonymize_to_continent(self, ip_address: str) -> Optional[str]:
        """
        IP 주소를 대륙 코드로만 변환
        
        Args:
            ip_address: IP 주소
        
        Returns:
            대륙 코드 (예: "AS", "EU") 또는 None
        """
        info = self.anonymize(ip_address)
        return info.continent_code
    
    def get_continent_name(self, continent_code: str) -> Optional[str]:
        """대륙 코드를 대륙 이름으로 변환"""
        return self.CONTINENT_MAP.get(continent_code)


# 모듈 테스트용
if __name__ == "__main__":
    anonymizer = IPAnonymizer()
    
    test_ips = [
        "192.168.1.1",  # 사설 IP
        "8.8.8.8",      # Google DNS
        "1.1.1.1",      # Cloudflare DNS
    ]
    
    print("IP Anonymization Test:")
    print("=" * 60)
    
    for ip in test_ips:
        info = anonymizer.anonymize(ip)
        print(f"\nIP: {ip}")
        print(f"  Country: {info.country_code}")
        print(f"  Continent: {info.continent_code}")
        print(f"  Private: {info.is_private}")
        print(f"  Valid: {info.is_valid}")


