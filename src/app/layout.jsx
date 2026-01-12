"use client";
import { Inter } from "next/font/google";
import "../styles/globals.scss";
import Sidebar from "../components/ui/sidebar/sidebar";
import { AuthProvider } from "../context/AuthContext";
import { DarkModeProvider } from "../context/DarkModeContext";

const inter = Inter({ subsets: ["latin"] });

export default function Layout({ children }) {
  return (
    <html>
      <body>
        <DarkModeProvider>
          <AuthProvider>
            <Sidebar />
            <section className={inter.className}>{children}</section>
          </AuthProvider>
        </DarkModeProvider>
      </body>
    </html>
  );
}
