import os
import subprocess
import wave
import contextlib
import shutil
from dataclasses import dataclass
from typing import List, Optional

# PIL.Image.ANTIALIAS互換性修正（Pillow 10+対応）
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import fitz  # pymupdf
import pandas as pd
import edge_tts
import imageio_ffmpeg
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)


@dataclass
class _SlideItem:
    page_index: int
    image_path: str
    audio_path: str
    script_text: str
    duration: float


def clear_temp_folder(temp_dir: str) -> bool:
    """tempフォルダを削除して再作成（上書き更新）。

    Returns:
        bool: 成功した場合True、エラーが発生した場合False
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleared temp folder: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
        return True
    except PermissionError as e:
        print(f"Warning: Could not clear temp folder (file locked): {e}")
        # ロックされていても続行
        os.makedirs(temp_dir, exist_ok=True)
        return False
    except Exception as e:
        print(f"Warning: Error clearing temp folder: {e}")
        os.makedirs(temp_dir, exist_ok=True)
        return False


def _get_render_scale() -> float:
    """PDFを画像化する倍率。高すぎると遅く/重くなるため環境変数で調整可能にする。"""
    try:
        return float(os.environ.get("SLIDE_RENDER_SCALE", "1.5"))
    except Exception:
        return 1.5


def _get_output_max_width() -> int:
    """出力動画の最大幅。大きいほど高品質だがエンコードは遅い。"""
    try:
        return int(os.environ.get("OUTPUT_MAX_WIDTH", "1280"))
    except Exception:
        return 1280


def _get_output_fps() -> int:
    """静止画ベースのため低fpsでも破綻しにくい。速度優先で既定15fps。"""
    try:
        return int(os.environ.get("OUTPUT_FPS", "15"))
    except Exception:
        return 15


def _get_vp9_cpu_used() -> int:
    """VP9速度パラメータ(0-8程度)。大きいほど速いが画質低下。最大8で高速化。"""
    try:
        return int(os.environ.get("VP9_CPU_USED", "8"))
    except Exception:
        return 8


def _get_vp9_crf() -> int:
    """VP9品質パラメータ。大きいほど軽い（低画質）。"""
    try:
        return int(os.environ.get("VP9_CRF", "40"))
    except Exception:
        return 40


def _get_use_vp8() -> bool:
    """VP8を使用（VP9より高速だがやや低品質）。"""
    try:
        return os.environ.get("USE_VP8", "1") == "1"
    except Exception:
        return True


def _get_silence_slide_duration() -> float:
    """原稿が空のページを何秒表示するか。"""
    try:
        return float(os.environ.get("SILENCE_SLIDE_DURATION", "5"))
    except Exception:
        return 5.0


def _file_exists_nonempty(path: str) -> bool:
    try:
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def _write_concat_list(paths: List[str], durations: Optional[List[float]], out_path: str) -> None:
    """FFmpeg concat demuxer list を書き出す。

    - durations は paths と同じ長さを想定。
    - durations を指定する場合、仕様上「最後のファイルは duration 行なし」が安全なため、
      最後のファイルを再掲して終端を作る。
    - durations が None（例: 音声側）では、末尾の再掲は行わない。
      ※末尾を重複させると最後の音声が二重に再生されてしまう。
    """

    def q(p: str) -> str:
        # concat demuxer は forward slash の方が安全
        p2 = os.path.abspath(p).replace("\\", "/")
        return p2.replace("'", "\\'")

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for idx, p in enumerate(paths):
            f.write(f"file '{q(p)}'\n")
            if durations is not None and idx < len(paths) - 1:
                d = float(durations[idx])
                if d <= 0:
                    d = 0.01
                f.write(f"duration {d:.6f}\n")

        # durations を書いた場合は、終端用に最後のファイルを再掲する
        # (audio 側のように durations が無い場合は再掲しない)
        if paths and durations is not None:
            f.write(f"file '{q(paths[-1])}'\n")


def _ensure_silence_wav(path: str, duration: float, sample_rate: int = 48000) -> None:
    if _file_exists_nonempty(path):
        return
    if duration <= 0:
        duration = 0.01
    n_samples = int(sample_rate * duration)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with contextlib.closing(wave.open(path, "wb")) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)


def _ensure_silence_mp3(path: str, duration: float, sample_rate: int = 24000) -> None:
    """FFmpegで無音MP3を生成する（concat demuxerで混在を避けるため）。"""
    if _file_exists_nonempty(path):
        return
    if duration <= 0:
        duration = 0.01

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    args = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r={int(sample_rate)}:cl=mono",
        "-t",
        f"{float(duration):.6f}",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "9",
        path,
    ]

    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = proc.stderr or b""
        try:
            msg = stderr.decode("utf-8")
        except Exception:
            msg = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to generate silence mp3: {msg}")


def _get_audio_duration_seconds(path: str) -> float:
    """MoviePyで音声長を取得（必ずcloseする）。"""
    clip = None
    try:
        clip = AudioFileClip(path)
        return float(clip.duration or 0)
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass


def _render_webm_with_ffmpeg(
    slides: List[_SlideItem],
    output_path: str,
    temp_dir: str,
) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    fps = _get_output_fps()
    max_w = _get_output_max_width()
    cpu_used = _get_vp9_cpu_used()
    crf = _get_vp9_crf()
    use_vp8 = _get_use_vp8()
    threads = str(min(os.cpu_count() or 4, 8))

    video_list = os.path.join(temp_dir, "__video_concat.txt")
    audio_list = os.path.join(temp_dir, "__audio_concat.txt")

    image_paths = [s.image_path for s in slides]
    audio_paths = [s.audio_path for s in slides]
    durations = [s.duration for s in slides]

    _write_concat_list(image_paths, durations, video_list)
    _write_concat_list(audio_paths, None, audio_list)

    # 高速化: bilinearよりfast_bilinearを使用
    vf = f"scale='min(iw,{max_w})':-2:flags=fast_bilinear,format=yuv420p"

    if use_vp8:
        # VP8は高速だがやや低品質
        args = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            video_list,
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            audio_list,
            "-vf",
            vf,
            "-fps_mode",
            "vfr",
            "-c:v",
            "libvpx",  # VP8
            "-deadline",
            "realtime",
            "-cpu-used",
            str(min(cpu_used, 16)),
            "-threads",
            threads,
            "-b:v",
            "1M",
            "-qmin",
            "4",
            "-qmax",
            "50",
            "-c:a",
            "libvorbis",  # Vorbis for VP8
            "-q:a",
            "4",
            "-shortest",
            output_path,
        ]
    else:
        # VP9（より高品質だが遅い）
        args = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            video_list,
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            audio_list,
            "-vf",
            vf,
            "-fps_mode",
            "vfr",
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            str(cpu_used),
            "-row-mt",
            "1",
            "-threads",
            threads,
            "-b:v",
            "0",
            "-crf",
            str(crf),
            "-c:a",
            "libopus",
            "-b:a",
            "64k",
            "-vbr",
            "on",
            "-shortest",
            output_path,
        ]

    print(f"FFmpeg: {ffmpeg}")
    print(f"Encoding with {'VP8' if use_vp8 else 'VP9'} (high-speed mode)...")
    proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = proc.stderr or b""
        stdout = proc.stdout or b""

        # まずutf-8で読んでダメならcp932、最後はreplace
        def safe_decode(b: bytes) -> str:
            for enc in ("utf-8", "cp932"):
                try:
                    return b.decode(enc)
                except Exception:
                    continue
            return b.decode("utf-8", errors="replace")

        err = (safe_decode(stderr) or safe_decode(stdout)).strip()
        raise RuntimeError(f"FFmpeg failed (code={proc.returncode}): {err}")


def _embed_subtitles(input_path: str, subtitle_path: str, output_path: str) -> None:
    """動画に字幕を埋め込む"""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cpu_used = _get_vp9_cpu_used()
    crf = _get_vp9_crf()
    use_vp8 = _get_use_vp8()
    threads = str(min(os.cpu_count() or 4, 8))
    
    # Windows用にパスをエスケープ
    escaped_path = subtitle_path.replace('\\', '/').replace(':', '\\:')
    vf = f"subtitles='{escaped_path}'"
    
    print(f"Embedding subtitles...")
    
    if use_vp8:
        args = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-nostats",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libvpx",
            "-deadline", "realtime",
            "-cpu-used", str(min(cpu_used, 16)),
            "-threads", threads,
            "-b:v", "1M",
            "-qmin", "4",
            "-qmax", "50",
            "-c:a", "copy",
            output_path,
        ]
    else:
        args = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-nostats",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libvpx-vp9",
            "-deadline", "realtime",
            "-cpu-used", str(cpu_used),
            "-row-mt", "1",
            "-threads", threads,
            "-b:v", "0",
            "-crf", str(crf),
            "-c:a", "copy",
            output_path,
        ]
    
    proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = proc.stderr or b""
        def safe_decode(b: bytes) -> str:
            for enc in ("utf-8", "cp932"):
                try:
                    return b.decode(enc)
                except Exception:
                    continue
            return b.decode("utf-8", errors="replace")
        err = safe_decode(stderr).strip()
        raise RuntimeError(f"FFmpeg subtitle embedding failed (code={proc.returncode}): {err}")


async def generate_voice(text, output_path, voice="ja-JP-NanamiNeural"):
    """Edge TTSを使って音声を生成する"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


