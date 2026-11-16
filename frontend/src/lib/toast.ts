import { useEffect, useState } from "react";

export interface ToastItem {
  id: number;
  kind: "info" | "success" | "warn";
  title: string;
  body?: string;
}

type Listener = (items: ToastItem[]) => void;

let nextId = 1;
const items: ToastItem[] = [];
const listeners = new Set<Listener>();

function emit() {
  const snapshot = [...items];
  listeners.forEach((fn) => fn(snapshot));
}

export function toast(kind: ToastItem["kind"], title: string, body?: string) {
  const item: ToastItem = { id: nextId++, kind, title, body };
  items.push(item);
  emit();
  window.setTimeout(() => {
    const idx = items.findIndex((t) => t.id === item.id);
    if (idx >= 0) {
      items.splice(idx, 1);
      emit();
    }
  }, 3200);
  return item.id;
}

export function useToasts() {
  const [state, setState] = useState<ToastItem[]>(items);
  useEffect(() => {
    const fn: Listener = (s) => setState(s);
    listeners.add(fn);
    fn([...items]);
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return state;
}
