import Link from "next/link";
export default function Home() {
  return (
    <main className="product-home">
      <section className="product-hero">
        <div>
          <p className="eyebrow">VISION / Assistive scene understanding</p>
          <h1>
            More context.
            <br />
            <em>Less noise.</em>
          </h1>
          <p className="hero-copy">
            A research prototype exploring when a changing scene deserves your
            attention. Built to keep uncertainty visible—and your camera data
            local.
          </p>
          <div className="product-actions">
            <Link className="button-link" href="/demo">
              Explore a decision <span aria-hidden="true">↗</span>
            </Link>
            <Link href="/how-it-works">How Guardian works →</Link>
          </div>
          <p className="microcopy">
            Supervised local Alpha · Requires a Windows inference PC
          </p>
        </div>
        <div
          className="scene-study"
          role="img"
          aria-label="Illustration of scene observations feeding a decision. Not a live camera or measured detection."
        >
          <span className="scene-caption">A scene is more than a label.</span>
          <svg viewBox="0 0 480 340" aria-hidden="true">
            <path
              d="M0 285 L215 145 L480 260 M0 338 L215 175 L480 320"
              fill="none"
              stroke="currentColor"
              opacity=".2"
            />
            <path
              d="M155 320 L227 180 L255 180 L335 320"
              fill="#b8d8ce"
              opacity=".45"
            />
            <rect
              x="102"
              y="117"
              width="62"
              height="122"
              rx="30"
              fill="#415e57"
            />
            <circle cx="133" cy="89" r="22" fill="#415e57" />
            <rect
              x="304"
              y="166"
              width="90"
              height="72"
              rx="6"
              fill="#c7a874"
            />
            <path
              d="M90 71v-16h20 M160 55h20v16 M90 242v16h20 M160 258h20v-16"
              stroke="#254f42"
              strokeWidth="3"
              fill="none"
            />
            <path
              d="M278 210l-32 0m0 0 10-8m-10 8 10 8"
              stroke="#254f42"
              strokeWidth="2"
            />
          </svg>
          <div className="scene-note">
            <span className="status-dot" />
            Observe. Track. Consider. Then speak.
          </div>
          <small>Concept illustration · no footage or live inference</small>
        </div>
      </section>
      <section className="editorial-section">
        <p className="eyebrow">Who we are building for</p>
        <div className="editorial-split">
          <h2>
            Support awareness.
            <br />
            Respect attention.
          </h2>
          <div>
            <p>
              VISION explores assistive context for people who may benefit from
              spoken scene information, including people with visual
              impairments.
            </p>
            <p>
              It is not a replacement for a cane, guide dog, trained support or
              your own judgment. We are still evaluating whether its
              interruptions are useful.
            </p>
          </div>
        </div>
      </section>
      <section className="reasoning-band">
        <p className="eyebrow">The Guardian approach</p>
        <h2>
          Not everything seen
          <br />
          needs to be said.
        </h2>
        <ol className="reasoning-steps">
          {[
            ["01", "Observe", "Find regions and retain unknown objects."],
            [
              "02",
              "Track",
              "Follow changes across frames; separate camera motion from evidence about objects.",
            ],
            [
              "03",
              "Consider",
              "Use geometry, freshness and uncertainty to decide whether to interrupt.",
            ],
            [
              "04",
              "Present",
              "Speak a short authorized message—or remain silent without implying safety.",
            ],
          ].map(([n, t, d]) => (
            <li key={n}>
              <span>{n}</span>
              <h3>{t}</h3>
              <p>{d}</p>
            </li>
          ))}
        </ol>
        <Link href="/technology">Explore the architecture →</Link>
      </section>
      <section className="editorial-section editorial-split">
        <div>
          <p className="eyebrow">Private by default</p>
          <h2>
            Your view is not
            <br />
            our data collection.
          </h2>
        </div>
        <div>
          <p>
            The local field connection processes camera frames in bounded
            memory. Continuous camera recording and training contribution are
            not enabled by default.
          </p>
          <Link href="/privacy">Read the data boundaries →</Link>
        </div>
      </section>
      <section className="honest-note">
        <p className="eyebrow">Where we are today</p>
        <h2>
          A working prototype.
          <br />
          An open evaluation.
        </h2>
        <p>
          Recorded software tests show progress. Real-phone audio, independent
          human usefulness and physical safety are separate gates. We do not
          call this safe for unsupervised use.
        </p>
        <div className="product-actions">
          <Link className="button-link" href="/get-vision">
            Plan a supervised test
          </Link>
          <Link href="/limitations">Read the limitations</Link>
        </div>
      </section>
    </main>
  );
}
