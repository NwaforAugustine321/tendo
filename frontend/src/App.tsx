import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./context/auth";

import { ProtectedRoute } from "./components/containers/ProtectedRoute";

import { Landing } from "./pages/Landing";
import { Login } from "./pages/auth/Login";
import { Register } from "./pages/auth/Register";
import { Welcome } from "./pages/auth/Welcome";
import { ResetPassword } from "./pages/auth/ResetPassword";
import { ForgotPassword } from "./pages/auth/ForgotPassword";

import { SelectBusiness } from "./pages/SelectBusiness";
import { Onboarding } from "./pages/Onboarding";

import { WorkspaceLayout } from "./layout/WorkspaceLayout";

import HomeSpace from "./pages/HomeSpace";
import { Profile } from "./pages/workspace/Profile";
import KnowledgeSpace from "./pages/KnowledgeSpace";

import ActivitySpace from "./pages/ActivitySpace";
import InsightSnapSpace from "./pages/InsightSpace";
import AttentionSnapSpace from "./pages/AttentionSnapSpace";
import ActivityDetailSpace from "./pages/ActivityDetailSpace";
import InsightDetailSpace from "./pages/InsightDetailSpace";
import AttentionDetailSpace from "./pages/AttentionDetailSpace";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* ============================================================ */}
        {/* Public routes                                                 */}
        {/* ============================================================ */}

        <Route path="/" element={<Landing />} />

        <Route path="/login" element={<Login />} />

        <Route path="/forgot-password" element={<ForgotPassword />} />

        <Route path="/reset-password" element={<ResetPassword />} />

        <Route path="/register" element={<Register />} />

        <Route path="/welcome" element={<Welcome />} />

        {/* ============================================================ */}
        {/* Protected setup routes                                        */}
        {/* ============================================================ */}

        <Route
          path="/business-profile"
          element={
            <ProtectedRoute>
              <SelectBusiness />
            </ProtectedRoute>
          }
        />

        <Route
          path="/onboarding"
          element={
            <ProtectedRoute>
              <Onboarding />
            </ProtectedRoute>
          }
        />

        <Route
          path="/me"
          element={
            <ProtectedRoute>
              <WorkspaceLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<HomeSpace />} />

          <Route path="profile" element={<Profile />} />

          <Route path="knowledge" element={<KnowledgeSpace />} />

          <Route path="attention" element={<AttentionSnapSpace />} />

          <Route path="insights" element={<InsightSnapSpace />} />

          <Route path="activity" element={<ActivitySpace />} />
          <Route path="activity/:id" element={<ActivityDetailSpace />} />
          <Route path="insights/:id" element={<InsightDetailSpace />} />
          <Route path="attention/:id" element={<AttentionDetailSpace />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
