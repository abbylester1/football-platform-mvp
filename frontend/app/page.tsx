'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import Link from 'next/link';
import HeroAnimation from '@/components/HeroAnimation';
import ProcessingAnimation from '@/components/ProcessingAnimation';

interface Drill {
  id: string; name: string; status: string; category: string; created_at: string;
}

type Stage = 'idle' | 'uploading' | 'processing' | 'complete' | 'error';

const frameIcon = <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><rect x="1.5" y="2" width="11" height="10" rx="1"/><path d="M5.5 5v4M8.5 5v4M1.5 6.5h11"/></svg>;
const playerIcon = <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="7" cy="4" r="1.8"/><path d="M3 12.5c0-2.2 1.8-4 4-4s4 1.8 4 4"/></svg>;
const ballIcon = <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="7" cy="7" r="5.5"/><path d="M2 4.5l4 1L7 2M10 9.5l-2.5-1.5L7 12"/><path d="M11 5l-3.5 1L7 2"/><path d="M12 9l-4 .5-1 3M2.5 9.5L7 9"/></svg>;
const poseIcon = <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="7" cy="2.5" r="1"/><path d="M7 4v3M7 7l-2 3M7 7l2 3M5 12l2-1.5L9 12"/></svg>;
const motionIcon = <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><path d="M10 1.5A5.5 5.5 0 111 7"/><path d="M10 5V1.5H5.5"/></svg>;
const sceneIcon = <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><rect x="1.5" y="2.5" width="5" height="4" rx="0.5"/><rect x="7.5" y="2.5" width="5" height="4" rx="0.5"/><rect x="1.5" y="7.5" width="5" height="4" rx="0.5"/><rect x="7.5" y="7.5" width="5" height="4" rx="0.5"/></svg>;

const STEPS = [
  { label: 'Extracting Frames', icon: frameIcon },
  { label: 'Detecting Players', icon: playerIcon },
  { label: 'Tracking Ball', icon: ballIcon },
  { label: 'Estimating Pose', icon: poseIcon },
  { label: 'Reconstructing Motion', icon: motionIcon },
  { label: 'Building 3D Scene', icon: sceneIcon },
];

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  passing: <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"><path d="M7 1v12M1 7h12"/><path d="M4.5 3.5l3-2.5 3 2.5"/><path d="M4.5 10.5l3 2.5 3-2.5"/></svg>,
  shooting: <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="7" cy="7" r="5.5"/><circle cx="7" cy="7" r="1.5"/><path d="M7 1v1.5M7 11.5V13M1 7h1.5M11.5 7H13"/></svg>,
  movement: <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="7" cy="3.5" r="1.2"/><path d="M4.5 13l1.5-5 1 1 1-1 1.5 5"/><path d="M3 8l4-2 4 2"/></svg>,
  possession: <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><path d="M10 1.5A5.5 5.5 0 111 7"/><path d="M10 5V1.5H5.5"/></svg>,
};

