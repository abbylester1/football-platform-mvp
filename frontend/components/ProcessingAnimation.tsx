'use client';

interface ProcessingAnimationProps {
  currentStep: number;
  steps: { label: string; icon: React.ReactNode }[];
  estimatedTime?: number;
  progressPercent?: number;
  progressLabel?: string;
  elapsedSeconds?: number;
}

export default function ProcessingAnimation({ currentStep, steps, estimatedTime = 180, progressPercent = 0, progressLabel = '', elapsedSeconds = 0 }: ProcessingAnimationProps) {
  const remaining = Math.max(0, Math.round(estimatedTime));
  // Use real progress from backend, fallback to step-based
  const progress = progressPercent > 0 ? progressPercent : Math.min(100, ((currentStep + 1) / steps.length) * 100);

  return (
    <div className="max-w-2xl mx-auto py-24 animate-fade-up">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        {/* Left: Steps */}
        <div>
          <div className="flex items-center gap-2 mb-8">
            <div className="relative">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            </div>
            <span className="text-xs text-gray-500 font-medium uppercase tracking-widest">
              Analyzing Your Drill
            </span>
          </div>

          <div className="space-y-4">
            {steps.map((step, i) => {
              const isComplete = i < currentStep;
              const isCurrent = i === currentStep;
              const isPending = i > currentStep;

              return (
                <div
                  key={i}
                  className={`
                    flex items-center gap-4 p-3 rounded-xl transition-all duration-500
                    ${isCurrent ? 'bg-white/[0.03] border border-white/[0.06]' : ''}
                    ${isComplete ? 'opacity-60' : ''}
                  `}
                >
                  {/* Step indicator */}
                  <div className="relative">
                    {isComplete ? (
                      <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-emerald-400">
                          <path d="M11.5 4L5.5 10L2.5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </div>
                    ) : isCurrent ? (
                      <div className="w-8 h-8 rounded-full border-2 border-white/20 flex items-center justify-center animate-step-glow">
                        <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-full border border-gray-800 flex items-center justify-center">
                        <span className="text-[10px] text-gray-600">{i + 1}</span>
                      </div>
                    )}
                  </div>

                  {/* Step content */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`w-4 h-4 ${isCurrent ? 'text-white' : isComplete ? 'text-emerald-400' : 'text-gray-600'}`}>
                        {step.icon}
                      </span>
                      <span className={`text-sm font-medium transition-colors duration-300 ${
                        isCurrent ? 'text-white' : isComplete ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        {step.label}
                      </span>
                    </div>
                    
                    {isCurrent && (
                      <div className="mt-2 h-1 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-1000"
                          style={{ width: `${((i + 1) / steps.length) * 100}%` }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Time estimate */}
          <div className="mt-6 space-y-2">
            <div className="flex items-center gap-3 text-xs text-gray-600">
              <div className="flex items-center gap-1.5">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.2">
                  <circle cx="6" cy="6" r="5"/>
                  <path d="M6 3v3l2 1"/>
                </svg>
                <span>Estimated remaining</span>
              </div>
              <span className="text-gray-400 font-medium">
                {Math.floor(remaining / 60)}m {remaining % 60}s
              </span>
            </div>
            {progressPercent > 0 && (
              <div className="flex items-center gap-3 text-xs">
                <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-1000"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-gray-500 font-mono tabular-nums">{progress}%</span>
              </div>
            )}
            {progressLabel && (
              <span className="text-[11px] text-gray-600">{progressLabel}</span>
            )}
          </div>
        </div>

        {/* Right: Visual */}
        <div className="hidden md:flex items-center justify-center">
          <div className="relative w-48 h-48">
            {/* Outer ring */}
            <div className="absolute inset-0 border border-gray-800/50 rounded-full" />
            <div
              className="absolute inset-0 border-2 border-transparent border-t-emerald-500/50 rounded-full animate-spin"
              style={{ animationDuration: '3s' }}
            />
            
            {/* Middle ring */}
            <div className="absolute inset-4 border border-gray-800/30 rounded-full" />
            <div
              className="absolute inset-4 border-2 border-transparent border-b-cyan-500/40 rounded-full animate-spin"
              style={{ animationDuration: '2s', animationDirection: 'reverse' }}
            />
            
            {/* Inner ring */}
            <div className="absolute inset-8 border border-gray-800/20 rounded-full" />
            
            {/* Center icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="relative">
                {/* Skeleton icon */}
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-emerald-400/70 animate-pulse">
                  <circle cx="16" cy="6" r="3"/>
                  <path d="M16 10v8"/>
                  <path d="M16 18l-4 8"/>
                  <path d="M16 18l4 8"/>
                  <path d="M10 14l-4 2"/>
                  <path d="M22 14l4 2"/>
                </svg>
                
                {/* Floating particles */}
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute w-1 h-1 rounded-full bg-emerald-400/50 animate-float"
                    style={{
                      left: `${50 + Math.cos(i * Math.PI / 3) * 100}%`,
                      top: `${50 + Math.sin(i * Math.PI / 3) * 100}%`,
                      animationDelay: `${i * 0.5}s`,
                      animationDuration: `${3 + i * 0.5}s`,
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Progress ring */}
            <svg className="absolute inset-0 w-full h-full -rotate-90">
              <circle
                cx="96"
                cy="96"
                r="90"
                fill="none"
                stroke="rgba(74, 222, 128, 0.2)"
                strokeWidth="2"
                strokeDasharray={`${(progress / 100) * 565} ${565 - (progress / 100) * 565}`}
                className="transition-all duration-1000"
              />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
