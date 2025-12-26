"use client";
import styles from "./sidebar.module.scss";
import Link from "next/link";
import { CiSearch } from "react-icons/ci";

const MENU_ITEMS = [
  { name: "Home", path: "/" },
  { name: "Cats", path: "/cats" },
  { name: "About", path: "/about" },
  { name: "Login", path: "/login" },
  { name: "Register", path: "/register" },
];

function Sidebar() {
  return (
    <div className={styles.sidebar}>
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
              <Link href={item.path} className={styles.link}>
                {item.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

export default Sidebar;
