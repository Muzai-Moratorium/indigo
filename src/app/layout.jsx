"use client";
import { Inter } from "next/font/google";
import "../styles/globals.scss";
import { AuthProvider } from "../context/AuthContext";
import { DarkModeProvider } from "../context/DarkModeContext";
import Navbar from "../components/ui/navbar/Navbar";

const inter = Inter({ subsets: ["latin"] });

export default function Layout({ children }) {
  return (
    <html>
      <body>
        <DarkModeProvider>
          <AuthProvider>
            <Navbar />
            <section className={inter.className}>{children}</section>
          </AuthProvider>
        </DarkModeProvider>
      </body>
    </html>
  );
}
