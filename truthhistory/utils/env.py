# -*- coding: utf-8 -*-
"""프로젝트 루트의 `.env` 파일을 OS 환경 변수로 로드하는 경량 파서.

python-dotenv 의존성 없이 동작(서버리스 225MB 제약 대응).

규칙:
- `KEY=VALUE` 한 줄 한 항목. `#` 시작 줄은 주석, 빈 줄 무시.
- `export KEY=VALUE` 형식 허용.
- 값의 양끝 따옴표(' 또는 ")는 제거.
- 이미 설정된 OS 환경 변수는 .env 값으로 덮어쓰지 않음(환경 변수 우선).
"""
import os
from pathlib import Path

def load_env(path: str = ".env") -> int:
    """`.env` 파일을 읽어 OS 환경 변수에 반영하고 로드된 키 개수를 반환한다.

    파일이 없거나 읽을 수 없으면 조용히 0을 반환(에러 아님).
    """
    env_path = Path(path)
    if not env_path.is_file():
        return 0

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0

    loaded = 0
    for raw in lines:
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded += 1
    return loaded
