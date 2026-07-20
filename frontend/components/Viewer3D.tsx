'use client';
import { useRef, useEffect, useState, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';
import * as THREE from 'three';

interface AnimData {
  type: string; id: string; label: string;
  frames: { frame: number; x: number; y: number; z: number }[];
}

function Field() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
      <planeGeometry args={[30, 20]} />
      <meshStandardMaterial color="#2d5a3f" />
    </mesh>
  );
}

const TYPE_COLORS: Record<string, string> = {
  player: '#e74c3c', ball: '#f1c40f', cone: '#e67e22',
};

function Avatar({ position, color, label }: { position: [number, number, number]; color: string; label: string }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.6, 0]} castShadow>
        <capsuleGeometry args={[0.15, 0.7, 4, 8]} />
        <meshStandardMaterial color={color} />
      </mesh>
      <mesh position={[0, 1.2, 0]} castShadow>
        <sphereGeometry args={[0.12, 8, 8]} />
        <meshStandardMaterial color="#f5d0b0" />
      </mesh>
      <Text position={[0, 1.5, 0]} fontSize={0.15} color="white" anchorX="center" anchorY="middle">{label}</Text>
    </group>
  );
}

function Sphere({ position, color }: { position: [number, number, number]; color: string }) {
  return (
    <mesh position={position} castShadow>
      <sphereGeometry args={[0.1, 8, 8]} />
      <meshStandardMaterial color={color} />
    </mesh>
  );
}

function Cone({ position }: { position: [number, number, number] }) {
  return (
    <mesh position={position} castShadow>
      <coneGeometry args={[0.04, 0.12, 6]} />
      <meshStandardMaterial color="#f39c12" />
    </mesh>
  );
}

interface AnimatedObjectProps {
  data: AnimData; color: string;
  playingRef: React.MutableRefObject<boolean>;
  speedRef: React.MutableRefObject<number>;
  timeRef: React.MutableRefObject<number>;
  totalFramesRef: React.MutableRefObject<number>;
}

function AnimatedObject({ data, color, playingRef, speedRef, timeRef, totalFramesRef }: AnimatedObjectProps) {
  const groupRef = useRef<THREE.Group>(null);
  const clockRef = useRef(0);

  useFrame((_, delta) => {
    if (data.frames.length < 2) return;
    totalFramesRef.current = data.frames.length;
    if (!playingRef.current) return;
    clockRef.current += delta * speedRef.current;
    const fps = 10;
    if (clockRef.current < 1 / fps) return;
    clockRef.current = 0;
    timeRef.current = (timeRef.current + 1) % data.frames.length;
    const f = data.frames[Math.floor(timeRef.current)];
    if (groupRef.current && f) groupRef.current.position.set(f.x, 0, f.z);
  });

  if (data.frames.length === 0) return null;

  const baseColor = data.type === 'player' ? color : data.type === 'ball' ? '#ffffff' : '#f39c12';

  return (
    <group ref={groupRef}>
      {data.type === 'player' ? (
        <Avatar position={[0, 0, 0]} color={baseColor} label={data.label} />
      ) : data.type === 'ball' ? (
        <Sphere position={[0, 0.1, 0]} color={baseColor} />
      ) : (
        <Cone position={[0, 0.06, 0]} />
      )}
    </group>
  );
}

function CameraController({ view }: { view: string }) {
  const { camera } = useThree();
  useEffect(() => {
    if (view === 'top') {
      camera.position.set(0, 20, 0.1);
      camera.lookAt(0, 0, 0);
    } else if (view === 'player') {
      camera.position.set(0, 1.5, 8);
      camera.lookAt(0, 0, 0);
    } else {
      camera.position.set(15, 12, 15);
      camera.lookAt(0, 0, 0);
    }
  }, [view, camera]);
  return null;
}

