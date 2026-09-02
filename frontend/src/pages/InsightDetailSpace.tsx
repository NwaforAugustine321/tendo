import { useNavigate, useParams } from "react-router-dom";
import InsightDetail, {
  type InsightDetailData,
} from "../components/containers/home/InsightDetail";

const DUMMY_INSIGHTS: InsightDetailData[] = [
  {
    id: "insight-1",
    title: "Wholesale orders increased 24%",
    message:
      "Tendo noticed that wholesale orders have increased compared with recent activity.",
    detected: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    area: "Orders",
    type: "Growth",
    whyItMatters:
      "The increase suggests stronger wholesale demand. If the pattern continues, it may affect inventory, supplier planning, and expected revenue.",
    whatTendoKnows: [
      "Wholesale order activity is higher than it was during the recent comparison period.",
      "The increase is large enough to stand out from normal activity.",
      "Tendo will continue watching wholesale orders to see whether the change continues.",
    ],
    supportingInformation: [
      {
        label: "Change",
        value: "+24%",
      },
      {
        label: "Area",
        value: "Wholesale orders",
      },
      {
        label: "Pattern",
        value: "Increasing",
      },
    ],
    relatedActivity: [
      {
        id: "activity-4",
        title: "Tendo found a change in wholesale orders",
        date: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: "activity-3",
        title: "Tendo updated order information",
        date: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "insight-2",
    title: "Amina Stores is becoming a high-value customer",
    message:
      "Tendo noticed that Amina Stores is showing stronger activity and may be becoming an increasingly valuable customer.",
    detected: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    area: "Customers",
    type: "Customer insight",
    whyItMatters:
      "Customers showing sustained increases in activity may deserve closer attention because they can represent opportunities for stronger relationships and future revenue.",
    whatTendoKnows: [
      "Amina Stores has shown increased activity compared with its previous pattern.",
      "Recent customer activity suggests stronger engagement.",
      "Tendo is watching the relationship for a sustained change.",
    ],
    supportingInformation: [
      {
        label: "Customer",
        value: "Amina Stores",
      },
      {
        label: "Activity",
        value: "Increasing",
      },
      {
        label: "Pattern",
        value: "High-value potential",
      },
    ],
    relatedActivity: [
      {
        id: "activity-1",
        title: "Tendo learned about Musa Ibrahim",
        date: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
      },
      {
        id: "activity-5",
        title: "Customer information was updated",
        date: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "insight-3",
    title: "Customer activity is strongest on weekdays",
    message:
      "Tendo noticed that customer activity is consistently stronger during weekdays.",
    detected: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    area: "Customers",
    type: "Pattern",
    whyItMatters:
      "Knowing when customers are most active can help you decide when to follow up, respond to requests, or focus customer-facing work.",
    whatTendoKnows: [
      "Customer activity is concentrated around weekdays.",
      "The pattern has appeared across recent activity.",
      "Tendo will continue comparing activity over time.",
    ],
    supportingInformation: [
      {
        label: "Pattern",
        value: "Weekday activity",
      },
      {
        label: "Area",
        value: "Customer activity",
      },
    ],
    relatedActivity: [
      {
        id: "activity-5",
        title: "Customer information was updated",
        date: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "insight-4",
    title: "Northern Foods has increased its order frequency",
    message:
      "Tendo noticed that Northern Foods has been placing orders more frequently.",
    detected: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    area: "Customers",
    type: "Customer insight",
    whyItMatters:
      "An increase in order frequency can be a useful signal of growing demand or a strengthening customer relationship.",
    whatTendoKnows: [
      "Northern Foods has increased its recent order frequency.",
      "The change is visible in recent order activity.",
      "Tendo is watching whether the increase continues.",
    ],
    supportingInformation: [
      {
        label: "Customer",
        value: "Northern Foods",
      },
      {
        label: "Order frequency",
        value: "Increasing",
      },
    ],
    relatedActivity: [
      {
        id: "activity-2",
        title: "You added Northern Foods",
        date: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "insight-5",
    title: "Several customers have not reordered recently",
    message:
      "Tendo noticed that several customers have not placed another order within their usual timeframe.",
    detected: new Date(Date.now() - 18 * 60 * 60 * 1000).toISOString(),
    area: "Customers",
    type: "Customer activity",
    whyItMatters:
      "Customers who normally reorder but have become inactive may be worth checking before the relationship weakens further.",
    whatTendoKnows: [
      "Several customers have longer gaps between orders than usual.",
      "The pattern differs from their previous activity.",
      "Tendo can continue watching these customers for further changes.",
    ],
    supportingInformation: [
      {
        label: "Signal",
        value: "Reduced reorder activity",
      },
      {
        label: "Area",
        value: "Customer retention",
      },
    ],
    relatedActivity: [
      {
        id: "activity-5",
        title: "Customer information was updated",
        date: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "insight-6",
    title: "Supplier activity has changed this month",
    message:
      "Tendo noticed a change in the recent pattern of supplier activity.",
    detected: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    area: "Suppliers",
    type: "Pattern",
    whyItMatters:
      "Changes in supplier activity can affect purchasing, availability, delivery timing, and the way you plan upcoming orders.",
    whatTendoKnows: [
      "Supplier activity differs from the recent pattern.",
      "The change has appeared across recent supplier-related activity.",
      "Tendo will continue watching supplier activity for a clearer trend.",
    ],
    supportingInformation: [
      {
        label: "Area",
        value: "Suppliers",
      },
      {
        label: "Pattern",
        value: "Changed",
      },
    ],
    relatedActivity: [
      {
        id: "activity-6",
        title: "Tendo reviewed supplier activity",
        date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },
];

export default function InsightDetailSpace() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const insight = DUMMY_INSIGHTS.find((item) => item.id === id);

  if (!insight) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center px-6">
        <div className="text-center">
          <h1 className="text-[16px] font-medium text-zinc-300">
            Insight not found
          </h1>

          <button
            type="button"
            onClick={() => navigate("/me/insights")}
            className="mt-3 text-[12px] text-zinc-600 transition-colors hover:text-zinc-300"
          >
            Back to What Tendo Found
          </button>
        </div>
      </div>
    );
  }

  return (
    <InsightDetail
      insight={insight}
      onBack={() => navigate("/me/insights")}
      onOpenActivity={(activityId) => {
        navigate(`/me/activity/${activityId}`);
      }}
    />
  );
}
