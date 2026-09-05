import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import "./index.css";
import App from "./App";
import { AuthProvider } from "./context/auth";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#141414",
            border: "1px solid rgba(39, 39, 42, 0.9)",
            color: "#e4e4e7",
            fontSize: "13px",
            fontFamily: "Inter, sans-serif",
          },
          className: "rounded-lg",
        }}
      />
    </BrowserRouter>
  </StrictMode>,
);
