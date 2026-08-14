import { create } from "zustand";
import { getMe, getProfile, type AuthUser } from "../lib/services/auth";

type AuthStore = {
  user: AuthUser | null;
  loading: boolean;
  fetchUser: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  setUser: (user: AuthUser | null) => void;
  clear: () => void;
};

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  loading: true,

  fetchUser: async () => {
    set({ loading: true });
    try {
      const user = await getMe();
      set({ user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  fetchProfile: async () => {
    try {
      const user = await getProfile();
      set({ user });
    } catch {
      // toast is handled by http layer
    }
  },

  setUser: (user) => set({ user, loading: false }),

  clear: () => set({ user: null, loading: false }),
}));