async def generate_single_audio(slide_index: int, script: str, output_dir: str) -> str:
    """単一スライドの音声を生成してファイルパスを返す"""
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_path = os.path.join(temp_dir, f"slide_{slide_index:03d}.mp3")
    
    if script and script.strip():
        await generate_voice(script.strip(), audio_path)
        return audio_path
    return ""


import re

def _get_subtitle_segments(script: str) -> List[dict]:
    """原稿を句読点で分割し、文字数比率でタイミングを計算する（プレビューと同じロジック）"""
    if not script:
        return []
    
    # 句読点で分割（プレビューと同じ正規表現）
    raw_segments = re.split(r'([。、！？!?\n]+)', script)
    raw_segments = [s for s in raw_segments if s.strip()]
    
    # テキストと句読点をマージ
    merged_segments = []
    i = 0
    while i < len(raw_segments):
        text = raw_segments[i]
        punctuation = raw_segments[i + 1] if i + 1 < len(raw_segments) and re.match(r'^[。、！？!?\n]+$', raw_segments[i + 1]) else ""
        if punctuation:
            merged_segments.append(text + punctuation)
            i += 2
        else:
            merged_segments.append(text)
            i += 1
    
    if not merged_segments:
        return []
    
    # 文字数比率でタイミング計算
    total_chars = sum(len(s) for s in merged_segments)
    if total_chars == 0:
        return []
    
    char_count = 0
    segments = []
    for text in merged_segments:
        start_ratio = char_count / total_chars
        char_count += len(text)
        end_ratio = char_count / total_chars
        segments.append({
            'text': text,
            'start_ratio': start_ratio,
            'end_ratio': end_ratio
        })
    
    return segments


