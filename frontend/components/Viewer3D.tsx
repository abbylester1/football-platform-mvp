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
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[30, 20]} />
        <meshStandardMaterial color="#2d5a3f" />
      </mesh>
      {/* Field markings */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <planeGeometry args={[28, 18]} />
        <meshBasicMaterial color="#3a7a4f" wireframe />
      </mesh>
      {/* Center line */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <planeGeometry args={[0.04, 18]} />
        <meshBasicMaterial color="white" opacity={0.3} transparent />
      </mesh>
      {/* Center circle */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <ringGeometry args={[4.5, 4.54, 32]} />
        <meshBasicMaterial color="white" opacity={0.3} transparent side={THREE.DoubleSide} />
      </mesh>
      {/* Center dot */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <circleGeometry args={[0.2, 16]} />
        <meshBasicMaterial color="white" opacity={0.3} transparent />
      </mesh>
    </group>
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

function ConeMesh({ position }: { position: [number, number, number] }) {
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
        <ConeMesh position={[0, 0.06, 0]} />
      )}
    </group>
  );
}

function CameraController({ view }: { view: string }) {
  const { camera } = useThree();
  useEffect(() => {
    if (view === 'top') {
      camera.position.set(0, 20, 0.1);
    } else if (view === 'player') {
      camera.position.set(0, 1.5, 8);
    } else {
      camera.position.set(15, 12, 15);
    }
    camera.lookAt(0, 0, 0);
  }, [view, camera]);
  return null;
}

const IconPlay = () => <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor"><polygon points="2,1 10,6 2,11"/></svg>;
const IconPause = () => <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor"><rect x="2.5" y="1.5" width="2.5" height="9" rx="0.5"/><rect x="7" y="1.5" width="2.5" height="9" rx="0.5"/></svg>;
const IconFullscreen = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
    <path d="M2 4.5V2h2.5M10 4.5V2H7.5M2 7.5V10h2.5M10 7.5V10H7.5"/>
  </svg>
);
const IconMinimize = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
    <path d="M4.5 2v2.5H2M7.5 2v2.5H10M4.5 10V7.5H2M7.5 10V7.5H10"/>
  </svg>
);
const IconCamera = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1.5" y="3" width="9" height="6.5" rx="1"/><circle cx="6" cy="6.5" r="2"/><path d="M8.5 3L9.5 1.5h-7L3.5 3"/>
  </svg>
);
const IconTopView = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
    <circle cx="6" cy="6" r="4.5"/><path d="M6 1.5v9M1.5 6h9"/>
  </svg>
);
const IconReset = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1.5 6.5a4.5 4.5 0 108-2.8"/><polyline points="4.5 2 9.5 2 9.5 3.7"/><path d="M9.5 2l-2.5 3"/>
  </svg>
);

export default function Viewer3D({ objects, sceneUrl }: { objects: AnimData[]; sceneUrl?: string }) {
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalFrames, setTotalFrames] = useState(1);
  const [cameraView, setCameraView] = useState('default');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const playingRef = useRef(true);
  const speedRef = useRef(1);
  const timeRef = useRef(0);
  const totalFramesRef = useRef(1);

  useEffect(() => { playingRef.current = playing; }, [playing]);
  useEffect(() => { speedRef.current = speed; }, [speed]);

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
  const progress = totalFrames > 0 ? (currentTime / totalFrames) * 100 : 0;

  return (
    <div ref={containerRef} className={`relative bg-gray-900 overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50' : 'w-full h-[65vh] rounded-xl'}`}>
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

      {/* Bottom bar */}
      <div className="absolute bottom-0 left-0 right-0 px-4 pb-3 pt-8 bg-gradient-to-t from-black/80 to-transparent">
        <div className="flex items-center gap-2.5">
          <button onClick={togglePlay}
            className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all active:scale-90 text-white"
          >
            {playing ? <IconPause /> : <IconPlay />}
          </button>

          <div className="flex gap-0.5">
            {[0.5, 1, 2].map(s => (
              <button key={s} onClick={() => setSpeed(s)}
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md transition-all ${
                  speed === s ? 'bg-white/20 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
              >{s}x</button>
            ))}
          </div>

          <div className="flex-1 relative h-4 cursor-pointer group py-1" onMouseDown={handleSeek}>
            <div className="h-0.5 bg-gray-700 rounded-full group-hover:h-1 transition-all duration-200 relative top-1/2 -translate-y-1/2">
              <div className="h-full bg-white rounded-full" style={{ width: `${progress}%` }} />
            </div>
            <div className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-white -ml-1.25 opacity-0 group-hover:opacity-100 transition-opacity duration-200 shadow-lg"
              style={{ left: `${progress}%` }}
            />
          </div>

          <span className="text-[10px] text-gray-500 tabular-nums font-medium">
            {String(currentSec).padStart(2, '0')}:{String(Math.floor((currentTime % 10) * 6)).padStart(2, '0')} / {String(durationSec).padStart(2, '0')}:00
          </span>
        </div>
      </div>

      {/* Right controls */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 flex flex-col gap-1.5">
        {[
          { label: 'Fullscreen', icon: isFullscreen ? <IconMinimize /> : <IconFullscreen />, onClick: toggleFullscreen, active: false },
          { label: 'Player view', icon: <IconCamera />, onClick: () => setCameraView(v => v === 'player' ? 'default' : 'player'), active: cameraView === 'player' },
          { label: 'Top view', icon: <IconTopView />, onClick: () => setCameraView(v => v === 'top' ? 'default' : 'top'), active: cameraView === 'top' },
          { label: 'Reset camera', icon: <IconReset />, onClick: () => setCameraView('default'), active: false },
        ].map((b, i) => (
          <button key={i} onClick={b.onClick} title={b.label}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 active:scale-90 ${
              b.active ? 'bg-white/20 text-white' : 'bg-black/40 text-gray-400 hover:bg-black/60 hover:text-white'
            }`}
          >
            {b.icon}
          </button>
        ))}
      </div>
    </div>
  );
}
