'use client';
import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import ReviewScreen from '../../../components/ReviewScreen';
import Viewer3D from '../../../components/Viewer3D';
import ProcessingStatus from '../../../components/ProcessingStatus';

interface Frame { frame: number; x: number; y: number; z: number; }
interface DetectedObject {
  type: string;
  id: string;
  label: string;
  avatar_id?: string;
  frames: Frame[];
}
interface DrillData {
  id: string;
  name: string;
  status: string;
  video_key: string;
  detected_objects: DetectedObject[];
  scene_key: string;
}

export default function DrillPage() {
  const params = useParams();
  const drillId = params.id as string;
  const [drill, setDrill] = useState<DrillData | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'loading' | 'processing' | 'review' | 'viewer'>('loading');

  useEffect(() => {
    fetch(`/api/drills/${drillId}`)
      .then(r => r.json())
      .then((data: DrillData) => {
        setDrill(data);
        if (data.status === 'uploading') setView('processing');
        else if (data.status === 'processing') setView('processing');
        else if (data.status === 'review') setView('review');
        else if (data.status === 'ready') setView('viewer');
        else setView('review');
      })
      .catch(() => setLoading(false))
      .finally(() => setLoading(false));
  }, [drillId]);

  const handleProcessingComplete = useCallback(() => {
    fetch(`/api/drills/${drillId}`)
      .then(r => r.json())
      .then((data: DrillData) => {
        setDrill(data);
        setView('review');
      });
  }, [drillId]);

  const handleReviewConfirm = useCallback(() => {
    setView('processing');
    fetch(`/api/process/${drillId}`, { method: 'POST' })
      .then(r => r.json())
      .then(() => fetch(`/api/drills/${drillId}`))
      .then(r => r.json())
      .then((data: DrillData) => {
        setDrill(data);
        setView(data.status === 'ready' ? 'viewer' : 'review');
      });
  }, [drillId]);

  if (loading) return <div className="p-6 text-center text-gray-400">Loading...</div>;
  if (!drill) return <div className="p-6 text-center text-red-400">Drill not found</div>;

  const videoSrc = `/api/video/${drill.video_key}`;
  const sceneUrl = drill.scene_key ? `/api/scene/${drill.scene_key}` : undefined;

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{drill.name || 'Untitled Drill'}</h1>
        <span className={`px-3 py-1 rounded text-sm ${
          drill.status === 'ready' ? 'bg-green-900 text-green-300' :
          drill.status === 'processing' ? 'bg-yellow-900 text-yellow-300' :
          drill.status === 'review' ? 'bg-blue-900 text-blue-300' :
          drill.status === 'failed' ? 'bg-red-900 text-red-300' :
          'bg-gray-700 text-gray-300'
        }`}>{drill.status}</span>
      </div>

      {view === 'processing' && (
        <ProcessingStatus drillId={drillId} onComplete={handleProcessingComplete} />
      )}

      {view === 'review' && (
        <ReviewScreen
          drillId={drillId}
          videoSrc={videoSrc}
          initialObjects={(drill.detected_objects || []).map(o => ({
            type: o.type, id: o.id, label: o.label, avatar_id: o.avatar_id,
          }))}
          onConfirm={handleReviewConfirm}
        />
      )}

      {view === 'viewer' && drill.detected_objects && (
        <Viewer3D objects={drill.detected_objects} sceneUrl={sceneUrl} />
      )}
    </main>
  );
}
