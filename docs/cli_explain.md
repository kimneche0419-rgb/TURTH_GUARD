# TruthGuard SDK: CLI & Explain API 상세 구현 설계서

본 문서는 `click` 라이브러리를 이용한 CLI(명령줄 인터페이스) 설계 및 터미널 시각화 출력, 그리고 XAI 반환 객체를 검증하는 Explain API의 내부 구현을 상술합니다.

---

## 1. CLI 아키텍처 및 구현 코드

터미널 도구의 완성도를 위해 `click` 라이브러리와 터미널 서식화 도구인 `rich`를 사용하여 CLI를 구현합니다.

### 1.1 Python CLI 구현 예시 (`truthguard/cli/main.py`)

```python
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from truthguard import detect_text, detect_image

console = Console()

@click.group()
def main():
    """TruthGuard SDK 명령줄 스캔 도구"""
    pass

@main.command(name="scan")
@click.argument("target_path", type=click.Path(exists=True))
@click.option("-c", "--config", type=click.Path(), help="설정 JSON 파일 경로")
@click.option("-f", "--format", type=click.Choice(["text", "json", "table"]), default="text", help="출력 형식")
@click.option("--threshold", type=float, default=0.5, help="변조 위험 판정 임계점")
def scan(target_path: str, config: str, format: str, threshold: float):
    """
    지정된 파일(텍스트, 이미지, 비디오)의 변조 신뢰도를 스캔합니다.
    """
    # 1. 파일 확장자 분석을 통한 유형 탐색
    file_ext = target_path.split(".")[-1].lower()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description=f"스캔 중: {target_path}...", total=None)
        
        # 2. 개별 모듈 분석 위임
        if file_ext in ["txt", "md"]:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            result = detect_text(content)
        elif file_ext in ["jpg", "jpeg", "png", "webp"]:
            result = detect_image(target_path)
        else:
            console.print(f"[bold red]에러:[/bold red] 지원하지 않는 파일 형식입니다 (.{file_ext})")
            raise click.exceptions.ExitCodeException(2)

    # 3. 포맷별 결과 출력 분기
    if format == "json":
        console.print_json(result.model_dump_json(indent=2))
        
    elif format == "table":
        table = Table(title="[bold green]TruthGuard Scan Summary[/bold green]")
        table.add_column("Target File", style="cyan")
        table.add_column("Credibility Score", style="magenta")
        table.add_column("Risk Level", style="yellow")
        table.add_column("Manipulated?", style="red")
        
        table.add_row(
            target_path,
            f"{result.credibility_score:.2f}",
            result.risk_level,
            "YES" if result.is_manipulated else "NO"
        )
        console.print(table)
        
    else:  # 'text' 기본 모드
        console.print("\n[bold]========== TruthGuard Scan Report ==========[/bold]")
        console.print(f"대상 파일: [cyan]{target_path}[/cyan]")
        console.print(f"종합 신뢰도: {result.credibility_score:.2f} ({result.risk_level} RISK)")
        
        if result.is_manipulated:
            console.print("스캔 결과: [bold red]변조 및 허위 정보 의심[/bold red]")
        else:
            console.print("스캔 결과: [bold green]정상 콘텐츠[/bold green]")
            
        console.print("\n[bold]탐지 근거:[/bold]")
        for reason in result.reasons:
            console.print(f" - [yellow]{reason}[/yellow]")
            
    # 판정 결과에 따른 프로세스 종료 코드 리턴 (CI/CD 자동화 연동용)
    if result.is_manipulated:
        raise click.exceptions.ExitCodeException(1)
    else:
        raise click.exceptions.ExitCodeException(0)
```

---

## 2. Explain API JSON 스포팅 엔진 구현

XAI 출력을 JSON 규격으로 가공하고 엄격히 검증하는 `ExplainEngine` 클래스 설계입니다.

```python
from typing import List, Dict, Any
from pydantic import ValidationError
from truthguard.base import AnalysisResult

class ExplainEngine:
    """
    모듈별 분석 리포트를 기반으로 최종 설명 JSON 데이터 포맷팅 및 검증 수행
    """
    
    @staticmethod
    def format_explanations(
        target_file: str, 
        media_type: str, 
        result: AnalysisResult,
        anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        AnalysisResult 객체와 세부 에러 코드를 결합하여 표준화된 JSON 데이터 빌드
        """
        response_data = {
            "target_file": target_file,
            "media_type": media_type,
            "decision": {
                "is_manipulated": result.is_manipulated,
                "credibility_score": round(result.credibility_score, 2),
                "risk_level": result.risk_level
            },
            "metrics": {
                "ai_generation_probability": round(result.ai_probability, 4),
                "editing_artifact_score": round(result.analysis_details.get("artifact_score", 0.0), 4),
                "semantic_consistency_score": round(result.analysis_details.get("semantic_score", 1.0), 4)
            },
            "explanations": []
        }
        
        for anomaly in anomalies:
            response_data["explanations"].append({
                "code": anomaly.get("code", "UNKNOWN_ERR"),
                "severity": anomaly.get("severity", "INFO"),
                "message": anomaly.get("message", ""),
                "location": anomaly.get("location", "global")
            })
            
        return response_data
```

---

## 3. 에러 핸들링 및 Exit Code 표준 규정

오픈소스 SDK의 도구 연동성 극대화를 위해 비정상 상황에 따른 Exit Code를 엄격히 강제하고 시스템 에러 블록을 처리합니다.

```python
import sys
import logging

# 에러 로거 설정
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("TruthGuard")

def run_cli_safe():
    """
    CLI 실행 진입점에서 발생하는 공통 에러 블록 제어
    """
    try:
        main()
    except click.exceptions.ExitCodeException as e:
        sys.exit(e.exit_code)
    except FileNotFoundError as e:
        logger.error(f"지정한 파일 또는 경로를 찾을 수 없습니다: {str(e)}")
        sys.exit(2)
    except ImportError as e:
        logger.error(f"의존성 패키지 임포트 오류 (지연 로딩 실패): {str(e)}")
        sys.exit(3)
    except Exception as e:
        logger.error(f"알 수 없는 런타임 엔진 오류: {str(e)}")
        sys.exit(5)
```
