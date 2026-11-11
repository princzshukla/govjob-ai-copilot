// frontend/src/components/adaptive/StartDrillButton.tsx
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

interface StartDrillButtonProps {
  topic: string;
  examId?: string;
  className?: string;
}

export function StartDrillButton({
  topic,
  examId = "ssc-cgl-tier1",
  className,
}: StartDrillButtonProps) {
  return (
    <Button asChild size="sm" className={className}>
      <Link
        to={`/quiz/${encodeURIComponent(examId)}/${encodeURIComponent(topic)}` as never}
      >
        Start Adaptive Practice
      </Link>
    </Button>
  );
}