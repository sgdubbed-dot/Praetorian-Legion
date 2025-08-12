import React from "react";
import { api } from "../api";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, err: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, err: error };
  }

  async componentDidCatch(error, info) {
    try {
      await api.post("/events", {
        event_name: "fe_error",
        source: "frontend",
        payload: {
          page: this.props.page || "unknown",
          message: String(error?.message || error),
          stack: String(error?.stack || info?.componentStack || ""),
        },
      });
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("Failed to report FE error", e);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, err: null });
    if (this.props.onRetry) this.props.onRetry();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-white rounded shadow">
          <div className="text-red-700 font-semibold mb-2">Something went wrong</div>
          <div className="text-xs text-neutral-700 mb-3">{String(this.state.err?.message || this.state.err || "Unknown error")}</div>
          <button onClick={this.handleRetry} className="px-3 py-1 bg-neutral-800 text-white rounded">Retry</button>
        </div>
      );
    }
    return this.props.children;
  }
}