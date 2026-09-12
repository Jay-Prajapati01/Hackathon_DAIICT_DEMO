import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { verifyService } from '../services/verifyService';

export const verifyCertificate = createAsyncThunk(
  'verify/verifyCertificate',
  async ({ file, claim, claimedBy }, { rejectWithValue }) => {
    try {
      const result = await verifyService.verify(file, { claim, claimedBy });
      return { ...result, file_name: file.name, file_size: file.size };
    } catch (err) {
      return rejectWithValue({ message: err.message, status: err.status });
    }
  },
);

const verifySlice = createSlice({
  name: 'verify',
  initialState: { status: 'idle', result: null, error: null, history: [] },
  reducers: {
    clearVerifyResult(state) {
      state.result = null;
      state.error = null;
      state.status = 'idle';
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(verifyCertificate.pending, (state) => {
        state.status = 'loading';
        state.error = null;
        state.result = null;
      })
      .addCase(verifyCertificate.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.result = action.payload;
        state.history.unshift(action.payload);
        state.history = state.history.slice(0, 20);
      })
      .addCase(verifyCertificate.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload || { message: action.error.message };
      });
  },
});

export const { clearVerifyResult } = verifySlice.actions;
export default verifySlice.reducer;
