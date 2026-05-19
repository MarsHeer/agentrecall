import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentRecall Dashboard",
  description: "Manage your agent memory cloud",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
