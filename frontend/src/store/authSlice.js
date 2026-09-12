import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { authService } from '../services/authService';
import { TOKEN_KEY, USER_KEY } from '../services/api';

function loadPersisted() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const user = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    return token && user ? { token, user } : { token: null, user: null };
  } catch {
    return { token: null, user: null };
  }
}

function persist(token, user) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

export const login = createAsyncThunk('auth/login', async ({ email, password }, { rejectWithValue }) => {
  try {
    return await authService.login(email, password);
  } catch (err) {
    return rejectWithValue({ message: err.message, details: err.details });
  }
});

export const register = createAsyncThunk('auth/register', async (payload, { rejectWithValue }) => {
  try {
    return await authService.register(payload);
  } catch (err) {
    return rejectWithValue({ message: err.message, details: err.details });
  }
});

const authSlice = createSlice({
  name: 'auth',
  initialState: { ...loadPersisted(), status: 'idle', error: null },
  reducers: {
    logout(state) {
      state.token = null;
      state.user = null;
      state.error = null;
      persist(null, null);
    },
  },
  extraReducers: (builder) => {
    const pending = (state) => {
      state.status = 'loading';
      state.error = null;
    };
    const fulfilled = (state, action) => {
      state.status = 'succeeded';
      state.token = action.payload.access_token;
      state.user = action.payload.user;
      persist(state.token, state.user);
    };
    const rejected = (state, action) => {
      state.status = 'failed';
      state.error = action.payload || { message: action.error.message };
    };
    builder
      .addCase(login.pending, pending)
      .addCase(login.fulfilled, fulfilled)
      .addCase(login.rejected, rejected)
      .addCase(register.pending, pending)
      .addCase(register.fulfilled, fulfilled)
      .addCase(register.rejected, rejected);
  },
});

export const { logout } = authSlice.actions;
export const selectUser = (state) => state.auth.user;
export const selectIsAuthenticated = (state) => Boolean(state.auth.token);
export const selectCanRegulate = (state) => ['regulator', 'admin'].includes(state.auth.user?.role);
export default authSlice.reducer;
