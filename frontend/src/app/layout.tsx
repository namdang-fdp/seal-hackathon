import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/app-sidebar";
import { Providers } from "./providers";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "RAGNAROK — AI Data Agency",
  description:
    "Upload raw data files and chat with AI to extract insights, ask questions, and analyze your data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full dark antialiased`}>
      <body className="min-h-full flex bg-zinc-950 text-zinc-50">
        <AppSidebar />
        <main className="flex-1 ml-[260px] min-h-screen">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
