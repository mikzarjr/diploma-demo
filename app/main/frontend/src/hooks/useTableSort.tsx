"use client";

import { useMemo, useState } from "react";
import { TableCell, TableSortLabel } from "@mui/material";
import type { TableCellProps } from "@mui/material";

export type SortDir = "asc" | "desc" | null;

export interface SortState<K extends string> {
  key: K | null;
  dir: SortDir;
}

export type SortValue = string | number | Date | null | undefined;

export type SortKeyMap<T, K extends string> = Record<K, (item: T) => SortValue>;

export interface UseTableSortResult<T, K extends string> {
  sorted: T[];
  state: SortState<K>;
  toggle: (key: K) => void;
  getProps: (key: K) => {
    active: boolean;
    direction: "asc" | "desc";
    onClick: () => void;
  };
}

function compare(a: SortValue, b: SortValue): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (a instanceof Date && b instanceof Date) return a.getTime() - b.getTime();
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "ru", { numeric: true, sensitivity: "base" });
}

export function useTableSort<T, K extends string>(
  items: T[],
  keys: SortKeyMap<T, K>
): UseTableSortResult<T, K> {
  const [state, setState] = useState<SortState<K>>({ key: null, dir: null });

  const toggle = (key: K) => {
    setState((prev) => {
      if (prev.key !== key) return { key, dir: "asc" };
      if (prev.dir === "asc") return { key, dir: "desc" };
      return { key: null, dir: null };
    });
  };

  const sorted = useMemo(() => {
    if (!state.key || !state.dir) return items;
    const getter = keys[state.key];
    const mul = state.dir === "asc" ? 1 : -1;
    return [...items].sort((a, b) => compare(getter(a), getter(b)) * mul);
  }, [items, state, keys]);

  const getProps = (key: K) => ({
    active: state.key === key,
    direction: (state.key === key && state.dir ? state.dir : "asc") as "asc" | "desc",
    onClick: () => toggle(key),
  });

  return { sorted, state, toggle, getProps };
}

interface SortableCellProps<T, K extends string> extends Omit<TableCellProps, "onClick"> {
  sortKey: K;
  sort: UseTableSortResult<T, K>;
  children: React.ReactNode;
}

export function SortableCell<T, K extends string>({
  sortKey,
  sort,
  children,
  ...cellProps
}: SortableCellProps<T, K>) {
  const props = sort.getProps(sortKey);
  return (
    <TableCell {...cellProps} sortDirection={props.active ? props.direction : false}>
      <TableSortLabel
        active={props.active}
        direction={props.direction}
        onClick={props.onClick}
        sx={{ fontWeight: "inherit" }}
      >
        {children}
      </TableSortLabel>
    </TableCell>
  );
}
