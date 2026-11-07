import Link from "next/link";
export default function Page() {
  return (
    <main className="product-page">
      <p className="eyebrow">VISION / research</p>
      <h1>Evidence with its scope intact.</h1>
      <p className="reading-copy">
        The frozen Alpha recording produced 18,541 updates at 12.368 updates per
        source second, with publication-age P95 241.947 ms. These are
        recorded-source software measurements, not physical camera-to-ear
        latency.
      </p>
      <p className="reading-copy">
        Private source footage and annotations stay in the authenticated local
        Lab. No raw research recording is bundled in the public build.
      </p>
      <p className="reading-copy">
        Independent people, scenarios and review are needed before usefulness or
        generalization claims. Model proposals are not human truth.
      </p>
      <Link href="/demo">Explore a recorded decision →</Link>
    </main>
  );
}
