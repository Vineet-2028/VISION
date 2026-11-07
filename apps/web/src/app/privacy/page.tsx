import Link from "next/link";
export default function Page() {
  return (
    <main className="product-page">
      <p className="eyebrow">VISION / privacy</p>
      <h1>Your camera. Clear boundaries.</h1>
      <p className="reading-copy">
        Continuous camera frames are processed in bounded memory, not recorded
        by default. Diagnostic exports contain structured metadata and exclude
        raw images/audio.
      </p>
      <p className="reading-copy">
        Important-event history is a separate local product feature. User
        feedback is not automatically a training label. Any contribution to
        model improvement requires separate, informed opt-in.
      </p>
      <p className="reading-copy">
        No cloud upload or history sync is enabled by this website. Downloaded
        exports are copies you control; deleting app history cannot erase files
        you have exported.
      </p>
      <Link href="/demo">Explore a recorded decision →</Link>
    </main>
  );
}
