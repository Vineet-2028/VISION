import Link from "next/link";
export default function Page() {
  return (
    <main className="product-page">
      <p className="eyebrow">VISION / get vision</p>
      <h1>Start with a supervised test.</h1>
      <p className="reading-copy">
        You need an Android phone, a supported Windows GPU PC and a trusted
        local network. The PC must remain on. A public website cannot run the
        Guardian GPU engine for you.
      </p>
      <p className="reading-copy">
        Install the developer APK from your own build, pair with the local
        operator, test the camera and audio, then start a short stationary
        supervised session. See
        docs/releases/VISION_WIRELESS_ALPHA_FIELD_GUIDE.md in the repository.
      </p>
      <p className="reading-copy">
        No public app-store release, hosted inference service or standalone
        on-device engine is claimed. Do not enter pairing secrets into this
        public site.
      </p>
      <Link href="/demo">Explore a recorded decision →</Link>
    </main>
  );
}
