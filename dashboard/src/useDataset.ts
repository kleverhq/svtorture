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
        return (await response.json()) as Dataset;
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
