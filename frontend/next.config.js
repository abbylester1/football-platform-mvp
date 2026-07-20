/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const base = (process.env.NEXT_PUBLIC_RENDER_URL || 'https://football-platform-mvp.onrender.com').replace(/[\s\r\n]+$/, '');
    if (!base.startsWith('http://') && !base.startsWith('https://') && !base.startsWith('/')) {
      return [];
    }
    return [
      {
        source: '/api/:path*',
        destination: `${base}/api/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
