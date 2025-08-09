import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
if (!BACKEND_URL) {
  // Do not hardcode; just warn in console to set .env
  // eslint-disable-next-line no-console
  console.warn("REACT_APP_BACKEND_URL is not set. Frontend API calls will fail.");
}

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: { "Content-Type": "application/json" },
});

export const phoenixTime = (ts) => {
  if (!ts) return "-";
  try {
    const d = new Date(ts);
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Phoenix",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(d);
  } catch (e) {
    return ts;
  }
};