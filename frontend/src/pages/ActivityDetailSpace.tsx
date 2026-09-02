import { useNavigate, useParams } from "react-router-dom";

import ActivityDetail from "../components/containers/home/ActivityDetail";

import { type RecentActivityItem } from "../components/containers/home/RecentActivity";

export default function ActivityDetailSpace() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  /*
   * For now RecentActivity contains our dummy data.
   * We use the same data here to find the selected activity.
   */
  const activities: RecentActivityItem[] = [
    {
      id: "activity-1",
      title: "Tendo learned about Musa Ibrahim",
      date: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
      message: "New customer information was added to what Tendo knows.",
    },
    {
      id: "activity-2",
      title: "You added Northern Foods",
      date: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
      message: "Northern Foods was added to your business knowledge.",
    },
    {
      id: "activity-3",
      title: "Tendo updated order information",
      date: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      message: "Order information was updated from recent business activity.",
    },
    {
      id: "activity-4",
      title: "Tendo found a change in wholesale orders",
      date: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
      message: "Wholesale orders have increased compared with recent activity.",
    },
    {
      id: "activity-5",
      title: "Customer information was updated",
      date: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
      message: "Tendo noticed new information related to a customer.",
    },
    {
      id: "activity-6",
      title: "Tendo reviewed supplier activity",
      date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      message: "Recent supplier activity was reviewed.",
    },
  ];

  const activity = activities.find((item) => item.id === id);

  if (!activity) {
    return (
      <div className="h-full min-h-0 overflow-y-auto">
        <div className="mx-auto w-full max-w-[900px] px-6 py-10 lg:px-8">
          <button
            type="button"
            onClick={() => navigate("/me/activity")}
            className="text-[11px] text-zinc-600 transition-colors hover:text-zinc-300"
          >
            ← Recent Activity
          </button>

          <div className="mt-10">
            <h1 className="text-[20px] font-medium text-zinc-100">
              Activity not found
            </h1>

            <p className="mt-2 text-[12px] text-zinc-600">
              This activity may no longer be available.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ActivityDetail
      activity={activity}
      onBack={() => navigate("/me/activity")}
    />
  );
}
