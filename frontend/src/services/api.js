const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function planRoute(payload) {
  const response = await fetch(`${API_BASE_URL}/api/routes/plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || "Route planning failed. Please try again.";
    throw new Error(typeof message === "string" ? message : "Route planning failed. Please check your journey details.");
  }

  return data;
}
