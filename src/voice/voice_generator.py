import os
from pathlib import Path
from TTS.api import TTS
import torch
import platform
import subprocess

class Voice:
    def __init__(self):
        print("音声モデルを初期化中...")
        
        # TorchCodecを無効化してtorchaudioを使用するように環境変数を設定
        os.environ['TORCHAUDIO_USE_BACKEND_DISPATCHER'] = '1'
        os.environ.pop('USE_TORCHCODEC', None)
        
        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tts = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2"
        ).to(device)

        # リポジトリルートを基準にパスを決定
        repo_root = Path(__file__).resolve().parents[2]

        # 複数候補からサンプルWAVを探す（プロジェクト内の場所が変更されている場合に対応）
        candidate_wavs = [
            repo_root / "src" / "voice" / "models" / "samples" / "sample.wav",
        ]
        found = None
        for p in candidate_wavs:
            if p.exists():
                found = str(p)
                break

        if found:
            self.speaker_wav = found
        else:
            # 見つからなければ None にして TTS のデフォルト合成を利用
            self.speaker_wav = None
            print("Warning: speaker sample not found; using default voice. Searched:")
            for p in candidate_wavs:
                print(f"  - {p}")

        # 出力はリポジトリルートの output に揃える
        out_dir = repo_root / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        print("初期化完了！")

    def speak(self, text, output_filename="output.wav"):
        repo_root = Path(__file__).resolve().parents[2]
        output_path = repo_root / "output" / output_filename
        try:
            print(f"音声生成中: {text}")
            
            # speaker_wavなしでデフォルト合成モードを利用
            # XTTS v2はspeaker_wav必須のため、ここではEdge TTSにフォールバック
            # （または事前に埋め込みspeakerを使う）
            # 簡易対処：speakerなしの場合はEdge TTSを呼ぶ
            if not self.speaker_wav:
                print("Warning: speaker_wavがないためEdge TTSで生成します")
                import edge_tts
                import asyncio
                communicate = edge_tts.Communicate(text, "ja-JP-NanamiNeural")
                asyncio.run(communicate.save(str(output_path)))
                print(f"生成完了: {output_path}")
                return output_path
            
            # speaker_wavがある場合、パスを直接渡さずに一時的にロードして渡す
            try:
                import soundfile as sf
                
                # soundfileで読み込む（torchcodecを使わない）
                audio_data, sample_rate = sf.read(self.speaker_wav)
                
                # 一時ファイルに書き出す（torchaudioではなくsoundfileで）
                temp_wav = repo_root / "output" / "_temp_speaker.wav"
                sf.write(str(temp_wav), audio_data, sample_rate)
                
                print(f"speaker_wavを読み込みました: {self.speaker_wav}")
                
                # 環境変数でtorchaudioバックエンドを強制（TorchCodecを回避）
                import os
                os.environ['TORCHAUDIO_BACKEND'] = 'soundfile'
                
                self.tts.tts_to_file(
                    text=text,
                    speaker_wav=str(temp_wav),
                    language="ja",
                    file_path=str(output_path)
                )
                print(f"生成完了: {output_path}")
                return output_path
            except Exception as e_coqui:
                print(f"Warning: Coqui TTS failed ({e_coqui}), falling back to Edge TTS")
                import edge_tts
                import asyncio
                communicate = edge_tts.Communicate(text, "ja-JP-NanamiNeural")
                asyncio.run(communicate.save(str(output_path)))
                print(f"生成完了(Edge TTS): {output_path}")
                return output_path
                
        except Exception as e:
            print(f"エラー発生: {e}")
            return None

    def test_voice(self):
        test_text = "こんにちは、お母さん。今日も元気ですか？"
        output_file = self.speak(test_text, "test_voice.wav")

        if output_file:
            print(f"テスト音声を生成しました: {output_file}")
            # クロスプラットフォームで再生
            try:
                plat = platform.system()
                if plat == "Darwin":
                    subprocess.run(["afplay", str(output_file)])
                elif plat == "Windows":
                    # powershell の Start-Process を直接呼ぶ方法もあるが subprocess で start を利用
                    subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{output_file}').PlaySync();"]) 
                else:
                    # Linux: aplay または paplay
                    played = False
                    for cmd in (["paplay", str(output_file)], ["aplay", str(output_file)]):
                        try:
                            subprocess.run(cmd, check=True)
                            played = True
                            break
                        except Exception:
                            continue
                    if not played:
                        print("再生コマンドが見つかりません（paplay/aplay）。ファイルを手動で再生してください。")
            except Exception as e:
                print(f"再生中にエラー: {e}")  

        return output_file

if __name__ == "__main__":
    voice = Voice()
    voice.test_voice()
    voice.speak("お薬の時間です", "medicine_time.wav")
    voice.speak("今日は良い天気ですね", "good_weather.wav")
