import { create } from 'zustand';
import { User } from '../service/account';

const ACCESS_TOKEN_EXPIRES_IN = 1296000;

type AuthState = {
    accessToken: string | null;
    user: User | null;
    expiresAt: number | null;
    setToken: (token: string | null) => void;
    setUser: (user: User | null) => void;
    clear: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
    accessToken: null,
    user: null,
    expiresAt: null,
    setToken: (token) => {
        if (!token) return set({ accessToken: null, expiresAt: null });

        const expiresAt = Date.now() + ACCESS_TOKEN_EXPIRES_IN * 1000;

        return set({ accessToken: token, expiresAt });
    },
    setUser: (user) => set({ user }),
    clear: () => set({ accessToken: null, user: null, expiresAt: null }),
}));
