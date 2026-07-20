'use client';
import { useEffect, useState } from 'react';

export default function ProcessingStatus({ drillId, onComplete, onError }: {
  drillId: string;
  onComplete: (data: any) => void;
  onError: () => void;
}) {
  const [message, setMessage] = useState('Starting processing...');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval>;

    async function start() {
      setMessage('Processing video...');
      const res = await fetch(`/api/process/${drillId}`, { method: 'POST' });
      if (cancelled) return;
      if (!res.ok) {
        setFailed(true);
        setMessage('Processing failed to start. Please try again.');
        onError();
        return;
      }
      setMessage('Processing...');
      pollTimer = setInterval(poll, 2000);
    }

    async function poll() {
      try {
        const res = await fetch(`/api/process/${drillId}/status`);
        if (cancelled) return;
        if (!res.ok) { clearInterval(pollTimer); return; }
        const data = await res.json();
        if (data.status === 'review' || data.status === 'ready') {
          clearInterval(pollTimer);
          setMessage('Complete!');
          onComplete(data);
        } else if (data.status === 'failed') {
          clearInterval(pollTimer);
          setFailed(true);
          setMessage('Processing failed. Please try again.');
          onError();
        }
      } catch {
        if (cancelled) return;
      }
    }

    start();
    return () => {
      cancelled = true;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [drillId, onComplete, onError]);

  return (
    <div className="max-w-md mx-auto py-20 text-center">
      {failed ? (
        <div className="space-y-4">
          <div className="text-4xl">⚠️</div>
          <p className="text-red-400 text-sm">{message}</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="relative w-16 h-16 mx-auto">
            <div className="absolute inset-0 rounded-full border-2 border-gray-800" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-green-500 animate-spin" />
          </div>
          <div>
            <p className="text-sm font-medium">Processing</p>
            <p className="text-xs text-gray-500 mt-1">{message}</p>
          </div>
        </div>
      )}
    </div>
  );
}
