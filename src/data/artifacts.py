"""Fetch immutable deployment data artifacts into the runtime cache."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from config import DATA_BASE_URL


def ensure_artifact(path: Path) -> Path:
    """Return a local artifact, downloading it atomically when configured remotely."""
    if path.exists():
        return path
    if not DATA_BASE_URL:
        raise FileNotFoundError(
            f"Missing data artifact: {path}. Build it locally or set DATA_BASE_URL."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{DATA_BASE_URL}/{quote(path.name)}"
    temporary: Path | None = None
    try:
        request = Request(url, headers={"User-Agent": "global-commodity-dashboard/1.0"})
        with urlopen(request, timeout=180) as response, tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".part", delete=False
        ) as target:
            temporary = Path(target.name)
            shutil.copyfileobj(response, target, length=1024 * 1024)
        if not temporary.stat().st_size:
            raise RuntimeError(f"Downloaded artifact is empty: {url}")
        temporary.replace(path)
    except (OSError, URLError) as exc:
        if temporary:
            temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Unable to download data artifact {url}: {exc}") from exc
    return path
