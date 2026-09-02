import { useLocation } from "react-router-dom";
import { InsightsFeed } from "./InsightsFeed";
import HomeSpace from "../../pages/HomeSpace";
import { Dashboard } from "../../pages/workspace/Dashboard";
import { Profile } from "../../pages/workspace/Profile";
import KnowledgeSpace from "../../pages/KnowledgeSpace";

export function WorkspaceContent() {
  const location = useLocation();
  const path = location.pathname;

  if (path === "/me" || path === "/me/") {
    return <HomeSpace />;
  }

  if (path.startsWith("/me/insights")) {
    return <Dashboard />;
  }

  if (path.startsWith("/me/profile")) {
    return <Profile />;
  }

  if (path.startsWith("/me/knowledge")) {
    return <KnowledgeSpace />;
  }

  return <InsightsFeed />;
}
