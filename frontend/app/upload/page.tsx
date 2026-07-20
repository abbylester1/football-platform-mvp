'use client';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';

export default function UploadPage() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setUploading(true);
    const form = new FormData(formRef.current!);

    const res = await fetch('/api/upload', { method: 'POST', body: form });
    if (!res.ok) { alert('Upload failed'); setUploading(false); return; }
    const drill = await res.json();
    router.push(`/drill/${drill.id}`);
  }

  return (
    <main className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Upload New Drill</h1>
      <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">Video (MP4/MOV, max 2GB)</label>
          <input type="file" name="file" accept=".mp4,.mov" required className="w-full bg-gray-800 rounded p-2" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-1">Drill Name</label>
            <input type="text" name="name" required className="w-full bg-gray-800 rounded p-2" />
          </div>
          <div>
            <label className="block text-sm mb-1">Category</label>
            <select name="category" className="w-full bg-gray-800 rounded p-2">
              <option value="">Select...</option>
              <option value="passing">Passing</option>
              <option value="movement">Movement</option>
              <option value="possession">Possession</option>
              <option value="shooting">Shooting</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Age Group</label>
            <select name="age_group" className="w-full bg-gray-800 rounded p-2">
              <option value="">Select...</option>
              <option value="U10">U10</option>
              <option value="U12">U12</option>
              <option value="U14">U14</option>
              <option value="adult">Adult</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Difficulty</label>
            <select name="difficulty" className="w-full bg-gray-800 rounded p-2">
              <option value="">Select...</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm mb-1">Description (optional)</label>
          <textarea name="description" className="w-full bg-gray-800 rounded p-2" rows={3} />
        </div>
        <button type="submit" disabled={uploading} className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg disabled:opacity-50">
          {uploading ? 'Uploading...' : 'Upload & Process'}
        </button>
      </form>
    </main>
  );
}
