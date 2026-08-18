'use client';

interface WaveLoaderProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'white' | 'emerald' | 'cyan';
  className?: string;
}

export default function WaveLoader({ size = 'md', color = 'white', className = '' }: WaveLoaderProps) {
  const sizeMap = {
    sm: { bar: 'w-0.5 h-3', gap: 'gap-0.5' },
    md: { bar: 'w-1 h-4', gap: 'gap-1' },
    lg: { bar: 'w-1.5 h-6', gap: 'gap-1.5' },
  };

  const colorMap = {
    white: 'bg-white',
    emerald: 'bg-emerald-500',
    cyan: 'bg-cyan-500',
  };

  const { bar, gap } = sizeMap[size];

  return (
    <div className={`flex items-center justify-center ${gap} ${className}`}>
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`${bar} ${colorMap[color]} rounded-full animate-wave`}
          style={{
            animationDelay: `${i * 0.1}s`,
            animationDuration: '0.8s',
          }}
        />
      ))}
    </div>
  );
}
