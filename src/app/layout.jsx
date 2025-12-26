"use client";
import { Inter } from "next/font/google";
import "../styles/globals.scss";
import Sidebar from "../components/ui/sidebar/sidebar";
const inter = Inter({ subsets: ["latin"] });

export default function Layout({ children }) {
  return (
    <html>
      <body>
        <Sidebar />
        <section className={inter.className}>{children}</section>
      </body>
    </html>
  );
}
