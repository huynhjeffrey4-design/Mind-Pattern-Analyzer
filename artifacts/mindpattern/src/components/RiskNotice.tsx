import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function RiskNotice() {
  return (
    <Card className="border-destructive/60 bg-destructive/5">
      <CardContent className="flex gap-3 pt-5 pb-5">
        <AlertTriangle className="w-5 h-5 text-destructive mt-0.5 shrink-0" />
        <div>
          <p className="font-semibold text-destructive text-sm">Important Safety Notice</p>
          <p className="text-sm text-muted-foreground mt-1">
            If you may hurt yourself or someone else, call emergency services now. If you are in the
            U.S., you can call or text{" "}
            <span className="font-bold text-foreground">988</span> for crisis support.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
