"use client";
import { useState } from "react";
import styles from "./sidebar.module.scss";
import Link from "next/link";
import { CiSearch } from "react-icons/ci";
import { useAuth } from "../../../context/AuthContext";
import DayNightToggle from "../darkmodeBtn/DayNightToggle";
import { PiHamburgerBold } from "react-icons/pi";

const MENU_ITEMS = [
  { name: "홈", path: "/" },
  { name: "CCTV", path: "/cctv" },
  { name: "정보", path: "/about" },
];

function Sidebar() {
  const { user, loading, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => setIsOpen(!isOpen);
  const closeMenu = () => setIsOpen(false);

  return (
    <>
      <button className={styles.menuButton} onClick={toggleMenu}>
        <PiHamburgerBold />
      </button>

      <div
        className={`${styles.overlay} ${isOpen ? styles.open : ""}`}
        onClick={closeMenu}
      />

      <div className={`${styles.sidebar} ${isOpen ? styles.open : ""}`}>
        <h1 className={styles.title}>반응형테스트</h1>
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

            {!loading && (
              <>
                {user ? (
                  <>
                    <li className={styles.navItem}>
                      <Link
                        href="/mypage"
                        className={styles.link}
                        onClick={closeMenu}
                      >
                        {user.email}
                      </Link>
                    </li>
                    <li className={styles.navItem}>
                      <button
                        onClick={() => {
                          logout();
                          closeMenu();
                        }}
                        className={styles.link}
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

        <div className={styles.toggleWrapper}>
          <DayNightToggle />
        </div>
      </div>
    </>
  );
}

export default Sidebar;
