import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useJsonData } from "./useJsonData";

describe("useJsonData hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns idle state when url is null", () => {
    const { result } = renderHook(() => useJsonData<{ test: string }>(null));

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("fetches and returns data successfully", async () => {
    const mockData = { gameId: "123", homeTeam: "DET" };
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockData),
        } as Response)
      )
    );

    const { result } = renderHook(() =>
      useJsonData<typeof mockData>("http://example.com/data.json")
    );

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://example.com/data.json",
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it("handles fetch errors gracefully", async () => {
    const errorMessage = "Network error";
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error(errorMessage))));

    const { result } = renderHook(() =>
      useJsonData<{ test: string }>("http://example.com/data.json")
    );

    // Initially loading
    expect(result.current.loading).toBe(true);

    // Wait for error
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toBe(errorMessage);
  });

  it("handles HTTP error responses gracefully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
        } as Response)
      )
    );

    const { result } = renderHook(() =>
      useJsonData<{ test: string }>("http://example.com/missing.json")
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toContain("HTTP 404");
  });

  it("re-fetches when URL changes", async () => {
    const data1 = { gameId: "1" };
    const data2 = { gameId: "2" };

    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("1.json")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(data1),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(data2),
        } as Response);
      })
    );

    const { result, rerender } = renderHook(
      ({ url }) => useJsonData<typeof data1>(url),
      { initialProps: { url: "http://example.com/1.json" } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(data1);

    // Change URL
    rerender({ url: "http://example.com/2.json" });

    await waitFor(() => {
      expect(result.current.data).toEqual(data2);
    });

    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });

  it("handles non-Error objects thrown during fetch", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject("string error")));

    const { result } = renderHook(() =>
      useJsonData<{ test: string }>("http://example.com/data.json")
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toBe("string error");
  });

  it("clears error when URL changes from error state to valid URL", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("error")) {
          return Promise.reject(new Error("Bad URL"));
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ gameId: "123" }),
        } as Response);
      })
    );

    const { result, rerender } = renderHook(
      ({ url }) => useJsonData<{ gameId: string }>(url),
      { initialProps: { url: "http://example.com/error.json" } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).not.toBeNull();

    // Change to valid URL
    rerender({ url: "http://example.com/valid.json" });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data?.gameId).toBe("123");
  });
});
