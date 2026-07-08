import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Blobs } from "@/components/Blobs";
import { clerkAppearance } from "@/lib/clerkAppearance";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CareerOS",
  description: "Tailored resumes and cover letters, instantly.",
};

export const viewport: Viewport = {
  themeColor: "#111110",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth();

  return (
    <ClerkProvider appearance={clerkAppearance}>
      <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
        <body>
          <div className="relative min-h-screen">
            <Blobs />
            {userId && <Navbar />}
            <main className={`relative z-10 ${userId ? "pt-24" : ""}`}>
              {children}
            </main>
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
}