export default function Viewer3D({ objects, sceneUrl }: { objects: AnimData[]; sceneUrl?: string }) {
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalFrames, setTotalFrames] = useState(1);
  const [cameraView, setCameraView] = useState('default');
  const [seeking, setSeeking] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const playingRef = useRef(true);
  const speedRef = useRef(1);
  const timeRef = useRef(0);
  const totalFramesRef = useRef(1);

  useEffect(() => {
    playingRef.current = playing;
  }, [playing]);

  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(timeRef.current);
      setTotalFrames(totalFramesRef.current);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const togglePlay = useCallback(() => setPlaying(p => !p), []);

  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    timeRef.current = Math.round(pct * totalFramesRef.current);
    setCurrentTime(timeRef.current);
  }, []);

  const toggleFullscreen = useCallback(async () => {
    if (!containerRef.current) return;
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      setIsFullscreen(false);
    } else {
      await containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    }
  }, []);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const durationSec = totalFrames > 0 ? Math.round(totalFrames / 10) : 0;
  const currentSec = Math.round(currentTime / 10);

  return (
    <div ref={containerRef} className={`relative bg-gray-900 rounded-xl overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50 rounded-none' : 'w-full h-[65vh]'}`}>
      <Canvas camera={{ position: [15, 12, 15], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 15, 10]} intensity={0.8} castShadow />
        <Field />
        {objects.map(obj => (
          <AnimatedObject key={obj.id} data={obj} color={TYPE_COLORS[obj.type] || '#888'}
            playingRef={playingRef} speedRef={speedRef} timeRef={timeRef} totalFramesRef={totalFramesRef} />
        ))}
        <OrbitControls />
        <CameraController view={cameraView} />
      </Canvas>

      {/* Bottom Timeline */}
      <div className="absolute bottom-0 left-0 right-0 px-5 pb-4 pt-10 bg-gradient-to-t from-black/80 to-transparent">
        <div className="flex items-center gap-3 mb-2">
          <button onClick={togglePlay} className="text-white hover:text-gray-300 transition-colors">
            {playing ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><rect x="3" y="2" width="3" height="10" rx="0.5"/><rect x="8" y="2" width="3" height="10" rx="0.5"/></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><polygon points="3,2 12,7 3,12"/></svg>
            )}
          </button>
          <div className="flex gap-1">
            {[0.5, 1, 2].map(s => (
              <button key={s} onClick={() => setSpeed(s)}
                className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${speed === s ? 'bg-white/20 text-white' : 'text-gray-500 hover:text-gray-300'}`}
              >{s}x</button>
            ))}
          </div>
          <div className="flex-1 relative h-5 cursor-pointer group" onMouseDown={handleSeek}>
            <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-0.5 bg-gray-700 rounded group-hover:h-1 transition-all">
              <div className="h-full bg-white rounded" style={{ width: `${totalFrames > 0 ? (currentTime / totalFrames) * 100 : 0}%` }} />
            </div>
            <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${totalFrames > 0 ? (currentTime / totalFrames) * 100 : 0}%` }}>
              <div className="w-3 h-3 rounded-full bg-white -ml-1.5 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
          <span className="text-[11px] text-gray-400 tabular-nums w-16 text-right">
            {String(currentSec).padStart(2, '0')}:{String(Math.floor((currentTime % 10) * 10)).padStart(2, '0')} / {String(durationSec).padStart(2, '0')}:00
          </span>
        </div>
      </div>

      {/* Right Floating Controls */}
      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col gap-2">
        <button onClick={toggleFullscreen}
          className="w-9 h-9 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center hover:bg-black/70 transition-colors text-gray-400 hover:text-white"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            {isFullscreen ? (
              <><path d="M3 3h2v2M11 3h-2v2M3 11h2v-2M11 11h-2v-2"/></>
            ) : (
              <><path d="M3 3h2v2M11 3h-2v2M3 11h2v-2M11 11h-2v-2"/></>
            )}
          </svg>
        </button>
        <button onClick={() => setCameraView(v => v === 'player' ? 'default' : 'player')}
          className={`w-9 h-9 rounded-full backdrop-blur-sm flex items-center justify-center transition-colors text-xs ${
            cameraView === 'player' ? 'bg-white/20 text-white' : 'bg-black/50 text-gray-400 hover:bg-black/70 hover:text-white'
          }`}
        >🎥</button>
        <button onClick={() => setCameraView(v => v === 'top' ? 'default' : 'top')}
          className={`w-9 h-9 rounded-full backdrop-blur-sm flex items-center justify-center transition-colors text-xs ${
            cameraView === 'top' ? 'bg-white/20 text-white' : 'bg-black/50 text-gray-400 hover:bg-black/70 hover:text-white'
          }`}
        >🛰</button>
        <button onClick={() => setCameraView('default')}
          className="w-9 h-9 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center hover:bg-black/70 transition-colors text-gray-400 hover:text-white text-xs"
        >🧭</button>
      </div>
    </div>
  );
}
