# -*- coding: utf-8 -*-
import urllib.request
from html.parser import HTMLParser
from typing import Optional

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.ignore = False
        
    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style", "meta", "link", "head", "noscript", "footer", "nav", "iframe"]:
            self.ignore = True
            
    def handle_endtag(self, tag):
        if tag in ["script", "style", "meta", "link", "head", "noscript", "footer", "nav", "iframe"]:
            self.ignore = False
            
    def handle_data(self, data):
        if not self.ignore:
            cleaned = data.strip()
            if cleaned:
                self.text.append(cleaned)
                
    def get_text(self) -> str:
        return "\n".join(self.text)

def fetch_url_text(url: str, timeout: int = 10) -> str:
    """
    지정된 URL의 HTML 페이지를 가져와 순수 본문 텍스트만 추출하여 반환합니다.
    """
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html_bytes = response.read()
            # 인코딩 처리
            encoding = response.headers.get_content_charset() or "utf-8"
            html_content = html_bytes.decode(encoding, errors="ignore")
            
        extractor = HTMLTextExtractor()
        extractor.feed(html_content)
        return extractor.get_text()
    except Exception as e:
        raise RuntimeError(f"웹페이지 데이터 수집 실패: {str(e)}")
