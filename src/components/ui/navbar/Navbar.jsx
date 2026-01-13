"use client";
import { useAuth } from "../../../context/AuthContext";
import { useDarkMode } from "../../../context/DarkModeContext";
import CardNav from "./CardNav";
import DayNightToggle from "../darkmodeBtn/DayNightToggle";
import { LuDog } from "react-icons/lu";
import { LuCat } from "react-icons/lu";

const Navbar = () => {
  const { user, loading, logout } = useAuth();
  const { isDarkMode } = useDarkMode();

  // 기본 메뉴 아이템
  const baseItems = [
    {
      label: "메뉴",
      bgColor: isDarkMode ? "#1A252F" : "#D35400",
      textColor: "#fff",
      links: [
        { label: "홈", href: "/", ariaLabel: "홈으로 이동" },
        { label: "CCTV", href: "/cctv", ariaLabel: "CCTV 페이지" },
        { label: "정보", href: "/about", ariaLabel: "정보 페이지" },
      ],
    },
  ];

  // 인증 상태에 따른 계정 메뉴
  const accountItem = user
    ? {
        label: "계정",
        bgColor: isDarkMode ? "#1A252F" : "#D35400",
        textColor: "#fff",
        links: [
          { label: user.email, href: "/mypage", ariaLabel: "마이페이지" },
          {
            label: "로그아웃",
            href: "#",
            ariaLabel: "로그아웃",
            onClick: logout,
          },
        ],
      }
    : {
        label: "계정",
        bgColor: isDarkMode ? "#1A252F" : "#D35400",
        textColor: "#fff",
        links: [
          { label: "로그인", href: "/login", ariaLabel: "로그인" },
          { label: "회원가입", href: "/signup", ariaLabel: "회원가입" },
        ],
      };

  // 다크모드 토글 메뉴
  const settingsItem = {
    label: "설정",
    bgColor: isDarkMode ? "#1A252F" : "#D35400",
    textColor: "#fff",
    customContent: <DayNightToggle />,
    links: [],
  };

  const items = loading ? baseItems : [...baseItems, accountItem, settingsItem];

  return (
    <CardNav
      items={items}
      ease="back.out(1.7)"
      baseColor={isDarkMode ? "#2C3E50" : "#FF8C00"}
      menuColor="#fff"
      buttonBgColor={isDarkMode ? "#ffffffff" : "#fff"}
      buttonTextColor={isDarkMode ? "#2C3E50" : "#FF8C00"}
      logoText={
        isDarkMode ? (
          <>
            YoloNyang
            <LuCat />
          </>
        ) : (
          <>
            YoloMung
            <LuDog />
          </>
        )
      }
    />
  );
};

export default Navbar;
