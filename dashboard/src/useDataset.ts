import { useEffect, useState } from "react";

import type { Dataset } from "./types";

interface DatasetState {
  dataset?: Dataset;
  error?: string;
}

export function useDataset(): DatasetState {
  const [state, setState] = useState<DatasetState>({});
  useEffect(() => {
    let active = true;
    fetch("./data/dataset.json", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`dataset request failed: ${response.status}`);
        const value: unknown = await response.json();
        if (
          typeof value !== "object" ||
          value === null ||
          !("schema_version" in value) ||
          value.schema_version !== 5
        ) {
          throw new Error("unsupported dataset schema");
        }
        return value as Dataset;
      })
      .then((dataset) => {
        if (active) setState({ dataset });
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            error: error instanceof Error ? error.message : "dataset request failed",
          });
        }
      });
    return () => {
      active = false;
    };
  }, []);
  return state;
}