def _generate_ass_subtitle(slides_info: List[dict], output_path: str, video_width: int, video_height: int) -> None:
    """ASS形式の字幕ファイルを生成する（プレビューと同じセグメント分割方式）"""
    # ASS header
    header = f"""[Script Info]
Title: Slide Voice Maker Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans JP,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def format_time(seconds: float) -> str:
        """秒をASS時刻形式(H:MM:SS.CC)に変換"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"
    
    events = []
    current_time = 0.0
    
    for slide in slides_info:
        script = slide.get('script', '').strip()
        duration = slide.get('duration', 3.0)
        
        if script:
            # プレビューと同じセグメント分割
            segments = _get_subtitle_segments(script)
            
            for seg in segments:
                # 文字数比率からタイミングを計算
                seg_start = current_time + (duration * seg['start_ratio'])
                seg_end = current_time + (duration * seg['end_ratio'])
                
                # テキストをASS用にエスケープ
                text = seg['text'].replace('\n', '\\N')
                
                start_str = format_time(seg_start)
                end_str = format_time(seg_end)
                events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")
        
        current_time += duration
    
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(header)
        f.write('\n'.join(events))


def combine_audio_video(output_dir: str, resolution: int = 1280, output_name: str = "output", subtitle: bool = True) -> str:
    """output/temp内の音声・画像ファイルから動画を生成する（高速FFmpeg版）
    
    Args:
        output_dir: 出力ディレクトリ
        resolution: 動画の幅（px）
        output_name: 出力ファイル名（拡張子なし）
        subtitle: 字幕を埋め込むかどうか
    
    Returns:
        生成された動画ファイルのパス
    """
    temp_dir = os.path.join(output_dir, "temp")
    if not os.path.exists(temp_dir):
        raise FileNotFoundError(f"temp folder not found: {temp_dir}")
    
    # 画像と音声のペアを収集
    image_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.png')])
    audio_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.mp3')])
    
    if not image_files:
        raise ValueError("No image files found in temp folder")
    
    # 原稿ファイルを読み込み（字幕用）
    script_data = {}
    script_path = os.path.join(os.path.dirname(output_dir), "input", "原稿.csv")
    if not os.path.exists(script_path):
        script_path = os.path.join(output_dir, "..", "input", "原稿.csv")
    
    if os.path.exists(script_path):
        try:
            df = None
            for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
                try:
                    df = pd.read_csv(script_path, encoding=enc, engine="python", keep_default_na=False)
                    break
                except UnicodeDecodeError:
                    continue
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                if "index" in df.columns and "script" in df.columns:
                    for _, row in df.iterrows():
                        try:
                            idx = int(row["index"])
                            script_data[idx] = str(row["script"])
                        except (ValueError, TypeError):
                            pass
        except Exception as e:
            print(f"Warning: Failed to read script CSV: {e}")
    
    slides: List[_SlideItem] = []
    silence_duration = _get_silence_slide_duration()
    
    for img_file in image_files:
        # slide_000.png -> slide_000.mp3
        base = os.path.splitext(img_file)[0]
        audio_file = base + ".mp3"
        img_path = os.path.join(temp_dir, img_file)
        audio_path = os.path.join(temp_dir, audio_file) if audio_file in audio_files else None
        
        # スライドインデックスを抽出 (slide_000 -> 0)
        try:
            slide_index = int(base.split('_')[-1])
        except (ValueError, IndexError):
            slide_index = len(slides)
        
        # 音声の長さを取得
        duration = silence_duration
        if audio_path and os.path.exists(audio_path):
            try:
                duration = _get_audio_duration_seconds(audio_path)
            except Exception:
                pass
        
        # 音声がない場合は無音MP3を生成
        if not audio_path or not os.path.exists(audio_path):
            audio_path = os.path.join(temp_dir, f"_silence_{slide_index:03d}.mp3")
            _ensure_silence_mp3(audio_path, duration)
        
        slides.append(_SlideItem(
            page_index=slide_index,
            image_path=img_path,
            audio_path=audio_path,
            script_text=script_data.get(slide_index, ''),
            duration=duration
        ))
    
    if not slides:
        raise ValueError("No slides to process")
    
    output_path = os.path.join(output_dir, f"{output_name}.webm")
    
    # 高速FFmpegでエンコード
    print(f"Generating video with FFmpeg (high-speed mode)...")
    os.environ["OUTPUT_MAX_WIDTH"] = str(resolution)
    
    if subtitle:
        # 字幕あり: 一時ファイルに動画を生成してから字幕を埋め込む
        temp_video_path = os.path.join(temp_dir, f"_temp_{output_name}.webm")
        _render_webm_with_ffmpeg(slides, temp_video_path, temp_dir)
        
        # 字幕ファイルを生成
        subtitle_path = os.path.join(temp_dir, f"_subtitles_{output_name}.ass")
        slides_info = [
            {
                'page_index': s.page_index,
                'script': s.script_text,
                'duration': s.duration
            }
            for s in slides
        ]
        # 動画解像度を取得
        video_width = resolution
        video_height = int(resolution * 9 / 16)
        try:
            from PIL import Image
            with Image.open(slides[0].image_path) as img:
                video_width, video_height = img.size
                if video_width > resolution:
                    ratio = resolution / video_width
                    video_width = resolution
                    video_height = int(video_height * ratio)
        except Exception:
            pass
        _generate_ass_subtitle(slides_info, subtitle_path, video_width, video_height)
        print(f"Generated subtitle file: {subtitle_path}")
        
        # 字幕を埋め込む
        _embed_subtitles(temp_video_path, subtitle_path, output_path)
        
        # 一時ファイルを削除
        try:
            os.remove(temp_video_path)
        except Exception:
            pass
    else:
        # 字幕なし: 直接出力
        _render_webm_with_ffmpeg(slides, output_path, temp_dir)
    
    print(f"Video generated: {output_path}")
    return output_path


