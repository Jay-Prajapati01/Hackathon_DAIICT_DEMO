import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { issueService } from '../services/issueService';

export const issueCertificate = createAsyncThunk('issue/issueCertificate', async (payload, { rejectWithValue }) => {
  try {
    return await issueService.issue(payload);
  } catch (err) {
    return rejectWithValue({ message: err.message, details: err.details, status: err.status });
  }
});

const issueSlice = createSlice({
  name: 'issue',
  initialState: { status: 'idle', result: null, error: null, history: [] },
  reducers: {
    clearIssueResult(state) {
      state.result = null;
      state.error = null;
      state.status = 'idle';
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(issueCertificate.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(issueCertificate.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.result = action.payload;
        state.history.unshift(action.payload);
        state.history = state.history.slice(0, 20);
      })
      .addCase(issueCertificate.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload || { message: action.error.message };
      });
  },
});

export const { clearIssueResult } = issueSlice.actions;
export default issueSlice.reducer;
