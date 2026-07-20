'use client';
import { useRef, useState } from 'react';

interface BBox { x: number; y: number; w: number; h: number; label: string; color: string; }

export default function VideoPlayer({ src, boundingBoxes, onDrawBox }: {
  src: string;
  boundingBoxes: BBox[];
  onDrawBox?: (box: { x: number; y: number; w: number; h: number }) => void;
}) {
  const [drawing, setDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentBox, setCurrentBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  function getContainerRect() {
    return containerRef.current!.getBoundingClientRect();
  }

  function handleMouseDown(e: React.MouseEvent) {
    if (!onDrawBox) return;
    setDrawing(true);
    const r = getContainerRect();
    setStartPos({ x: e.clientX - r.left, y: e.clientY - r.top });
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!drawing) return;
    const r = getContainerRect();
    const x = Math.min(startPos.x, e.clientX - r.left);
    const y = Math.min(startPos.y, e.clientY - r.top);
    const w = Math.abs(e.clientX - r.left - startPos.x);
    const h = Math.abs(e.clientY - r.top - startPos.y);
    setCurrentBox({ x, y, w, h });
  }

  function handleMouseUp() {
    if (drawing && currentBox && onDrawBox) {
      onDrawBox(currentBox);
    }
    setDrawing(false);
    setCurrentBox(null);
  }

  return (
    <div
      ref={containerRef}
      className="relative"
      style={{ aspectRatio: '16/9' }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      <video src={src} controls className="w-full h-full object-contain bg-black rounded" />
      {boundingBoxes.map((b, i) => (
        <div
          key={i}
          style={{
            position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h,
            border: '2px solid red', borderRadius: 4, pointerEvents: 'none',
          }}
        >
          <span style={{
            background: b.color, color: '#fff', fontSize: 10,
            padding: '0 4px', borderRadius: '0 4px 0 0', display: 'inline-block'
          }}>
            {b.label}
          </span>
        </div>
      ))}
      {currentBox && drawing && (
        <div style={{
          position: 'absolute', left: currentBox.x, top: currentBox.y,
          width: currentBox.w, height: currentBox.h,
          border: '2px dashed #fff', background: 'rgba(255,255,255,0.1)',
          borderRadius: 4, pointerEvents: 'none',
        }} />
      )}
    </div>
  );
}
