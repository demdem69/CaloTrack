function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

export const API_BASE_URL = normalizeBaseUrl(
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000",
);

