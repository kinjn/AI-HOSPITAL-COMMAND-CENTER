import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
    // App-level key required by every existing endpoint (api/deps.py::verify_api_key).
    // There is no per-patient auth header — access to a single encounter is
    // granted purely by knowing its tracking ID (sent in the URL path), per
    // the security model in BACKEND_REQUIREMENTS.md.
    "x-api-key": import.meta.env.VITE_API_KEY || "",
  },
  timeout: 300_000, // sequential agent calls (triage -> routing -> summary -> billing -> follow-up) can take minutes
});

export interface ApiErrorShape {
  detail?: string | { msg: string }[];
}

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiErrorShape | undefined;
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      return data.detail.map((d) => d.msg.replace(/^Value error,\s*/, "")).join(", ");
    }
    if (error.code === "ECONNABORTED") return "That took too long to respond. Please try again.";
    if (!error.response) return "Can't reach the server right now. Check your connection and try again.";
    if (error.response.status === 404) return "We couldn't find a consultation with that Tracking ID.";
    if (error.response.status === 403) return "That Tracking ID doesn't grant access to this resource.";
    return `Something went wrong (${error.response.status}). Please try again.`;
  }
  return "Something went wrong. Please try again.";
}
