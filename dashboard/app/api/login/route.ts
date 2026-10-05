import { NextResponse, type NextRequest } from "next/server";
import { passwordMatches, SESSION_COOKIE } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const password = form.get("password");
  const candidate = typeof password === "string" ? password : undefined;

  if (!passwordMatches(candidate, process.env.DASHBOARD_PASSWORD)) {
    return NextResponse.redirect(new URL("/login?error=1", request.url), 303);
  }

  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set(SESSION_COOKIE, candidate!, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return response;
}
