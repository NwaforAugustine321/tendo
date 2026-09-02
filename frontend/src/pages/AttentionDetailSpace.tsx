import { useNavigate, useParams } from "react-router-dom";
import AttentionDetail, {
  type AttentionDetailData,
} from "../components/containers/home/AttentionDetail";

const DUMMY_ATTENTION: AttentionDetailData[] = [
  {
    id: "attention-1",
    title: "Supplier payment is overdue",
    action: "Review the outstanding payment",
    message:
      "A supplier payment appears to be overdue and may need your attention.",
    detected: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    area: "Suppliers",
    type: "Payment",
    whatHappened:
      "Tendo noticed that a supplier payment has passed its expected payment date.",
    whyItNeedsAttention:
      "An overdue supplier payment may affect your relationship with the supplier or lead to delays if it remains unresolved.",
    whatTendoKnows: [
      "The payment has passed its expected payment date.",
      "The activity is related to a supplier account.",
      "Tendo has identified the payment as something worth reviewing.",
    ],
    whatYouCanDo: [
      "Review the outstanding payment.",
      "Confirm whether the payment has already been made.",
      "If it is still outstanding, decide whether to make or follow up on the payment.",
    ],
    relatedActivity: [
      {
        id: "activity-6",
        title: "Tendo reviewed supplier activity",
        date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "attention-2",
    title: "Order #1042 may be delayed",
    action: "Review the order status",
    message:
      "Recent activity suggests that order #1042 may not arrive within the expected timeframe.",
    detected: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    area: "Orders",
    type: "Order status",
    whatHappened:
      "Tendo noticed activity around order #1042 that suggests the expected timing may have changed.",
    whyItNeedsAttention:
      "A delayed order can affect customer expectations and may require an update or follow-up.",
    whatTendoKnows: [
      "Order #1042 is associated with recent order activity.",
      "The recent activity differs from the expected timing.",
      "Tendo considers the order worth reviewing.",
    ],
    whatYouCanDo: [
      "Review the current order status.",
      "Check whether the expected delivery date has changed.",
      "Follow up with the relevant customer or supplier if necessary.",
    ],
    relatedActivity: [
      {
        id: "activity-3",
        title: "Tendo updated order information",
        date: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "attention-3",
    title: "Cash flow changed this week",
    action: "Review recent cash flow activity",
    message: "Tendo noticed a meaningful change in recent cash flow activity.",
    detected: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    area: "Cash flow",
    type: "Financial activity",
    whatHappened:
      "Recent business activity shows a change in the movement of money compared with the recent pattern.",
    whyItNeedsAttention:
      "Changes in cash flow can affect upcoming payments, purchasing decisions, and the amount of money available to operate the business.",
    whatTendoKnows: [
      "Recent cash flow activity differs from the recent pattern.",
      "The change was significant enough for Tendo to surface it.",
      "Tendo is watching related activity for further changes.",
    ],
    whatYouCanDo: [
      "Review recent incoming and outgoing payments.",
      "Check upcoming obligations.",
      "Decide whether the change requires any adjustment.",
    ],
    relatedActivity: [
      {
        id: "activity-3",
        title: "Tendo updated order information",
        date: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "attention-4",
    title: "Northern Foods payment is approaching",
    action: "Review the upcoming payment",
    message:
      "An upcoming payment related to Northern Foods may need to be reviewed.",
    detected: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    area: "Payments",
    type: "Upcoming payment",
    whatHappened:
      "Tendo identified an upcoming payment associated with Northern Foods.",
    whyItNeedsAttention:
      "Reviewing upcoming payments can help prevent missed deadlines and unexpected disruptions.",
    whatTendoKnows: [
      "Northern Foods is associated with recent business activity.",
      "A payment related to the relationship is approaching.",
      "Tendo surfaced it so it is not overlooked.",
    ],
    whatYouCanDo: [
      "Review the payment details.",
      "Confirm the expected payment date.",
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
    id: "attention-5",
    title: "Several customer orders need review",
    action: "Review recent customer orders",
    message: "Tendo noticed several customer orders that may need attention.",
    detected: new Date(Date.now() - 10 * 60 * 60 * 1000).toISOString(),
    area: "Orders",
    type: "Order review",
    whatHappened:
      "Several recent customer orders have activity that may require a closer look.",
    whyItNeedsAttention:
      "Reviewing these orders now may help identify delays, missing information, or other issues before they affect customers.",
    whatTendoKnows: [
      "Several orders have recent activity.",
      "Some order information may require confirmation.",
      "Tendo has grouped the activity because it may be useful to review together.",
    ],
    whatYouCanDo: [
      "Review the affected orders.",
      "Confirm that the order information is complete.",
      "Follow up on anything that looks unusual.",
    ],
    relatedActivity: [
      {
        id: "activity-3",
        title: "Tendo updated order information",
        date: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  {
    id: "attention-6",
    title: "Supplier activity has slowed",
    action: "Review recent supplier activity",
    message: "Tendo noticed that recent supplier activity is lower than usual.",
    detected: new Date(Date.now() - 16 * 60 * 60 * 1000).toISOString(),
    area: "Suppliers",
    type: "Activity change",
    whatHappened:
      "Recent supplier-related activity is lower than the recent pattern.",
    whyItNeedsAttention:
      "A change in supplier activity can affect ordering, availability, and upcoming business operations.",
    whatTendoKnows: [
      "Supplier activity has decreased compared with the recent pattern.",
      "The change has appeared across recent supplier-related activity.",
      "Tendo is watching for further changes.",
    ],
    whatYouCanDo: [
      "Review recent supplier activity.",
      "Check whether any expected supplier interactions are missing.",
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

export default function AttentionDetailSpace() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const attention = DUMMY_ATTENTION.find((item) => item.id === id);

  if (!attention) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center px-6">
        <div className="text-center">
          <h1 className="text-[16px] font-medium text-zinc-300">
            Attention item not found
          </h1>

          <button
            type="button"
            onClick={() => navigate("/me/attention")}
            className="mt-3 text-[12px] text-zinc-600 transition-colors hover:text-zinc-300"
          >
            Back to What Needs Your Attention
          </button>
        </div>
      </div>
    );
  }

  return (
    <AttentionDetail
      attention={attention}
      onBack={() => navigate("/me/attention")}
      onOpenActivity={(activityId) => {
        navigate(`/me/activity/${activityId}`);
      }}
    />
  );
}
