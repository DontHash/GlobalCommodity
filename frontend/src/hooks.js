import { useEffect, useRef, useState } from "react";
import { api } from "./api";

export function useApi(path, filters = {}, params = {}) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [version, setVersion] = useState(0);
  const key = JSON.stringify([path, filters, params]);
  const current = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const request = ++current.current;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    api(path, filters, params, controller.signal)
      .then((data) => request === current.current && setState({ data, loading: false, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError" && request === current.current) setState((previous) => ({ ...previous, loading: false, error: error.message }));
      });
    return () => controller.abort();
  }, [key, version]);
  return { ...state, retry: () => setVersion((value) => value + 1) };
}