const STATUS_COLOR: Record<string, string> = {
  ready: 'text-emerald-500', review: 'text-sky-400', processing: 'text-amber-400', failed: 'text-red-400',
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
  const [showDrills, setShowDrills] = useState(false);
  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch('/api/drills').then(r => r.json()).then(d => {
      setDrills(d);
      if (d.length > 0) setShowDrills(true);
    }).catch(() => {}).finally(() => setLoadingDrills(false));
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
      } else { setError('Upload failed. Please try again.'); setStage('error'); }
    };
    xhr.onerror = () => { setError('Upload failed. Please try again.'); setStage('error'); };
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

  const retry = useCallback(() => { setError(''); setStage('idle'); setUploadProgress(0); }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
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
      <header className="border-b border-gray-800/40">
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center justify-between">
          <span className="text-sm font-semibold tracking-tight">Foot Drill</span>
          {stage === 'idle' && showDrills && (
            <span className="text-[11px] text-gray-600">{drills.length} drill{drills.length > 1 ? 's' : ''}</span>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-6">
        {stage === 'idle' && (
          <div className="animate-fade-up relative">
            <HeroAnimation />
            <div className="relative z-10 py-28 md:py-36 text-center">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-[11px] text-gray-500 mb-8">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
                AI-powered 3D reconstruction
              </div>
              <h1 className="text-[clamp(2rem,5vw,3.5rem)] font-bold tracking-tight leading-[1.1]">
                Turn Football Drills<br />
                <span className="text-gray-500">into Interactive 3D</span>
              </h1>
              <p className="text-gray-600 mt-3 max-w-sm mx-auto text-sm leading-relaxed">
                Upload one training video. Our AI reconstructs player movement into an interactive 3D drill.
              </p>

              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`mx-auto mt-10 max-w-xs border-2 border-dashed rounded-2xl py-10 px-8 cursor-pointer transition-all duration-300 ${
                  dragOver
                    ? 'border-white bg-white/[0.03] scale-[1.02]'
                    : 'border-gray-800 hover:border-gray-700 hover:bg-gray-900/30'
                }`}
              >
                <div className="w-11 h-11 mx-auto rounded-xl bg-gray-900 flex items-center justify-center mb-3">
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-gray-400">
                    <path d="M9 2v10m0 0l-3-3m3 3l3-3M3 13v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <p className="text-sm font-medium">Upload Video</p>
                <p className="text-xs text-gray-600 mt-1.5">Drag &amp; Drop &middot; MP4 / MOV &middot; Max 2GB</p>
              </div>
              <input ref={fileInputRef} type="file" accept=".mp4,.mov,video/*" className="hidden" onChange={handleFileSelect} />
            </div>

            {loadingDrills ? (
              <div className="pb-24 max-w-xs mx-auto space-y-1.5">
                {[1,2,3].map(i => <div key={i} className="h-10 bg-gray-900/30 rounded-xl animate-pulse" />)}
              </div>
            ) : showDrills && (
              <div className="pb-24 max-w-xs mx-auto">
                <div className="flex items-center gap-2 px-1 mb-3">
                  <span className="text-[11px] text-gray-600 font-medium uppercase tracking-wider">Recent</span>
                  <span className="h-px flex-1 bg-gray-800/50" />
                </div>
                <div className="space-y-0.5">
                  {drills.slice(0, 5).map(d => (
                    <Link key={d.id} href={`/drill/${d.id}`}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-900/60 transition-all duration-200 group active:scale-[0.99]"
                    >
                      <span className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center shrink-0 group-hover:bg-gray-800 transition-colors">
                        {CATEGORY_ICON[d.category] || <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="7" cy="7" r="5.5"/><path d="M2 4.5l4 1L7 2M10 9.5l-2.5-1.5L7 12"/><path d="M11 5l-3.5 1L7 2"/><path d="M12 9l-4 .5-1 3M2.5 9.5L7 9"/></svg>}
                      </span>
                      <span className="text-sm truncate flex-1 group-hover:text-white transition-colors duration-200">
                        {d.name || 'Untitled'}
                      </span>
                      <span className={`text-[11px] font-medium ${STATUS_COLOR[d.status] || 'text-gray-600'}`}>
                        {d.status === 'ready' ? 'Ready' : d.status === 'review' ? 'Review' : d.status}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {stage === 'uploading' && (
          <div className="max-w-sm mx-auto py-36 animate-fade-up">
            <p className="text-[11px] text-gray-600 font-medium uppercase tracking-wider mb-3">Uploading</p>
            <div className="h-1.5 bg-gray-900 rounded-full overflow-hidden mb-3">
              <div className="h-full bg-white rounded-full transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="text-sm truncate">{fileName}</p>
            <p className="text-xs text-gray-600 mt-1">Estimated time: 2 minutes</p>
            <button onClick={cancelUpload} className="mt-4 text-xs text-gray-600 hover:text-gray-400 transition-colors">
              Cancel
            </button>
          </div>
        )}

        {stage === 'processing' && (
          <ProcessingAnimation
            currentStep={currentStep}
            steps={STEPS}
            estimatedTime={180}
          />
        )}

        {stage === 'complete' && (
          <div className="max-w-xs mx-auto py-36 text-center animate-scale-in">
            <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/15 flex items-center justify-center mb-5">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" className="text-emerald-400">
                <path d="M18 6L8.5 15.5l-4.5-4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="text-lg font-semibold mb-5">Your Drill is Ready</h2>
            <div className="space-y-2">
              <Link href={`/drill/${drillId}`}
                className="block w-full bg-white text-black font-medium py-2.5 rounded-xl text-sm hover:bg-gray-200 transition-all duration-200 active:scale-[0.98]"
              >
                Open Drill
              </Link>
              <button onClick={() => {
                if (!drillId) return;
                fetch(`/api/drills/${drillId}`).then(r => r.json()).then(d => {
                  if (d.scene_key) {
                    const link = document.createElement('a');
                    link.href = `/api/scenes/${d.scene_key}`;
                    link.download = `${d.name || 'drill'}.glb`;
                    link.click();
                  }
                });
              }} className="block w-full bg-gray-900 text-gray-500 font-medium py-2.5 rounded-xl text-sm hover:bg-gray-800 hover:text-gray-300 transition-all duration-200 active:scale-[0.98]">
                Download GLB
              </button>
              <button onClick={() => {
                if (drillId) {
                  navigator.clipboard.writeText(`${window.location.origin}/drill/${drillId}`);
                  alert('Link copied to clipboard!');
                }
              }} className="block w-full bg-gray-900 text-gray-500 font-medium py-2.5 rounded-xl text-sm hover:bg-gray-800 hover:text-gray-300 transition-all duration-200 active:scale-[0.98]">
                Share
              </button>
            </div>
          </div>
        )}

        {stage === 'error' && (
          <div className="max-w-xs mx-auto py-36 text-center animate-fade-up">
            <div className="w-11 h-11 mx-auto rounded-full bg-red-500/15 flex items-center justify-center mb-4">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-red-400">
                <path d="M8 5v3m0 2v.01M3.07 14h9.86a1 1 0 00.87-1.5L8.87 2.5a1 1 0 00-1.74 0L2.2 12.5a1 1 0 00.87 1.5z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p className="text-sm text-red-400 mb-5">{error}</p>
            <button onClick={retry}
              className="bg-white text-black font-medium px-5 py-2.5 rounded-xl text-sm hover:bg-gray-200 transition-all duration-200 active:scale-[0.98]"
            >
              Try again
            </button>
          </div>
        )}
      </main>

      {/* About Section */}
      {stage === 'idle' && (
        <footer className="border-t border-gray-800/40 mt-auto">
          <div className="max-w-5xl mx-auto px-6 py-16">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
              {/* What We Do */}
              <div>
                <h3 className="text-sm font-semibold mb-3">What We Do</h3>
                <p className="text-xs text-gray-600 leading-relaxed">
                  We transform raw football training footage into interactive 3D visualizations.
                  Our AI pipeline detects players, extracts skeletal poses, and reconstructs
                  drill movements — giving coaches actionable insights from every session.
                </p>
              </div>

              {/* How It Works */}
              <div>
                <h3 className="text-sm font-semibold mb-3">How It Works</h3>
                <ul className="space-y-2 text-xs text-gray-600">
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5">01</span>
                    <span>Upload a training video (MP4/MOV, up to 2GB)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5">02</span>
                    <span>AI detects players, ball, and cones using YOLOv11</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5">03</span>
                    <span>MediaPipe extracts 33 skeletal landmarks per player</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5">04</span>
                    <span>3D scene with articulated stick-figure skeletons</span>
                  </li>
                </ul>
              </div>

              {/* Tech Stack */}
              <div>
                <h3 className="text-sm font-semibold mb-3">Built With</h3>
                <div className="flex flex-wrap gap-2">
                  {['YOLOv11', 'MediaPipe', 'Next.js', 'Three.js', 'FastAPI', 'OpenCV'].map(tech => (
                    <span key={tech} className="px-2.5 py-1 rounded-lg bg-gray-900/60 border border-gray-800/50 text-[11px] text-gray-500">
                      {tech}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-gray-700 mt-4">
                  Open source · MIT License
                </p>
                <a
                  href="https://github.com/abbylester1/football-platform-mvp"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[11px] text-gray-500 hover:text-white transition-colors mt-2"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M6 0C2.69 0 0 2.69 0 6c0 2.69 1.75 4.97 4.19 5.77.31.06.42-.13.42-.3 0-.15-.01-.65-.01-1.27-1.7.37-2.06-.82-2.06-.82-.28-.7-.68-.89-.68-.89-.55-.38.04-.37.04-.37.61.04.93.63.93.63.54.92 1.42.65 1.77.5.05-.39.21-.65.38-.8-1.36-.15-2.79-.68-2.79-3.04 0-.67.24-1.22.63-1.65-.06-.15-.27-.77.06-1.6 0 0 .52-.17 1.7.63a5.94 5.94 0 013.12 0c1.18-.8 1.7-.63 1.7-.63.34.83.13 1.45.06 1.6.39.43.63.98.63 1.65 0 2.37-1.43 2.89-2.8 3.04.22.19.42.56.42 1.13 0 .82-.01 1.48-.01 1.68 0 .17.11.37.42.3C10.25 10.96 12 8.68 12 6c0-3.31-2.69-6-6-6z"/>
                  </svg>
                  View on GitHub
                </a>
              </div>
            </div>

            <div className="mt-12 pt-6 border-t border-gray-800/30 flex items-center justify-between text-[11px] text-gray-700">
              <span>© 2026 Football Drill Digitization Platform</span>
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" />
                All systems operational
              </span>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}
