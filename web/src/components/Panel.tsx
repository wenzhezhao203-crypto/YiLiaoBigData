import type { ReactNode } from "react";
import { Activity } from "lucide-react";

export function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <section className="panel"><header className="panel-head"><h2><Activity size={15} />{title}</h2>{action}</header>{children}</section>;
}

export function State({ children }: { children: ReactNode }) { return <div className="state">{children}</div>; }
