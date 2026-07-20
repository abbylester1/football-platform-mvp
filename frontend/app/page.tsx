'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import Link from 'next/link';

interface Drill {
  id: string; name: string; status: string; category: string; created_at: string;
}

type Stage = 'idle' | 'uploading' | 'processing' | 'complete' | 'error';

const STEPS = [
  { label: 'Extracting Frames', icon: '🎞️' },
  { label: 'Detecting Players', icon: '👤' },
  { label: 'Tracking Ball', icon: '⚽' },
  { label: 'Estimating Pose', icon: '🧍' },
  { label: 'Reconstructing Motion', icon: '🔄' },
  { label: 'Building 3D Scene', icon: '🏗️' },
];

const CATEGORY_ICON: Record<string, string> = {
  passing: '⚡', shooting: '🎯', movement: '🏃', possession: '🔄',
};

export default function Home() {
  const [stage, setStage] = useState<Stage>('idle');
  const [drills, setDrills] = useState<Drill[]>([]);
  const [loadingDrills, setLoadingDrills] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileName, setFileName] = useState('');
  const [drillId, setDrillId] = useState<string | null>(null);
  const [sceneKey, setSceneKey] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch('/api/drills')
      .then(r => r.json())
      .then(setDrills)
      .catch(() => {})
      .finally(() => setLoadingDrills(false));
  }, []);

  const startUpload = useCallback((file: File) => {
    if (!file.type.startsWith('video/')) { setError('Please select a video file'); return; }
    if (file.size > 2 * 1024 ** 3) { setError('Video must be under 2GB'); return; }
    setError('');
    setFileName(file.name);
    setUploadProgress(0);
    setStage('uploading');

    const form = new FormData();
    form.append('file', file);
    form.append('name', file.name.replace(/\.[^.]+$/, ''));
    form.append('category', '');
    form.append('age_group', '');
    form.append('difficulty', '');
    form.append('description', '');

    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) setUploadProgress(Math.round((e.loaded / e.total) * 100));
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const drill = JSON.parse(xhr.responseText);
        setDrillId(drill.id);
        setStage('processing');
        startProcessing(drill.id);
      } else {
        setError('Upload failed. Please try again.');
        setStage('error');
      }
    };

    xhr.onerror = () => {
      setError('Upload failed. Please try again.');
      setStage('error');
    };

    xhr.open('POST', '/api/upload');
    xhr.send(form);
  }, []);

  const startProcessing = useCallback(async (id: string) => {
    setCurrentStep(-1);
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
    }, 8000);

    try {
      const res = await fetch(`/api/process/${id}`, { method: 'POST' });
      if (!res.ok) { clearInterval(stepInterval); setError('Processing failed to start'); setStage('error'); return; }

      while (true) {
        const statusRes = await fetch(`/api/process/${id}/status`);
        if (!statusRes.ok) { await new Promise(r => setTimeout(r, 2000)); continue; }
        const data = await statusRes.json();
        if (data.status === 'ready' || data.status === 'review') {
          clearInterval(stepInterval);
          setCurrentStep(STEPS.length - 1);
          setSceneKey(data.scene_key || null);
          await new Promise(r => setTimeout(r, 800));
          setStage('complete');
          setDrills(prev => {
            const exists = prev.some(d => d.id === id);
            if (exists) return prev.map(d => d.id === id ? { ...d, status: data.status } : d);
            return [{ id, name: fileName.replace(/\.[^.]+$/, ''), status: data.status, category: '', created_at: new Date().toISOString() }, ...prev];
          });
          return;
        }
        if (data.status === 'failed') {
          clearInterval(stepInterval);
          setError('Processing failed. Please try again.');
          setStage('error');
          return;
        }
        await new Promise(r => setTimeout(r, 2000));
      }
    } catch {
      clearInterval(stepInterval);
      setError('Processing failed. Please try again.');
      setStage('error');
    }
  }, [fileName]);

  const cancelUpload = useCallback(() => {
    if (xhrRef.current) xhrRef.current.abort();
    xhrRef.current = null;
    setStage('idle');
    setUploadProgress(0);
  }, []);

  const retry = useCallback(() => {
    setError('');
    setStage('idle');
    setUploadProgress(0);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) startUpload(f);
  }, [startUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) startUpload(f);
  }, [startUpload]);

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}m ${s}s`;
  };

  const estimatedTotal = 180;
  const elapsed = currentStep >= 0 ? currentStep * 8 + 8 : 0;
  const remaining = Math.max(0, estimatedTotal - elapsed);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800/50">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="text-sm font-bold tracking-tight">Foot Drill</span>
          {stage === 'idle' && drills.length > 0 && (
            <span className="text-xs text-gray-600">{drills.length} drill{drills.length > 1 ? 's' : ''}</span>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-6">
        {/* IDLE STATE */}
        {stage === 'idle' && (
          <div className="animate-fade-up">
            <div className="py-24 md:py-32 text-center">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
                Turn Football Drills<br />
                <span className="text-gray-400">into Interactive 3D</span>
              </h1>
              <p className="text-gray-600 mt-4 max-w-md mx-auto text-sm leading-relaxed">
                Upload one training video. Our AI reconstructs player movement into an interactive 3D drill.
              </p>

              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`mx-auto mt-10 max-w-sm border-2 border-dashed rounded-2xl py-12 px-8 cursor-pointer transition-all duration-200 ${
                  dragOver
                    ? 'border-white bg-white/[0.03]'
                    : 'border-gray-800 hover:border-gray-700 hover:bg-gray-900/30'
                }`}
              >
                <div className="w-12 h-12 mx-auto rounded-xl bg-gray-900 flex items-center justify-center mb-4">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-gray-400">
                    <path d="M10 3v10m0 0l-3-3m3 3l3-3M4 14v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <p className="text-sm font-medium">Upload Video</p>
                <p className="text-xs text-gray-600 mt-2">Drag &amp; Drop &middot; MP4 / MOV &middot; Max 2GB</p>
              </div>
              <input ref={fileInputRef} type="file" accept=".mp4,.mov,video/*" className="hidden" onChange={handleFileSelect} />
            </div>

            {/* Recent Drills */}
            {loadingDrills ? (
              <div className="pb-16 space-y-2 max-w-sm mx-auto">
                {[1,2,3].map(i => (
                  <div key={i} className="h-12 bg-gray-900/30 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : drills.length > 0 && (
              <div className="pb-24 max-w-sm mx-auto">
                <p className="text-xs text-gray-600 font-medium uppercase tracking-wider mb-3 px-1">Recent Drills</p>
                <div className="space-y-1">
                  {drills.slice(0, 5).map((d, i) => {
                    const statusColors: Record<string, string> = {
                      ready: 'text-emerald-500', review: 'text-sky-400', processing: 'text-amber-400', failed: 'text-red-400',
                    };
                    return (
                      <Link key={d.id} href={`/drill/${d.id}`}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-900/50 transition-colors group"
                      >
                        <span className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center text-xs shrink-0">
                          {CATEGORY_ICON[d.category] || '⚽'}
                        </span>
                        <span className="text-sm truncate flex-1 group-hover:text-white transition-colors">
                          {d.name || 'Untitled'}
                        </span>
                        <span className={`text-xs ${statusColors[d.status] || 'text-gray-600'}`}>
                          {d.status === 'ready' ? 'Ready' : d.status === 'review' ? 'Review' : d.status}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* UPLOADING STATE */}
        {stage === 'uploading' && (
          <div className="max-w-sm mx-auto py-32 animate-fade-up">
            <p className="text-xs text-gray-600 font-medium uppercase tracking-wider mb-3">Uploading...</p>
            <div className="h-2 bg-gray-900 rounded-full overflow-hidden mb-3">
              <div className="h-full bg-white rounded-full transition-all duration-300 ease-out" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="text-sm truncate">{fileName}</p>
            <p className="text-xs text-gray-600 mt-1">Estimated time: 2 minutes</p>
            <button onClick={cancelUpload} className="mt-4 text-xs text-gray-600 hover:text-gray-400 transition-colors">
              Cancel
            </button>
          </div>
        )}

        {/* PROCESSING STATE */}
        {stage === 'processing' && (
          <div className="max-w-2xl mx-auto py-20 animate-fade-up">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
              <div>
                <p className="text-xs text-gray-600 font-medium uppercase tracking-wider mb-6">Analyzing Your Drill</p>
                <div className="space-y-4">
                  {STEPS.map((step, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      {i < currentStep ? (
                        <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs">✓</span>
                      ) : i === currentStep ? (
                        <span className="w-5 h-5 rounded-full border-2 border-white/30 flex items-center justify-center">
                          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot" />
                        </span>
                      ) : (
                        <span className="w-5 h-5 rounded-full border border-gray-800" />
                      )}
                      <span className={i <= currentStep ? 'text-white' : 'text-gray-600'}>{step.label}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-600 mt-6">Estimated Remaining &middot; {formatTime(remaining)}</p>
              </div>

              <div className="hidden md:flex items-center justify-center">
                <div className="relative w-48 h-48">
                  <div className="absolute inset-0 flex items-center justify-center opacity-10 text-7xl">🎬</div>
                  <div className="absolute inset-0 flex items-center justify-center opacity-20 text-5xl animate-step-visual">🏃</div>
                  <div className="absolute inset-0 flex items-center justify-center opacity-10 text-4xl animate-step-visual" style={{ animationDelay: '0.5s', marginTop: '-30px' }}>⚽</div>
                  <div className="absolute inset-0 flex items-center justify-center text-3xl animate-step-visual" style={{ animationDelay: '1s', marginTop: '30px' }}>🧍</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* COMPLETE STATE */}
        {stage === 'complete' && (
          <div className="max-w-sm mx-auto py-32 text-center animate-scale-in">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-500/20 flex items-center justify-center mb-6">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
                <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="text-xl font-bold mb-6">Your Drill is Ready</h2>
            <div className="space-y-2">
              <Link href={`/drill/${drillId}`}
                className="block w-full bg-white text-black font-medium py-2.5 rounded-xl text-sm hover:bg-gray-200 transition-all"
              >
                Open Drill
              </Link>
              <button className="block w-full bg-gray-900 text-gray-400 font-medium py-2.5 rounded-xl text-sm hover:bg-gray-800 hover:text-gray-300 transition-all">
                Download GLB
              </button>
              <button className="block w-full bg-gray-900 text-gray-400 font-medium py-2.5 rounded-xl text-sm hover:bg-gray-800 hover:text-gray-300 transition-all">
                Share
              </button>
            </div>
          </div>
        )}

        {/* ERROR STATE */}
        {stage === 'error' && (
          <div className="max-w-sm mx-auto py-32 text-center animate-fade-up">
            <div className="w-12 h-12 mx-auto rounded-full bg-red-500/20 flex items-center justify-center mb-4">
              <span className="text-red-400 text-lg">!</span>
            </div>
            <p className="text-sm text-red-400 mb-6">{error}</p>
            <button onClick={retry}
              className="bg-white text-black font-medium px-6 py-2.5 rounded-xl text-sm hover:bg-gray-200 transition-all"
            >
              Try again
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
