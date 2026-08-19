'use client';
import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';
import * as THREE from 'three';

interface Keypoint {
  x: number;
  y: number;
  z: number;
  visibility: number;
}

interface AnimData {
  type: string; id: string; label: string;
  frames: { frame: number; x: number; y: number; z: number; keypoints?: Keypoint[] }[];
}

function Field() {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[30, 20]} />
        <meshStandardMaterial color="#2d5a3f" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <planeGeometry args={[28, 18]} />
        <meshBasicMaterial color="#3a7a4f" wireframe />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <planeGeometry args={[0.04, 18]} />
        <meshBasicMaterial color="white" opacity={0.3} transparent />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <ringGeometry args={[4.5, 4.54, 32]} />
        <meshBasicMaterial color="white" opacity={0.3} transparent side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <circleGeometry args={[0.2, 16]} />
        <meshBasicMaterial color="white" opacity={0.3} transparent />
      </mesh>
    </group>
  );
}

/* ─── Team color palettes ─── */
const TEAM_COLORS = {
  red:    { jersey: '#cc2233', shorts: '#ffffff', socks: '#cc2233', skin: '#f5d0a9' },
  blue:   { jersey: '#2244aa', shorts: '#ffffff', socks: '#2244aa', skin: '#f5d0a9' },
  yellow: { jersey: '#ddaa00', shorts: '#222222', socks: '#ddaa00', skin: '#f5d0a9' },
  green:  { jersey: '#228833', shorts: '#ffffff', socks: '#228833', skin: '#f5d0a9' },
  white:  { jersey: '#f0f0f0', shorts: '#222222', socks: '#f0f0f0', skin: '#f5d0a9' },
  black:  { jersey: '#222222', shorts: '#ffffff', socks: '#222222', skin: '#f5d0a9' },
};

const TEAM_NAMES = Object.keys(TEAM_COLORS);

function assignTeam(id: string, label: string): typeof TEAM_COLORS.red {
  // Assign team based on ID hash — consistent across renders
  let hash = 0;
  const str = id + label;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(hash) % TEAM_NAMES.length;
  return TEAM_COLORS[TEAM_NAMES[idx] as keyof typeof TEAM_COLORS];
}

