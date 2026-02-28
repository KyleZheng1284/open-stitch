export default function VideoPlayer({ src }: { src: string }) {
  return (
    <div className="bg-neutral-900 rounded-2xl overflow-hidden">
      <video src={src} controls className="w-full max-h-[70vh]" />
    </div>
  );
}
