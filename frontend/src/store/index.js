import { configureStore } from '@reduxjs/toolkit';
import issueReducer from './issueSlice';
import verifyReducer from './verifySlice';
import authReducer from './authSlice';

export const store = configureStore({
  reducer: { issue: issueReducer, verify: verifyReducer, auth: authReducer },
  middleware: (getDefault) => getDefault({ serializableCheck: false }),
});

export default store;