/* ─── Realistic Football Player ─── */
function FootballPlayer({ color, label, walkPhase }: {
  color: typeof TEAM_COLORS.red;
  label: string;
  walkPhase: number;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const leftArmRef = useRef<THREE.Group>(null);
  const rightArmRef = useRef<THREE.Group>(null);
  const leftLegRef = useRef<THREE.Group>(null);
  const rightLegRef = useRef<THREE.Group>(null);

  useFrame(() => {
    const swing = Math.sin(walkPhase) * 0.4;
    if (leftArmRef.current) leftArmRef.current.rotation.x = swing;
    if (rightArmRef.current) rightArmRef.current.rotation.x = -swing;
    if (leftLegRef.current) leftLegRef.current.rotation.x = -swing * 0.7;
    if (rightLegRef.current) rightLegRef.current.rotation.x = swing * 0.7;
  });

  return (
    <group ref={groupRef}>
      {/* ── Torso (jersey) ── */}
      <mesh position={[0, 0.85, 0]} castShadow>
        <boxGeometry args={[0.32, 0.4, 0.2]} />
        <meshStandardMaterial color={color.jersey} />
      </mesh>

      {/* ── Jersey number ── */}
      {label && (
        <Text
          position={[0, 0.85, 0.11]}
          fontSize={0.1}
          color="white"
          anchorX="center"
          anchorY="middle"
          fontWeight="bold"
        >
          {label}
        </Text>
      )}

      {/* ── Shorts ── */}
      <mesh position={[0, 0.58, 0]} castShadow>
        <boxGeometry args={[0.34, 0.16, 0.22]} />
        <meshStandardMaterial color={color.shorts} />
      </mesh>

      {/* ── Head ── */}
      <mesh position={[0, 1.18, 0]} castShadow>
        <sphereGeometry args={[0.1, 12, 12]} />
        <meshStandardMaterial color={color.skin} />
      </mesh>

      {/* ── Hair ── */}
      <mesh position={[0, 1.23, -0.02]} castShadow>
        <sphereGeometry args={[0.1, 12, 12, 0, Math.PI * 2, 0, Math.PI * 0.55]} />
        <meshStandardMaterial color="#3a2a1a" />
      </mesh>

      {/* ── Left Arm ── */}
      <group ref={leftArmRef} position={[-0.22, 0.95, 0]}>
        {/* Upper arm (jersey) */}
        <mesh position={[0, -0.08, 0]} castShadow>
          <boxGeometry args={[0.08, 0.16, 0.08]} />
          <meshStandardMaterial color={color.jersey} />
        </mesh>
        {/* Lower arm (skin) */}
        <mesh position={[0, -0.22, 0]} castShadow>
          <boxGeometry args={[0.06, 0.12, 0.06]} />
          <meshStandardMaterial color={color.skin} />
        </mesh>
      </group>

      {/* ── Right Arm ── */}
      <group ref={rightArmRef} position={[0.22, 0.95, 0]}>
        <mesh position={[0, -0.08, 0]} castShadow>
          <boxGeometry args={[0.08, 0.16, 0.08]} />
          <meshStandardMaterial color={color.jersey} />
        </mesh>
        <mesh position={[0, -0.22, 0]} castShadow>
          <boxGeometry args={[0.06, 0.12, 0.06]} />
          <meshStandardMaterial color={color.skin} />
        </mesh>
      </group>

      {/* ── Left Leg ── */}
      <group ref={leftLegRef} position={[-0.1, 0.48, 0]}>
        {/* Thigh (skin) */}
        <mesh position={[0, -0.1, 0]} castShadow>
          <boxGeometry args={[0.1, 0.2, 0.1]} />
          <meshStandardMaterial color={color.skin} />
        </mesh>
        {/* Shin (sock) */}
        <mesh position={[0, -0.28, 0]} castShadow>
          <boxGeometry args={[0.08, 0.16, 0.08]} />
          <meshStandardMaterial color={color.socks} />
        </mesh>
        {/* Boot (cleat) */}
        <mesh position={[0, -0.38, 0.02]} castShadow>
          <boxGeometry args={[0.09, 0.06, 0.14]} />
          <meshStandardMaterial color="#111111" />
        </mesh>
      </group>

      {/* ── Right Leg ── */}
      <group ref={rightLegRef} position={[0.1, 0.48, 0]}>
        <mesh position={[0, -0.1, 0]} castShadow>
          <boxGeometry args={[0.1, 0.2, 0.1]} />
          <meshStandardMaterial color={color.skin} />
        </mesh>
        <mesh position={[0, -0.28, 0]} castShadow>
          <boxGeometry args={[0.08, 0.16, 0.08]} />
          <meshStandardMaterial color={color.socks} />
        </mesh>
        <mesh position={[0, -0.38, 0.02]} castShadow>
          <boxGeometry args={[0.09, 0.06, 0.14]} />
          <meshStandardMaterial color="#111111" />
        </mesh>
      </group>
    </group>
  );
}

/* ─── Skeleton (when keypoints available) ─── */
const SKELETON_CONNECTIONS: [number, number][] = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [24, 26], [26, 28],
];
const JOINT_INDICES = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];

function Skeleton({ keypoints, color }: { keypoints: Keypoint[]; color: string }) {
  const boneGeometry = useMemo(() => new THREE.CylinderGeometry(0.015, 0.015, 1, 6), []);
  const bones = SKELETON_CONNECTIONS
    .filter(([a, b]) => keypoints[a]?.visibility > 0.5 && keypoints[b]?.visibility > 0.5)
    .map(([a, b]) => {
      const start = new THREE.Vector3(keypoints[a].x, keypoints[a].y, keypoints[a].z);
      const end = new THREE.Vector3(keypoints[b].x, keypoints[b].y, keypoints[b].z);
      const midpoint = start.clone().add(end).multiplyScalar(0.5);
      const length = start.distanceTo(end);
      const direction = end.clone().sub(start).normalize();
      const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
      return { midpoint, length, quaternion, key: `${a}-${b}` };
    });

  return (
    <group>
      {JOINT_INDICES.map((idx, i) => {
        const kp = keypoints[idx];
        if (!kp || kp.visibility <= 0.5) return null;
        return (
          <mesh key={`joint-${i}`} position={[kp.x, kp.y, kp.z]}>
            <sphereGeometry args={[0.03, 8, 8]} />
            <meshStandardMaterial color={color} />
          </mesh>
        );
      })}
      {bones.map((bone) => (
        <mesh key={bone.key} position={[bone.midpoint.x, bone.midpoint.y, bone.midpoint.z]}
              quaternion={bone.quaternion} geometry={boneGeometry} scale={[1, bone.length, 1]}>
          <meshStandardMaterial color={color} />
        </mesh>
      ))}
      {keypoints[0]?.visibility > 0.5 && (
        <mesh position={[keypoints[0].x, keypoints[0].y + 0.05, keypoints[0].z]}>
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshStandardMaterial color="#f5d0b0" />
        </mesh>
      )}
    </group>
  );
}

