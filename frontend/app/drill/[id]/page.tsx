'use client';
import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Viewer3D from '@/components/Viewer3D';

interface AnimData {
  type: string; id: string; label: string;
  frames: { frame: number; x: number; y: number; z: number }[];
}

const MAX_RETRIES = 5;

export default function DrillPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [drill, setDrill] = useState<any>(null);
  const [scene, setScene] = useState<AnimData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retries, setRetries] = useState(0);
  const [showShare, setShowShare] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchDrill = useCallback(async () => {
    try {
      const res = await fetch(`/api/drills/${id}`);
      if (!res.ok) throw new Error('Not found');
      const data = await res.json();
      setDrill(data);
      setScene(data.detected_objects || []);
      setLoading(false);
    } catch {
      if (retries < MAX_RETRIES) {
        setRetries(r => r + 1);
      } else {
        setError('Could not load drill');
        setLoading(false);
      }
    }
  }, [id, retries]);

  useEffect(() => {
    if (retries > MAX_RETRIES) return;
    const delay = retries > 0 ? 2000 * Math.min(retries, 3) : 0;
    const timer = setTimeout(fetchDrill, delay);
    return () => clearTimeout(timer);
  }, [fetchDrill, retries]);

  const copyLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement('input');
      input.value = window.location.href;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  const downloadGLB = useCallback(() => {
    if (!drill?.scene_key) return;
    const link = document.createElement('a');
    link.href = `/api/scenes/${drill.scene_key}`;
    link.download = `${drill.name || 'drill'}.glb`;
    link.click();
  }, [drill]);

  const downloadVideo = useCallback(() => {
    if (!drill?.video_key) return;
    const link = document.createElement('a');
    link.href = `/api/video/${drill.video_key}`;
    link.download = `${drill.name || 'drill'}.mp4`;
    link.click();
  }, [drill]);

  const deleteDrill = useCallback(async () => {
    setDeleting(true);
    try {
      const res = await fetch(`/api/drills/${id}`, { method: 'DELETE' });
      if (res.ok) {
        router.push('/');
      } else {
        setError('Failed to delete drill');
        setShowDelete(false);
      }
    } catch {
      setError('Failed to delete drill');
      setShowDelete(false);
    } finally {
      setDeleting(false);
    }
  }, [id, router]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="text-center space-y-3">
        <div className="animate-spin rounded-full h-4 w-4 border-[1.5px] border-gray-700 border-t-white mx-auto" />
        <p className="text-xs text-gray-600">{retries > 0 ? `Loading${' .'.repeat(retries)}` : 'Loading drill'}</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 gap-4">
      <p className="text-sm text-red-400">{error}</p>
      <div className="flex gap-3">
        <button onClick={() => { setError(''); setLoading(true); setRetries(0); }}
          className="bg-white text-black font-medium px-5 py-2 rounded-xl text-sm hover:bg-gray-200 transition-all active:scale-[0.98]"
        >
          Retry
        </button>
        <Link href="/" className="text-sm text-gray-500 hover:text-white px-5 py-2 transition-colors">
          Back
        </Link>
      </div>
    </div>
  );

  const players = scene.filter(o => o.type === 'player').length;
  const totalFrames = Math.max(...scene.map(o => o.frames.length), 0);
  const durationSec = Math.round(totalFrames / 10);

  const sidebarItems = [
    { label: 'Category', value: drill?.category || '—' },
    { label: 'Age', value: drill?.age_group || '—' },
    { label: 'Difficulty', value: drill?.difficulty || '—' },
    { label: 'Players', value: players || '—' },
    { label: 'Duration', value: durationSec ? `${durationSec}s` : '—' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <div className="flex items-center h-11 px-4 border-b border-gray-800/40 gap-2 shrink-0">
        <Link href="/" className="text-gray-600 hover:text-gray-300 transition-colors p-1 -ml-1">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><path d="M9 3L5 7l4 4"/></svg>
        </Link>
        <span className="text-sm font-medium truncate">{drill?.name || 'Drill'}</span>
        <div className="ml-auto flex items-center gap-1.5">
          <button onClick={() => setShowShare(!showShare)}
            className="text-xs text-gray-500 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-gray-800 transition-all"
          >
            Share
          </button>
          <button onClick={downloadGLB}
            className="text-xs text-gray-500 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-gray-800 transition-all"
          >
            Export
          </button>
          <button onClick={downloadVideo}
            className="text-xs text-gray-500 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-gray-800 transition-all"
          >
            Video
          </button>
          <button onClick={() => setShowDelete(true)}
            className="text-xs text-red-500/70 hover:text-red-400 px-2.5 py-1.5 rounded-lg hover:bg-red-500/10 transition-all"
          >
            Delete
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row">
        <div className="flex-1 min-h-0">
          <Viewer3D objects={scene} />
        </div>

        <div className="w-full lg:w-56 border-l border-gray-800/40 p-4 space-y-5 overflow-y-auto shrink-0">
          {sidebarItems.map((item, i) => (
            <div key={i}>
              <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-1.5">{item.label}</p>
              <p className="text-sm capitalize">{item.value}</p>
            </div>
          ))}
          {drill?.description && (
            <div className="pt-3 border-t border-gray-800/40">
              <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-1.5">Description</p>
              <p className="text-sm text-gray-400 leading-relaxed">{drill.description}</p>
            </div>
          )}
        </div>
      </div>

      {showShare && (
        <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={() => setShowShare(false)} role="dialog" aria-modal="true" aria-label="Share drill">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-gray-950 border border-gray-800 rounded-t-2xl w-full max-w-sm p-5 animate-fade-up shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="w-8 h-1 rounded-full bg-gray-800 mx-auto mb-5" />
            <h3 className="text-sm font-medium mb-4">Share Drill</h3>
            <div className="flex items-center gap-2 bg-gray-900 rounded-xl px-3.5 py-2.5 mb-4 border border-gray-800/50">
              <input readOnly value={typeof window !== 'undefined' ? window.location.href : ''}
                className="bg-transparent text-xs flex-1 min-w-0 truncate focus:outline-none text-gray-400"
                aria-label="Drill link"
              />
              <button onClick={copyLink}
                className="text-xs text-white bg-white/10 hover:bg-white/20 px-3 py-1 rounded-lg transition-all shrink-0 font-medium"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="space-y-1.5">
              <button onClick={() => { downloadGLB(); setShowShare(false); }}
                className="w-full bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-all active:scale-[0.99]">
                Export GLB
              </button>
              <button onClick={() => { downloadVideo(); setShowShare(false); }}
                className="w-full bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-all active:scale-[0.99]">
                Download Video
              </button>
            </div>
          </div>
        </div>
      )}

      {showDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => setShowDelete(false)} role="dialog" aria-modal="true" aria-label="Delete drill">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div className="relative bg-gray-950 border border-gray-800 rounded-2xl w-full max-w-xs p-6 animate-scale-in shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="w-10 h-10 mx-auto rounded-full bg-red-500/15 flex items-center justify-center mb-4">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-red-400">
                <path d="M3 5h12M7 5V3h4v2M6 5v10h6V5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h3 className="text-sm font-medium text-center mb-2">Delete Drill?</h3>
            <p className="text-xs text-gray-500 text-center mb-6">
              This will permanently remove <span className="text-gray-300">{drill?.name || 'this drill'}</span> and all its data. This cannot be undone.
            </p>
            <div className="flex gap-2">
              <button onClick={() => setShowDelete(false)}
                className="flex-1 bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-all active:scale-[0.98]"
              >
                Cancel
              </button>
              <button onClick={deleteDrill} disabled={deleting}
                className="flex-1 bg-red-600 hover:bg-red-500 text-white text-sm py-2.5 rounded-xl transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleting ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-3 h-3 border-[1.5px] border-white/30 border-t-white rounded-full animate-spin" />
                    Deleting
                  </span>
                ) : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
