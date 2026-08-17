import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智慧医疗住院数据分析平台",
  description: "Hospital inpatient discharge BI dashboard",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
