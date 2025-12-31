import os
import re
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from processor import clear_temp_folder, process_pdf_and_script


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _input_dir(repo_root: Path) -> Path:
    # テスト容易性のため、入出力ディレクトリは環境変数で差し替え可能にする
    return Path(os.environ.get("SVM_INPUT_DIR", str(repo_root / "input"))).resolve()


def _output_dir(repo_root: Path) -> Path:
    return Path(os.environ.get("SVM_OUTPUT_DIR", str(repo_root / "output"))).resolve()


RESOLUTION_MAP: dict[str, int] = {
    "720": 1280,
    "720p": 1280,
    "1080": 1920,
    "1080p": 1920,
    "1440": 2560,
    "1440p": 2560,
}


app = FastAPI(title="Slide Voice Maker Local API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _sanitize_filename(name: str) -> str:
    # すごく雑に危険文字だけ落とす（Windows/Unix両方を意識）
    name = name.strip().replace("\\", "_").replace("/", "_")
    name = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", name)
    if not name:
        raise HTTPException(status_code=400, detail="ファイル名が不正です")
    return name


@app.post("/api/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDFファイルを指定してください")

    repo_root = _repo_root()
    in_dir = _input_dir(repo_root)
    in_dir.mkdir(parents=True, exist_ok=True)

    filename = _sanitize_filename(Path(file.filename).name)
    dst = in_dir / filename

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="PDFが空です")

    dst.write_bytes(data)
    return {"saved": str(dst), "filename": filename}


@app.post("/api/upload/csv")
async def upload_csv(file: UploadFile = File(...)) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSVファイルを指定してください")

    repo_root = _repo_root()
    in_dir = _input_dir(repo_root)
    in_dir.mkdir(parents=True, exist_ok=True)

    dst = in_dir / "原稿.csv"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="CSVが空です")

    dst.write_bytes(data)
    return {"saved": str(dst), "filename": dst.name}


class GenerateRequest(BaseModel):
    pdf_name: str
    resolution: Literal["720", "720p", "1080", "1080p", "1440", "1440p"] = "720p"


@app.post("/api/generate")
async def generate(req: GenerateRequest) -> dict[str, str]:
    repo_root = _repo_root()
    in_dir = _input_dir(repo_root)
    out_dir = _output_dir(repo_root)

    pdf_name = _sanitize_filename(req.pdf_name)
    if not pdf_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="pdf_nameは .pdf を指定してください")

    pdf_path = in_dir / pdf_name
    script_path = in_dir / "原稿.csv"

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDFが見つかりません: {pdf_path}")
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"原稿CSVが見つかりません: {script_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # 解像度→環境変数
    width = RESOLUTION_MAP.get(req.resolution, 1280)
    os.environ["OUTPUT_MAX_WIDTH"] = str(width)

    base_name = pdf_path.stem
    temp_dir = out_dir / "temp" / base_name
    clear_temp_folder(str(temp_dir))

    await process_pdf_and_script(str(pdf_path), str(script_path), str(out_dir))

    webm = out_dir / f"{base_name}.webm"
    if not webm.exists() or webm.stat().st_size == 0:
        raise HTTPException(status_code=500, detail="動画webmの生成に失敗しました")

    return {"webm": webm.name, "path": str(webm)}


@app.get("/api/list_outputs")
def list_outputs() -> dict[str, list[str]]:
    repo_root = _repo_root()
    out_dir = _output_dir(repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([p.name for p in out_dir.glob("*.webm")])
    return {"webm": files}


@app.get("/api/download")
def download(name: str) -> FileResponse:
    repo_root = _repo_root()
    out_dir = _output_dir(repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = _sanitize_filename(name)
    if not safe.lower().endswith(".webm"):
        raise HTTPException(status_code=400, detail=".webm を指定してください")

    path = out_dir / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="指定ファイルが見つかりません")

    return FileResponse(
        path=str(path),
        media_type="video/webm",
        filename=safe,
    )


# APIより後に static をマウント（/api を潰さない）
app.mount("/", StaticFiles(directory=str(_repo_root()), html=True), name="static")
