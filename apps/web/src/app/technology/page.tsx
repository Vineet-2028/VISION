import Link from "next/link";
export default function Page() {
  return (
    <main className="product-page">
      <p className="eyebrow">VISION / technology</p>
      <h1>One engine. Three clear boundaries.</h1>
      <p className="reading-copy">
        Runtime: Python perception and scheduling plus Guardian mathematical and
        decision components. Product: Android capture/audio/history and the
        public website. Research: consented offline review and evaluation.
      </p>
      <p className="reading-copy">
        The frozen measured profile uses PicoDet-S FP32 CUDA, LK optical flow
        and PIDNet-S CUDA. Optional semantic enrichment and metric depth are
        disabled. No new model is being trained in this product pass.
      </p>
      <p className="reading-copy">
        On-device inference is a separate future milestone. Website deployment
        does not supply cloud GPUs, replace the Windows runtime or complete
        Task019.
      </p>
      <Link href="/demo">Explore a recorded decision →</Link>
    </main>
  );
}
