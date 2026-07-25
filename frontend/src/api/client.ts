import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
    "x-api-key": import.meta.env.VITE_API_KEY || "",
  },
  timeout: 300_000, // local CPU LLM inference across several sequential agent calls can take minutes
});

export interface ApiErrorShape {
  detail?: string | { msg: string }[];
}

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiErrorShape | undefined;
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      return data.detail.map((d) => d.msg).join(", ");
    }
    if (error.code === "ECONNABORTED") return "The request timed out. Please try again.";
    if (!error.response) return "Unable to reach the server. Check your connection and try again.";
    return `Request failed (${error.response.status}).`;
  }
  return "Something went wrong. Please try again.";
}
