"use client";
import { useState } from "react";
import styles from "./sidebar.module.scss";
import Link from "next/link";
import { CiSearch } from "react-icons/ci";
import { useAuth } from "../../../context/AuthContext";

const MENU_ITEMS = [
  { name: "Home", path: "/" },
  { name: "Cats", path: "/cats" },
  { name: "About", path: "/about" },
];

function Sidebar() {
  const { user, loading, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => setIsOpen(!isOpen);
  const closeMenu = () => setIsOpen(false);

  return (
    <>
      {/* 햄버거 버튼 (모바일) */}
      <button className={styles.menuButton} onClick={toggleMenu}>
        ☰
      </button>

      {/* 오버레이 (모바일) */}
      <div
        className={`${styles.overlay} ${isOpen ? styles.open : ""}`}
        onClick={closeMenu}
      />

      {/* 사이드바 */}
      <div className={`${styles.sidebar} ${isOpen ? styles.open : ""}`}>
        <h1 className={styles.title}>Sidebar</h1>
        <form action="search">
          <input type="text" name="search" />
          <button type="submit">
            <CiSearch />
          </button>
        </form>
        <nav>
          <ul className={styles.navList}>
            {MENU_ITEMS.map((item) => (
              <li key={item.path} className={styles.navItem}>
                <Link
                  href={item.path}
                  className={styles.link}
                  onClick={closeMenu}
                >
                  {item.name}
                </Link>
              </li>
            ))}

            {/* 인증 상태에 따른 메뉴 */}
            {!loading && (
              <>
                {user ? (
                  <>
                    <li className={styles.navItem}>
                      <span className={styles.link}>{user.email}</span>
                    </li>
                    <li className={styles.navItem}>
                      <button
                        onClick={() => {
                          logout();
                          closeMenu();
                        }}
                        className={styles.link}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          width: "100%",
                          textAlign: "left",
                        }}
                      >
                        로그아웃
                      </button>
                    </li>
                  </>
                ) : (
                  <>
                    <li className={styles.navItem}>
                      <Link
                        href="/login"
                        className={styles.link}
                        onClick={closeMenu}
                      >
                        로그인
                      </Link>
                    </li>
                    <li className={styles.navItem}>
                      <Link
                        href="/signup"
                        className={styles.link}
                        onClick={closeMenu}
                      >
                        회원가입
                      </Link>
                    </li>
                  </>
                )}
              </>
            )}
          </ul>
        </nav>
      </div>
    </>
  );
}

export default Sidebar;
