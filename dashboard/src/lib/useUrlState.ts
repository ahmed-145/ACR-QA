import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

type ParamValue = string | null;

export function useUrlState(key: string, defaultValue: string = "") {
  const [params, setParams] = useSearchParams();

  const value = params.get(key) ?? defaultValue;

  const setValue = useCallback(
    (next: ParamValue) => {
      setParams((prev) => {
        const p = new URLSearchParams(prev);
        if (next === null || next === defaultValue) {
          p.delete(key);
        } else {
          p.set(key, next);
        }
        return p;
      }, { replace: true });
    },
    [key, defaultValue, setParams]
  );

  return [value, setValue] as const;
}

export function useUrlStateMulti<T extends Record<string, string>>(defaults: T) {
  const [params, setParams] = useSearchParams();

  const values = Object.fromEntries(
    Object.entries(defaults).map(([k, d]) => [k, params.get(k) ?? d])
  ) as T;

  const setValues = useCallback(
    (updates: Partial<T>) => {
      setParams((prev) => {
        const p = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(updates)) {
          if (v === null || v === defaults[k]) {
            p.delete(k);
          } else {
            p.set(k, v as string);
          }
        }
        return p;
      }, { replace: true });
    },
    [defaults, setParams]
  );

  return [values, setValues] as const;
}
