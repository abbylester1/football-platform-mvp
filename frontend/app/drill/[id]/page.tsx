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
  const [showShare, setShowShare] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch(`/api/drills/${id}`).then(r => {
      if (!r.ok) throw new Error('Not found');
      return r.json();
    }).then(d => {
      setDrill(d);
      setScene(d.detected_objects || []);
    }).catch(() => setError('Could not load drill'))
    .finally(() => setLoading(false));
  }, [id]);

  const copyLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-600 border-t-white" />
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 gap-4">
      <p className="text-sm text-red-400">{error}</p>
      <Link href="/" className="text-sm text-gray-500 hover:text-white transition-colors">&larr; Back</Link>
    </div>
  );

  const players = scene.filter(o => o.type === 'player').length;
  const totalFrames = Math.max(...scene.map(o => o.frames.length), 0);
  const durationSec = Math.round(totalFrames / 10);

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center h-12 px-4 border-b border-gray-800/50 gap-3 shrink-0">
        <Link href="/" className="text-gray-600 hover:text-gray-300 transition-colors">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M10 3L5 8l5 5"/></svg>
        </Link>
        <span className="text-sm font-medium truncate">{drill?.name || 'Drill'}</span>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setShowShare(!showShare)}
            className="text-xs text-gray-500 hover:text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Share
          </button>
          <a href={`/api/video/${drill?.video_key}`} download
            className="text-xs text-gray-500 hover:text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Download
          </a>
        </div>
      </div>

      {/* Main layout */}
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* 3D Viewer */}
        <div className="flex-1 min-h-0">
          <Viewer3D objects={scene} />
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-64 border-l border-gray-800/50 p-5 space-y-5 overflow-y-auto shrink-0">
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Category</p>
            <p className="text-sm capitalize">{drill?.category || '—'}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Age</p>
            <p className="text-sm">{drill?.age_group || '—'}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Difficulty</p>
            <p className="text-sm capitalize">{drill?.difficulty || '—'}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Players</p>
            <p className="text-sm">{players || '—'}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Duration</p>
            <p className="text-sm">{durationSec ? `${durationSec} sec` : '—'}</p>
          </div>
          {drill?.description && (
            <div>
              <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">Description</p>
              <p className="text-sm text-gray-400 leading-relaxed">{drill.description}</p>
            </div>
          )}
        </div>
      </div>

      {/* Share drawer */}
      {showShare && (
        <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={() => setShowShare(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div className="relative bg-gray-950 border border-gray-800 rounded-t-2xl w-full max-w-md p-6 animate-fade-up" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-medium mb-4">Share Drill</h3>
            <div className="flex items-center gap-2 bg-gray-900 rounded-xl px-4 py-3 mb-4">
              <input readOnly value={typeof window !== 'undefined' ? window.location.href : ''}
                className="bg-transparent text-sm flex-1 min-w-0 truncate focus:outline-none text-gray-400"
              />
              <button onClick={copyLink}
                className="text-xs text-white bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors shrink-0"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="space-y-2">
              <button className="w-full bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-colors">
                Export GLB
              </button>
              <button className="w-full bg-gray-900 hover:bg-gray-800 text-sm py-2.5 rounded-xl transition-colors">
                Download MP4 Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
