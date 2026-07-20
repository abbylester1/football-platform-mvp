'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Drill { id: string; name: string; status: string; created_at: string; }

export default function Home() {
  const [drills, setDrills] = useState<Drill[]>([]);

  useEffect(() => {
    fetch('/api/drills').then(r => r.json()).then(setDrills).catch(() => {});
  }, []);

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Football Drills</h1>
        <Link href="/upload" className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg">Upload New Drill</Link>
      </div>

      {drills.length === 0 && <p className="text-gray-400">No drills yet. Upload your first one!</p>}

      <div className="grid gap-4">
        {drills.map(d => (
          <Link key={d.id} href={`/drill/${d.id}`} className="bg-gray-800 p-4 rounded-lg hover:bg-gray-700 flex justify-between items-center">
            <div>
              <div className="font-semibold">{d.name || 'Untitled Drill'}</div>
              <div className="text-sm text-gray-400">{new Date(d.created_at).toLocaleDateString()}</div>
            </div>
            <span className={`px-2 py-1 rounded text-xs ${statusColor(d.status)}`}>{d.status}</span>
          </Link>
        ))}
      </div>
    </main>
  );
}

function statusColor(s: string) {
  switch(s) {
    case 'ready': return 'bg-green-900 text-green-300';
    case 'processing': return 'bg-yellow-900 text-yellow-300';
    case 'review': return 'bg-blue-900 text-blue-300';
    case 'failed': return 'bg-red-900 text-red-300';
    default: return 'bg-gray-700 text-gray-300';
  }
}
