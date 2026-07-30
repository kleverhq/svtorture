import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDataset } from "./useDataset";

describe("useDataset", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects datasets from another schema version", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ schema_version: 4 }),
      }),
    );

    const { result } = renderHook(() => useDataset());
    await waitFor(() => expect(result.current.error).toBe("unsupported dataset schema"));
    expect(result.current.dataset).toBeUndefined();
  });
});
