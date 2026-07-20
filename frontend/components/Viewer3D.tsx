'use client';
import { useRef, useEffect, useState, useCallback } from 'react';
import React from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';
import * as THREE from 'three';

function Field() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
      <planeGeometry args={[30, 20]} />
      <meshStandardMaterial color="#2d5a3f" />
    </mesh>
  );
}

interface AvatarProps {
  position: [number, number, number];
  color: string;
  label: string;
}

const Avatar = React.forwardRef<THREE.Group, AvatarProps>(({ position, color, label }, ref) => {
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
      <Text position={[0, 1.5, 0]} fontSize={0.15} color="white" anchorX="center" anchorY="middle">
        {label}
      </Text>
    </group>
  );
});

function Ball({ position }: { position: [number, number, number] }) {
  return (
    <mesh position={position} castShadow>
      <sphereGeometry args={[0.1, 8, 8]} />
      <meshStandardMaterial color="white" />
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

interface AnimData {
  type: string;
  id: string;
  label: string;
  frames: { frame: number; x: number; y: number; z: number }[];
}

function AnimatedObject({ data, color }: { data: AnimData; color: string }) {
  const groupRef = useRef<THREE.Group>(null);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const frameRef = useRef(0);
  const clockRef = useRef(0);

  useEffect(() => {
    const handler = (e: CustomEvent) => {
      if (e.detail.type === 'play') setPlaying(true);
      else if (e.detail.type === 'pause') setPlaying(false);
      else if (e.detail.type === 'setTime') frameRef.current = Math.round(e.detail.time);
      else if (e.detail.type === 'setSpeed') setSpeed(e.detail.speed);
    };
    window.addEventListener('drill-control' as any, handler);
    return () => window.removeEventListener('drill-control' as any, handler);
  }, []);

  useFrame((_, delta) => {
    if (!playing || data.frames.length < 2) return;
    clockRef.current += delta * speed;

    const fps = 10;
    const frameDuration = 1 / fps;
    if (clockRef.current < frameDuration) return;
    clockRef.current = 0;

    frameRef.current = (frameRef.current + 1) % data.frames.length;
    const f = data.frames[frameRef.current];
    if (groupRef.current) {
      groupRef.current.position.set(f.x, 0, f.z);
    }
  });

  if (data.frames.length === 0) return null;

  const baseColor = data.type === 'player' ? color : data.type === 'ball' ? '#ffffff' : '#f39c12';

  if (data.type === 'player') {
    return (
      <group ref={groupRef}>
        <Avatar position={[0, 0, 0]} color={baseColor} label={data.label} />
      </group>
    );
  }

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {data.type === 'ball' ? <Ball position={[0, 0.1, 0]} /> : <Cone position={[0, 0.06, 0]} />}
    </group>
  );
}

const TYPE_COLORS: Record<string, string> = {
  player: '#e74c3c', ball: '#f1c40f', cone: '#e67e22',
};

export default function Viewer3D({ objects, sceneUrl }: { objects: AnimData[]; sceneUrl?: string }) {
  return (
    <div className="w-full h-[600px] rounded-lg overflow-hidden bg-gray-900">
      <Canvas camera={{ position: [15, 12, 15], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 15, 10]} intensity={0.8} castShadow />
        <Field />
        {objects.map(obj => (
          <AnimatedObject key={obj.id} data={obj} color={TYPE_COLORS[obj.type] || '#888'} />
        ))}
        <OrbitControls />
      </Canvas>
    </div>
  );
}
