import Link from "next/link";
export default function Page() {
  return (
    <main className="product-page">
      <p className="eyebrow">VISION / limitations</p>
      <h1>Progress is not proof of safety.</h1>
      <p className="reading-copy">
        VISION is a supervised research prototype, not a navigation aid. Do not
        rely on it around traffic, stairs or other hazards. Silence is not an
        all-clear.
      </p>
      <p className="reading-copy">
        The frozen baseline was measured on one recording containing non-walking
        segments. Camera calibration, real walking direction, human usefulness
        and Bluetooth acoustic timing are not validated by replay tests.
      </p>
      <p className="reading-copy">
        Orientation correction is partial. Poor light, occlusion, network
        failure and stale evidence can make the system unavailable.
        Physical-phone qualification remains a separate gate.
      </p>
      <Link href="/demo">Explore a recorded decision →</Link>
    </main>
  );
}
