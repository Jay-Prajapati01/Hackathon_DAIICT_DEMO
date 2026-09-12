// frontend/src/App.jsx — main layout + routing
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Layout/Header';
import Sidebar from './components/Layout/Sidebar';
import Footer from './components/Layout/Footer';
import AppToaster from './components/Common/Toast';
import IssuePage from './pages/IssuePage';
import VerifyPage from './pages/VerifyPage';
import LedgerPage from './pages/LedgerPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import './App.css';

function AppLayout({ children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="app-content">{children}</main>
        <Footer />
      </div>
    </div>
  );
}

/** Route table without a router, so tests can mount it inside a MemoryRouter. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AppLayout><DashboardPage /></AppLayout>} />
      <Route path="/issue" element={<AppLayout><IssuePage /></AppLayout>} />
      <Route path="/verify" element={<AppLayout><VerifyPage /></AppLayout>} />
      <Route path="/ledger" element={<AppLayout><LedgerPage /></AppLayout>} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppToaster />
      <AppRoutes />
    </BrowserRouter>
  );
}
