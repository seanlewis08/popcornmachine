import { useState, useEffect } from "react";

/**
 * Generic hook for fetching JSON data from a URL
 * Handles loading states, errors, and null URLs gracefully
 *
 * @param url - The URL to fetch from, or null to skip fetching
 * @returns Object with data (or null), loading state, and error (or null)
 */
export function useJsonData<T>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // If no URL, return idle state
    if (!url) {
      return;
    }

    const abortController = new AbortController();

    // Start loading
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);

    fetch(url, { signal: abortController.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: Failed to fetch ${url}`);
        }
        return response.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setError(err instanceof Error ? err : new Error(String(err)));
        setLoading(false);
        setData(null);
      });

    return () => {
      abortController.abort();
    };
  }, [url]);

  return { data, loading, error };
}
