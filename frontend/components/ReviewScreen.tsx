'use client';
import { useState } from 'react';
import VideoPlayer from './VideoPlayer';

interface DetectedObject {
  type: string;
  id: string;
  label: string;
  avatar_id?: string;
}

const TYPE_COLORS: Record<string, string> = {
  player: '#e74c3c', ball: '#f1c40f', cone: '#e67e22',
};

export default function ReviewScreen({ drillId, videoSrc, initialObjects, onConfirm }: {
  drillId: string;
  videoSrc: string;
  initialObjects: DetectedObject[];
  onConfirm: (objects: DetectedObject[]) => void;
}) {
  const [objects, setObjects] = useState<DetectedObject[]>(initialObjects);
  const [addingType, setAddingType] = useState<'player' | 'cone' | null>(null);

  function handleRename(id: string, newLabel: string) {
    setObjects(prev => prev.map(o => o.id === id ? { ...o, label: newLabel } : o));
  }

  function handleDelete(id: string) {
    setObjects(prev => prev.filter(o => o.id !== id));
  }

  function handleAddBox() {
    if (!addingType) return;
    const newId = `${addingType}_${Date.now()}`;
    setObjects(prev => [...prev, { type: addingType, id: newId, label: `New ${addingType}` }]);
    setAddingType(null);
  }

  async function handleConfirm() {
    await fetch(`/api/drills/${drillId}/objects`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        detected_objects: objects.map(o => ({ type: o.type, id: o.id, label: o.label, frames: [] })),
      }),
    });
    await fetch(`/api/process/${drillId}`, { method: 'POST' });
    onConfirm(objects);
  }

  const bboxes = objects.map(o => ({
    x: 10, y: 10, w: 50, h: 80,
    label: o.label || o.id, color: TYPE_COLORS[o.type] || '#888',
  }));

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="col-span-2">
        <VideoPlayer src={videoSrc} boundingBoxes={bboxes} onDrawBox={addingType ? handleAddBox : undefined} />
      </div>
      <div className="bg-gray-800 p-4 rounded-lg space-y-3">
        <h3 className="font-bold">Detected Objects</h3>

        {(['player', 'ball', 'cone'] as const).map(type => {
          const items = objects.filter(o => o.type === type);
          return (
            <div key={type}>
              <div className="text-sm font-semibold capitalize mb-1">{type}s ({items.length})</div>
              <div className="space-y-1">
                {items.map(o => (
                  <div key={o.id} className="flex items-center gap-2 text-sm">
                    <span className="w-2 h-2 rounded-full shrink-0"
                      style={{ background: TYPE_COLORS[type] }} />
                    <input
                      value={o.label}
                      onChange={e => handleRename(o.id, e.target.value)}
                      className="bg-gray-700 px-2 py-0.5 rounded text-sm flex-1 min-w-0"
                    />
                    <button onClick={() => handleDelete(o.id)}
                      className="text-red-400 hover:text-red-300 text-xs">x</button>
                  </div>
                ))}
                {type !== 'ball' && (
                  <button
                    onClick={() => setAddingType(addingType === type ? null : type)}
                    className={`text-xs px-2 py-1 rounded mt-1 ${
                      addingType === type ? 'bg-green-600' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    {addingType === type ? 'Cancel' : '+ Add'}
                  </button>
                )}
              </div>
            </div>
          );
        })}

        <button
          onClick={handleConfirm}
          className="w-full bg-green-600 hover:bg-green-700 py-2 rounded-lg mt-4"
        >
          Looks good — Generate 3D
        </button>
      </div>
    </div>
  );
}
