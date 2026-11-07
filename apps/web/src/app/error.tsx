"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="wide">
      <section className="panel" role="alert">
        <h1>This view could not be loaded.</h1>
        <p>
          The scene is unavailable. No safety or navigation conclusion can be
          drawn from this view.
        </p>
        <button onClick={reset}>Try again</button>
      </section>
    </main>
  );
}
