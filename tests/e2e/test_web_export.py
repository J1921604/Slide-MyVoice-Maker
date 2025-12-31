import os
import socket
import subprocess
import time
from pathlib import Path

import fitz
import pytest


def _wait_port(host: str, port: int, *, timeout_s: float = 10.0) -> None:
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


def _write_shift_jis_csv(path: Path, pages: int) -> None:
    # Web側CSV読み込み（文字化け対処）の回帰テスト: Shift_JIS（cp932）で書く
    lines = ["index,script"]
    for i in range(pages):
        lines.append(f"{i},\"これはスライド{i+1}の原稿です。\"")
    data = ("\r\n".join(lines) + "\r\n").encode("cp932", errors="strict")
    path.write_bytes(data)


@pytest.mark.e2e
def test_web_export_download_is_not_empty(tmp_path: Path) -> None:
    # Playwrightは重いので、CI/ローカルで明示実行する想定
    from playwright.sync_api import sync_playwright  # import inside to keep startup light

    repo_root = Path(__file__).resolve().parents[2]

    pdf_path = tmp_path / "sample.pdf"
    csv_path = tmp_path / "原稿.csv"
    _make_sample_pdf(pdf_path, pages=2)
    _write_shift_jis_csv(csv_path, pages=2)

    host = "127.0.0.1"
    port = 8000

    # ローカルHTTPサーバー起動（py -3.10）
    server = subprocess.Popen(
        ["py", "-3.10", "-m", "http.server", str(port), "--bind", host],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_port(host, port, timeout_s=15.0)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.goto(f"http://{host}:{port}/index.html", wait_until="domcontentloaded")

            # PDFアップロード（ホームはPDFボタンのみ）
            with page.expect_file_chooser() as fc_pdf:
                page.get_by_role("button", name="PDFをアップロード").click()
            fc_pdf.value.set_files(str(pdf_path))

            # ヘッダー表示まで待つ
            page.get_by_role("button", name="PDF").wait_for(timeout=15000)

            # 原稿CSVアップロード（要件: PDF後の画面で削除しない）
            with page.expect_file_chooser() as fc_csv:
                page.get_by_role("button", name="原稿CSV").click()
            fc_csv.value.set_files(str(csv_path))

            # WebM出力（空ファイルにならないこと）
            with page.expect_download() as dl_info:
                page.get_by_role("button", name="WebM出力").click()
            download = dl_info.value
            save_path = tmp_path / "out.webm"
            download.save_as(str(save_path))

            assert save_path.exists(), "WebMがダウンロードされていません"
            assert save_path.stat().st_size > 0, "ダウンロードWebMが空です"

            context.close()
            browser.close()

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:  # noqa: BLE001
            server.kill()
