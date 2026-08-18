'use client';
import { useEffect, useRef } from 'react';

export default function HeroAnimation() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let particles: Particle[] = [];
    let connections: Connection[] = [];
    let time = 0;

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };

    class Particle {
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      color: string;
      alpha: number;
      targetX: number;
      targetY: number;

      constructor(x: number, y: number) {
        this.x = x;
        this.y = y;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.radius = Math.random() * 2 + 1;
        this.color = Math.random() > 0.5 ? '#4ade80' : '#22d3ee';
        this.alpha = Math.random() * 0.5 + 0.3;
        this.targetX = x;
        this.targetY = y;
      }

      update(w: number, h: number) {
        // Gentle floating motion
        this.x += this.vx + Math.sin(time * 0.01 + this.x * 0.01) * 0.2;
        this.y += this.vy + Math.cos(time * 0.01 + this.y * 0.01) * 0.2;

        // Soft boundary bounce
        if (this.x < 0 || this.x > w) this.vx *= -1;
        if (this.y < 0 || this.y > h) this.vy *= -1;

        // Pulsing alpha
        this.alpha = 0.3 + Math.sin(time * 0.02 + this.x) * 0.2;
      }

      draw(ctx: CanvasRenderingContext2D) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.globalAlpha = this.alpha;
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    }

    class Connection {
      p1: Particle;
      p2: Particle;
      distance: number;

      constructor(p1: Particle, p2: Particle) {
        this.p1 = p1;
        this.p2 = p2;
        this.distance = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      }

      update() {
        this.distance = Math.hypot(this.p2.x - this.p1.x, this.p2.y - this.p1.y);
      }

      draw(ctx: CanvasRenderingContext2D) {
        if (this.distance > 120) return;
        const alpha = (1 - this.distance / 120) * 0.15;
        ctx.beginPath();
        ctx.moveTo(this.p1.x, this.p1.y);
        ctx.lineTo(this.p2.x, this.p2.y);
        ctx.strokeStyle = '#4ade80';
        ctx.globalAlpha = alpha;
        ctx.lineWidth = 0.5;
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }

    const init = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      particles = [];
      connections = [];

      // Create particles
      const count = Math.min(40, Math.floor((w * h) / 15000));
      for (let i = 0; i < count; i++) {
        particles.push(new Particle(Math.random() * w, Math.random() * h));
      }

      // Create connections between nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          connections.push(new Connection(particles[i], particles[j]));
        }
      }
    };

    const animate = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      
      ctx.clearRect(0, 0, w, h);

      // Update and draw connections
      connections.forEach(conn => {
        conn.update();
        conn.draw(ctx);
      });

      // Update and draw particles
      particles.forEach(p => {
        p.update(w, h);
        p.draw(ctx);
      });

      time++;
      animationId = requestAnimationFrame(animate);
    };

    resize();
    init();
    animate();

    window.addEventListener('resize', () => {
      resize();
      init();
    });

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ opacity: 0.6 }}
      />
      
      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-b from-gray-950 via-transparent to-gray-950" />
      <div className="absolute inset-0 bg-gradient-to-r from-gray-950 via-transparent to-gray-950" />
      
      {/* Radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/5 rounded-full blur-[100px]" />
    </div>
  );
}
