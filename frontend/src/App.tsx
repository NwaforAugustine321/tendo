import { Routes, Route, Navigate } from "react-router-dom";
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
import { Conversation } from "./pages/Conversation";
import { WorkspaceLayout } from "./layout/WorkspaceLayout";
import { WorkspaceHome } from "./pages/workspace/Home";
import { Business } from "./pages/workspace/Business";
import { Inventory } from "./pages/workspace/Inventory";
import { Customers } from "./pages/workspace/Customers";
import { Analytics } from "./pages/workspace/Analytics";
import { Profile } from "./pages/workspace/Profile";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/register" element={<Register />} />
        <Route path="/welcome" element={<Welcome />} />

        {/* Requires auth */}
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

        {/* Protected workspace */}
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <WorkspaceLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<WorkspaceHome />} />
          <Route path="business" element={<Business />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="customers" element={<Customers />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="profile" element={<Profile />} />
          <Route path="*" element={<WorkspaceHome />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
