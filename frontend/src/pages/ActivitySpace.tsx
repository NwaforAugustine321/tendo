import {
  RecentActivity,
  type RecentActivityItem,
} from "../components/containers/home/RecentActivity";
import { useNavigate } from "react-router-dom";

export default function ActivitySpace() {
  const navigate = useNavigate();

  return (
    <RecentActivity
      onOpen={(item: RecentActivityItem) => {
        navigate(`/me/activity/${item.id}`);
      }}
    />
  );
}