function Ball({ position }: { position: [number, number, number] }) {
  return (
    <mesh position={position} castShadow>
      <sphereGeometry args={[0.1, 16, 16]} />
      <meshStandardMaterial color="#ffffff" roughness={0.3} metalness={0.1} />
    </mesh>
  );
}

function ConeMesh({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh castShadow>
        <coneGeometry args={[0.04, 0.15, 8]} />
        <meshStandardMaterial color="#ff8c00" />
      </mesh>
      <mesh position={[0, -0.075, 0]}>
        <cylinderGeometry args={[0.06, 0.06, 0.02, 8]} />
        <meshStandardMaterial color="#ff6600" />
      </mesh>
    </group>
  );
}

/* ─── Animated Object ─── */
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
  const currentFrameRef = useRef<number>(0);
  const walkPhaseRef = useRef(0);

  // Assign consistent team colors
  const teamColor = useMemo(() => assignTeam(data.id, data.label), [data.id, data.label]);

  useFrame((_, delta) => {
    if (data.frames.length < 2) return;
    totalFramesRef.current = data.frames.length;
    if (!playingRef.current) return;

    clockRef.current += delta * speedRef.current;
    const fps = 10;
    if (clockRef.current < 1 / fps) return;
    clockRef.current = 0;

    const prevFrame = currentFrameRef.current;
    timeRef.current = (timeRef.current + 1) % data.frames.length;
    currentFrameRef.current = Math.floor(timeRef.current);
    const f = data.frames[currentFrameRef.current];

    if (groupRef.current && f) {
      groupRef.current.position.set(f.x, 0, f.z);

      // Calculate walk phase from movement
      if (prevFrame !== currentFrameRef.current) {
        const prevF = data.frames[prevFrame] || f;
        const dx = f.x - prevF.x;
        const dz = f.z - prevF.z;
        const speed = Math.sqrt(dx * dx + dz * dz);
        walkPhaseRef.current += speed * 8;

        // Rotate player to face movement direction
        if (speed > 0.01) {
          groupRef.current.rotation.y = Math.atan2(dx, dz);
        }
      }
    }
  });

  if (data.frames.length === 0) return null;

  const baseColor = data.type === 'ball' ? '#ffffff' : data.type === 'cone' ? '#ff8c00' : color;
  const currentFrameIdx = Math.floor(timeRef.current);
  const currentFrame = data.frames[currentFrameIdx] || data.frames[0];
  const hasKeypoints = currentFrame?.keypoints && currentFrame.keypoints.length > 0;

  return (
    <group ref={groupRef}>
      {data.type === 'player' ? (
        hasKeypoints ? (
          <group>
            <Skeleton keypoints={currentFrame.keypoints!} color={baseColor} />
            <Text position={[0, 1.3, 0]} fontSize={0.15} color="white" anchorX="center" anchorY="middle">
              {data.label}
            </Text>
          </group>
        ) : (
          <FootballPlayer
            color={teamColor}
            label={data.label || ''}
            walkPhase={walkPhaseRef.current}
          />
        )
      ) : data.type === 'ball' ? (
        <Ball position={[0, 0.11, 0]} />
      ) : (
        <ConeMesh position={[0, 0.075, 0]} />
      )}
    </group>
  );
}

/* ─── Camera ─── */
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

/* ─── Icons ─── */
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

/* ─── Main Viewer ─── */
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
      <Canvas camera={{ position: [15, 12, 15], fov: 50 }} shadows>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 15, 10]} intensity={0.8} castShadow />
        <hemisphereLight args={['#87ceeb', '#2d5a3f', 0.3]} />
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
              style={{ left: `${progress}%` }} />
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

      {/* Team legend */}
      <div className="absolute left-3 top-3 flex flex-col gap-1">
        {objects.filter(o => o.type === 'player').slice(0, 2).map((p, i) => {
          const t = assignTeam(p.id, p.label);
          return (
            <div key={i} className="flex items-center gap-1.5 bg-black/40 rounded px-2 py-0.5">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ background: t.jersey }} />
              <span className="text-[10px] text-gray-300">{p.label || `Player ${i + 1}`}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const TYPE_COLORS: Record<string, string> = {
  player: '#4FC3F7', ball: '#ffffff', cone: '#ff8c00',
};
