import { type NextRequest, NextResponse } from "next/server";
import { createSessionToken, COOKIE_NAME } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const { username, password } = await req.json();

  const validUser = process.env.ADMIN_USERNAME;
  const validPass = process.env.ADMIN_PASSWORD;

  if (!validUser || !validPass) {
    return NextResponse.json(
      { error: "Auth not configured (ADMIN_USERNAME/ADMIN_PASSWORD not set)" },
      { status: 500 }
    );
  }

  if (username !== validUser || password !== validPass) {
    // Constant-time delay to slow brute-force
    await new Promise((r) => setTimeout(r, 400));
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const token = await createSessionToken(username);
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 8 * 60 * 60, // 8 hours
    path: "/",
  });
  return res;
}
