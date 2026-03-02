import { create } from "zustand";
import { persist } from "zustand/middleware";

interface DevStore {
  devMode: boolean;
  setDevMode: (val: boolean) => void;
}

export const useDevStore = create<DevStore>()(
  persist(
    (set) => ({
      devMode: false,
      setDevMode: (devMode) => set({ devMode }),
    }),
    { name: "open-stitch-dev" }
  )
);