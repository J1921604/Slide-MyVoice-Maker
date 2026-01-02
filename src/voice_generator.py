import os
from TTS.api import TTS
import torch

class AkiVoice:
    def __init__(self):
        print("音声モデルを初期化中...")
        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tts = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2"
        ).to(device)

        self.speaker_wav = "models/samples/aki_sample.wav"
        os.makedirs("output", exist_ok=True)
        print("初期化完了！")

    def speak(self, text, output_filename="output.wav"):
        output_path = os.path.join("output", output_filename)
        try:
            print(f"音声生成中: {text}")
            self.tts.tts_to_file(
                text=text,
                speaker_wav=self.speaker_wav,
                language="ja",
                file_path=output_path
            )
            print(f"生成完了: {output_path}")
            return output_path
        except Exception as e:
            print(f"エラー発生: {e}")
            return None

    def test_voice(self):
        test_text = "こんにちは、お母さん。今日も元気ですか？"
        output_file = self.speak(test_text, "test_voice.wav")

        if output_file:
            print(f"テスト音声を生成しました: {output_file}")
            os.system(f"afplay {output_file}")  # Mac の場合再生

        return output_file

if __name__ == "__main__":
    voice = AkiVoice()
    voice.test_voice()
    voice.speak("お薬の時間です", "medicine_time.wav")
    voice.speak("今日は良い天気ですね", "good_weather.wav")