async def process_pdf_and_script(pdf_path, script_path, output_dir):
    """メイン処理"""
    print(f"Processing: {pdf_path}")
    
    # ファイル名の取得（拡張子なし）
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # 原稿の読み込み (CSV: index,script) - mojibake-safe
    try:
        df = None
        last_err = None
        for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
            try:
                df = pd.read_csv(
                    script_path,
                    encoding=enc,
                    engine="python",  # allow newlines inside quoted cells
                    keep_default_na=False,
                )
                break
            except UnicodeDecodeError as e:
                last_err = e
                continue

        if df is None:
            raise last_err or ValueError("Failed to read script CSV")

        df.columns = [str(c).strip() for c in df.columns]
        if "index" not in df.columns or "script" not in df.columns:
            raise ValueError("Script CSV must have columns: index, script")

        df["index"] = pd.to_numeric(df["index"], errors="coerce")
    except Exception as e:
        print(f"Error reading script CSV ({script_path}): {e}")
        return

    # PDFの読み込み
    doc = fitz.open(pdf_path)
    
    temp_dir = os.path.join(output_dir, "temp", base_name)
    os.makedirs(temp_dir, exist_ok=True)

    use_moviepy = os.environ.get("USE_MOVIEPY", "0") == "1"

    slides: List[_SlideItem] = []
    video_clips = []
    final_video = None

    try:
        for i in range(len(doc)):
            print(f"Processing page {i+1}/{len(doc)}")
            page = doc.load_page(i)

            # 画像として保存 (高解像度で)
            image_path = os.path.join(temp_dir, f"slide_{i}.png")
            if not _file_exists_nonempty(image_path):
                scale = _get_render_scale()
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                pix.save(image_path)

            # 原稿の取得
            script_text = ""
            script_row = df.loc[df["index"] == i, "script"]
            if not script_row.empty:
                script_text = str(script_row.iloc[0])

            # 音声生成
            audio_path = os.path.join(temp_dir, f"audio_{i}.mp3")
            if script_text.strip():
                if not _file_exists_nonempty(audio_path):
                    await generate_voice(script_text, audio_path)
            else:
                # 音声が無い場合でも concat demuxer のため MP3 に揃える
                audio_path = os.path.join(temp_dir, f"silence_{i}.mp3")

            # duration決定（音声があれば音声長、無音なら固定）
            if script_text.strip():
                if os.path.exists(audio_path):
                    duration = _get_audio_duration_seconds(audio_path)
                else:
                    duration = _get_silence_slide_duration()
            else:
                duration = _get_silence_slide_duration()

            if duration <= 0:
                duration = 0.01

            # 無音MP3の場合はduration確定後に生成
            if audio_path.lower().endswith(".mp3") and "silence_" in os.path.basename(audio_path):
                _ensure_silence_mp3(audio_path, duration)

            slides.append(
                _SlideItem(
                    page_index=i,
                    image_path=image_path,
                    audio_path=audio_path,
                    script_text=script_text,
                    duration=duration,
                )
            )

        # 動画出力
        print("Generating video...")
        video_output_path = os.path.join(output_dir, f"{base_name}.webm")

        if not use_moviepy:
            # 高速: FFmpegでconcat（字幕なし）
            _render_webm_with_ffmpeg(slides, video_output_path, temp_dir)
        else:
            # フォールバック: MoviePy（遅い）
            for slide in slides:
                img_clip = ImageClip(slide.image_path).set_duration(slide.duration)
                if slide.audio_path and os.path.exists(slide.audio_path):
                    audio_clip = AudioFileClip(slide.audio_path)
                    img_clip = img_clip.set_audio(audio_clip)
                video_clips.append(img_clip)

            final_video = concatenate_videoclips(video_clips, method="compose")
            temp_audiofile = os.path.join(temp_dir, f"{base_name}__temp_audio.ogg")
            final_video.write_videofile(
                video_output_path,
                fps=_get_output_fps(),
                codec="libvpx-vp9",
                audio_codec="libvorbis",
                temp_audiofile=temp_audiofile,
                remove_temp=True,
            )

        print("Done!")
    finally:
        try:
            doc.close()
        except Exception:
            pass

        # MoviePyリソース解放
        if final_video is not None:
            try:
                final_video.close()
            except Exception:
                pass

        for c in video_clips:
            try:
                c.close()
            except Exception:
                pass

