import { NextResponse } from "next/server";

function unauthorized() {
  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="eScape mobile preview", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

export function proxy(request) {
  const username = process.env.APP_BASIC_AUTH_USERNAME;
  const password = process.env.APP_BASIC_AUTH_PASSWORD;

  // Authentication is opt-in so ordinary local development remains simple.
  if (!username || !password) return NextResponse.next();

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ")) return unauthorized();

  let credentials;
  try {
    credentials = atob(authorization.slice(6));
  } catch {
    return unauthorized();
  }

  if (credentials !== `${username}:${password}`) return unauthorized();

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
