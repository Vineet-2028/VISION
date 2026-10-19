import Link from "next/link";

export default function Home() {
  return (
    <main>
      <h1>Sentinel</h1>
      <p>Guardian Disabled</p>
      <Link href="/health">View system health</Link>
    </main>
  );
}
