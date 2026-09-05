import { Navigate, Outlet } from "react-router-dom"; // Import Outlet
import { useAuth } from "../../context/auth";
import { Spinner } from "../atoms/Spinner";

export function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#0a0a0a]">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
