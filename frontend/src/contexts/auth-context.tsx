import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  api,
  clearTokens,
  ensureSession,
  getAccessToken,
  getActiveHouseholdId,
  getRefreshToken,
  setActiveHouseholdId,
  storeTokens,
} from "@/lib/api";
import type { Household, User } from "@/lib/types";

type AuthState = {
  user: User | null;
  households: Household[];
  activeHousehold: Household | null;
  loading: boolean;
  initialized: boolean | null;
  registrationMode: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  setup: (input: {
    email: string;
    password: string;
    displayName: string;
    householdName: string;
    timezone?: string;
    latitude?: number | null;
    longitude?: number | null;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshHouseholds: () => Promise<void>;
  setActiveHousehold: (household: Household) => void;
  acceptInvite: (token: string) => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [activeHousehold, setActiveHouseholdState] = useState<Household | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [registrationMode, setRegistrationMode] = useState<string | null>(null);

  const applyHouseholds = useCallback((list: Household[], preferredId?: string | null) => {
    setHouseholds(list);
    const stored = preferredId ?? getActiveHouseholdId();
    const match = list.find((h) => h.id === stored) ?? list[0] ?? null;
    setActiveHouseholdState(match);
    setActiveHouseholdId(match?.id ?? null);
  }, []);

  const refreshHouseholds = useCallback(async () => {
    const list = await api.listHouseholds();
    applyHouseholds(list, getActiveHouseholdId());
  }, [applyHouseholds]);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    try {
      const status = await api.authStatus();
      setInitialized(status.initialized);
      setRegistrationMode(status.registration_mode);

      // Revive session from refresh token when access token expired
      if (!getAccessToken() && getRefreshToken()) {
        await ensureSession();
      }

      if (!getAccessToken()) {
        setUser(null);
        setHouseholds([]);
        setActiveHouseholdState(null);
        return;
      }

      try {
        const me = await api.me();
        setUser(me);
        const list = await api.listHouseholds();
        applyHouseholds(list);
      } catch {
        // One more refresh attempt then give up (keep account data — just re-login)
        const ok = await ensureSession();
        if (ok) {
          try {
            const me = await api.me();
            setUser(me);
            const list = await api.listHouseholds();
            applyHouseholds(list);
            return;
          } catch {
            /* fall through */
          }
        }
        clearTokens();
        setUser(null);
        setHouseholds([]);
        setActiveHouseholdState(null);
      }
    } finally {
      setLoading(false);
    }
  }, [applyHouseholds]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api.login({ email, password });
      storeTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      setInitialized(true);
      await refreshHouseholds();
    },
    [refreshHouseholds],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      const data = await api.register({
        email,
        password,
        display_name: displayName,
      });
      storeTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      setInitialized(true);
      await refreshHouseholds();
    },
    [refreshHouseholds],
  );

  const setup = useCallback(
    async (input: {
      email: string;
      password: string;
      displayName: string;
      householdName: string;
      timezone?: string;
      latitude?: number | null;
      longitude?: number | null;
    }) => {
      const data = await api.setup({
        email: input.email,
        password: input.password,
        display_name: input.displayName,
        household_name: input.householdName,
        timezone: input.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
        latitude: input.latitude ?? null,
        longitude: input.longitude ?? null,
      });
      storeTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      setInitialized(true);
      setActiveHouseholdId(data.household_id);
      await refreshHouseholds();
    },
    [refreshHouseholds],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* ignore */
    }
    clearTokens();
    setActiveHouseholdId(null);
    setUser(null);
    setHouseholds([]);
    setActiveHouseholdState(null);
  }, []);

  const setActiveHousehold = useCallback((household: Household) => {
    setActiveHouseholdState(household);
    setActiveHouseholdId(household.id);
  }, []);

  const acceptInvite = useCallback(
    async (token: string) => {
      const household = await api.acceptInvitation(token);
      setActiveHouseholdId(household.id);
      await refreshHouseholds();
    },
    [refreshHouseholds],
  );

  const value = useMemo(
    () => ({
      user,
      households,
      activeHousehold,
      loading,
      initialized,
      registrationMode,
      login,
      register,
      setup,
      logout,
      refreshHouseholds,
      setActiveHousehold,
      acceptInvite,
    }),
    [
      user,
      households,
      activeHousehold,
      loading,
      initialized,
      registrationMode,
      login,
      register,
      setup,
      logout,
      refreshHouseholds,
      setActiveHousehold,
      acceptInvite,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
