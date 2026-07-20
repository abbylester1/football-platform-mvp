'use client';
import { useEffect, useState } from 'react';

export default function ProcessingStatus({ drillId, onComplete }: {
  drillId: string;
  onComplete: () => void;
}) {
  const [message, setMessage] = useState('Starting processing...');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setMessage('Processing video...');
      const res = await fetch(`/api/process/${drillId}`, { method: 'POST' });
      if (cancelled) return;
      if (!res.ok) {
        setFailed(true);
        setMessage('Processing failed. Please try again.');
        return;
      }
      const data = await res.json();
      if (data.status === 'complete') {
        setMessage('Complete!');
        onComplete();
      }
    }

    run();
    return () => { cancelled = true; };
  }, [drillId, onComplete]);

  return (
    <div className="bg-gray-800 p-6 rounded-lg max-w-md mx-auto text-center space-y-4">
      <h2 className="text-lg font-bold">Processing Drill</h2>
      <div className="flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
      </div>
      <p className="text-sm text-gray-300">{message}</p>
      {failed && (
        <p className="text-red-400 text-sm">Processing failed. Please try again.</p>
      )}
    </div>
  );
}
