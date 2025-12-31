"use client";
import { Inter } from "next/font/google";
import "../styles/globals.scss";
import Sidebar from "../components/ui/sidebar/sidebar";
import { AuthProvider } from "../context/AuthContext";

const inter = Inter({ subsets: ["latin"] });

export default function Layout({ children }) {
  return (
    <html>
      <body>
        <AuthProvider>
          <Sidebar />
          <section className={inter.className}>{children}</section>
        </AuthProvider>
      </body>
    </html>
  );
}
