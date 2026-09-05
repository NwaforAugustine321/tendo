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

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  loading: true,

  fetchUser: async () => {
    // Only show the loading spinner on first load when no user is known yet.
    // This prevents navigation from triggering a blank spinner screen.
    if (!get().user) {
      set({ loading: true });
    }
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
