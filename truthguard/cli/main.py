# -*- coding: utf-8 -*-
import os
import json
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from truthguard import detect_text, detect_image, detect_video, detect_audio

console = Console()

@click.group()
def main():
    """TruthGuard SDK: AI 콘텐츠 신뢰성 평가 오픈소스 프레임워크 CLI"""
    pass

@main.command(name="scan")
@click.argument("target_path", type=click.Path(exists=True))
@click.option("-c", "--config", type=click.Path(), help="설정 JSON 파일 경로")
@click.option("-f", "--format", type=click.Choice(["text", "json", "table"]), default="text", help="출력 형식")
@click.option("--threshold", type=float, default=0.5, help="변조 위험 판정 임계점")
def scan(target_path: str, config: str, format: str, threshold: float):
    """
    지정된 파일(텍스트, 이미지, 비디오, 오디오)의 변조 신뢰도를 스캔합니다.
    """
    file_ext = target_path.split(".")[-1].lower()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task(description=f"스캔 중: {target_path}...", total=None)
        
        try:
            if file_ext in ["txt", "md"]:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                result = detect_text(content)
            elif file_ext in ["jpg", "jpeg", "png", "webp"]:
                result = detect_image(target_path)
            elif file_ext in ["mp4", "avi", "mov", "mkv"]:
                result = detect_video(target_path)
            elif file_ext in ["wav", "mp3", "m4a", "flac"]:
                result = detect_audio(target_path)
            else:
                console.print(f"[bold red]에러:[/bold red] 지원하지 않는 파일 형식입니다 (.{file_ext})")
                raise click.ClickException("Unsupported file format")
        except Exception as e:
            console.print(f"[bold red]런타임 에러:[/bold red] {str(e)}")
            # 에러 발생 시 Exit Code 2 (사용자/포맷/파일 에러)
            import sys
            sys.exit(2)

    # 포맷별 결과 출력
    if format == "json":
        from truthguard.explain.engine import ExplainEngine
        
        media_type = "unknown"
        if file_ext in ["txt", "md"]:
            media_type = "text"
        elif file_ext in ["jpg", "jpeg", "png", "webp"]:
            media_type = "image"
        elif file_ext in ["mp4", "avi", "mov", "mkv"]:
            media_type = "video"
        elif file_ext in ["wav", "mp3", "m4a", "flac"]:
            media_type = "audio"
            
        anomalies = []
        for reason in result.reasons:
            anomalies.append({
                "code": "MANIPULATION_DETECTED",
                "severity": "CRITICAL" if result.risk_level in ["HIGH", "CRITICAL"] else "WARNING",
                "message": reason,
                "location": "global"
            })
            
        explain_report = ExplainEngine.format_explanations(
            target_file=target_path,
            media_type=media_type,
            result=result,
            anomalies=anomalies
        )
        console.print_json(data=explain_report)
        
    elif format == "table":
        table = Table(title="[bold green]TruthGuard Scan Summary[/bold green]")
        table.add_column("Target File", style="cyan")
        table.add_column("Credibility Score", style="magenta")
        table.add_column("Risk Level", style="yellow")
        table.add_column("Manipulated?", style="red")
        
        table.add_row(
            os.path.basename(target_path),
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
            console.log("스캔 결과: [bold red]변조 및 허위 정보 의심[/bold red]")
        else:
            console.log("스캔 결과: [bold green]정상 콘텐츠[/bold green]")
            
        console.print("\n[bold]탐지 근거:[/bold]")
        if result.reasons:
            for reason in result.reasons:
                console.print(f" - [yellow]{reason}[/yellow]")
        else:
            console.print(" - 특이사항 없음")

    # 변조 판정 여부에 따른 프로세스 종료 코드 리턴 (CI/CD 자동화 연동용)
    import sys
    if result.is_manipulated:
        sys.exit(1)
    else:
        sys.exit(0)

@main.command(name="init")
@click.option("-f", "--force", is_flag=True, help="기존 설정 파일이 있는 경우 덮어씁니다.")
def init(force: bool):
    """
    TruthGuard 작업 환경 및 설정 파일을 초기화합니다.
    """
    config_path = "truthguard.json"
    
    # 1. 기존 설정 확인
    if os.path.exists(config_path) and not force:
        console.print(f"[bold yellow]주의:[/bold yellow] 이미 `{config_path}` 파일이 존재합니다.")
        console.print("덮어쓰려면 [bold cyan]--force[/bold cyan] 옵션을 사용하십시오.")
        raise click.ClickException("Config file already exists")

    # 2. uploads 디렉터리 생성
    os.makedirs("uploads", exist_ok=True)
    
    # 3. 설정 데이터 작성
    default_config = {
        "threshold": 0.5,
        "media_directories": {
            "uploads": "uploads"
        },
        "explain_format": "text"
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        console.print(f"[bold red]설정 파일 저장 실패:[/bold red] {str(e)}")
        raise click.ClickException(f"Failed to save config: {str(e)}")
        
    console.print("[bold green]Success:[/bold green] TruthGuard SDK 환경 초기화 완료!")
    console.print(f" - 생성됨: [cyan]{config_path}[/cyan]")
    console.print(" - 생성됨: [cyan]uploads/[/cyan] 디렉터리")
    console.print("\n[bold]다음 단계:[/bold]")
    console.print(" 1. `truthguard scan <파일경로>` 또는 `tg scan <파일경로>` 명령어로 파일을 분석해보세요.")
    console.print(" 2. `python truthguard_server.py`를 실행하여 REST API 서버를 시작하거나,")
    console.print("    `run.bat` 스크립트를 사용해 대시보드와 서버를 한 번에 기동하세요.")

if __name__ == "__main__":
    main()

