import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { LAB_COOKIE, validLabSession } from "../../../lib/lab-auth";
export default async function LabLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  if (
    !validLabSession(
      (await cookies()).get(LAB_COOKIE)?.value,
      process.env.VISION_LAB_SECRET,
    )
  )
    redirect("/lab/login");
  return (
    <>
      <nav className="lab-nav" aria-label="Private Lab">
        {["replay", "metrics", "review", "live", "session", "diagnostics"].map(
          (p) => (
            <Link href={`/lab/${p}`} key={p}>
              {p}
            </Link>
          ),
        )}
      </nav>
      {children}
    </>
  );
}
