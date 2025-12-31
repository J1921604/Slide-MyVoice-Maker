import os
import socket
import subprocess
import time
from pathlib import Path

import fitz
import pytest


def _wait_port(host: str, port: int, *, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.1)
    raise TimeoutError(f"HTTPサーバーが起動しませんでした: {host}:{port} ({last_err})")


def _make_sample_pdf(path: Path, *, pages: int = 2, width: float = 1280, height: float = 720) -> None:
    doc = fitz.open()
    try:
        for i in range(pages):
            page = doc.new_page(width=width, height=height)
            page.insert_text((72, 72), f"Slide {i+1}")
        doc.save(path)
    finally:
        doc.close()


def _write_empty_csv(path: Path, pages: int) -> None:
    # Edge TTSに依存しないよう、scriptは空（ローカルでも無音MP3→WebM生成が成立する）
    lines = ["index,script"]
    for i in range(pages):
        lines.append(f"{i},\"\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.e2e
def test_local_backend_generates_and_downloads_webm(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright  # import inside

    repo_root = Path(__file__).resolve().parents[2]

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = tmp_path / "sample.pdf"
    csv_path = tmp_path / "原稿.csv"
    _make_sample_pdf(pdf_path, pages=2)
    _write_empty_csv(csv_path, pages=2)

    host = "127.0.0.1"
    port = 8123

    env = os.environ.copy()
    env["SVM_INPUT_DIR"] = str(input_dir)
    env["SVM_OUTPUT_DIR"] = str(output_dir)
    env["USE_VP8"] = "1"
    env["OUTPUT_FPS"] = "15"
    env["SLIDE_RENDER_SCALE"] = "1.5"

    # 仮想環境のPythonを使用
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    python_cmd = str(venv_python) if venv_python.exists() else "py"

    server = subprocess.Popen(
        [
            python_cmd,
            "-m",
            "uvicorn",
            "src.server:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_port(host, port, timeout_s=30.0)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.goto(f"http://{host}:{port}/index.html", wait_until="domcontentloaded")

            # PDFアップロード（input/へ保存される）
            with page.expect_file_chooser() as fc_pdf:
                page.get_by_role("button", name="PDFをアップロード").click()
            fc_pdf.value.set_files(str(pdf_path))

            # ヘッダー表示まで待つ
            page.get_by_role("button", name="PDF").wait_for(timeout=20000)

            # CSVアップロード
            with page.expect_file_chooser() as fc_csv:
                page.get_by_role("button", name="原稿CSV入力").click()
            fc_csv.value.set_files(str(csv_path))

            # 画像・音声生成（output/tempに保存される）
            page.get_by_role("button", name="画像・音声生成").click()
            page.get_by_text("生成完了").wait_for(timeout=300000)

            # 動画生成（output/に保存される）
            page.get_by_role("button", name="動画生成").click()
            page.get_by_text("動画生成完了").wait_for(timeout=300000)

            # output選択とダウンロード
            page.get_by_role("button", name="動画WebM出力").wait_for(timeout=15000)
            with page.expect_download() as dl_info:
                page.get_by_role("button", name="動画WebM出力").click()
            download = dl_info.value
            save_path = tmp_path / "downloaded.webm"
            download.save_as(str(save_path))

            assert save_path.exists(), "WebMがダウンロードされていません"
            assert save_path.stat().st_size > 0, "ダウンロードWebMが空です"

            context.close()
            browser.close()

        # サーバーが書き込んだ output 側にもファイルがある
        generated = output_dir / "sample.webm"
        assert generated.exists(), "output/にWebMが生成されていません"
        assert generated.stat().st_size > 0, "output/のWebMが空です"

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:  # noqa: BLE001
            server.kill()
