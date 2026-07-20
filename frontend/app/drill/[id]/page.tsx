'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Viewer3D from '@/components/Viewer3D';

interface AnimData {
  type: string; id: string; label: string;
  frames: { frame: number; x: number; y: number; z: number }[];
}

export default function DrillPage() {
  const { id } = useParams<{ id: string }>();
  const [drill, setDrill] = useState<any>(null);
  const [scene, setScene] = useState<AnimData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retries, setRetries] = useState(0);
  const [showShare, setShowShare] = useState(false);
  const [copied, setCopied] = useState(false);
  const maxRetries = 5;

  useEffect(() => {
    if (retries > maxRetries) return;
    const timer = retries > 0 ? setTimeout : (fn: () => void) => { fn(); return undefined; };
    const t = timer(() => {
      fetch(`/api/drills/${id}`).then(r => {
        if (!r.ok) throw new Error('Not found');
        return r.json();
      }).then(d => {
        setDrill(d);
        setScene(d.detected_objects || []);
        setLoading(false);
      }).catch(() => {
        if (retries < maxRetries) setRetries(r => r + 1);
        else { setError('Could not load drill'); setLoading(false); }
      });
    }, retries > 0 ? 2000 : 0);
    return () => { if (t) clearTimeout(t); };
  }, [id, retries, maxRetries]);

  const copyLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
          <a href={`/api/video/${drill?.video_key}`} download
            className="text-xs text-gray-500 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-gray-800 transition-all"
          >
            Download
          </a>
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
        <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={() => setShowShare(false)}>
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-gray-950 border border-gray-800 rounded-t-2xl w-full max-w-sm p-5 animate-fade-up shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="w-8 h-1 rounded-full bg-gray-800 mx-auto mb-5" />
            <h3 className="text-sm font-medium mb-4">Share Drill</h3>
            <div className="flex items-center gap-2 bg-gray-900 rounded-xl px-3.5 py-2.5 mb-4 border border-gray-800/50">
              <input readOnly value={typeof window !== 'undefined' ? window.location.href : ''}
                className="bg-transparent text-xs flex-1 min-w-0 truncate focus:outline-none text-gray-400"
              />
              <button onClick={copyLink}
                className="text-xs text-white bg-white/10 hover:bg-white/20 px-3 py-1 rounded-lg transition-all shrink-0 font-medium"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="space-y-1.5">
              <button className="w-full bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-all active:scale-[0.99]">
                Export GLB
              </button>
              <button className="w-full bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-all active:scale-[0.99]">
                Download MP4 Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
