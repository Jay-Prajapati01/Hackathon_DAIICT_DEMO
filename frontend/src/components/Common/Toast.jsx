import React from 'react';
import { Toaster } from 'react-hot-toast';

/** Application-wide toaster configured with the REC Guard design tokens. */
export default function AppToaster() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border)',
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--text-sm)',
        },
        success: { iconTheme: { primary: 'var(--green-400)', secondary: 'var(--bg-primary)' } },
        error: { iconTheme: { primary: 'var(--red-400)', secondary: 'var(--bg-primary)' } },
      }}
    />
  );
}
