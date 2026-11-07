import Link from "next/link";
export default function Lab() {
  return (
    <main>
      <p className="eyebrow">Authorized research only</p>
      <h1>Evidence, kept separate.</h1>
      <p>
        Private playback and review use the frozen local recording. It includes
        non-walking footage and does not establish physical safety. Do not
        publish or redistribute it without appropriate rights.
      </p>
      <Link className="button-link" href="/lab/replay">
        Open private replay
      </Link>
    </main>
  );
}
