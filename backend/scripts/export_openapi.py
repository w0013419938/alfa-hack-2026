"""Экспорт схемы API в docs/openapi.json.

Запуск (из корня репозитория):
    docker compose run --rm -v "$PWD/docs:/docs" backend python -m scripts.export_openapi /docs/openapi.json
"""

import json
import sys
from pathlib import Path

from app.main import app

target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Схема API сохранена в {target}")
