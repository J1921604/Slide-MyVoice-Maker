import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Upload, FileText, Play, Square, Video, Download, Mic, Volume2, HelpCircle, X, ChevronLeft, ChevronRight, Loader2, Wand2 } from 'lucide-react';

const apiKey = "";
const ttsApiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent`;

const preloadedScripts = [
  "スライド1の原稿をここに記載（50〜150文字程度）。",
  "スライド2の原稿をここに記載（50〜150文字程度）。",
  "スライド3の原稿をここに記載（50〜150文字程度）。"
];

const pcmToWav = (pcmBase64, sampleRate = 24000) => {
  const binaryString = window.atob(pcmBase64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
  const buffer = bytes.buffer;
  const wavHeader = new ArrayBuffer(44);
  const view = new DataView(wavHeader);
  const writeString = (offset, string) => { for (let i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i)); };
  writeString(0, 'RIFF');
  view.setUint32(4, 32 + buffer.byteLength, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, buffer.byteLength, true);
  const blob = new Blob([wavHeader, buffer], { type: 'audio/wav' });
  return URL.createObjectURL(blob);
};

// 字幕セグメントを句読点で分割し、比率を計算
const getSubtitleSegments = (script) => {
  if (!script) return [];
  const rawSegments = script.split(/([。、！？!?\n]+)/).filter(s => s.trim().length > 0);
  const mergedSegments = [];
  for (let i = 0; i < rawSegments.length; i += 2) {
    const text = rawSegments[i];
    const punctuation = rawSegments[i + 1] || "";
    mergedSegments.push(text + punctuation);
  }
  const totalChars = mergedSegments.reduce((acc, s) => acc + s.length, 0);
  let charCountAccumulator = 0;
  return mergedSegments.map(text => {
    const startRatio = charCountAccumulator / totalChars;
    charCountAccumulator += text.length;
    const endRatio = charCountAccumulator / totalChars;
    return { text, startRatio, endRatio };
  });
};

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const PlayerOverlay = ({ currentSlide, audioRef, isPlaying }) => {
  const [currentSubtitle, setCurrentSubtitle] = useState("");
  const subtitleSegments = useMemo(() => getSubtitleSegments(currentSlide?.script), [currentSlide]);
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handleTimeUpdate = () => {
      if (!currentSlide?.audio) { setCurrentSubtitle(""); return; }
      const duration = audio.duration;
      const currentTime = audio.currentTime;
      if (!duration || !isFinite(duration)) return;
      const currentRatio = currentTime / duration;
      const activeSegment = subtitleSegments.find(seg => currentRatio >= seg.startRatio && currentRatio < seg.endRatio);
      if (activeSegment) setCurrentSubtitle(activeSegment.text);
      else if (currentRatio >= 1 && subtitleSegments.length > 0) setCurrentSubtitle(subtitleSegments[subtitleSegments.length - 1].text);
    };
    audio.addEventListener('timeupdate', handleTimeUpdate);
    return () => audio.removeEventListener('timeupdate', handleTimeUpdate);
  }, [audioRef, currentSlide, subtitleSegments]);
  return (
    <div className="w-full h-[80px] bg-[#1a1a2e] border-t border-white/5 flex items-center justify-center px-8 transition-colors duration-300 flex-shrink-0">
      <div className="text-white text-lg md:text-2xl font-bold text-center leading-relaxed">{currentSubtitle}</div>
    </div>
  );
};

export default function AISlideStudio() {
  const [slides, setSlides] = useState([]);
  const [activeSlideIndex, setActiveSlideIndex] = useState(0);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [pptxExporting, setPptxExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const audioRef = useRef(null);
  const exportCanvasRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const loadScript = (src) => new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const script = document.createElement("script");
      script.src = src; script.async = true; script.onload = resolve; script.onerror = reject;
      document.body.appendChild(script);
    });
    const loadLibraries = async () => {
      await Promise.all([
        loadScript("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"),
        loadScript("https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundle.js")
      ]);
    };
    loadLibraries();
  }, []);

  const handlePdfUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setPdfLoading(true);
    try {
      const images = await convertPdfToImages(file);
      const newSlides = images.map((image, index) => ({
        id: crypto.randomUUID(), image, script: preloadedScripts[index] || "", audio: null, isGenerating: false
      }));
      setSlides(newSlides);
      setActiveSlideIndex(0);
    } catch (error) { alert(`PDF読み込み失敗: ${error.message}`); }
    finally { setPdfLoading(false); }
  };

  const convertPdfToImages = async (file) => {
    if (!window.pdfjsLib) throw new Error("PDF処理ライブラリを読み込み中です。");
    const pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib.GlobalWorkerOptions.workerSrc) pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const images = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale: 2.0 });
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      canvas.height = viewport.height; canvas.width = viewport.width;
      await page.render({ canvasContext: context, viewport }).promise;
      images.push(canvas.toDataURL('image/png'));
    }
    return images;
  };

  const generateSpeechFromText = async (text, retryCount = 0) => {
    if (!text) return null;
    const payload = { contents: [{ parts: [{ text }] }], generationConfig: { responseModalities: ["AUDIO"], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: "Aoede" } } } } };
    try {
      const response = await fetch(ttsApiUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!response.ok) {
        if ((response.status === 429 || response.status >= 500) && retryCount < 5) { await sleep(Math.pow(2, retryCount) * 1000); return generateSpeechFromText(text, retryCount + 1); }
        throw new Error(`TTS API Error: ${response.status}`);
      }
      const result = await response.json();
      const audioData = result.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      if (audioData) return pcmToWav(audioData);
      throw new Error("No audio data");
    } catch (e) { return null; }
  };

  const generateAllAudio = async () => {
    if (isGeneratingAudio) return;
    setIsGeneratingAudio(true);
    const indicesToProcess = slides.map((s, i) => (!s.audio && s.script ? i : -1)).filter(i => i !== -1);
    if (indicesToProcess.length === 0) { setIsGeneratingAudio(false); return; }
    const batchSize = 5;
    for (let i = 0; i < indicesToProcess.length; i += batchSize) {
      const batch = indicesToProcess.slice(i, i + batchSize);
      setSlides(prev => prev.map((s, idx) => batch.includes(idx) ? { ...s, isGenerating: true } : s));
      await Promise.allSettled(batch.map(async (idx) => {
        const audioUrl = await generateSpeechFromText(slides[idx].script);
        setSlides(prev => { const newSlides = [...prev]; newSlides[idx] = { ...newSlides[idx], audio: audioUrl, isGenerating: false }; return newSlides; });
      }));
      if (i + batchSize < indicesToProcess.length) await sleep(500);
    }
    setIsGeneratingAudio(false);
  };

  // ============================================================
  // 改善版: タイムライン方式による動画エクスポート
  // ============================================================
  const exportVideo = async () => {
    if (isExporting || slides.length === 0) return;
    setIsExporting(true);
    setExportProgress(0);

    const canvas = exportCanvasRef.current;
    canvas.width = 1920;
    canvas.height = 1160;
    const ctx = canvas.getContext('2d');

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const dest = audioCtx.createMediaStreamDestination();
    const canvasStream = canvas.captureStream(30);
    const combinedStream = new MediaStream([...canvasStream.getVideoTracks(), ...dest.stream.getAudioTracks()]);
    const mediaRecorder = new MediaRecorder(combinedStream, { mimeType: 'video/webm;codecs=vp9,opus' });
    const chunks = [];
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'video/webm' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `presentation-${Date.now()}.webm`;
      a.click();
      setIsExporting(false);
      audioCtx.close();
      setExportProgress(0);
    };

    const slideAreaHeight = 1080;
    const subtitleAreaHeight = 80;
    const SLIDE_GAP = 0.33; // スライド間のギャップ（秒）

    // フレーム描画関数
    const drawFrame = (img, subtitleText) => {
      ctx.fillStyle = '#0f0f1a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      if (img) {
        const scale = Math.min(canvas.width / img.width, slideAreaHeight / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        const x = (canvas.width - w) / 2;
        const y = (slideAreaHeight - h) / 2;
        ctx.drawImage(img, x, y, w, h);
      }
      ctx.fillStyle = '#1a1a2e';
      ctx.fillRect(0, slideAreaHeight, canvas.width, subtitleAreaHeight);
      if (subtitleText) {
        ctx.fillStyle = 'white';
        ctx.font = 'bold 36px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(subtitleText, canvas.width / 2, slideAreaHeight + subtitleAreaHeight / 2, canvas.width - 80);
      }
    };

    try {
      // ステップ1: 全スライドの画像をプリロード
      setExportProgress(5);
      const preloadedImages = [];
      for (let i = 0; i < slides.length; i++) {
        const img = new Image();
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
          img.src = slides[i].image;
        });
        preloadedImages.push(img);
      }

      // ステップ2: 全音声の実測時間を取得し、AudioBufferを保持
      setExportProgress(10);
      const slideAudioData = [];
      for (let i = 0; i < slides.length; i++) {
        const slide = slides[i];
        if (slide.audio) {
          const response = await fetch(slide.audio);
          const arrayBuffer = await response.arrayBuffer();
          const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
          slideAudioData.push({
            hasAudio: true,
            buffer: audioBuffer,
            duration: audioBuffer.duration
          });
        } else {
          // 音声なしスライドは3秒固定
          slideAudioData.push({
            hasAudio: false,
            buffer: null,
            duration: 3.0
          });
        }
        setExportProgress(10 + Math.round((i / slides.length) * 10));
      }

      // ステップ3: タイムラインを構築（各スライドの開始・終了時刻）
      const timeline = [];
      let cumulativeTime = 0;
      for (let i = 0; i < slides.length; i++) {
        const audioDuration = slideAudioData[i].duration;
        const start = cumulativeTime;
        const audioEnd = cumulativeTime + audioDuration; // 音声終了時刻
        const end = audioEnd + SLIDE_GAP; // ギャップ込みの終了時刻
        timeline.push({
          slideIndex: i,
          start,
          audioEnd,
          end,
          audioDuration
        });
        cumulativeTime = end;
      }
      const totalDuration = cumulativeTime;

      // 字幕セグメントを事前計算
      const allSubtitleSegments = slides.map(slide => getSubtitleSegments(slide.script));

      // ステップ4: 録画開始
      setExportProgress(25);
      mediaRecorder.start();

      // ステップ5: 全音声をスケジュール再生
      const recordingStartTime = audioCtx.currentTime;
      for (let i = 0; i < slides.length; i++) {
        if (slideAudioData[i].hasAudio && slideAudioData[i].buffer) {
          const source = audioCtx.createBufferSource();
          source.buffer = slideAudioData[i].buffer;
          source.connect(dest);
          // 各スライドの開始時刻に合わせて再生をスケジュール
          source.start(recordingStartTime + timeline[i].start);
        }
      }

      // ステップ6: フレーム描画ループ（絶対時間ベース）
      while (true) {
        const elapsed = audioCtx.currentTime - recordingStartTime;

        // 終了判定
        if (elapsed >= totalDuration) {
          break;
        }

        // 進捗更新
        setExportProgress(25 + Math.round((elapsed / totalDuration) * 70));

        // 現在時刻からスライドを特定
        let currentSlideIndex = 0;
        for (let i = 0; i < timeline.length; i++) {
          if (elapsed >= timeline[i].start && elapsed < timeline[i].end) {
            currentSlideIndex = i;
            break;
          }
          if (i === timeline.length - 1) {
            currentSlideIndex = i;
          }
        }

        const currentTimeline = timeline[currentSlideIndex];
        const currentSlide = slides[currentSlideIndex];
        const currentImage = preloadedImages[currentSlideIndex];
        const segments = allSubtitleSegments[currentSlideIndex];

        // 字幕を計算
        let subtitleText = "";
        const slideElapsed = elapsed - currentTimeline.start;

        // ギャップ時間中（音声終了後）は字幕を消す
        if (slideElapsed < currentTimeline.audioDuration) {
          if (segments.length > 0) {
            const ratio = slideElapsed / currentTimeline.audioDuration;
            const activeSegment = segments.find(seg => ratio >= seg.startRatio && ratio < seg.endRatio);
            if (activeSegment) {
              subtitleText = activeSegment.text;
            } else if (ratio >= 1) {
              // 音声終了間際は最後のセグメントを表示
              subtitleText = segments[segments.length - 1].text;
            }
          } else {
            // セグメントがない場合は原稿全体を表示
            subtitleText = currentSlide.script || "";
          }
        }
        // else: ギャップ時間中は subtitleText = "" のまま

        // フレーム描画
        drawFrame(currentImage, subtitleText);

        // 約30fpsで次フレームへ
        await sleep(33);
      }

      // 最終フレーム（空白）を数フレーム描画
      const lastImage = preloadedImages[preloadedImages.length - 1];
      for (let f = 0; f < 10; f++) {
        drawFrame(lastImage, "");
        await sleep(33);
      }

      setExportProgress(100);
      mediaRecorder.stop();

    } catch (error) {
      console.error("Video export error:", error);
      alert("動画エクスポート中にエラーが発生しました: " + error.message);
      setIsExporting(false);
      audioCtx.close();
    }
  };

  const exportPptx = async () => {
    if (!window.PptxGenJS || slides.length === 0) return;
    setPptxExporting(true);
    try {
      const pptx = new window.PptxGenJS();
      const firstSlide = slides.find(s => s.image);
      if (firstSlide) { const img = new Image(); await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; img.src = firstSlide.image; }); const ratio = img.width / img.height; if (Math.abs(ratio - 16/9) < 0.1) pptx.layout = 'LAYOUT_16x9'; else if (Math.abs(ratio - 4/3) < 0.1) pptx.layout = 'LAYOUT_4x3'; else { pptx.defineLayout({ name: 'CUSTOM', width: 10, height: 10 / ratio }); pptx.layout = 'CUSTOM'; } }
      for (const slideData of slides) { const slide = pptx.addSlide(); if (slideData.image) slide.addImage({ data: slideData.image, x: 0, y: 0, w: '100%', h: '100%' }); if (slideData.script) slide.addNotes(slideData.script); }
      await pptx.writeFile({ fileName: `presentation-${Date.now()}.pptx` });
    } catch (error) { alert("PPTX書き出し失敗: " + error.message); }
    setPptxExporting(false);
  };

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) { audio.pause(); audio.currentTime = 0; setIsPlaying(false); }
  }, [activeSlideIndex]);

  const handlePreviewPlay = () => {
    const audio = audioRef.current;
    if (!audio || !activeSlide?.audio) return;
    if (isPlaying) { audio.pause(); }
    else { audio.currentTime = audio.currentTime || 0; audio.play().catch(() => {}); }
  };

  const updateScript = (index, newScript) => { setSlides(prev => { const newSlides = [...prev]; newSlides[index] = { ...newSlides[index], script: newScript, audio: null }; return newSlides; }); };

  // 個別スライドの音声を再生成
  const regenerateAudio = async (index) => {
    const slide = slides[index];
    if (!slide?.script || slide.isGenerating) return;
    
    // 生成中フラグを立てる
    setSlides(prev => {
      const newSlides = [...prev];
      newSlides[index] = { ...newSlides[index], isGenerating: true };
      return newSlides;
    });
    
    try {
      const audioUrl = await generateSpeechFromText(slide.script);
      setSlides(prev => {
        const newSlides = [...prev];
        newSlides[index] = { ...newSlides[index], audio: audioUrl, isGenerating: false };
        return newSlides;
      });
    } catch (error) {
      setSlides(prev => {
        const newSlides = [...prev];
        newSlides[index] = { ...newSlides[index], isGenerating: false };
        return newSlides;
      });
    }
  };

  if (slides.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-4 relative overflow-hidden font-sans">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-violet-600/30 rounded-full blur-[100px] animate-aurora-1" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-fuchsia-600/20 rounded-full blur-[120px] animate-aurora-2" />
        <div className="z-10 bg-slate-900/60 backdrop-blur-xl border border-white/10 p-12 rounded-3xl shadow-2xl max-w-2xl w-full text-center">
          <div className="mb-8 flex justify-center"><div className="bg-gradient-to-r from-violet-500 to-fuchsia-500 p-4 rounded-2xl shadow-lg shadow-violet-500/20"><Video size={48} className="text-white" /></div></div>
          <h1 className="text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-fuchsia-400">AI Slide Studio</h1>
          <p className="text-xl text-slate-300 mb-8 font-light">読み上げ原稿は準備済みです。<br/>同じPDFをアップロードしてください。</p>
          <button onClick={() => fileInputRef.current?.click()} disabled={pdfLoading} className="group relative px-8 py-4 bg-white text-slate-900 rounded-xl font-bold text-lg hover:bg-slate-100 transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed w-full max-w-md mx-auto overflow-hidden">
            {pdfLoading ? <span className="flex items-center justify-center gap-2"><Loader2 className="animate-spin" /> 解析中...</span> : <span className="flex items-center justify-center gap-2"><Upload size={24} /> PDFをアップロード</span>}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
          </button>
          <input type="file" ref={fileInputRef} onChange={handlePdfUpload} accept=".pdf" className="hidden" />
        </div>
        <style>{`@keyframes aurora-1 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(20px, -20px) scale(1.1); } } @keyframes aurora-2 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(-20px, 10px) scale(1.2); } } .animate-aurora-1 { animation: aurora-1 15s infinite ease-in-out; } .animate-aurora-2 { animation: aurora-2 18s infinite ease-in-out; }`}</style>
      </div>
    );
  }

  const activeSlide = slides[activeSlideIndex];
  return (
    <div className="h-screen bg-slate-950 text-slate-200 flex flex-col font-sans overflow-hidden">
      <canvas ref={exportCanvasRef} className="hidden" />
      <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-6 z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-lg flex items-center justify-center"><Video size={18} className="text-white" /></div>
          <h1 className="font-bold text-lg tracking-tight">AI Slide Studio</h1>
          <button onClick={() => setShowHelp(true)} className="ml-2 text-slate-400 hover:text-white transition-colors"><HelpCircle size={18} /></button>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={generateAllAudio} disabled={isGeneratingAudio || isExporting} className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${isGeneratingAudio ? 'bg-slate-800 text-slate-400 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'}`}>
            {isGeneratingAudio ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}{isGeneratingAudio ? '生成中...' : '音声生成'}
          </button>
          <div className="h-6 w-px bg-white/10 mx-1" />
          <button onClick={exportPptx} disabled={pptxExporting} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-lg font-medium shadow-lg shadow-orange-500/20 transition-all disabled:opacity-50">
            {pptxExporting ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}PPTX
          </button>
          <button onClick={exportVideo} disabled={isExporting} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium border border-white/10 transition-all disabled:opacity-50 relative overflow-hidden">
            {isExporting ? <><Loader2 size={16} className="animate-spin" /><span>{exportProgress}%</span><div className="absolute bottom-0 left-0 h-1 bg-green-500 transition-all duration-300" style={{ width: `${exportProgress}%` }} /></> : <><Video size={16} /> 動画</>}
          </button>
        </div>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 bg-slate-900 border-r border-white/5 flex flex-col">
          <div className="p-4 border-b border-white/5"><h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Slides ({slides.length})</h2></div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
            {slides.map((slide, index) => (
              <button key={slide.id} onClick={() => setActiveSlideIndex(index)} className={`w-full text-left p-2 rounded-lg transition-all border ${activeSlideIndex === index ? 'bg-slate-800 border-violet-500/50 shadow-md' : 'hover:bg-slate-800/50 border-transparent hover:border-white/5'}`}>
                <div className="flex gap-3">
                  <div className="relative w-16 aspect-video bg-slate-950 rounded overflow-hidden border border-white/10 flex-shrink-0">
                    <img src={slide.image} className="w-full h-full object-cover" alt={`Slide ${index + 1}`} />
                    {slide.isGenerating && <div className="absolute inset-0 bg-black/50 flex items-center justify-center"><Loader2 size={12} className="animate-spin text-white" /></div>}
                  </div>
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <span className="text-sm font-medium text-slate-300 truncate block">Slide {index + 1}</span>
                    <div className="flex items-center gap-2 mt-1">{slide.audio ? <span className="text-[10px] flex items-center gap-1 text-green-400"><Volume2 size={10} /> Audio</span> : <span className="text-[10px] flex items-center gap-1 text-orange-400"><FileText size={10} /> Text</span>}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 flex flex-col bg-slate-950 relative overflow-hidden">
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex-1 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-slate-950 relative flex items-center justify-center p-4">
              <div className="relative w-full h-full max-w-5xl flex flex-col items-center justify-center group">
                <div className="relative shadow-2xl rounded-lg overflow-hidden border border-slate-800 bg-black flex-shrink-1 min-h-0">
                  <img src={activeSlide?.image} className="max-w-full max-h-[calc(100vh-400px)] object-contain mx-auto" alt="Slide Preview" />
                  <audio ref={audioRef} src={activeSlide?.audio || ""} onPlay={() => setIsPlaying(true)} onPause={() => setIsPlaying(false)} onEnded={() => { setIsPlaying(false); if(audioRef.current) audioRef.current.currentTime = 0; }} />
                  {activeSlide?.audio && <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${isPlaying ? 'opacity-0 group-hover:opacity-100' : 'opacity-100'}`}><button onClick={handlePreviewPlay} className="w-16 h-16 bg-violet-600/90 hover:bg-violet-500 text-white rounded-full flex items-center justify-center shadow-xl backdrop-blur-sm transition-transform hover:scale-105 active:scale-95">{isPlaying ? <Square size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" className="ml-1" />}</button></div>}
                </div>
              </div>
              <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 flex justify-between pointer-events-none">
                <button onClick={() => setActiveSlideIndex(Math.max(0, activeSlideIndex - 1))} disabled={activeSlideIndex === 0} className="pointer-events-auto p-3 rounded-full bg-slate-900/50 hover:bg-slate-800 text-slate-300 backdrop-blur-sm transition-all disabled:opacity-0"><ChevronLeft size={32} /></button>
                <button onClick={() => setActiveSlideIndex(Math.min(slides.length - 1, activeSlideIndex + 1))} disabled={activeSlideIndex === slides.length - 1} className="pointer-events-auto p-3 rounded-full bg-slate-900/50 hover:bg-slate-800 text-slate-300 backdrop-blur-sm transition-all disabled:opacity-0"><ChevronRight size={32} /></button>
              </div>
            </div>
            <PlayerOverlay currentSlide={activeSlide} audioRef={audioRef} isPlaying={isPlaying} />
            <div className="h-8 bg-slate-900 border-t border-b border-white/5 flex items-center justify-center gap-4 text-xs text-slate-500 font-mono"><span>SLIDE {String(activeSlideIndex + 1).padStart(2, '0')} / {String(slides.length).padStart(2, '0')}</span></div>
          </div>
          <div className="h-[200px] bg-slate-900 flex flex-col flex-shrink-0">
            <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-slate-900/50">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2"><FileText size={12} /> Narration Script</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-600">{activeSlide?.script?.length || 0} characters</span>
                <button 
                  onClick={() => regenerateAudio(activeSlideIndex)} 
                  disabled={!activeSlide?.script || activeSlide?.isGenerating || isGeneratingAudio}
                  className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10"
                >
                  {activeSlide?.isGenerating ? <Loader2 size={12} className="animate-spin" /> : <Mic size={12} />}
                  {activeSlide?.isGenerating ? '生成中...' : '再生成'}
                </button>
              </div>
            </div>
            <textarea value={activeSlide?.script || ""} onChange={(e) => updateScript(activeSlideIndex, e.target.value)} className="flex-1 bg-slate-900 p-4 text-slate-300 text-lg leading-relaxed resize-none focus:outline-none focus:bg-slate-800/50 transition-colors font-medium" placeholder="ここに読み上げ原稿を入力してください..." />
          </div>
        </div>
      </div>
      {showHelp && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-white/10 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between p-6 border-b border-white/10 bg-gradient-to-r from-slate-900 to-slate-800"><h3 className="text-xl font-bold text-white flex items-center gap-2"><span className="text-2xl">🔮</span> 使い方ガイド</h3><button onClick={() => setShowHelp(false)} className="text-slate-400 hover:text-white"><X size={24} /></button></div>
            <div className="p-6 space-y-4">
              <div className="bg-slate-800/50 rounded-lg p-4 border border-white/5"><h4 className="font-bold text-violet-400 mb-2">[STEP 1] 原稿の自動セット</h4><p className="text-sm text-slate-300">PDFをアップロードすると、AIが生成した読み上げ原稿が自動的に各スライドに割り当てられます。</p></div>
              <div className="bg-slate-800/50 rounded-lg p-4 border border-white/5"><h4 className="font-bold text-violet-400 mb-2">[STEP 2] 編集と生成</h4><p className="text-sm text-slate-300">下部のエリアで原稿を自由に編集できます。<span className="text-white font-bold bg-indigo-600/50 px-1 rounded">音声生成</span> ボタンでAIナレーターが音声を吹き込みます。</p></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-orange-950/30 rounded-lg p-4 border border-orange-500/20"><h4 className="font-bold text-orange-400 mb-2 flex items-center gap-2"><FileText size={16}/> PPTX</h4><p className="text-xs text-orange-200/80">音声不要。原稿がスピーカーノートに入ったパワポをDL。</p></div>
                <div className="bg-indigo-950/30 rounded-lg p-4 border border-indigo-500/20"><h4 className="font-bold text-indigo-400 mb-2 flex items-center gap-2"><Video size={16}/> 動画</h4><p className="text-xs text-indigo-200/80">音声と字幕が同期したプレゼン動画(WebM)を作成。</p></div>
              </div>
            </div>
            <div className="p-4 bg-slate-950 border-t border-white/5 flex justify-end"><button onClick={() => setShowHelp(false)} className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors">閉じる</button></div>
          </div>
        </div>
      )}
    </div>
  );
}